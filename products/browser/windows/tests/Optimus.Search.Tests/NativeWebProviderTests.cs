using System.Diagnostics;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using Optimus.Core;

static class NativeWebProviderTests
{
    public static void Register(Action<string, Func<Task>> test)
    {
        test("a live spawned child cannot authorize another same-profile responder without its channel identity", async () =>
        {
            using var fixture = new HostFixture { MissingIdentity = true };
            var result = await fixture.Launcher.ConnectAsync(new WebSearchConfiguration(WebProvider.Mwmbl), default);
            Require(fixture.Launcher.OwnsProcess && result.GetError(OptimusSearchScope.Index) is null, "Keep the live child and authenticated Index available");
            Require(result.GetError(OptimusSearchScope.Web) is not null, "Profile proof plus a live child is insufficient to disclose a Web query");
        });
        test("owned Web target carries the identity supplied by its private child channel", async () =>
        {
            using var fixture = new HostFixture();
            var result = await fixture.Launcher.ConnectAsync(new WebSearchConfiguration(WebProvider.Mwmbl), default);
            Require(result.GetError(OptimusSearchScope.Web) is null && result.Target.ExpectedSpkiSha256 == HostFixture.OwnerPin, "Carry the owned TLS pin to the actual request, not just readiness");
        });
        test("malformed owned TLS pins never dispatch a local HTTP request", async () =>
        {
            var calls = 0;
            using var client = new HttpClient(new Handler((_, _) => { calls++; return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("{\"query\":\"q\",\"results\":[],\"optimus\":{\"version\":1,\"scope\":\"web\",\"webConfigured\":true,\"indexedDocuments\":0}}") }); }));
            var service = new OptimusSearchService(client, _ => TestTransport.Borrow(client));
            foreach (var pin in new[] { "", new string('g',64), new string('c',63), new string('c',64)+"\n" })
                Require((await service.SearchAsync("q", [], new OptimusSearchTarget(OptimusSearchScope.Web,null,HostFixture.Bearer,pin),default)).Error is not null && calls == 0, "Reject a malformed expected identity before any HTTP disclosure");
        });
        test("native Web arguments select exactly one explicit provider", () =>
        {
            var app = Path.GetTempPath(); const string path = "profile/service.token";
            var none = SearchHostLauncher.CreateStartInfo(app, new WebSearchConfiguration(WebProvider.None, "https://remembered.example/"), path);
            Require(none.ArgumentList.SequenceEqual(new[] { "--token-file", path, "--owner-stdin", "true", "--owner-identity-stdout", "true" }), "Web off must not transmit the remembered server or select another provider");
            var mwmbl = SearchHostLauncher.CreateStartInfo(app, new WebSearchConfiguration(WebProvider.Mwmbl), path);
            Require(mwmbl.ArgumentList.SequenceEqual(new[] { "--token-file", path, "--web-provider", "mwmbl", "--owner-stdin", "true", "--owner-identity-stdout", "true" }), "Explicit Mwmbl must reach the bundled service");
            var searx = SearchHostLauncher.CreateStartInfo(app, new WebSearchConfiguration(WebProvider.Searx, "https://operator.example/"), path);
            Require(searx.ArgumentList.SequenceEqual(new[] { "--token-file", path, "--searx-url", "https://operator.example/", "--owner-stdin", "true", "--owner-identity-stdout", "true" }), "SearXNG and Mwmbl options must never be combined");
            Require(!mwmbl.UseShellExecute && mwmbl.RedirectStandardInput && mwmbl.RedirectStandardOutput && Path.IsPathFullyQualified(mwmbl.FileName), "Keep argument isolation and owned graceful shutdown");
            return Task.CompletedTask;
        });
        test("changing native Web mode restarts only its owned host even without endpoints", async () =>
        {
            using var fixture = new HostFixture();
            foreach (var config in new[] { new WebSearchConfiguration(WebProvider.Mwmbl), new WebSearchConfiguration(WebProvider.Searx, "https://operator.example/"), new WebSearchConfiguration(WebProvider.None), new WebSearchConfiguration(WebProvider.Mwmbl) })
                Require((await fixture.Launcher.ConnectAsync(config, default)).Error is null, "Selected host must become ready");
            Require(fixture.Processes.Count == 4 && fixture.Processes.Take(3).All(p => p.Stopped), "None to Mwmbl must restart although both lack a SearXNG endpoint");
            Require(fixture.Starts[0].ArgumentList.Contains("--web-provider") && !fixture.Starts[2].ArgumentList.Contains("--web-provider"), "Each restart uses its exact effective choice");
        });
        test("Web off keeps the index usable and blocks Web submission", async () =>
        {
            using var fixture = new HostFixture(); var result = await fixture.Launcher.ConnectAsync(new WebSearchConfiguration(WebProvider.None), default);
            Require(result.GetError(OptimusSearchScope.Index) is null && result.GetError(OptimusSearchScope.Web) is not null, "Web off must not block offline Index or allow external submission");
        });
        test("independent service cannot confirm a selected Web source but still serves Index", async () =>
        {
            using var fixture = new HostFixture { Ready = true };
            var result = await fixture.Launcher.ConnectAsync(new WebSearchConfiguration(WebProvider.Mwmbl), default);
            Require(result.Target.BearerToken == HostFixture.Bearer && result.GetError(OptimusSearchScope.Index) is null, "Verified independent service remains available to Index");
            Require(result.GetError(OptimusSearchScope.Web) is not null && fixture.Processes.Count == 0 && !fixture.Launcher.OwnsProcess, "Do not send a Web query to an unconfirmed provider or take over the external host");
        });
        test("native Web reconfiguration invalidates an in-flight identity result", async () =>
        {
            using var fixture = new HostFixture { Ready = true };
            var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            fixture.Probe = async (request, token) => { entered.TrySetResult(); await release.Task.WaitAsync(token); return HostFixture.Proof(request); };
            var pending = fixture.Launcher.ConnectAsync(new WebSearchConfiguration(WebProvider.Mwmbl), default);
            await entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
            fixture.Launcher.ConfigureUpstream(new WebSearchConfiguration(WebProvider.Searx, "https://operator.example/"));
            release.SetResult(); var result = await pending.WaitAsync(TimeSpan.FromSeconds(2));
            Require(result.Error is not null && fixture.Processes.Count == 0, "An identity response for the old configuration cannot become successful readiness");
        });
        test("failed owned shutdown blocks native Web source changes and restart", async () =>
        {
            using var fixture = new HostFixture();
            await fixture.Launcher.ConnectAsync(new WebSearchConfiguration(WebProvider.Mwmbl), default);
            fixture.Processes[0].RefuseStop = true;
            fixture.Launcher.ConfigureUpstream(new WebSearchConfiguration(WebProvider.Searx, "https://operator.example/"));
            var result = await fixture.Launcher.ConnectAsync(new WebSearchConfiguration(WebProvider.None), default);
            Require(result.Error is not null && fixture.Launcher.ShutdownError is not null && fixture.Processes.Count == 1, "No successful new choice or duplicate process after unconfirmed cleanup");
        });
    }

    private static void Require(bool value, string message) { if (!value) throw new Exception(message); }
    private sealed class HostFixture : IDisposable
    {
        public const string Bearer = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
        public const string OwnerPin = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
        private readonly string directory = Path.Combine(Path.GetTempPath(), "optimus-native-web-" + Guid.NewGuid().ToString("N"));
        private readonly HttpClient client;
        public bool Ready;
        public bool MissingIdentity;
        public Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>>? Probe;
        public List<ProcessStartInfo> Starts { get; } = [];
        public List<ProcessFixture> Processes { get; } = [];
        public SearchHostLauncher Launcher { get; }
        public HostFixture()
        {
            Directory.CreateDirectory(Path.Combine(directory, "Optimus", "Search")); Directory.CreateDirectory(Path.Combine(directory, "Search"));
            File.WriteAllText(Path.Combine(directory, "Optimus", "Search", "service.token"), Bearer);
            File.WriteAllText(Path.Combine(directory, "Search", "Optimus.SearchHost.exe"), "test fixture; never executed");
            client = new HttpClient(new Handler(async (request, token) =>
            {
                Require(request.RequestUri!.AbsoluteUri == "https://127.0.0.1:17831/health" && request.Headers.Authorization is null, "Only non-disclosing local readiness probes are expected");
                return Probe is not null ? await Probe(request, token) : Ready ? Proof(request) : new(HttpStatusCode.ServiceUnavailable);
            }));
            Launcher = new SearchHostLauncher(client, directory, directory, start =>
            {
                Starts.Add(start); Ready = true; var process = new ProcessFixture(() => Ready = false, MissingIdentity ? null : OwnerPin); Processes.Add(process); return process;
            }, _ => TestTransport.Borrow(client));
        }
        public static HttpResponseMessage Proof(HttpRequestMessage request)
        {
            var nonce = request.Headers.GetValues("X-Optimus-Nonce").Single();
            var message = "OptimusSearch/v1|127.0.0.1:17831|" + nonce;
            var response = new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("{\"name\":\"OptimusSearch\",\"version\":1}", Encoding.UTF8, "application/json") };
            response.Headers.Add("X-Optimus-Proof", Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.ASCII.GetBytes(Bearer), Encoding.ASCII.GetBytes(message))));
            return response;
        }
        public void Dispose()
        {
            foreach (var process in Processes) process.RefuseStop = false;
            Launcher.Dispose(); client.Dispose(); Directory.Delete(directory, true);
        }
    }
    private sealed class ProcessFixture(Action stopped, string? ownerPin) : ISearchHostProcess
    {
        public bool Stopped { get; private set; }
        public bool RefuseStop;
        public bool HasExited => Stopped;
        public Task<string?> ReadOwnerSpkiAsync(CancellationToken token) => Task.FromResult(ownerPin);
        public void Stop() { if (RefuseStop) throw new InvalidOperationException("Expected failed cleanup"); Stopped = true; stopped(); }
        public void Dispose() { }
    }
    private sealed class Handler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send) : HttpMessageHandler
    { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token) => send(request, token); }
}
