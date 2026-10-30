using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Net.Security;
using System.Security.Authentication;
using System.Security.Cryptography.X509Certificates;
using System.Security.Cryptography;
using System.Text;
using Optimus.Core;
using Optimus.Search;

static class IdentityProofTests
{
    private const string Token = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    private const string Health = "{\"name\":\"OptimusSearch\",\"version\":1}";
    public static void Register(Action<string, Func<Task>> test)
    {
        // Removing proof verification would disclose a target to a name/version port squatter.
        foreach (var mode in new[] { "missing", "random", "malformed", "wrong-token", "unknown-marker" })
            test("real TLS launcher rejects " + mode + " identity without bearer or query disclosure", async () =>
            {
                using var profile = new Profile(Token);
                await using var impostor = new Listener(async (stream, headers) =>
                {
                    var nonce = Header(headers, "X-Optimus-Nonce") ?? new string('0', 64);
                    var proof = mode switch
                    {
                        "missing" => null,
                        "random" => new string('0', 64),
                        "malformed" => new string('g', 64),
                        "wrong-token" => Proof(new string('b', 64), 17831, nonce),
                        _ => Proof(Token, 17831, nonce)
                    };
                    await Send(stream, mode == "unknown-marker" ? "{\"name\":\"OtherService\",\"version\":1}" : Health, proof);
                });
                using var client = Client();
                using var launcher = new SearchHostLauncher(client, profile.Directory, profile.Directory);
                var connection = await launcher.ConnectAsync(null, default);
                Require(connection.Error is not null && connection.Target.BearerToken is null, "Unproven identity must never yield bearer target");
                var result = await new OptimusSearchService(client).SearchAsync("private query", [], connection.Target, default);
                Require(result.Error is not null, "Failed connection cannot issue a search");
                launcher.Dispose();
                using var stillListening = await client.GetAsync(OptimusSearchTarget.LocalEndpoint + "/health");
                Require(stillListening.StatusCode == HttpStatusCode.OK && !launcher.OwnsProcess, "Independent listener must survive launcher close");
                Undisclosed(impostor.Requests);
                var challenge = Header(impostor.Requests.First(), "X-Optimus-Nonce");
                Require(challenge is { Length: 64 } && challenge.All(Uri.IsHexDigit), "Challenge must be 32 random bytes encoded as 64 hex");
            });

        // Reusing a proof after a successful connection must fail against the next fresh nonce.
        test("real TLS launcher rejects replayed proof for a fresh connection nonce", async () =>
        {
            using var profile = new Profile(Token); string? captured = null;
            await using var impostor = new Listener(async (stream, headers) =>
            {
                captured ??= Proof(Token, 17831, Header(headers, "X-Optimus-Nonce") ?? new string('0', 64));
                await Send(stream, Health, captured);
            });
            using var client = Client(); using var launcher = new SearchHostLauncher(client, profile.Directory, profile.Directory);
            Require((await launcher.ConnectAsync(null, default)).Error is null, "First valid proof must establish connection");
            var replay = await launcher.ConnectAsync(null, default);
            Require(replay.Error is not null && replay.Target.BearerToken is null, "Old proof cannot authenticate fresh connection");
            var nonces = impostor.Requests.Select(r => Header(r, "X-Optimus-Nonce")).ToArray();
            Require(nonces.Length == 2 && nonces[0] is { Length: 64 } && nonces[0] != nonces[1], "Each connection needs a fresh nonce");
            Undisclosed(impostor.Requests);
        });

        // A relay to the real service on another port must not authorize this fixed listener.
        test("real TLS launcher rejects proof relayed from actual service on another port", async () =>
        {
            using var profile = new Profile(Token);
            await using var real = await SearchServer.StartAsync(new(0, Token), new LocalSearchIndex([]));
            using var relay = Client();
            await using var impostor = new Listener(async (stream, headers) =>
            {
                using var request = new HttpRequestMessage(HttpMethod.Get, real.Address + "/health");
                request.Headers.Add("X-Optimus-Nonce", Header(headers, "X-Optimus-Nonce") ?? new string('0', 64));
                using var response = await relay.SendAsync(request);
                var proof = response.Headers.TryGetValues("X-Optimus-Proof", out var values) ? values.Single() : null;
                await Send(stream, Health, proof);
            });
            using var client = Client(); using var launcher = new SearchHostLauncher(client, profile.Directory, profile.Directory);
            var connection = await launcher.ConnectAsync(null, default);
            Require(connection.Error is not null && connection.Target.BearerToken is null, "Another listener's valid proof must not authenticate this port");
            Undisclosed(impostor.Requests);
        });

        // Real service and native client exercise independent HMAC implementations through actual HTTP.
        test("actual service identity unlocks native authenticated index search over TLS", async () =>
        {
            using var profile = new Profile(Token);
            var index = new LocalSearchIndex([new CatalogDocument("https://example.org/help", "Optimus help", "Offline help", "Public help", DateTimeOffset.Parse("2026-10-30T00:00:00Z"))]);
            await using var real = await SearchServer.StartAsync(new(17831, Token), index);
            using var client = Client(); using var launcher = new SearchHostLauncher(client, profile.Directory, profile.Directory);
            var connection = await launcher.ConnectAsync(null, default);
            Require(connection.Error is null && connection.Target.BearerToken == Token && !launcher.OwnsProcess, "Actual service must prove shared profile token");
            var result = await new OptimusSearchService(client).SearchAsync("help", [], connection.Target with { Scope = OptimusSearchScope.Index }, default);
            Require(result.Error is null && result.Results.Single().Url == "https://example.org/help", "Authenticated native request must reach actual own index");
            launcher.Dispose(); using var health = await client.GetAsync(real.Address + "/health");
            Require(health.StatusCode == HttpStatusCode.OK, "Closing launcher must preserve independently started actual service");
        });

        test("actual search rejects listener replacement after verified health without bearer or query", async () =>
        {
            using var profile = new Profile(Token);
            var real = await SearchServer.StartAsync(new(17831, Token), new LocalSearchIndex([]));
            using var client = Client(); using var launcher = new SearchHostLauncher(client, profile.Directory, profile.Directory);
            var connection = await launcher.ConnectAsync(null, default);
            Require(connection.Error is null, "Legitimate identity must connect");
            await real.DisposeAsync();
            await using var impostor = new Listener((stream, headers) => Send(stream, "{\"results\":[],\"optimus\":{\"version\":1,\"scope\":\"web\",\"webConfigured\":true,\"indexedDocuments\":0}}", null), Certificate(new string('b', 64)));
            var result = await new OptimusSearchService(client).SearchAsync("private query", [], connection.Target, default);
            Require(result.Error is not null, "Replacement must be rejected");
            Require(impostor.Requests.All(r => !r.Contains("Authorization", StringComparison.OrdinalIgnoreCase) && !r.Contains("private") && !r.Contains(Token)), "Replacement stole bearer/query after verified health");
        });

        foreach (var mode in new[] { "missing", "malformed", "wrong-token", "wrong-port", "copied-proof" })
        test("actual search rejects " + mode + " TLS certificate before HTTP disclosure", async () =>
        {
            using var legitimate = Certificate(Token);
            using var cert = Certificate(mode == "wrong-token" ? new string('b',64) : Token, mode, mode == "wrong-port" ? 17832 : 17831,
                mode == "copied-proof" ? legitimate.Extensions.Cast<X509Extension>().Single().RawData : null);
            await using var attacker = new Listener((stream, headers) => Send(stream, Health, null), cert);
            using var client = Client();
            var result = await new OptimusSearchService(client).SearchAsync("private query", [], new OptimusSearchTarget(OptimusSearchScope.Index, null, Token), default);
            Require(result.Error is not null && !result.Error.Contains(Token), "Invalid TLS identity must give generic error");
            Require(attacker.Requests.IsEmpty, "No HTTP header, bearer or query may precede TLS authentication");
        });
        test("fresh search reconnect rejects changed certificate after a successful search", async () =>
        {
            using var client = Client(); var service = new OptimusSearchService(client);
            await using(var real = await SearchServer.StartAsync(new(17831, Token), new LocalSearchIndex([])))
                Require((await service.SearchAsync("private query", [], new OptimusSearchTarget(OptimusSearchScope.Index,null,Token),default)).Error is null,"Initial search succeeds");
            using var cert = Certificate(new string('b',64));
            await using var attacker = new Listener((stream, headers) => Send(stream, Health, null),cert);
            Require((await service.SearchAsync("private query", [], new OptimusSearchTarget(OptimusSearchScope.Index,null,Token),default)).Error is not null,"Reconnect must reauthenticate");
            Require(attacker.Requests.IsEmpty,"Reconnect leaked HTTP");
        });
        test("copied public certificate without private key cannot terminate TLS", async () =>
        {
            using var privateCertificate = Certificate(Token);
            using var publicCertificate = X509CertificateLoader.LoadCertificate(privateCertificate.RawData);
            Require(!publicCertificate.HasPrivateKey,"Attacker must have public certificate only");
            await using var attacker = new Listener((stream, headers) => Send(stream, Health, null), publicCertificate);
            using var client = Client();
            var result = await new OptimusSearchService(client).SearchAsync("private query",[],new OptimusSearchTarget(OptimusSearchScope.Index,null,Token),default);
            Require(result.Error is not null && attacker.Requests.IsEmpty,"Public certificate replay cannot authenticate actual transport");
        });

        test("accepted localhost configuration starts real backend with identical policy", async () =>
        {
            const string endpoint="http://localhost:8080/instance";
            Require(OptimusSearchService.IsValidEndpoint(endpoint),"Native policy accepts literal localhost");
            using var provider=new SearxSearchProvider(endpoint);
            await using var server=await SearchServer.StartAsync(new(17831,Token),new LocalSearchIndex([]),provider);
            using var profile=new Profile(Token);using var client=Client();
            using var launcher=new SearchHostLauncher(client,profile.Directory,profile.Directory);
            Require((await launcher.ConnectAsync(endpoint,default)).Error is null,"Accepted configuration must start and answer authenticated health");
        });
        test("actual TLS search cancellation closes pending body", async () =>
        {
            var started=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var closed=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            await using var listener=new Listener(async(stream,headers)=>{
                await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Length: 100\r\nConnection: close\r\n\r\n{"));
                started.TrySetResult();if(await stream.ReadAsync(new byte[1])==0)closed.TrySetResult();
            });
            using var client=Client();using var cancel=new CancellationTokenSource();
            var pending=new OptimusSearchService(client).SearchAsync("private query",[],new OptimusSearchTarget(OptimusSearchScope.Index,null,Token),cancel.Token);
            await started.Task.WaitAsync(TimeSpan.FromSeconds(2));cancel.Cancel();
            try{await pending;throw new Exception("Canceled search returned results");}catch(OperationCanceledException){}
            await closed.Task.WaitAsync(TimeSpan.FromSeconds(2));
        });

        // Cancellation after proof headers must not return credentials or retain a blocked body read.
        test("real TLS identity cancellation closes pending health without disclosing bearer or query", async () =>
        {
            using var profile = new Profile(Token);
            var started = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var closed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            await using var impostor = new Listener(async (stream, headers) =>
            {
                var proof = Proof(Token, 17831, Header(headers, "X-Optimus-Nonce") ?? new string('0', 64));
                await stream.WriteAsync(Encoding.ASCII.GetBytes($"HTTP/1.1 200 OK\r\nX-Optimus-Proof: {proof}\r\nContent-Length: 100\r\nConnection: close\r\n\r\n{{"));
                started.TrySetResult(); if (await stream.ReadAsync(new byte[1]) == 0) closed.TrySetResult();
            });
            using var client = Client(); using var launcher = new SearchHostLauncher(client, profile.Directory, profile.Directory);
            using var cancel = new CancellationTokenSource();
            var pending = launcher.ConnectAsync(null, cancel.Token);
            await started.Task.WaitAsync(TimeSpan.FromSeconds(2)); cancel.Cancel();
            try { await pending; throw new Exception("Canceled identity returned a connection"); } catch (OperationCanceledException) { }
            await closed.Task.WaitAsync(TimeSpan.FromSeconds(2));
            Require(!launcher.OwnsProcess, "Cancellation cannot claim independent process ownership"); Undisclosed(impostor.Requests);
        });
    }

    private static X509Certificate2 Certificate(string token, string mode = "valid", int port = 17831, byte[]? copiedProof = null)
    {
        using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
        var request = new CertificateRequest("CN=fixture", key, HashAlgorithmName.SHA256);
        var message = $"OptimusSearch/TLS/v1|https://127.0.0.1:{port}|{Convert.ToBase64String(key.ExportSubjectPublicKeyInfo())}";
        if (mode != "missing") request.CertificateExtensions.Add(new X509Extension("1.3.6.1.4.1.57264.2021.1", copiedProof ?? (mode == "malformed" ? new byte[31] : HMACSHA256.HashData(Encoding.ASCII.GetBytes(token), Encoding.ASCII.GetBytes(message))), false));
        return request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-1), DateTimeOffset.UtcNow.AddDays(1));
    }
    private static string Proof(string token, int port, string nonce) => Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.ASCII.GetBytes(token), Encoding.ASCII.GetBytes($"OptimusSearch/v1|127.0.0.1:{port}|{nonce}")));
    private static HttpClient Client() => LocalSearchTransport.CreateClient(Token);
    private static string? Header(string headers, string name) => headers.Split("\r\n").FirstOrDefault(line => line.StartsWith(name + ":", StringComparison.OrdinalIgnoreCase))?[(name.Length + 1)..].Trim();
    private static void Undisclosed(IEnumerable<string> requests)
    {
        foreach (var request in requests)
            Require(request.StartsWith("GET /health HTTP/1.1\r\n", StringComparison.Ordinal) && Header(request, "Authorization") is null && !request.Contains(Token) && !request.Contains("private"), "Unverified listener must receive only credential-free health");
    }
    private static async Task Send(Stream stream, string body, string? proof)
    {
        var bytes = Encoding.UTF8.GetBytes(body);
        await stream.WriteAsync(Encoding.ASCII.GetBytes($"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {bytes.Length}\r\nConnection: close\r\n" + (proof is null ? "" : $"X-Optimus-Proof: {proof}\r\n") + "\r\n"));
        await stream.WriteAsync(bytes);
    }
    private static void Require(bool value, string message) { if (!value) throw new Exception(message); }
    private sealed class Profile : IDisposable
    {
        public string Directory { get; } = Path.Combine(Path.GetTempPath(), "optimus-identity-" + Guid.NewGuid().ToString("N"));
        public Profile(string token) { var path = Path.Combine(Directory, "Optimus", "Search"); System.IO.Directory.CreateDirectory(path); File.WriteAllText(Path.Combine(path, "service.token"), token); }
        public void Dispose() => System.IO.Directory.Delete(Directory, true);
    }
    private sealed class Listener : IAsyncDisposable
    {
        private readonly TcpListener listener = new(IPAddress.Loopback, 17831);
        private readonly CancellationTokenSource stopping = new();
        private readonly Task serving;
        private readonly X509Certificate2? ownedCertificate;
        public ConcurrentQueue<string> Requests { get; } = new();
        public Listener(Func<Stream, string, Task> respond, X509Certificate2? certificate = null)
        {
            if (certificate is null) certificate = ownedCertificate = Certificate(Token);
            listener.Start();
            serving = Task.Run(async () =>
            {
                try
                {
                    while (!stopping.IsCancellationRequested)
                    {
                        using var peer = await listener.AcceptTcpClientAsync(stopping.Token);
                        await using var stream = new SslStream(peer.GetStream(), false);
                        try { await stream.AuthenticateAsServerAsync(new SslServerAuthenticationOptions { ServerCertificate = certificate, EnabledSslProtocols = SslProtocols.Tls12 | SslProtocols.Tls13 }, stopping.Token); }
                        catch (Exception ex) when (ex is AuthenticationException or IOException or CryptographicException) { continue; }
                        var bytes = new List<byte>(); var one = new byte[1];
                        while (bytes.Count < 16384 && await stream.ReadAsync(one, stopping.Token) > 0)
                        {
                            bytes.Add(one[0]);
                            if (bytes.Count >= 4 && Encoding.ASCII.GetString(bytes.TakeLast(4).ToArray()) == "\r\n\r\n") break;
                        }
                        if (bytes.Count == 0) continue; // A rejected TLS peer can complete the server handshake then close without HTTP.
                        var headers = Encoding.ASCII.GetString(bytes.ToArray()); Requests.Enqueue(headers);
                        await respond(stream, headers);
                    }
                }
                catch (Exception ex) when (ex is OperationCanceledException or IOException or SocketException or ObjectDisposedException) { }
            });
        }
        public async ValueTask DisposeAsync() { stopping.Cancel(); listener.Stop(); await serving.WaitAsync(TimeSpan.FromSeconds(3)); stopping.Dispose(); ownedCertificate?.Dispose(); }
    }
}
