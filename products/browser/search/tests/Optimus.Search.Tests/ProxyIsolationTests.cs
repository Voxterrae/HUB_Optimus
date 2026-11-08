using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using Optimus.Search;

static class ProxyIsolationTests
{
    public static void Register(Action<string, Func<Task>> test, Func<string, string[], ProcessStartInfo> dotnetStart)
    {
        // Catches a default/system proxy receiving a query meant only for the fixed operator.
        test("provider ignores ambient proxies and contacts only the configured operator", async () =>
        {
            await using var configured = new Responder();
            await using var proxy = new Responder();
            var start = dotnetStart(Assembly.GetExecutingAssembly().Location, ["--provider-proxy-worker", configured.Url]);
            // A fresh process is necessary because HttpClient.DefaultProxy caches its environment.
            string[] proxyNames = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"];
            foreach (var name in start.Environment.Keys.Where(name => proxyNames.Contains(name, StringComparer.OrdinalIgnoreCase)).ToArray())
                start.Environment.Remove(name);
            foreach (var name in proxyNames)
            {
                var value = name == "NO_PROXY" ? "" : proxy.Url;
                start.Environment[name] = value;
                start.Environment[name.ToLowerInvariant()] = value;
            }

            using var child = Process.Start(start) ?? throw new Exception("Provider proxy worker did not start");
            var output = child.StandardOutput.ReadToEndAsync();
            var errors = child.StandardError.ReadToEndAsync();
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(20));
            try { await child.WaitForExitAsync(deadline.Token); }
            finally
            {
                if (!child.HasExited)
                {
                    child.Kill(entireProcessTree: true);
                    await child.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5));
                }
                await Task.WhenAll(output, errors).WaitAsync(TimeSpan.FromSeconds(5));
            }
            Require(child.ExitCode == 0, "Provider proxy worker failed without returning its fixture results");
            Require(proxy.Contacts == 0, $"Ambient proxy received provider traffic; operator contacts={configured.Contacts}, proxy contacts={proxy.Contacts}");
            Require(configured.Contacts == 1 && configured.RequestLines.Count == 1, "Configured operator must receive exactly one request");
            Require(configured.RequestLines.Single() == "POST /search HTTP/1.1", "Configured operator received an unexpected method or request target");
            Require(configured.RequestBodies.Single() == "format=json&q=proxy-isolation-fixture&language=es&categories=general&safesearch=2", "Configured operator did not receive the fixed private form");
        });
    }

    public static async Task<int> RunWorkerAsync(string endpoint)
    {
        try
        {
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(10));
            using var provider = new SearxSearchProvider(endpoint);
            return (await provider.SearchAsync("proxy-isolation-fixture", "es", deadline.Token)).Count == 0 ? 0 : 1;
        }
        catch { return 2; } // Neither child output nor exception messages contain a query or profile data.
    }

    private static void Require(bool value, string message) { if (!value) throw new Exception(message); }

    private sealed class Responder : IAsyncDisposable
    {
        private readonly TcpListener listener = new(IPAddress.Loopback, 0);
        private readonly CancellationTokenSource stopping = new();
        private readonly Task serving;
        private int contacts;
        public string Url { get; }
        public int Contacts => Volatile.Read(ref contacts);
        public ConcurrentQueue<string> RequestLines { get; } = new();
        public ConcurrentQueue<string> RequestBodies { get; } = new();

        public Responder()
        {
            listener.Start();
            Url = $"http://127.0.0.1:{((IPEndPoint)listener.LocalEndpoint).Port}";
            serving = Task.Run(async () =>
            {
                try
                {
                    while (!stopping.IsCancellationRequested)
                    {
                        using var peer = await listener.AcceptTcpClientAsync(stopping.Token);
                        Interlocked.Increment(ref contacts);
                        await using var stream = peer.GetStream();
                        var bytes = new List<byte>(); var one = new byte[1];
                        while (bytes.Count < 16384 && await stream.ReadAsync(one, stopping.Token) != 0)
                        {
                            bytes.Add(one[0]);
                            if (bytes.Count >= 4 && bytes[^4] == '\r' && bytes[^3] == '\n' && bytes[^2] == '\r' && bytes[^1] == '\n') break;
                        }
                        var headers = Encoding.ASCII.GetString(bytes.ToArray());
                        RequestLines.Enqueue(headers.Split("\r\n", StringSplitOptions.None)[0]);
                        var lengthHeader=headers.Split("\r\n",StringSplitOptions.None).SingleOrDefault(x=>x.StartsWith("Content-Length:",StringComparison.OrdinalIgnoreCase));
                        var length=lengthHeader is null?0:int.Parse(lengthHeader[15..].Trim(),System.Globalization.CultureInfo.InvariantCulture);
                        if(length is <0 or >8192) throw new IOException("Fixture body exceeds bound");
                        var body=new byte[length];await stream.ReadExactlyAsync(body,stopping.Token);RequestBodies.Enqueue(Encoding.UTF8.GetString(body));
                        await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 14\r\nConnection: close\r\n\r\n{\"results\":[]}"), stopping.Token);
                    }
                }
                catch (Exception ex) when (ex is OperationCanceledException or SocketException or IOException or ObjectDisposedException) { }
            });
        }

        public async ValueTask DisposeAsync()
        {
            try { stopping.Cancel(); listener.Stop(); await serving.WaitAsync(TimeSpan.FromSeconds(5)); }
            finally { listener.Stop(); stopping.Dispose(); }
        }
    }
}
