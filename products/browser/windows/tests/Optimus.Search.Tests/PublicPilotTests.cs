using System.Diagnostics;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using Optimus.Core;
using Optimus.Search;

internal static class PublicPilotTests
{
    internal static void Register(Action<string, Func<Task>> test)
    {
        test("pilot imports actual fixed public corpus with real CLI and restores default selection", async () => {
            using var fixture = new PilotFixture();
            using var pilot = fixture.Pilot( ImportAsync);
            Check((await fixture.Launcher.ConnectAsync(null, default)).Error is null, "Default owned host ready");
            var changed = await pilot.SetActiveAsync(true, default);
            Check(changed.Error is null && changed.Active && pilot.IsActive, "Pilot activation must succeed");
            var selected = fixture.IndexPath;
            Check(selected is not null && Path.IsPathFullyQualified(selected), "Explicit imported index selected");
            var index = new LocalSearchIndex(await CatalogStore.LoadAsync(selected!));
            Check(index.DocumentCount == 8 && index.Search("contraste")[0].Url.Contains("support.microsoft.com"), "Actual CLI output resolves public topic");
            Check(index.Search("trilobites").Count == 0, "Genuine unrelated empty result");
            var restored = await pilot.SetActiveAsync(false, default);
            Check(restored.Error is null && !restored.Active && !pilot.IsActive && fixture.IndexPath is null, "Prior default restored");
            Check(!File.Exists(selected), "Only temporary pilot output removed after successful restore");
        });
        test("invalid public asset reload preserves working pilot and emits no path or content", async () => {
            using var fixture = new PilotFixture(); using var pilot = fixture.Pilot( ImportAsync);
            Check((await pilot.SetActiveAsync(true, default)).Error is null, "Initial pilot loaded");
            var previous = fixture.IndexPath; var starts = fixture.Starts;
            await File.WriteAllTextAsync(fixture.CatalogPath, "PRIVATE_SENTINEL");
            var changed = await pilot.SetActiveAsync(true, default);
            Check(changed.Error is not null && changed.Active && pilot.IsActive, "Invalid reload preserves pilot selection");
            Check(fixture.IndexPath == previous && fixture.Starts == starts && File.Exists(previous), "No service restart or old index overwrite");
            Check(!changed.Error!.Contains(fixture.Root) && !changed.Error.Contains("PRIVATE_SENTINEL"), "Generic diagnostics");
        });
        test("pilot real CLI import failure preserves previous service and selection", async () => {
            using var fixture = new PilotFixture();
            await fixture.Launcher.ConnectAsync(null, default); var starts = fixture.Starts;
            using var pilot = fixture.Pilot( async (start, token) => {
                var args = start.ArgumentList.ToArray();
                await File.WriteAllTextAsync(args[Array.IndexOf(args, "--input") + 1], "invalid", token);
                return await ImportAsync(start, token);
            });
            var changed = await pilot.SetActiveAsync(true, default);
            Check(changed.Error is not null && !changed.Active && !pilot.IsActive, "Actual importer exit2 cannot activate pilot");
            Check(fixture.Starts == starts && fixture.IndexPath is null, "Original service not stopped for failed import");
        });
        test("pilot refuses a healthy independent host without starting or stopping it", async () => {
            using var fixture = new PilotFixture { Independent = true };
            using var pilot = fixture.Pilot( ImportAsync);
            var changed = await pilot.SetActiveAsync(true, default);
            Check(changed.Error is not null && !changed.Active && fixture.Starts == 0 && fixture.Stops == 0, "Independent host untouched and selection unchanged");
        });
        test("pilot failed normal shutdown preserves previous selection and retained owned handle", async () => {
            using var fixture = new PilotFixture(); await fixture.Launcher.ConnectAsync(null, default);
            fixture.RefuseStop = true;
            using var pilot = fixture.Pilot( ImportAsync);
            var changed = await pilot.SetActiveAsync(true, default);
            Check(changed.Error is not null && !changed.Active && fixture.IndexPath is null && fixture.Starts == 1 && fixture.Launcher.OwnsProcess, "No false reconfiguration after failed cleanup");
            fixture.RefuseStop = false;
        });
        test("pilot failed authenticated new host startup rolls back previous selection", async () => {
            using var fixture = new PilotFixture(); await fixture.Launcher.ConnectAsync(null, default);
            fixture.RejectPilot = true;
            using var pilot = fixture.Pilot( ImportAsync);
            var changed = await pilot.SetActiveAsync(true, default);
            Check(changed.Error is not null && !changed.Active && !pilot.IsActive, "Failed readiness cannot publish pilot state");
            Check((await fixture.Launcher.ConnectAsync(null, default)).Error is null && fixture.IndexPath is null, "Following search restarts prior configuration");
        });
        test("unconfirmed candidate host cleanup retains its index until normal shutdown is confirmed", async () => {
            using var fixture = new PilotFixture(); await fixture.Launcher.ConnectAsync(null, default);
            fixture.RejectPilot = true; fixture.RefusePilotStop = true;
            using var pilot = fixture.Pilot( ImportAsync);
            var changed = await pilot.SetActiveAsync(true, default); var retained = fixture.IndexPath;
            Check(changed.Error is not null && !changed.Active && fixture.Launcher.OwnsProcess && fixture.Launcher.ShutdownError is not null, "Unconfirmed cleanup cannot claim activation");
            Check(retained is not null && File.Exists(retained), "Candidate files remain while owned host cleanup is unconfirmed");
            fixture.RefusePilotStop = false; fixture.Launcher.Dispose(); pilot.Dispose();
            Check(!File.Exists(retained), "Confirmed normal shutdown permits owned workspace cleanup");
        });
        test("cancellation after real import cannot publish a late pilot selection", async () => {
            using var fixture = new PilotFixture(); using var cancel = new CancellationTokenSource();
            using var pilot = fixture.Pilot( async (start, token) => {
                var code = await ImportAsync(start, token); cancel.Cancel(); return code;
            });
            var changed = await pilot.SetActiveAsync(true, cancel.Token);
            Check(changed.Error is not null && !changed.Active && fixture.Starts == 0 && fixture.IndexPath is null, "Late import completion remains unselected");
        });
        test("serialized load and restore leave the original catalog selected", async () => {
            using var fixture = new PilotFixture();
            var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var release = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            using var pilot = fixture.Pilot( async (start, token) => {
                entered.SetResult(); await release.Task.WaitAsync(token); return await ImportAsync(start, token);
            });
            var load = pilot.SetActiveAsync(true, default); await entered.Task.WaitAsync(TimeSpan.FromSeconds(2));
            var restore = pilot.SetActiveAsync(false, default); Check(!restore.IsCompleted, "Restore serializes with pending import");
            release.SetResult(); Check((await load).Error is null && (await restore).Error is null && !pilot.IsActive && fixture.IndexPath is null, "Final selection is deterministic");
        });
    }
    private static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
    private static async Task<int> ImportAsync(ProcessStartInfo source, CancellationToken token)
    {
        var start = new ProcessStartInfo("dotnet") { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true };
        start.ArgumentList.Add(typeof(SearchServer).Assembly.Location);
        foreach (var arg in source.ArgumentList) start.ArgumentList.Add(arg);
        using var process = Process.Start(start)!;
        try { await process.WaitForExitAsync(token); return process.ExitCode; }
        finally { if (!process.HasExited) { process.Kill(true); await process.WaitForExitAsync(); } }
    }
    private sealed class PilotFixture : IDisposable
    {
        internal string Root { get; } = Directory.CreateTempSubdirectory("optimus-pilot-test-").FullName;
        internal string CatalogPath => Path.Combine(Root, "Search", "catalog", "public-pilot-v0.1.json");
        internal SearchHostLauncher Launcher { get; }
        internal string? IndexPath;
        internal int Starts, Stops;
        internal bool Independent, RefuseStop, RefusePilotStop, RejectPilot;
        private FakeProcess? current;
        private readonly List<PublicPilotCatalog> pilots = [];
        internal PublicPilotCatalog Pilot(Func<ProcessStartInfo, CancellationToken, Task<int>> importer) { var pilot = new PublicPilotCatalog(Launcher, Root, importer); pilots.Add(pilot); return pilot; }
        private readonly HttpClient client;
        private const string Bearer = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        internal PilotFixture()
        {
            Directory.CreateDirectory(Path.GetDirectoryName(CatalogPath)!);
            foreach (var file in new[] { "public-pilot-v0.1.json", "public-pilot-v0.1.provenance.json" })
                File.Copy(Path.Combine(AppContext.BaseDirectory, "pilot-assets", file), Path.Combine(Path.GetDirectoryName(CatalogPath)!, file));
            File.WriteAllText(Path.Combine(Root, "Search", "Optimus.SearchHost.exe"), "owned OS-boundary fixture");
            var tokenPath = Path.Combine(Root, "Optimus", "Search", "service.token"); Directory.CreateDirectory(Path.GetDirectoryName(tokenPath)!); File.WriteAllText(tokenPath, Bearer);
            client = new HttpClient(new Health(this));
            Launcher = new SearchHostLauncher(client, Root, Root, start => {
                Starts++; var args = start.ArgumentList.ToArray(); var i = Array.IndexOf(args, "--index-file"); IndexPath = i < 0 ? null : args[i + 1];
                current = new FakeProcess(this); return current;
            }, _ => TestTransport.Borrow(client));
        }
        public void Dispose() { RefuseStop = false; RefusePilotStop = false; Launcher.Dispose(); foreach (var pilot in pilots) pilot.Dispose(); client.Dispose(); Directory.Delete(Root, true); }
        private sealed class FakeProcess(PilotFixture owner) : ISearchHostProcess
        {
            public bool HasExited { get; private set; }
            public void Stop() { if (owner.RefuseStop || owner.RefusePilotStop && owner.IndexPath is not null) throw new InvalidOperationException(); owner.Stops++; HasExited = true; owner.current = null; }
            public void Dispose() { }
        }
        private sealed class Health(PilotFixture owner) : HttpMessageHandler
        {
            protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
            {
                if (!(owner.Independent || owner.current is { HasExited: false }) || owner.RejectPilot && owner.IndexPath is not null)
                    return Task.FromResult(new HttpResponseMessage(HttpStatusCode.ServiceUnavailable));
                var nonce = request.Headers.GetValues("X-Optimus-Nonce").Single();
                var message = $"OptimusSearch/v1|127.0.0.1:{request.RequestUri!.Port}|{nonce}";
                var proof = Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.ASCII.GetBytes(Bearer), Encoding.ASCII.GetBytes(message)));
                var reply = new HttpResponseMessage(HttpStatusCode.OK) { Content = new StringContent("{\"name\":\"OptimusSearch\",\"version\":1}") };
                reply.Headers.Add("X-Optimus-Proof", proof); return Task.FromResult(reply);
            }
        }
    }
}
