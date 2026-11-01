using System.Diagnostics;
using System.Net;
using Optimus.Search;

static class OwnedIdentityTests
{
    public static void Register(Action<string, Func<Task>> test, Func<string[], ProcessStartInfo> cliStart)
    {
        test("owned CLI reports actual bound port and TLS SPKI through its private stdout", async () =>
        {
            var directory = Path.Combine(Path.GetTempPath(), "optimus-owned-identity-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(directory); var path = Path.Combine(directory, "service.token");
            var token = await TokenStore.LoadOrCreateAsync(path);
            var start = cliStart(["--port", "0", "--token-file", path, "--owner-stdin", "true", "--owner-identity-stdout", "true"]);
            start.RedirectStandardInput = true;
            using var process = Process.Start(start)!; var errors = process.StandardError.ReadToEndAsync();
            try
            {
                var line = await process.StandardOutput.ReadLineAsync().WaitAsync(TimeSpan.FromSeconds(10));
                var parts = line?.Split('|');
                Require(parts is { Length: 3 } && parts[0] == "OptimusSearch owner/1" && int.TryParse(parts[1], out var port) && port is > 0 and <= 65535 && TokenStore.IsValid(parts[2]), "The post-bind report must identify the exact listener and public key");
                Require(!line!.Contains(token, StringComparison.Ordinal) && !line.Contains(path, StringComparison.Ordinal), "No profile secret or path in startup stdout");
                using var client = Optimus.Core.LocalSearchTransport.CreateClient(token, parts![2]);
                using var response = await client.GetAsync("https://127.0.0.1:" + parts[1] + "/health");
                Require(response.StatusCode == HttpStatusCode.OK, "Reported key must authenticate the real bound server");
                process.StandardInput.Close(); await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5));
                Require(process.ExitCode == 0, "Owned EOF must dispose normally after identity reporting");
            }
            finally
            {
                if (!process.HasExited) { process.StandardInput.Close(); try { await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5)); } catch (TimeoutException) { process.Kill(true); await process.WaitForExitAsync(); } }
                await errors; Directory.Delete(directory, true);
            }
        });
        test("owned identity output requires the explicit owner pipe", async () =>
        {
            foreach (var args in new[] { new[] { "--owner-identity-stdout", "true" }, new[] { "--owner-identity-stdout", "false" } })
                Require(await Optimus.Search.Program.Main(args) == 2, "Unowned or malformed reporting must fail before starting the server");
        });
    }
    private static void Require(bool valid, string message) { if (!valid) throw new Exception(message); }
}
