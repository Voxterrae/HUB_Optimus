using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Interop;
using System.Windows.Media.Imaging;

namespace Optimus.Windows.Smoke;

internal static class GuiSmoke
{
    internal static void Run(string publication, string evidence, SmokeReport report)
    {
        // A dedicated disposable Windows user/VM is required. Never inspect an existing profile.
        var profile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Optimus");
        if (!Absent(profile)) throw new SmokeBlocked("GUI requires absent default Optimus profiles; use a clean disposable Windows user/VM.");
        if (!Environment.UserInteractive || Process.GetCurrentProcess().SessionId == 0) throw new SmokeBlocked("Interactive desktop unavailable; GUI/UIAutomation/capture blocked.");
        var guard = new TcpListener(IPAddress.Loopback, 17831);
        try { guard.Start(); } catch (SocketException) { throw new SmokeBlocked("Default GUI search port busy; existing service untouched."); } finally { guard.Stop(); }
        report.WebView2 = CheckWebViewRuntime(publication);
        Process? app = null;
        using var page = new LocalPage();
        try
        {
            // Recheck immediately before launch. No token/profile reads or environment redirection.
            if (!Absent(profile)) throw new SmokeBlocked("Default profile appeared before launch; GUI blocked.");
            app = Process.Start(new ProcessStartInfo(Path.Combine(publication, "Optimus.exe")) { UseShellExecute = false, WorkingDirectory = publication })
                ?? throw new InvalidOperationException("Packaged GUI did not start.");
            Wait(() => { app.Refresh(); return app.MainWindowHandle != 0 && !app.HasExited; }, "Owned GUI window unavailable.", true);
            var window = AutomationElement.FromHandle(app.MainWindowHandle);
            AutomationElement Find(string name) => FindOwned(window, name);
            void Invoke(string name) => ((InvokePattern)Find(name).GetCurrentPattern(InvokePattern.Pattern)).Invoke();
            void Set(string name, string value) => ((ValuePattern)Find(name).GetCurrentPattern(ValuePattern.Pattern)).SetValue(value);
            FindOwned(window, "Consulta de inicio de Optimus", blocked: true); report.Checks.Add("gui-native-home-uia");
            // Home's public index entry opens the real native search surface in Index scope.
            Invoke("Tu índice"); Set("Consulta de Optimus Search", "servicio local"); Invoke("Buscar en la fuente elegida");
            Find("Abrir: Ayuda Optimus: servicio local y privacidad"); report.Checks.Add("gui-index-public-help-result");
            Invoke("Inicio");
            Invoke("✧  Ayuda"); Set("Pregunta a la guía local", "permisos"); Invoke("Consultar guía");
            Wait(() => ((ValuePattern)Find("Respuesta de la guía local").GetCurrentPattern(ValuePattern.Pattern)).Current.Value.Contains("Guía local basada en reglas", StringComparison.Ordinal), "Local guide response unavailable.");
            Invoke("Cerrar ayuda"); report.Checks.Add("gui-local-guide-response");
            // Navigation is loopback only; server receipt plus UIA page heading prove rendering.
            Set("Dirección o búsqueda", page.Address); Invoke("Ir a la dirección o buscar");
            Wait(() => page.Received, "Owned loopback page was not requested.");
            Find("Optimus isolated smoke page"); report.Checks.Add("gui-loopback-navigation-rendered");
            Invoke("Nueva pestaña privada"); Find("Privado · no se restauran direcciones"); report.Checks.Add("gui-private-tab");
            // Sidebar is a native button; no keyboard injection or global mouse action.
            Invoke("⚙  Ajustes"); Find("Tamaño y zoom"); Invoke("Cerrar ajustes"); report.Checks.Add("gui-settings-open-close");
            Capture(app.MainWindowHandle, Path.Combine(evidence, "owned-window.png")); report.Checks.Add("gui-own-window-capture");
            ((WindowPattern)window.GetCurrentPattern(WindowPattern.Pattern)).Close();
            if (!app.WaitForExit(15000)) throw new InvalidOperationException("GUI graceful close did not finish.");
            report.Checks.Add("gui-graceful-close");
        }
        finally
        {
            Program.StopOwned(app, report, "gui");
            // Retain this fresh user's GUI state for diagnosis. The harness never recursively
            // deletes default profile paths; discard the disposable user/VM after the run.
            foreach (var relative in new[] { "private-pilot", "Search" })
                if (Directory.Exists(Path.Combine(profile, relative))) report.CreatedGuiDirectories.Add("Optimus/" + relative);
            report.Checks.Add("gui-default-profile-retained-discard-test-user");
        }
    }

    private static bool Absent(string path)
    {
        try { _ = File.GetAttributes(path); return false; }
        catch (FileNotFoundException) { return true; }
        catch (DirectoryNotFoundException) { return true; }
    }

    private static string CheckWebViewRuntime(string publication)
    {
        var loader = new[] { Path.Combine(publication, "WebView2Loader.dll"), Path.Combine(publication, "runtimes", "win-x64", "native", "WebView2Loader.dll") }.FirstOrDefault(File.Exists);
        if (loader is null) throw new SmokeBlocked("Packaged WebView2 loader absent; no runtime installed by diagnostics.");
        nint library = 0, version = 0;
        try
        {
            library = NativeLibrary.Load(loader);
            var query = Marshal.GetDelegateForFunctionPointer<RuntimeVersion>(NativeLibrary.GetExport(library, "GetAvailableCoreWebView2BrowserVersionString"));
            if (query(0, out version) != 0 || version == 0) throw new SmokeBlocked("WebView2 Evergreen runtime unavailable; install only by explicit operator choice.");
            var runtime = Marshal.PtrToStringUni(version);
            if (string.IsNullOrWhiteSpace(runtime)) throw new SmokeBlocked("WebView2 runtime version unavailable.");
            return runtime;
        }
        catch (Exception ex) when (ex is DllNotFoundException or BadImageFormatException or EntryPointNotFoundException)
        { throw new SmokeBlocked("WebView2 runtime preflight unavailable."); }
        finally { if (version != 0) Marshal.FreeCoTaskMem(version); if (library != 0) NativeLibrary.Free(library); }
    }
    [UnmanagedFunctionPointer(CallingConvention.StdCall)] private delegate int RuntimeVersion(nint browserFolder, out nint version);

