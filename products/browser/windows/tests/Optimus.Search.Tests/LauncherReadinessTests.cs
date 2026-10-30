using System.Diagnostics;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using Optimus.Core;

internal static class LauncherReadinessTests
{
    public static void Register(Action<string, Func<Task>> test)
    {
        test("fresh-profile launcher accepts readiness after 2.5 seconds before its global deadline", async () =>
        {
            using var host = new ReadinessHost(TimeSpan.FromMilliseconds(2500));
            using var client = new HttpClient(new HealthProof());
            using var launcher = host.Launcher(client);
            Require(!File.Exists(host.TokenPath), "Fresh profile must have no token before startup");
            var watch = Stopwatch.StartNew();
            var connection = await launcher.ConnectAsync(null, default).WaitAsync(TimeSpan.FromSeconds(6));
            Require(connection.Error is null && connection.Target.BearerToken == ReadinessHost.Token && launcher.OwnsProcess,
                "A host ready after 2.5 seconds must connect and remain owned within the four-second deadline");
            Require(watch.Elapsed >= TimeSpan.FromMilliseconds(2500) && watch.Elapsed < TimeSpan.FromSeconds(4),
                "Readiness must use the existing deadline rather than a shorter probe cap");
            launcher.Dispose();
            Require(host.HasExited && !launcher.OwnsProcess && launcher.ShutdownError is null,
                "Successful delayed startup must preserve owned-host cleanup");
        });
        test("fresh-profile launcher times out unready host at its global deadline and cleans up ownership", async () =>
        {
            using var host = new ReadinessHost(null);
            using var client = new HttpClient(new HealthProof());
            using var launcher = host.Launcher(client);
            var watch = Stopwatch.StartNew();
            var connection = await launcher.ConnectAsync(null, default).WaitAsync(TimeSpan.FromSeconds(6));
            Require(connection.Error is not null && connection.Target.BearerToken is null,
                "An unready host must return a visible failure without credentials");
            // Allow scheduler latency while rejecting the former approximately two-second cutoff.
            Require(watch.Elapsed >= TimeSpan.FromMilliseconds(3500) && watch.Elapsed < TimeSpan.FromSeconds(5),
                "Missing readiness must consume the four-second deadline and remain bounded");
            Require(host.HasExited && !launcher.OwnsProcess && launcher.ShutdownError is null && !File.Exists(host.TokenPath),
                "Deadline must terminate only the owned startup without retaining its token or handle");
        });
        test("fresh-profile caller cancellation interrupts readiness and releases only owned host", async () =>
        {
            using var host = new ReadinessHost(null);
            using var client = new HttpClient(new HealthProof());
            using var launcher = host.Launcher(client);
            using var cancel = new CancellationTokenSource();
            var pending = launcher.ConnectAsync(null, cancel.Token);
            await host.Started.Task.WaitAsync(TimeSpan.FromSeconds(1));
            cancel.Cancel();
            var canceled = false;
            try { await pending.WaitAsync(TimeSpan.FromSeconds(1)); }
            catch (OperationCanceledException) { canceled = true; }
            Require(canceled && host.HasExited && !launcher.OwnsProcess && launcher.ShutdownError is null,
                "Caller cancellation must propagate and terminate the owned startup");
        });
    }

    private static void Require(bool value, string message) { if (!value) throw new Exception(message); }

    // Only process creation is replaced. Real launcher polling, profile IO, nonce/HMAC verification,
    // deadline and cleanup run unchanged; production TLS transport remains covered by IdentityProofTests.
    private sealed class ReadinessHost : ISearchHostProcess
    {
        public const string Token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        private readonly string directory = Path.Combine(Path.GetTempPath(), "optimus-readiness-" + Guid.NewGuid());
        private readonly CancellationTokenSource lifetime = new();
        private readonly TimeSpan? delay;
        private Task? publication;
        private bool disposed;
        public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public string TokenPath => Path.Combine(directory, "Optimus", "Search", "service.token");
        public bool HasExited { get; private set; }

        public ReadinessHost(TimeSpan? delay)
        {
            this.delay = delay;
            Directory.CreateDirectory(Path.Combine(directory, "Search"));
            File.WriteAllText(Path.Combine(directory, "Search", "Optimus.SearchHost.exe"), "test process boundary");
        }

        public SearchHostLauncher Launcher(HttpClient client) => new(client, directory, directory, _ =>
        {
            Require(!Started.Task.IsCompleted, "Launcher must start exactly one owned host");
            Started.SetResult();
            if (delay is { } wait) publication = PublishTokenAsync(wait);
            return this;
        }, _ => TestTransport.Borrow(client));

        private async Task PublishTokenAsync(TimeSpan wait)
        {
            try
            {
                await Task.Delay(wait, lifetime.Token);
                Directory.CreateDirectory(Path.GetDirectoryName(TokenPath)!);
                await File.WriteAllTextAsync(TokenPath, Token, lifetime.Token);
            }
            catch (OperationCanceledException) when (lifetime.IsCancellationRequested) { }
        }

        public void Stop() { HasExited = true; lifetime.Cancel(); }
        public void Dispose()
        {
            if (disposed) return;
            Stop();
            publication?.GetAwaiter().GetResult();
            if (Directory.Exists(directory)) Directory.Delete(directory, true);
            lifetime.Dispose();
            disposed = true;
        }
    }

    private sealed class HealthProof : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            Require(request.RequestUri?.AbsoluteUri == "https://127.0.0.1:17831/health" && request.Headers.Authorization is null,
                "Readiness must send only credential-free health to the fixed local endpoint");
            var nonce = request.Headers.GetValues("X-Optimus-Nonce").Single();
            var proof = HMACSHA256.HashData(Encoding.ASCII.GetBytes(ReadinessHost.Token),
                Encoding.ASCII.GetBytes($"OptimusSearch/v1|127.0.0.1:17831|{nonce}"));
            var response = new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent("{\"name\":\"OptimusSearch\",\"version\":1}", Encoding.UTF8, "application/json")
            };
            response.Headers.Add("X-Optimus-Proof", Convert.ToHexStringLower(proof));
            return Task.FromResult(response);
        }
    }
}
