using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Threading;
using Optimus.Core;

namespace Optimus.App;

internal static class SearchUiRegression
{
    private const string Query = "café & privacidad #1";
    private const string ResultUrl = "https://fixture.example/result";
    private const string Token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    private static int passed;

    [STAThread]
    private static int Main(string[] args)
    {
        // Explicit disposable-runner opt-in; do not inspect, redirect or remove a real profile.
        if (args.Length != 1 || args[0] != "--disposable-profile-absent" ||
            !OperatingSystem.IsWindows() || !Environment.UserInteractive)
        {
            Console.Error.WriteLine("BLOCKED: disposable interactive Windows runner and explicit opt-in required.");
            return 2;
        }
        var profile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Optimus");
        if (!Absent(profile)) { Console.Error.WriteLine("BLOCKED: default Optimus profile must be absent."); return 2; }
        var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        foreach (var resource in new[] { "OptimusBrand.xaml", "OptimusTheme.xaml" })
            app.Resources.MergedDictionaries.Add(new ResourceDictionary
            { Source = new Uri("/Optimus.Search.Ui.Tests;component/Assets/" + resource, UriKind.Relative) });
        SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext());
        try
        {
            using var inputSource = new HwndSource(new HwndSourceParameters("Optimus regression input source")
            { Width = 1, Height = 1, PositionX = -32000, PositionY = -32000, WindowStyle = 0 });
            foreach (var provider in new[] { SearchProvider.Google, SearchProvider.DuckDuckGo })
                foreach (var enter in new[] { false, true })
                    Test($"legacy-{provider}-{(enter ? "raised-enter" : "raised-click")}-stays-native", () =>
                    {
                        using var fixture = new Fixture(profile, provider);
                        fixture.Window.TestAddress.Text = Query;
                        if (enter)
                        {
                            var key = new KeyEventArgs(Keyboard.PrimaryDevice, inputSource, 0, Key.Enter)
                            { RoutedEvent = Keyboard.KeyDownEvent };
                            fixture.Window.TestAddress.RaiseEvent(key);
                            Check(key.Handled, "Address Enter handler did not handle the event.");
                        }
                        else Click(Find<Button>(fixture.Window, "Ir a la dirección o buscar"));
                        PumpUntil(() => fixture.Results.Children.Count == 1);
                        Check(fixture.Tab.IsSearch && fixture.QueryBox.Text == Query, "Ordinary input did not become native search.");
                        Check(fixture.Transport.Requests == 1 && fixture.Transport.LastScope == "web", "Expected one native Web request.");
                        Check(fixture.Openings.Count == 0, "Ordinary input attempted external navigation.");
                        Check(fixture.Window.TestSettings.SearchProvider == provider, "Legacy preference was changed in memory.");
                        Check(fixture.Store.Save(fixture.Window.TestSettings) is null &&
                            fixture.Store.Load().Settings.SearchProvider == provider, "Legacy preference did not survive settings round-trip.");
                    });

            Test("external-controls-disclosed-collapsed-and-explicit", () =>
            {
                using var fixture = new Fixture(profile);
                Check(fixture.Window.FindName("SearchChoice") is null, "Settings still expose the legacy automatic portal selector.");
                Check(Descendants(fixture.Window).OfType<TextBlock>().Any(t =>
                    t.Text.Contains("La barra de dirección busca dentro de Optimus Search.", StringComparison.Ordinal)), "Settings do not explain the internal search behavior.");
                Check(!fixture.External.IsExpanded, "External section must start collapsed.");
                Check(fixture.External.MinHeight >= 44, "External section lost its minimum target height.");
                var buttons = Descendants(fixture.External).OfType<Button>().ToArray();
                Check(buttons.Length == 2 && buttons.All(b => b.Focusable && b.IsTabStop), "Two focusable portal buttons required.");
                var disclosure = string.Join(" ", Descendants(fixture.External).OfType<TextBlock>().Select(t => t.Text));
                Check(disclosure.Contains("consulta y conexión", StringComparison.Ordinal) &&
                    disclosure.Contains("publicidad", StringComparison.Ordinal) &&
                    disclosure.Contains("no cambia de buscador automáticamente", StringComparison.Ordinal), "External transmission disclosure absent.");
                fixture.QueryBox.Text = Query;
                fixture.External.IsExpanded = true;
                fixture.View.SetScope(OptimusSearchScope.Index);
                Check(fixture.Openings.Count == 0 && fixture.Transport.Requests == 0, "Editing/expanding/selecting a source submitted a request.");
                foreach (var (name, expected) in new[]
                {
                    ("DuckDuckGo", "https://duckduckgo.com/?q=caf%C3%A9%20%26%20privacidad%20%231"),
                    ("Google", "https://www.google.com/search?q=caf%C3%A9%20%26%20privacidad%20%231")
                })
                {
                    var before = fixture.Openings.Count;
                    Click(Find<Button>(fixture.External, "Buscar en " + name + " (externo)"));
                    Check(fixture.Openings.Count == before + 1 && fixture.Openings[^1] == expected, "Explicit button chose or encoded the wrong portal.");
                }
                Check(fixture.Transport.Requests == 0, "Explicit portal action also submitted a native query.");
                fixture.View.Cancel();
                Check(!fixture.External.IsExpanded && fixture.QueryBox.Text.Length == 0, "Cancel did not reset external section/query.");
                var count = fixture.Openings.Count;
                fixture.External.IsExpanded = true;
                Click(buttons[0]);
                Check(fixture.Openings.Count == count, "Empty external query escaped.");
                fixture.View.Disable();
                fixture.QueryBox.Text = Query; // Disable cancels/clears; use a valid query to isolate its guard.
                Click(buttons[1]);
                Check(fixture.Openings.Count == count, "Disabled search accepted external action.");
            });

            foreach (var portal in new[] { "DuckDuckGo", "Google" })
                Test("blocked-" + portal + "-retains-live-native-result", () =>
                {
                    using var fixture = new Fixture(profile);
                    Await(fixture.View.SearchAsync(Query, OptimusSearchScope.Index));
                    var card = fixture.Results.Children.Cast<UIElement>().Single();
                    var resultButton = Find<Button>(fixture.View, "Abrir: Fixture result");
                    fixture.External.IsExpanded = true;
                    Click(Find<Button>(fixture.External, "Buscar en " + portal + " (externo)"));
                    Check(fixture.Window.TestStatus == "Destino bloqueado por una regla local.", "Actual navigation handler did not report its local block.");
                    Check(fixture.Tab.IsSearch && fixture.QueryBox.Text == Query &&
                        fixture.Results.Children.Count == 1 && ReferenceEquals(fixture.Results.Children[0], card), "Blocked portal invalidated native query/results.");
                    var attempts = fixture.Openings.Count;
                    Click(resultButton);
                    Check(fixture.Openings.Count == attempts + 1 && fixture.Openings[^1] == ResultUrl, "Retained result callback became stale.");
                    Check(fixture.Transport.Requests == 1, "Blocked action automatically repeated a search.");
                    Await(fixture.View.SearchAsync("second query", OptimusSearchScope.Index));
                    Check(fixture.Transport.Requests == 2 && fixture.Results.Children.Count == 1, "Native search cannot be reused after block.");
                });

            foreach (var (reply, expected) in new[]
            {
                (Reply.Unconfigured, "no está configurada"),
                (Reply.UpstreamFailure, "No se consultó otro proveedor"),
                (Reply.Timeout, "tiempo límite"),
                (Reply.ConnectionFailure, "No se consultó otro proveedor"),
                (Reply.Empty, "Sin resultados.")
            })
                Test("web-" + reply + "-never-opens-fallback", () =>
                {
                    using var fixture = new Fixture(profile);
                    fixture.Transport.Next = reply;
                    Await(fixture.View.SearchAsync(Query, OptimusSearchScope.Web));
                    Check(fixture.Status.Text.Contains(expected, StringComparison.Ordinal), "Expected native Web error/empty state absent.");
                    Check(fixture.Transport.Requests == 1 && fixture.Openings.Count == 0, "Web failure/empty response invoked a fallback.");
                    Check(fixture.Tab.IsSearch && fixture.Results.Children.Count == 0 && !fixture.External.IsExpanded, "Failure/empty state escaped native search.");
                });

            Test("host-unavailable-does-not-submit-or-open-fallback", () =>
            {
                using var fixture = new Fixture(profile, connectionError: "Fixture host unavailable");
                Await(fixture.View.SearchAsync(Query, OptimusSearchScope.Web));
                Check(fixture.Status.Text == "Fixture host unavailable" && fixture.Transport.Requests == 0 && fixture.Openings.Count == 0,
                    "Failed host connection submitted a query or opened a fallback.");
            });
            Check(Absent(profile), "Regression created the default profile.");
            Console.WriteLine($"PASS: {passed} WPF search handler/state scenarios; no visible GUI, engine, provider or assistive-technology acceptance.");
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine("FAIL: " + error.GetType().Name + ": " + error.Message);
            return 1;
        }
        finally
        {
            // Also cover a constructor/fixture failure before its using declaration completed.
            foreach (var window in app.Windows.OfType<MainWindow>().ToArray()) window.TestDispose();
            app.Shutdown();
        }
    }

    private sealed class Fixture : IDisposable
    {
        private readonly string profile;
        private readonly string directory;
        private readonly HttpClient client;
        internal readonly ScriptedTransport Transport = new();
        internal readonly List<string> Openings = [];
        internal readonly MainWindow Window;
        internal readonly BrowserTab Tab;
        internal readonly OptimusSearchView View;
        internal readonly SettingsStore Store;
        internal TextBox QueryBox => Find<TextBox>(View, "Consulta de Optimus Search");
        internal Expander External => Find<Expander>(View, "Buscar en un portal externo");
        internal StackPanel Results => Field<StackPanel>(View, "_results");
        internal TextBlock Status => Field<TextBlock>(View, "_status");

        internal Fixture(string profile, SearchProvider provider = SearchProvider.Optimus, string? connectionError = null)
        {
            this.profile = profile;
            Check(Absent(profile), "Default profile appeared before fixture construction.");
            directory = Directory.CreateTempSubdirectory("Optimus-search-ui-").FullName;
            MainWindow? createdWindow = null;
            HttpClient? createdClient = null;
            try
            {
            var settingsPath = Path.Combine(directory, "settings.json");
            var settings = new BrowserSettings { SearchProvider = provider,
                PrivacyRules = [new("google.com", PrivacyAction.Block), new("duckduckgo.com", PrivacyAction.Block), new("fixture.example", PrivacyAction.Block)] };
            File.WriteAllText(settingsPath, JsonSerializer.Serialize(settings), new UTF8Encoding(false));
            Store = new(settingsPath);
            var loaded = Store.Load();
            Check(loaded.Error is null && loaded.Settings.SearchProvider == provider, "Legacy fixture did not deserialize.");
            Window = createdWindow = new MainWindow(); // Never Show, Raise Loaded, or initialize WebView2.
            Window.TestPreventPersistence();
            Tab = Window.TestAttach(loaded.Settings,
                _ => Task.FromResult(new SearchHostConnection(new(OptimusSearchScope.Web, OptimusSearchTarget.LocalEndpoint, Token), connectionError)), Openings);
            View = Tab.Host.Children.OfType<OptimusSearchView>().Single();
            client = createdClient = new HttpClient(Transport, disposeHandler: false);
            Func<string, HttpClient> localClient = token =>
            {
                Check(token == Token, "Synthetic request token changed.");
                return new HttpClient(Transport, disposeHandler: false);
            };
            var constructor = typeof(OptimusSearchService).GetConstructor(BindingFlags.Instance | BindingFlags.NonPublic,
                null, [typeof(HttpClient), typeof(Func<string, HttpClient>)], null)
                ?? throw new InvalidOperationException("Expected existing transport seam missing.");
            var service = (OptimusSearchService)constructor.Invoke([client, localClient]);
            var original = Field<SearchSubmissionGate>(View, "_submissions");
            var gate = new SearchSubmissionGate(service, () => !Tab.IsDisposed, CancellationToken.None);
            var field = typeof(OptimusSearchView).GetField("_submissions", BindingFlags.Instance | BindingFlags.NonPublic)
                ?? throw new InvalidOperationException("Expected submission seam missing.");
            field.SetValue(View, gate);
            Check(ReferenceEquals(Field<SearchSubmissionGate>(View, "_submissions"), gate), "Synthetic transport was not installed.");
            original.Dispose();
            Tab.ShowSearch();
            }
            catch
            {
                createdWindow?.TestDispose();
                createdClient?.Dispose();
                Transport.Dispose();
                File.Delete(Path.Combine(directory, "settings.json"));
                Directory.Delete(directory);
                throw;
            }
        }

        public void Dispose()
        {
            try
            {
                Check(!Window.IsLoaded && !Tab.IsFullyInitialized && !Window.TestHostStarted, "Fixture started a product window, engine or host.");
            }
            finally
            {
                Window.TestDispose();
                client.Dispose();
                Transport.Dispose();
                // Only the fixed file created by this fixture; unexpected entries prevent removal.
                File.Delete(Path.Combine(directory, "settings.json"));
                Directory.Delete(directory);
            }
            Check(Absent(profile), "Fixture touched the default profile.");
        }
    }

    private enum Reply { Results, Empty, Unconfigured, UpstreamFailure, Timeout, ConnectionFailure }
    private sealed class ScriptedTransport : HttpMessageHandler
    {
        internal Reply Next;
        internal int Requests;
        internal string? LastScope;
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            Requests++;
            var uri = request.RequestUri ?? throw new InvalidOperationException("Missing request URI.");
            Check(uri.GetLeftPart(UriPartial.Path) == OptimusSearchTarget.LocalEndpoint + "/search" && request.Method == HttpMethod.Get,
                "Unexpected destination/method reached the synthetic transport.");
            LastScope = uri.Query.Contains("&scope=index&", StringComparison.Ordinal) ? "index" : "web";
            Check(uri.Query.Contains("&scope=" + LastScope + "&language=es", StringComparison.Ordinal), "Native scope metadata absent.");
            Check(request.Headers.Authorization?.Scheme == "Bearer" && request.Headers.Authorization.Parameter == Token, "Synthetic local authentication absent.");
            if (Next == Reply.Timeout) return Task.FromException<HttpResponseMessage>(new OperationCanceledException());
            if (Next == Reply.ConnectionFailure) return Task.FromException<HttpResponseMessage>(new HttpRequestException());
            var status = Next switch { Reply.Unconfigured => HttpStatusCode.ServiceUnavailable, Reply.UpstreamFailure => HttpStatusCode.BadGateway, _ => HttpStatusCode.OK };
            var results = Next == Reply.Results
                ? new[] { new { title = "Fixture result", url = ResultUrl, content = "Synthetic local result", source = "fixture" } }
                : [];
            var payload = JsonSerializer.Serialize(new
            {
                optimus = new { version = 1, scope = LastScope, webConfigured = false, indexedDocuments = 1 }, results
            });
            return Task.FromResult(new HttpResponseMessage(status) { Content = new StringContent(payload, Encoding.UTF8, "application/json") });
        }
    }

    private static void Test(string name, Action test) { test(); passed++; Console.WriteLine("PASS " + name); }
    private static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
    private static void Click(Button button) => button.RaiseEvent(new RoutedEventArgs(ButtonBase.ClickEvent));
    private static T Field<T>(object target, string name) => (T)(target.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)?.GetValue(target)
        ?? throw new InvalidOperationException("Expected test observation field missing: " + name));
    private static T Find<T>(DependencyObject root, string name) where T : DependencyObject => Descendants(root).OfType<T>()
        .Single(item => AutomationProperties.GetName(item) == name);
    private static IEnumerable<DependencyObject> Descendants(DependencyObject root)
    {
        yield return root;
        foreach (var child in LogicalTreeHelper.GetChildren(root).OfType<DependencyObject>())
            foreach (var descendant in Descendants(child)) yield return descendant;
    }
    private static void Await(Task task) { PumpUntil(() => task.IsCompleted); task.GetAwaiter().GetResult(); }
    private static void PumpUntil(Func<bool> completed)
    {
        var deadline = Stopwatch.StartNew();
        while (!completed())
        {
            if (deadline.Elapsed > TimeSpan.FromSeconds(3)) throw new InvalidOperationException("WPF fixture completion timeout.");
            var frame = new DispatcherFrame();
            Dispatcher.CurrentDispatcher.BeginInvoke(DispatcherPriority.Background, new Action(() => frame.Continue = false));
            Dispatcher.PushFrame(frame);
        }
    }
    private static bool Absent(string path)
    {
        try { _ = File.GetAttributes(path); return false; }
        catch (FileNotFoundException) { return true; }
        catch (DirectoryNotFoundException) { return true; }
    }
}