    private static AutomationElement FindOwned(AutomationElement root, string name, bool blocked = false)
    {
        AutomationElement? found = null;
        Wait(() =>
        {
            found = root.FindFirst(TreeScope.Descendants, new AndCondition(new PropertyCondition(AutomationElement.NameProperty, name), new PropertyCondition(AutomationElement.IsOffscreenProperty, false)));
            return found is not null;
        }, "Required owned-window UIAutomation control unavailable.", blocked);
        return found!;
    }
    private static void Wait(Func<bool> predicate, string failure, bool blocked = false)
    {
        var deadline = Stopwatch.StartNew();
        while (deadline.Elapsed < TimeSpan.FromSeconds(20))
        {
            if (predicate()) return;
            Thread.Sleep(100);
        }
        if (blocked) throw new SmokeBlocked(failure);
        throw new InvalidOperationException(failure);
    }

    private static void Capture(nint hwnd, string path)
    {
        if (!GetClientRect(hwnd, out var bounds) || bounds.Right <= 0 || bounds.Bottom <= 0) throw new SmokeBlocked("Owned-window capture unavailable.");
        var dc = GetDC(hwnd); var memory = CreateCompatibleDC(dc); var bitmap = CreateCompatibleBitmap(dc, bounds.Right, bounds.Bottom); var previous = SelectObject(memory, bitmap);
        try
        {
            if (!PrintWindow(hwnd, memory, 3)) throw new SmokeBlocked("Owned-window capture unavailable.");
            var source = Imaging.CreateBitmapSourceFromHBitmap(bitmap, 0, Int32Rect.Empty, BitmapSizeOptions.FromEmptyOptions());
            // Reject a uniformly blank capture rather than treating an unavailable desktop as proof.
            var pixels = new byte[checked(source.PixelWidth * source.PixelHeight * 4)]; source.CopyPixels(pixels, source.PixelWidth * 4, 0);
            var diverse = false; for (var i = 4; i < pixels.Length; i += 4) if (pixels[i] != pixels[0] || pixels[i + 1] != pixels[1] || pixels[i + 2] != pixels[2]) { diverse = true; break; }
            if (!diverse) throw new SmokeBlocked("Owned-window capture blank; capture blocked.");
            var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(source)); using var output = File.Create(path); png.Save(output);
        }
        finally { SelectObject(memory, previous); DeleteObject(bitmap); DeleteDC(memory); ReleaseDC(hwnd, dc); }
    }
    [StructLayout(LayoutKind.Sequential)] private struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] private static extern bool GetClientRect(nint hwnd, out Rect rect);
    [DllImport("user32.dll")] private static extern nint GetDC(nint hwnd);
    [DllImport("user32.dll")] private static extern int ReleaseDC(nint hwnd, nint dc);
    [DllImport("user32.dll")] private static extern bool PrintWindow(nint hwnd, nint dc, uint flags);
    [DllImport("gdi32.dll")] private static extern nint CreateCompatibleDC(nint dc);
    [DllImport("gdi32.dll")] private static extern nint CreateCompatibleBitmap(nint dc, int width, int height);
    [DllImport("gdi32.dll")] private static extern nint SelectObject(nint dc, nint obj);
    [DllImport("gdi32.dll")] private static extern bool DeleteObject(nint obj);
    [DllImport("gdi32.dll")] private static extern bool DeleteDC(nint dc);

    private sealed class LocalPage : IDisposable
    {
        private readonly TcpListener listener = new(IPAddress.Loopback, 0);
        private readonly CancellationTokenSource stop = new();
        private readonly Task serving;
        private volatile bool received;
        public bool Received => received;
        public string Address { get; }
        public LocalPage()
        {
            listener.Start(); Address = $"http://127.0.0.1:{((IPEndPoint)listener.LocalEndpoint).Port}/";
            serving = ServeAsync();
        }
        private async Task ServeAsync()
        {
            try
            {
                while (!stop.IsCancellationRequested)
                {
                    using var client = await listener.AcceptTcpClientAsync(stop.Token); using var stream = client.GetStream();
                    using var deadline = CancellationTokenSource.CreateLinkedTokenSource(stop.Token); deadline.CancelAfter(2000);
                    var input = new byte[4096]; var count = await stream.ReadAsync(input, deadline.Token);
                    if (count == 0) continue;
                    received = true;
                    var body = Encoding.UTF8.GetBytes("<!doctype html><html><title>Optimus smoke</title><h1>Optimus isolated smoke page</h1><p>Loopback only.</p></html>");
                    var header = Encoding.ASCII.GetBytes($"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {body.Length}\r\nConnection: close\r\n\r\n");
                    await stream.WriteAsync(header, deadline.Token); await stream.WriteAsync(body, deadline.Token);
                }
            }
            catch (Exception ex) when (ex is OperationCanceledException or SocketException or IOException) { }
        }
        public void Dispose() { stop.Cancel(); listener.Stop(); serving.GetAwaiter().GetResult(); stop.Dispose(); }
    }
}
