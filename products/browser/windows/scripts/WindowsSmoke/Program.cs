using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Optimus.Core;

namespace Optimus.Windows.Smoke;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length is < 2 or > 3 || (args.Length == 3 && args[2] != "--gui")) return 2;
        var report = new SmokeReport();
        try
        {
            if (!OperatingSystem.IsWindows()) throw new SmokeBlocked("Windows execution required.");
            var publication = Path.GetFullPath(args[0]);
            foreach (var relative in new[] { "Optimus.exe", "Optimus.runtimeconfig.json", "Search/Optimus.SearchHost.exe", "Search/Optimus.SearchHost.runtimeconfig.json", "Search/index.json" })
                if (!File.Exists(Path.Combine(publication, relative))) throw new InvalidOperationException("Publication incomplete.");
            ServiceAsync(publication, report).GetAwaiter().GetResult();
            if (args.Length == 3) GuiSmoke.Run(publication, Path.GetDirectoryName(Path.GetFullPath(args[1]))!, report);
            report.Status = "passed";
        }
        catch (SmokeBlocked ex) { report.Status = "blocked"; report.Failure = ex.Message; }
        catch (Exception ex) { report.Status = "failed"; report.Failure = ex is InvalidOperationException ? ex.Message : ex.GetType().Name; }
        finally
        {
            if (report.CleanupFailures.Count != 0) report.Status = "failed";
            File.WriteAllText(args[1], JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        }
        return report.Status == "passed" ? 0 : report.Status == "blocked" ? 3 : 1;
    }

    private static async Task ServiceAsync(string publication, SmokeReport report)
    {
        var temporary = Path.Combine(Path.GetTempPath(), "OptimusSmoke-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(temporary);
        Process? host = null;
        try
        {
            var token = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
            var tokenFile = Path.Combine(temporary, "service.token");
            await File.WriteAllTextAsync(tokenFile, token, Encoding.ASCII);
            // Reservation is released immediately before startup. Any collision fails closed: TLS
            // proves token + SPKI + actual port before nonce or query HTTP bytes are sent.
            var reservation = new TcpListener(IPAddress.Loopback, 0);
            reservation.Start(); var port = ((IPEndPoint)reservation.LocalEndpoint).Port; reservation.Stop();
            var start = new ProcessStartInfo(Path.Combine(publication, "Search", "Optimus.SearchHost.exe"))
            { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = publication, RedirectStandardOutput = true, RedirectStandardError = true };
            foreach (var argument in new[] { "--port", port.ToString(System.Globalization.CultureInfo.InvariantCulture), "--token-file", tokenFile, "--index-file", Path.Combine(publication, "Search", "index.json") }) start.ArgumentList.Add(argument);
            host = Process.Start(start) ?? throw new InvalidOperationException("Owned host did not start.");
            // Drain pipes without persisting host output (could change to contain sensitive data).
            host.OutputDataReceived += (_, _) => { }; host.ErrorDataReceived += (_, _) => { };
            host.BeginOutputReadLine(); host.BeginErrorReadLine();
            var endpoint = new Uri($"https://127.0.0.1:{port}");
            using var client = LocalSearchTransport.CreateClient(token);
            using var startup = new CancellationTokenSource(TimeSpan.FromSeconds(15));
            var ready = false;
            while (!startup.IsCancellationRequested && !host.HasExited)
            {
                try { if (await ProveHealthAsync(client, endpoint, token, startup.Token)) { ready = true; break; } }
                catch (Exception ex) when (ex is HttpRequestException or IOException or OperationCanceledException) { }
                try { await Task.Delay(100, startup.Token); } catch (OperationCanceledException) { break; }
            }
            if (!ready || host.HasExited) throw new InvalidOperationException("Owned host startup/identity proof failed.");
            report.Checks.Add("packaged-host-startup-tls-spki-port-nonce-proof");
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            // An incorrect token must fail in TLS, before even a health HTTP request is sent.
            using (var wrong = LocalSearchTransport.CreateClient(Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32))))
            {
                try { using var unexpected = await wrong.GetAsync(new Uri(endpoint, "/health"), timeout.Token); throw new InvalidOperationException("Wrong-token TLS unexpectedly accepted."); }
                catch (HttpRequestException) { report.Checks.Add("wrong-token-tls-rejected"); }
            }
            using (var denied = await client.GetAsync(new Uri(endpoint, "/search?format=json&q=servicio%20local&scope=index&language=es"), timeout.Token))
                if (denied.StatusCode != HttpStatusCode.Unauthorized) throw new InvalidOperationException("Unauthenticated search was not rejected.");
            using var request = new HttpRequestMessage(HttpMethod.Get, new Uri(endpoint, "/search?format=json&q=servicio%20local&scope=index&language=es"));
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token);
            if (!response.IsSuccessStatusCode) throw new InvalidOperationException("Public index search failed.");
            using var json = JsonDocument.Parse(await ReadBoundedAsync(response, 1024 * 1024, timeout.Token));
            if (!json.RootElement.TryGetProperty("results", out var results) || !results.EnumerateArray().Any(r => r.GetProperty("title").GetString() == "Ayuda Optimus: servicio local y privacidad"))
                throw new InvalidOperationException("Expected public help index result absent.");
            report.Checks.Add("authenticated-public-help-index-result");
            if (host.HasExited) throw new InvalidOperationException("Owned host exited during acceptance.");
        }
        finally
        {
            StopOwned(host, report, "service");
            try { Directory.Delete(temporary, true); report.Checks.Add("isolated-service-temporary-cleanup"); }
            catch { report.CleanupFailures.Add("Isolated service temporary directory cleanup failed."); }
        }
    }

    private static async Task<bool> ProveHealthAsync(HttpClient client, Uri endpoint, string token, CancellationToken cancellationToken)
    {
        using var probe = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken); probe.CancelAfter(500);
        var nonce = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
        using var request = new HttpRequestMessage(HttpMethod.Get, new Uri(endpoint, "/health")); request.Headers.Add("X-Optimus-Nonce", nonce);
        using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, probe.Token);
        if (!response.IsSuccessStatusCode || !response.Headers.TryGetValues("X-Optimus-Proof", out var values)) return false;
        var proofs = values.ToArray();
        if (proofs.Length != 1 || !OptimusSearchService.IsValidToken(proofs[0])) return false;
        var expected = HMACSHA256.HashData(Encoding.ASCII.GetBytes(token), Encoding.ASCII.GetBytes($"OptimusSearch/v1|127.0.0.1:{endpoint.Port}|{nonce}"));
        if (!CryptographicOperations.FixedTimeEquals(expected, Convert.FromHexString(proofs[0]))) return false;
        using var json = JsonDocument.Parse(await ReadBoundedAsync(response, 1024, probe.Token));
        return json.RootElement.GetProperty("name").GetString() == "OptimusSearch" && json.RootElement.GetProperty("version").GetInt32() == 1;
    }

    private static async Task<byte[]> ReadBoundedAsync(HttpResponseMessage response, int limit, CancellationToken cancellationToken)
    {
        if (response.Content.Headers.ContentLength > limit) throw new InvalidOperationException("Response exceeded acceptance limit.");
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        using var output = new MemoryStream(); var buffer = new byte[4096]; int read;
        while ((read = await stream.ReadAsync(buffer, cancellationToken)) != 0)
        { if (output.Length + read > limit) throw new InvalidOperationException("Response exceeded acceptance limit."); await output.WriteAsync(buffer.AsMemory(0, read), cancellationToken); }
        return output.ToArray();
    }

    internal static void StopOwned(Process? process, SmokeReport report, string label)
    {
        if (process is null) return;
        try { if (!process.HasExited) { process.Kill(entireProcessTree: true); if (!process.WaitForExit(5000)) throw new InvalidOperationException(); } report.Checks.Add(label + "-owned-process-stopped"); }
        catch { report.CleanupFailures.Add(label + " owned-process shutdown failed."); }
        finally { process.Dispose(); }
    }
}

internal sealed class SmokeReport
{
    public string Status { get; set; } = "failed";
    public string? Failure { get; set; }
    public string Platform { get; set; } = Environment.OSVersion.VersionString;
    public string? WebView2 { get; set; }
    public string Runtime { get; set; } = Environment.Version.ToString();
    public List<string> Checks { get; } = [];
    public List<string> CreatedGuiDirectories { get; } = [];
    public List<string> CleanupFailures { get; } = [];
}
internal sealed class SmokeBlocked(string message) : Exception(message);
