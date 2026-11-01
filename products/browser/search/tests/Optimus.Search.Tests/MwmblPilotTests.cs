using System.Diagnostics;
using Optimus.Search;

static class MwmblPilotTests
{
    public static void Register(Action<string, Func<Task>> test, Func<string[], ProcessStartInfo> cliStart)
    {
        test("CLI rejects unknown repeated and conflicting Web provider selection", async () =>
        {
            foreach (var args in new[]
            {
                new[] { "--web-provider", "unknown" },
                new[] { "--web-provider", "Mwmbl" },
                new[] { "--web-provider", "mwmbl", "--web-provider", "mwmbl" },
                new[] { "--web-provider", "mwmbl", "--searx-url", "https://example.org/" },
                new[] { "--web-provider" },
                new[] { "index", "--web-provider", "mwmbl" }
            })
                if (await Optimus.Search.Program.Main(args) != 2) throw new Exception("Invalid provider selection must fail before startup or dispatch.");
        });
        test("CLI explicitly selected Mwmbl pilot starts and closes through its owner pipe", async () =>
        {
            var directory = Path.Combine(Path.GetTempPath(), "optimus-mwmbl-cli-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(directory);
            var start = cliStart(["--port", "0", "--token-file", Path.Combine(directory, "service.token"), "--owner-stdin", "true", "--web-provider", "mwmbl"]);
            start.RedirectStandardInput = true;
            start.Environment.Remove("DOTNET_ROOT");
            using var process = Process.Start(start)!;
            var errors = process.StandardError.ReadToEndAsync();
            try
            {
                var line = await process.StandardOutput.ReadLineAsync().WaitAsync(TimeSpan.FromSeconds(10));
                if (line != "OptimusSearch ready.") throw new Exception("Explicit Mwmbl selection must start the HTTPS host; it was rejected before readiness.");
                process.StandardInput.Close();
                await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5));
                if (process.ExitCode != 0) throw new Exception("Owner EOF must close the Mwmbl host normally.");
            }
            finally
            {
                if (!process.HasExited) { process.StandardInput.Close(); try { await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5)); } catch (TimeoutException) { process.Kill(true); await process.WaitForExitAsync(); } }
                await errors;
                Directory.Delete(directory, true);
            }
        });
    }
}
