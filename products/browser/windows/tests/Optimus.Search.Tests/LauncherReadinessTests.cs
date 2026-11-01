using System.Diagnostics;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using Optimus.Core;

internal static class LauncherReadinessTests
{
    public static void Register(Action<string, Func<Task>> test)
    {
        test("owner stdin EOF completes actual host TLS disposal with exit zero", async () =>
        {
            using var host = new OwnedProcessFixture();
            var start = host.StartInfo();
            start.ArgumentList.Add("--owner-stdin"); start.ArgumentList.Add("true");
            var child = host.Start(start);
            await child.WaitReadyAsync();
            await child.Process.StandardInput.WriteLineAsync("ignored owner input");
            await child.Process.StandardInput.FlushAsync();
            using var client = LocalSearchTransport.CreateClient(ReadinessHost.Token);
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(3));
            using var health = await client.GetAsync($"https://127.0.0.1:{child.Port}/health", deadline.Token);
            Require(health.IsSuccessStatusCode, "Actual TLS must create the host signing identity before shutdown");
            new SystemSearchHostProcess(child.Process).Stop();
            Require(child.HasExited && child.ExitCode == 0, "EOF must complete normal Main and certificate disposal");
        });
        if (!OperatingSystem.IsWindows())
        test("normal host shutdown wins while the owned stdin pipe remains open", async () =>
        {
            using var host = new OwnedProcessFixture();
            var start = host.StartInfo();
            start.ArgumentList.Add("--owner-stdin"); start.ArgumentList.Add("true");
            var child = host.Start(start);
            await child.WaitReadyAsync();
            using (var client = LocalSearchTransport.CreateClient(ReadinessHost.Token))
            using (var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(3)))
            using (var health = await client.GetAsync($"https://127.0.0.1:{child.Port}/health", deadline.Token))
                Require(health.IsSuccessStatusCode, "Actual TLS must create the host identity before its normal shutdown");
            var signal = new ProcessStartInfo("/bin/kill") { UseShellExecute = false };
            signal.ArgumentList.Add("-TERM");
            signal.ArgumentList.Add(child.Process.Id.ToString(System.Globalization.CultureInfo.InvariantCulture));
            using (var sender = Process.Start(signal) ?? throw new InvalidOperationException("Could not signal the owned child"))
            {
                await sender.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(3));
                Require(sender.ExitCode == 0, "The signal must reach the exact owned child");
            }
            // Deliberately keep StandardInput open: normal host shutdown must win the race.
            await child.Process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(3));
            Require(child.ExitCode == 0, "Host shutdown must unwind Main and dispose its identity without owner EOF");
        });
        test("owner stdin CLI rejects nonliteral and duplicate options before profile creation", async () =>
        {
            foreach (var arguments in new[] {
                new[] { "--owner-stdin", "false" }, new[] { "--owner-stdin", "True" },
                new[] { "--owner-stdin", "1" }, new[] { "--owner-stdin", "true", "--owner-stdin", "true" },
                new[] { "index", "--owner-stdin", "true" } })
            {
                using var host = new OwnedProcessFixture(createToken: false);
                var start = host.StartInfo();
                start.ArgumentList.Clear();
                foreach (var argument in arguments) start.ArgumentList.Add(argument);
                start.ArgumentList.Add("--token-file"); start.ArgumentList.Add(host.TokenPath);
                var child = host.Start(start, addPort: arguments[0] != "index");
                child.Process.StandardInput.Close();
                await child.Process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5));
                Require(child.ExitCode == 2 && !File.Exists(host.TokenPath), "Invalid owner lifecycle arguments must fail closed before token creation");
            }
        });
        test("actual launcher reconfiguration and close gracefully stop only owned children", async () =>
        {
            using var host = new OwnedProcessFixture();
            var independent = host.Start(host.StartInfo());
            await independent.WaitReadyAsync();
            using var client = new HttpClient(new HealthProof(() => host.OwnedReady));
            using var launcher = host.Launcher(client);
            Require((await launcher.ConnectAsync(null, default)).Error is null && launcher.OwnsProcess, "Real owned host must become ready");
            var first = host.Children.Last();
            launcher.ConfigureUpstream("https://new.example");
            Require(first.HasExited && first.ExitCode == 0 && launcher.ShutdownError is null && !independent.HasExited,
                "Reconfiguration must await normal owned exit without stopping an independent host");
            Require((await launcher.ConnectAsync("https://new.example", default)).Error is null && launcher.OwnsProcess, "Reconfiguration may start a new child after confirmed cleanup");
            var next = host.Children.Last();
            Require(!ReferenceEquals(first, next), "Reconfiguration must start a distinct owned process");
            launcher.Dispose();
            Require(next.HasExited && next.ExitCode == 0 && launcher.ShutdownError is null && !independent.HasExited,
                "Close must await normal disposal of only the current owned child");
        });
        test("forced owned host fallback reports unconfirmed cleanup and blocks restart", async () =>
        {
            using var host = new OwnedProcessFixture(ignoreOwnerInput: true);
            using var client = new HttpClient(new HealthProof(() => host.OwnedReady));
            using var launcher = host.Launcher(client);
            Require((await launcher.ConnectAsync(null, default)).Error is null && launcher.OwnsProcess, "Actual standalone child must become ready before forced fallback");
            var child = host.Children.Single();
            var watch = Stopwatch.StartNew();
            launcher.ConfigureUpstream("https://new.example");
            Require(child.HasExited && !launcher.OwnsProcess && launcher.ShutdownError is not null,
                "A forced exit must retain a visible cleanup failure instead of confirming key deletion");
            Require(watch.Elapsed < TimeSpan.FromSeconds(5), "Graceful wait and forced fallback must remain bounded");
            Require((await launcher.ConnectAsync("https://new.example", default)).Error is not null && host.Children.Count == 1 && launcher.ShutdownError is not null,
                "Unconfirmed cleanup must block reconfiguration and a second process");
        });
        test("already failed owned child cannot be reported as confirmed cleanup", async () =>
        {
            using var host = new OwnedProcessFixture(createToken: false);
            var start = host.StartInfo();
            start.ArgumentList.Add("--owner-stdin"); start.ArgumentList.Add("false");
            var child = host.Start(start);
            await child.Process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5));
            Require(child.ExitCode != 0, "Actual child must fail before cleanup verification");
            var rejected = false;
            try { new SystemSearchHostProcess(child.Process).Stop(); }
            catch (InvalidOperationException) { rejected = true; }
            Require(rejected, "Already exited nonzero processes must retain unconfirmed cleanup");
        });
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

    private sealed class HealthProof(Func<bool>? available = null) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            if (available is not null && !available()) return Task.FromResult(new HttpResponseMessage(HttpStatusCode.ServiceUnavailable));
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

    private sealed class OwnedProcessFixture : IDisposable
    {
        private readonly string directory = Path.Combine(Path.GetTempPath(), "optimus-owner-" + Guid.NewGuid().ToString("N"));
        private readonly bool ignoreOwnerInput;
        private Child? owned;
        public string TokenPath => Path.Combine(directory, "Optimus", "Search", "service.token");
        public List<Child> Children { get; } = [];
        public bool OwnedReady => owned is { Ready: true } && !owned.HasExited;
        public OwnedProcessFixture(bool createToken = true, bool ignoreOwnerInput = false)
        {
            this.ignoreOwnerInput = ignoreOwnerInput;
            Directory.CreateDirectory(Path.Combine(directory, "Search"));
            File.WriteAllText(Path.Combine(directory, "Search", "Optimus.SearchHost.exe"), "test process boundary");
            if (createToken)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(TokenPath)!); File.WriteAllText(TokenPath, ReadinessHost.Token);
                if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(TokenPath, UnixFileMode.UserRead | UnixFileMode.UserWrite);
            }
        }
        public ProcessStartInfo StartInfo()
        {
            var start = new ProcessStartInfo();
            start.ArgumentList.Add("--token-file"); start.ArgumentList.Add(TokenPath);
            return start;
        }
        public Child Start(ProcessStartInfo start, bool addPort = true)
        {
            start.FileName = Path.Combine(AppContext.BaseDirectory, OperatingSystem.IsWindows() ? "Optimus.SearchHost.exe" : "Optimus.SearchHost");
            start.WorkingDirectory = directory;
            start.UseShellExecute = false; start.CreateNoWindow = true;
            start.RedirectStandardInput = true; start.RedirectStandardOutput = true; start.RedirectStandardError = true;
            var reservation = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0);
            reservation.Start(); var port = ((IPEndPoint)reservation.LocalEndpoint).Port; reservation.Stop();
            if (addPort) { start.ArgumentList.Add("--port"); start.ArgumentList.Add(port.ToString(System.Globalization.CultureInfo.InvariantCulture)); }
            var child = new Child(start, port); Children.Add(child); return child;
        }
        public SearchHostLauncher Launcher(HttpClient client) => new(client, directory, directory, start =>
        {
            if (ignoreOwnerInput)
            {
                var index = start.ArgumentList.IndexOf("--owner-stdin");
                if (index >= 0) { start.ArgumentList.RemoveAt(index + 1); start.ArgumentList.RemoveAt(index); }
            }
            owned = Start(start);
            return new SystemSearchHostProcess(owned.Process);
        }, _ => TestTransport.Borrow(client));
        public void Dispose()
        {
            foreach (var child in Children) child.Dispose();
            Directory.Delete(directory, true);
        }
        public sealed class Child : IDisposable
        {
            private readonly TaskCompletionSource ready = new(TaskCreationOptions.RunContinuationsAsynchronously);
            private readonly Process observation;
            public bool HasExited => observation.HasExited;
            public int ExitCode => observation.ExitCode;
            public Process Process { get; }
            public int Port { get; }
            public bool Ready => ready.Task.IsCompletedSuccessfully;
            public Child(ProcessStartInfo start, int port)
            {
                Port = port; Process = new Process { StartInfo = start };
                Process.OutputDataReceived += (_, e) => { if (e.Data == "OptimusSearch ready.") ready.TrySetResult(); };
                Process.ErrorDataReceived += (_, _) => { };
                if (!Process.Start()) throw new InvalidOperationException("Actual child did not start");
                observation = System.Diagnostics.Process.GetProcessById(Process.Id);
                _ = observation.SafeHandle; // Retain an independent handle after the launcher releases its own.
                Process.BeginOutputReadLine(); Process.BeginErrorReadLine();
            }
            public async Task WaitReadyAsync()
            {
                await Task.WhenAny(ready.Task, Process.WaitForExitAsync()).WaitAsync(TimeSpan.FromSeconds(5));
                Require(Ready && !HasExited, "Actual host must publish readiness without an early exit");
            }
            public void Dispose()
            {
                try { if (!HasExited) { observation.Kill(entireProcessTree: true); observation.WaitForExit(1000); } }
                finally { Process.Dispose(); observation.Dispose(); }
            }
        }
    }
}
