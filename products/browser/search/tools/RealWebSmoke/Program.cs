using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Optimus.Core;

internal static class Program
{
    private const int HostPort = 17831;
    private const string Upstream = "http://127.0.0.1:18888";
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    private static readonly Case[] Cases = [new("python", "Python programming", "python", ["python.org"]), new("firefox", "Mozilla Firefox", "firefox", ["mozilla.org", "firefox.com"])];

    public static async Task<int> Main(string[] args)
    {
        if (args.SequenceEqual(["--self-test"], StringComparer.Ordinal)) return SelfTest();
        var report = new Report();
        Process? host = null;
        string? profile = null;
        bool profileCreated = false;
        Task? stdout = null, stderr = null;
        int outputOverflow = 0;
        var stage = "arguments";
        using var lifetime = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        using var interrupt = OperatingSystem.IsWindows() ? null : PosixSignalRegistration.Create(PosixSignal.SIGINT, signal => { signal.Cancel = true; lifetime.Cancel(); });
        using var terminate = OperatingSystem.IsWindows() ? null : PosixSignalRegistration.Create(PosixSignal.SIGTERM, signal => { signal.Cancel = true; lifetime.Cancel(); });
        try
        {
            var values = ParseArguments(args);
            var source = values["--source"];
            var hostPath = values["--host"];
            profile = values["--profile"];
            if (!Regex.IsMatch(source, "\\A[0-9a-f]{40}\\z", RegexOptions.CultureInvariant)
                || !Path.IsPathFullyQualified(hostPath) || !File.Exists(hostPath) || Path.GetFileName(hostPath) != "Optimus.SearchHost.dll"
                || !Path.IsPathFullyQualified(profile) || !IsOwnedTemporaryPath(profile)
                || File.Exists(profile) || Directory.Exists(profile)) throw new Blocked("invalid-arguments");
            report.Source = source;

            stage = "provenance";
            if (!HasSource(Assembly.GetExecutingAssembly(), report.Source) || !HasSource(typeof(OptimusSearchService).Assembly, report.Source)
                || !EndsWithSource(FileVersionInfo.GetVersionInfo(hostPath).ProductVersion, report.Source)) throw new Blocked("source-mismatch");
            report.ProvenanceVerified = true;
            stage = "host-preflight";
            using (var reservation = new TcpListener(IPAddress.Loopback, HostPort)) { reservation.Start(); }
            Directory.CreateDirectory(profile);
            profileCreated = true;
            if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(profile, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
            var tokenPath = Path.Combine(profile, "service.token");
            var start = new ProcessStartInfo(DotnetHost())
            {
                UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = profile,
                RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true
            };
            start.Environment.Clear();
            start.Environment["PATH"] = Environment.GetEnvironmentVariable("PATH") ?? "/usr/bin:/bin";
            var dotnetRoot = Environment.GetEnvironmentVariable("DOTNET_ROOT");
            if (!string.IsNullOrEmpty(dotnetRoot)) start.Environment["DOTNET_ROOT"] = dotnetRoot;
            start.Environment["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1";
            start.Environment["DOTNET_NOLOGO"] = "1";
            start.Environment["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1";
            foreach (var argument in new[] { hostPath, "--port", "17831", "--token-file", tokenPath, "--owner-stdin", "true", "--searx-url", Upstream }) start.ArgumentList.Add(argument);
            host = new Process { StartInfo = start };
            if (!host.Start()) throw new Blocked("host-start-failed");
            report.Cleanup.Attempted = true;
            stdout = DiscardAsync(host.StandardOutput);
            stderr = DiscardAsync(host.StandardError);
            stage = "health";
            var token = await WaitForHealthAsync(host, tokenPath, lifetime.Token);
            report.Ready = true;
            using var unusedFallback = new HttpClient(new HttpClientHandler { UseProxy = false, AllowAutoRedirect = false, UseCookies = false });
            var service = new OptimusSearchService(unusedFallback);
            var target = new OptimusSearchTarget(OptimusSearchScope.Web, OptimusSearchTarget.LocalEndpoint, token);
            foreach (var item in Cases)
            {
                if (report.Queries.Count != 0) await Task.Delay(TimeSpan.FromSeconds(2), lifetime.Token);
                if (Volatile.Read(ref outputOverflow) != 0) throw new Blocked("host-output-limit");
                stage = item.Id;
                // Exactly one typed web call per fixed case; no raw search prefetch or fallback.
                var response = await service.SearchAsync(item.Query, Array.Empty<Bookmark>(), target, lifetime.Token);
                var evidence = Qualify(item, response);
                report.Queries.Add(evidence);
                if (!evidence.Passed) throw new Blocked("web-result-blocked");
            }
            report.Reason = "none";

            async Task DiscardAsync(StreamReader reader)
            {
                var buffer = new char[1024];
                long count = 0;
                while (true)
                {
                    var read = await reader.ReadAsync(buffer);
                    if (read == 0) return;
                    count += read;
                    if (count > 65536) { Interlocked.Exchange(ref outputOverflow, 1); lifetime.Cancel(); }
                }
            }
        }
        catch (Blocked blocked) { report.Reason = blocked.Code; report.Stage = stage; }
        catch (OperationCanceledException) { report.Reason = "cancelled"; report.Stage = stage; }
        catch (Exception) { report.Reason = "probe-blocked"; report.Stage = stage; }
        finally
        {
            if (host is not null)
            {
                if (report.Cleanup.Attempted)
                {
                    try
                    {
                        if (!host.HasExited)
                        {
                            try { host.StandardInput.Close(); }
                            catch (Exception) { report.Cleanup.Failed = true; }
                        }
                        await host.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(4));
                    }
                    catch (Exception) { report.Cleanup.Failed = true; }
                    finally
                    {
                        try
                        {
                            if (!host.HasExited)
                            {
                                report.Cleanup.Forced = true;
                                report.Cleanup.Failed = true;
                                host.Kill(); // The exact Process created above; never a name lookup or tree-wide kill.
                                await host.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(2));
                            }
                            report.Cleanup.NormalExit = !report.Cleanup.Forced && host.ExitCode == 0;
                            if (!report.Cleanup.NormalExit) report.Cleanup.Failed = true;
                            if (stdout is not null && stderr is not null) await Task.WhenAll(stdout, stderr).WaitAsync(TimeSpan.FromSeconds(1));
                        }
                        catch (Exception) { report.Cleanup.Failed = true; }
                    }
                }
                host.Dispose();
            }
            if (Volatile.Read(ref outputOverflow) != 0) { report.Cleanup.Failed = true; if (report.Reason == "none") report.Reason = "host-output-limit"; }
            if (profileCreated)
            {
                try { Directory.Delete(profile!, recursive: true); report.Cleanup.ProfileRemoved = true; }
                catch (Exception) { report.Cleanup.Failed = true; }
            }
        }
        report.Passed = report.Reason == "none" && report.Queries.Count == Cases.Length && report.Queries.All(item => item.Passed)
            && report.Cleanup.NormalExit && report.Cleanup.ProfileRemoved && !report.Cleanup.Failed;
        if (!report.Passed && report.Reason == "none") { report.Reason = "cleanup-failed"; report.Stage = "cleanup"; }
        report.Status = report.Passed ? "passed" : "blocked";
        Console.WriteLine(JsonSerializer.Serialize(report, JsonOptions));
        return report.Passed ? 0 : 1;
    }

    private static Dictionary<string, string> ParseArguments(string[] args)
    {
        if (args.Length != 6) throw new Blocked("invalid-arguments");
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        for (var index = 0; index < args.Length; index += 2)
            if (args[index] is not ("--host" or "--profile" or "--source") || string.IsNullOrWhiteSpace(args[index + 1]) || !values.TryAdd(args[index], args[index + 1])) throw new Blocked("invalid-arguments");
        return values;
    }

    private static bool IsOwnedTemporaryPath(string value)
    {
        var path = Path.GetFullPath(value);
        var temporaryRoot = Path.GetFullPath(Environment.GetEnvironmentVariable("RUNNER_TEMP") ?? Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        if (!path.StartsWith(temporaryRoot, OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal)) return false;
        for (var parent = Path.GetDirectoryName(path); parent is not null; parent = Path.GetDirectoryName(parent))
            if (Directory.Exists(parent) && (File.GetAttributes(parent) & FileAttributes.ReparsePoint) != 0) return false;
        return true;
    }

    private static string DotnetHost()
    {
        var current = Environment.ProcessPath;
        return current is not null && Path.GetFileNameWithoutExtension(current).Equals("dotnet", StringComparison.OrdinalIgnoreCase) ? current : "dotnet";
    }
    private static bool HasSource(Assembly assembly, string source) => EndsWithSource(assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion, source);
    private static bool EndsWithSource(string? version, string source) => version?.EndsWith("+" + source, StringComparison.Ordinal) == true;

    private static async Task<string> WaitForHealthAsync(Process host, string tokenPath, CancellationToken cancellationToken)
    {
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(8));
        while (true)
        {
            deadline.Token.ThrowIfCancellationRequested();
            if (host.HasExited) throw new Blocked("host-exited-before-health");
            if (File.Exists(tokenPath) && new FileInfo(tokenPath).Length == 64)
            {
                var token = await File.ReadAllTextAsync(tokenPath, deadline.Token);
                if (!OptimusSearchService.IsValidToken(token)) throw new Blocked("invalid-profile-identity");
                using var client = LocalSearchTransport.CreateClient(token);
                using var attempt = CancellationTokenSource.CreateLinkedTokenSource(deadline.Token);
                attempt.CancelAfter(TimeSpan.FromMilliseconds(500));
                try
                {
                    var nonce = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
                    using var request = new HttpRequestMessage(HttpMethod.Get, OptimusSearchTarget.LocalEndpoint + "/health");
                    request.Headers.Add("X-Optimus-Nonce", nonce);
                    using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, attempt.Token);
                    var body = await ReadHealthAsync(response, attempt.Token);
                    var expected = Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.ASCII.GetBytes(token), Encoding.ASCII.GetBytes($"OptimusSearch/v1|127.0.0.1:{HostPort}|{nonce}")));
                    if (!response.IsSuccessStatusCode || !ValidHealth(body) || !response.Headers.TryGetValues("X-Optimus-Proof", out var values)
                        || values.Count() != 1 || !CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(expected), Encoding.ASCII.GetBytes(values.Single()))) throw new Blocked("invalid-health-protocol");
                    return token;
                }
                catch (HttpRequestException) { }
                catch (OperationCanceledException) when (!deadline.IsCancellationRequested) { }
            }
            await Task.Delay(100, deadline.Token); // Health-only readiness polling never resubmits a search.
        }
    }

    private static async Task<byte[]> ReadHealthAsync(HttpResponseMessage response, CancellationToken token)
    {
        if (response.Content.Headers.ContentLength > 512) throw new Blocked("health-size-limit");
        await using var stream = await response.Content.ReadAsStreamAsync(token);
        using var body = new MemoryStream();
        var buffer = new byte[513];
        while (true)
        {
            var read = await stream.ReadAsync(buffer.AsMemory(0, (int)Math.Min(buffer.Length, 513 - body.Length)), token);
            if (read == 0) return body.ToArray();
            body.Write(buffer, 0, read);
            if (body.Length > 512) throw new Blocked("health-size-limit");
        }
    }
    private static bool ValidHealth(byte[] body)
    {
        try
        {
            using var json = JsonDocument.Parse(body, new JsonDocumentOptions { MaxDepth = 4 });
            var root = json.RootElement;
            return root.ValueKind == JsonValueKind.Object && root.TryGetProperty("name", out var name) && name.ValueKind == JsonValueKind.String && name.GetString() == "OptimusSearch"
                && root.TryGetProperty("version", out var version) && version.ValueKind == JsonValueKind.Number && version.TryGetInt32(out var value) && value == 1;
        }
        catch (JsonException) { return false; }
    }

    private static QueryEvidence Qualify(Case item, SearchResponse response)
    {
        var typedWeb = response.Error is null;
        var sourceVerified = response.Results.Count != 0 && response.Results.All(result => result.Source == "SearXNG");
        var officialDomain = response.Results.Select(result => OfficialDomainEvidence(result.Url, item.Domains)).FirstOrDefault(domain => domain is not null);
        var topicMatched = response.Results.Any(result => result.Title.Contains(item.Topic, StringComparison.OrdinalIgnoreCase));
        var relevant = response.Results.FirstOrDefault(result => OfficialDomain(result.Url, item.Domains) is not null && result.Title.Contains(item.Topic, StringComparison.OrdinalIgnoreCase));
        return new(item.Id, typedWeb, sourceVerified, officialDomain, topicMatched, relevant is not null,
            typedWeb && sourceVerified && relevant is not null);
    }
    private static string? OfficialDomain(string value, IReadOnlyList<string> domains)
    {
        if (value.Any(char.IsControl) || value.Contains('\\') || !Uri.TryCreate(value, UriKind.Absolute, out var uri)
            || uri.Scheme != Uri.UriSchemeHttps || !uri.IsDefaultPort || uri.UserInfo.Length != 0 || uri.Query.Length != 0 || uri.Fragment.Length != 0) return null;
        var host = uri.IdnHost.ToLowerInvariant();
        return domains.Any(domain => host == domain || host.EndsWith("." + domain, StringComparison.Ordinal)) ? host : null;
    }

    private static string? OfficialDomainEvidence(string value, IReadOnlyList<string> domains)
    {
        var host = OfficialDomain(value, domains);
        if (host is null) return null;
        if (host is "python.org" or "www.python.org" or "docs.python.org" or "mozilla.org" or "www.mozilla.org" or "firefox.com" or "www.firefox.com") return host;
        return domains.First(domain => host == domain || host.EndsWith("." + domain, StringComparison.Ordinal));
    }

    private static int SelfTest()
    {
        var checks = 0;
        void Check(bool condition) { checks++; if (!condition) throw new Blocked("self-test-failed"); }
        try
        {
            Check(ValidHealth(Encoding.UTF8.GetBytes("{\"name\":\"OptimusSearch\",\"version\":1}")));
            foreach (var json in new[] { "[]", "{}", "{\"name\":\"other\",\"version\":1}", "{\"name\":\"OptimusSearch\",\"version\":2}", "{\"name\":\"OptimusSearch\",\"version\":\"1\"}", "invalid" }) Check(!ValidHealth(Encoding.UTF8.GetBytes(json)));
            foreach (var url in new[] { "https://python.org/", "https://docs.python.org/3/", "https://WWW.PYTHON.ORG/" }) Check(OfficialDomain(url, Cases[0].Domains) is not null);
            foreach (var url in new[] { "https://python.org.evil.test/", "https://evilpython.org/", "http://python.org/", "https://python.org:444/", "https://user@python.org/", "https://python.org/?x=1", "https://python.org/#x", "https://python.org./", "https://python.org\\@evil.test/" }) Check(OfficialDomain(url, Cases[0].Domains) is null);
            var python = new SearchResult("Welcome to Python", "https://www.python.org/", "", "SearXNG");
            var firefox = new SearchResult("Mozilla Firefox Browser", "https://www.mozilla.org/firefox/", "", "SearXNG");
            Check(Qualify(Cases[0], new([python], "Web Optimus y marcadores", null)).Passed);
            Check(Qualify(Cases[1], new([firefox], "Web Optimus y marcadores", null)).Passed);
            Check(!Qualify(Cases[0], new([], "Web Optimus y marcadores", null)).Passed);
            Check(!Qualify(Cases[0], new([python], "Web Optimus y marcadores", "blocked")).Passed);
            Check(!Qualify(Cases[0], new([python with { Source = "Marcadores" }], "Web Optimus y marcadores", null)).Passed);
            Check(!Qualify(Cases[1], new([firefox with { Title = "Mozilla Foundation" }], "Web Optimus y marcadores", null)).Passed);
            Check(!Qualify(Cases[0], new([python with { Url = "https://python.org.evil.test/" }], "Web Optimus y marcadores", null)).Passed);
            var domainOnly = Qualify(Cases[0], new([python with { Title = "Welcome" }], "Web Optimus y marcadores", null));
            Check(domainOnly.OfficialDomain == "www.python.org" && !domainOnly.TopicMatched && !domainOnly.Passed);
            var topicOnly = Qualify(Cases[0], new([python with { Url = "https://untrusted.example/?token=private-fixture" }], "Web Optimus y marcadores", null));
            Check(topicOnly.OfficialDomain is null && topicOnly.TopicMatched && !topicOnly.Passed);
            var split = Qualify(Cases[0], new([python with { Title = "Welcome" }, python with { Url = "https://untrusted.example/" }], "Web Optimus y marcadores", null));
            var splitJson = JsonSerializer.SerializeToElement(split, JsonOptions);
            Check(split.OfficialDomain == "www.python.org" && split.TopicMatched && !split.Passed
                && splitJson.TryGetProperty("pairedMatch", out var splitPair) && !splitPair.GetBoolean());
            var pairJson = JsonSerializer.SerializeToElement(Qualify(Cases[0], new([python], "Web Optimus y marcadores", null)), JsonOptions);
            Check(pairJson.TryGetProperty("pairedMatch", out var pair) && pair.GetBoolean());
            Check(!JsonSerializer.Serialize(topicOnly, JsonOptions).Contains("private-fixture", StringComparison.Ordinal));
            var privateLabel = Qualify(Cases[0], new([python with { Title = "Welcome", Url = "https://private-fixture.python.org/" }], "Web Optimus y marcadores", null));
            Check(privateLabel.OfficialDomain == "python.org" && !JsonSerializer.Serialize(privateLabel, JsonOptions).Contains("private-fixture", StringComparison.Ordinal));
            Check(Qualify(Cases[0], new([python with { Url = "https://private-fixture.python.org/" }], "Web Optimus y marcadores", null)).Passed);
            Console.WriteLine(JsonSerializer.Serialize(new { status = "passed", mode = "self-test", checks }, JsonOptions));
            return 0;
        }
        catch (Exception) { Console.WriteLine(JsonSerializer.Serialize(new { status = "blocked", mode = "self-test", checks }, JsonOptions)); return 1; }
    }

    private sealed class Blocked(string code) : Exception { public string Code { get; } = code; }
    private sealed record Case(string Id, string Query, string Topic, string[] Domains);
    private sealed record QueryEvidence(string Id, bool TypedWeb, bool SourceVerified, string? OfficialDomain, bool TopicMatched, bool PairedMatch, bool Passed);
    private sealed class CleanupEvidence { public bool Attempted { get; set; } public bool NormalExit { get; set; } public bool Forced { get; set; } public bool ProfileRemoved { get; set; } public bool Failed { get; set; } }
    private sealed class Report { public string Status { get; set; } = "blocked"; public bool Passed { get; set; } public string Source { get; set; } = ""; public bool ProvenanceVerified { get; set; } public bool Ready { get; set; } public string Reason { get; set; } = "not-started"; public string Stage { get; set; } = "none"; public List<QueryEvidence> Queries { get; } = []; public CleanupEvidence Cleanup { get; } = new(); }
}
