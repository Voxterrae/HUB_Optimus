using System.Net;
using System.Text;
using System.Text.Json;
using Optimus.Search.Brave;

const string Key = "synthetic-test-secret-not-a-real-key";
var tests = new List<(string Name, Func<Task> Run)>();
void Test(string name, Func<Task> run) => tests.Add((name, run));
void Check(bool value) { if (!value) throw new Exception("Assertion failed."); }
async Task Throws<T>(Func<Task> run) where T : Exception {
    try { await run(); } catch (T) { return; }
    throw new Exception("Expected " + typeof(T).Name);
}
string Payload(params object[] results) => JsonSerializer.Serialize(new { type = "search", web = new { type = "search", results } });
object Item(string url = "https://example.org/help", string title = "Help", string? description = "Synthetic text") => new { url, title, description };
HttpResponseMessage Json(string json) => new(HttpStatusCode.OK) { Content = new StringContent(json, Encoding.UTF8, "application/json") };
Test("emits only fixed strict Web request and authenticates by header", async () => {
    using var handler = new SyntheticHandler((request, _) => {
        Check(request.Method == HttpMethod.Get);
        Check(request.RequestUri!.AbsoluteUri == "https://api.search.brave.com/res/v1/web/search?q=a%20%26%20b&search_lang=es&count=20&safesearch=strict&text_decorations=false&result_filter=web");
        Check(request.Headers.GetValues("x-subscription-token").Single() == Key);
        Check(!request.RequestUri.ToString().Contains(Key) && request.Headers.Authorization == null && !request.Headers.Contains("Cookie"));
        Check(request.Headers.Accept.Single().MediaType == "application/json");
        return Task.FromResult(Json(Payload(Item())));
    });
    using var provider = new BraveSearchProvider(Key, handler);
    var result = await provider.SearchAsync("a & b", "es-ES");
    Check(result.Count == 1 && result[0] == new BraveSearchResult("Help", "https://example.org/help", "Synthetic text", "Brave"));
    Check(handler.Calls == 1);
});
foreach (var language in new[] { "es", "ca", "en", "de", "fr", "ru" }) Test("maps supported language " + language, async () => {
    using var handler = new SyntheticHandler((request, _) => { Check(request.RequestUri!.Query.Contains("search_lang=" + language + "&")); return Task.FromResult(Json(Payload())); });
    using var provider = new BraveSearchProvider(Key, handler);
    Check((await provider.SearchAsync("valid", language.ToUpperInvariant())).Count == 0);
});
foreach (var query in new[] { "", " ", "bad\nquery", "bad\0query", new string('x', 501), string.Join(' ', Enumerable.Repeat("a", 76)) }) Test("rejects invalid query before any send " + tests.Count, async () => {
    using var handler = new SyntheticHandler((_, _) => throw new Exception("Must not send."));
    using var provider = new BraveSearchProvider(Key, handler);
    await Throws<ArgumentException>(() => provider.SearchAsync(query, "en")); Check(handler.Calls == 0);
});
foreach (var language in new[] { "", "it", "en-GB-extra", "en&count=50", " es", "en\n" }) Test("rejects unsupported or malformed language " + tests.Count, async () => {
    using var handler = new SyntheticHandler((_, _) => throw new Exception("Must not send."));
    using var provider = new BraveSearchProvider(Key, handler);
    await Throws<ArgumentException>(() => provider.SearchAsync("valid", language)); Check(handler.Calls == 0);
});
foreach (var key in new[] { "", " ", "bad\r\nheader", new string('x', 513), "clé" }) Test("rejects unsafe credential " + tests.Count, async () => {
    await Throws<ArgumentException>(() => { using var p = new BraveSearchProvider(key); return Task.CompletedTask; });
});
Test("accepts query bounds of 500 characters and 75 words", async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json(Payload())));
    using var provider = new BraveSearchProvider(Key, handler);
    await provider.SearchAsync(new string('a', 500), "en"); await provider.SearchAsync(string.Join(' ', Enumerable.Repeat("a", 75)), "en"); Check(handler.Calls == 2);
});
Test("filters unsafe URLs and deduplicates normalized fragments preserving order", async () => {
    var entries = new[] { Item("javascript:alert(1)"), Item("https://user:pass@example.org/"), Item("file:///tmp/private"), Item("https://example.org/\\evil"), Item(" https://example.org/"), Item("https://example.org/a#one", "First"), Item("https://example.org/a#two", "Second"), Item("http://example.org/b", "Next") };
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json(Payload(entries))));
    using var provider = new BraveSearchProvider(Key, handler); var result = await provider.SearchAsync("valid", "en");
    Check(result.Count == 2 && result[0].Title == "First" && result[0].Url == "https://example.org/a" && result[1].Title == "Next");
});
Test("bounds text safely and returns plain decoded text", async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json(Payload(Item(title: "<b>Fish &amp; chips</b>", description: "<script>literal text</script>"), Item("https://example.org/long", new string('a', 239) + "😀", new string('b', 1199) + "😀")))));
    using var provider = new BraveSearchProvider(Key, handler); var result = await provider.SearchAsync("valid", "en");
    Check(result[0].Title == "Fish & chips" && result[0].Content == "literal text");
    Check(result[1].Title.Length == 239 && result[1].Content.Length == 1199);
});
Test("caps output at 20 and ignores unrelated response types", async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json(Payload(Enumerable.Range(0, 25).Select(i => Item("https://example.org/" + i)).ToArray()))));
    using var provider = new BraveSearchProvider(Key, handler); var result = await provider.SearchAsync("valid", "en");
    Check(result.Count == 20 && result[19].Url == "https://example.org/19");
});
foreach (var json in new[] { "{\"type\":\"search\"}", "{\"type\":\"search\",\"web\":null}", "{\"type\":\"search\",\"web\":{\"type\":\"search\",\"results\":[]}}" }) Test("genuine empty response " + tests.Count, async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json(json))); using var provider = new BraveSearchProvider(Key, handler);
    Check((await provider.SearchAsync("valid", "en")).Count == 0);
});
foreach (var json in new[] { "not-json", "[]", "{}", "{\"type\":\"error\"}", "{\"type\":\"search\",\"web\":[]}", "{\"type\":\"search\",\"web\":{}}", "{\"type\":\"search\",\"web\":{\"type\":\"search\",\"results\":{}}}", "{\"type\":\"search\",\"type\":\"search\"}" }) Test("rejects invalid or ambiguous response " + tests.Count, async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json(json))); using var provider = new BraveSearchProvider(Key, handler);
    try { await provider.SearchAsync("valid", "en"); throw new Exception("Expected failure."); }
    catch (BraveSearchException ex) { Check(ex.Failure == BraveSearchFailure.InvalidResponse && ex.InnerException == null && !ex.ToString().Contains(json)); }
});
foreach (var pair in new[] { (401, BraveSearchFailure.Authentication), (403, BraveSearchFailure.Authentication), (429, BraveSearchFailure.RateLimited), (500, BraveSearchFailure.Upstream), (302, BraveSearchFailure.Upstream) }) Test("sanitizes status and does not retry " + pair.Item1, async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(new HttpResponseMessage((HttpStatusCode)pair.Item1) { Content = new StringContent(Key), Headers = { Location = new Uri("https://example.org/" + Key) } }));
    using var provider = new BraveSearchProvider(Key, handler);
    try { await provider.SearchAsync("valid", "en"); throw new Exception("Expected failure."); }
    catch (BraveSearchException ex) { Check(ex.Failure == pair.Item2 && ex.InnerException == null && !ex.ToString().Contains(Key)); }
    Check(handler.Calls == 1);
});
Test("sanitizes transport exception and never retries", async () => {
    using var handler = new SyntheticHandler((_, _) => throw new HttpRequestException("secret " + Key)); using var provider = new BraveSearchProvider(Key, handler);
    try { await provider.SearchAsync("valid", "en"); throw new Exception("Expected failure."); }
    catch (BraveSearchException ex) { Check(ex.Failure == BraveSearchFailure.Transport && !ex.ToString().Contains(Key) && ex.InnerException == null); }
    Check(handler.Calls == 1);
});
Test("pre-cancelled caller does not send", async () => {
    using var handler = new SyntheticHandler((_, _) => throw new Exception("Must not send.")); using var provider = new BraveSearchProvider(Key, handler); using var stop = new CancellationTokenSource(); stop.Cancel();
    await Throws<OperationCanceledException>(() => provider.SearchAsync("valid", "en", stop.Token)); Check(handler.Calls == 0);
});
foreach (var dishonest in new[] { false, true }) Test("bounds actual streamed bytes despite length " + dishonest, async () => {
    using var stream = new TrackedStream(new byte[1024 * 1024 + 1]);
    using var handler = new SyntheticHandler((_, _) => {
        var content = new StreamContent(stream); if (dishonest) content.Headers.ContentLength = 1;
        return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = content });
    });
    using var provider = new BraveSearchProvider(Key, handler);
    try { await provider.SearchAsync("valid", "en"); throw new Exception("Expected failure."); }
    catch (BraveSearchException ex) { Check(ex.Failure == BraveSearchFailure.InvalidResponse); }
    Check(stream.Disposed && stream.BytesRead == 1024 * 1024 + 1 && handler.Calls == 1);
});
Test("accepts exactly 1 MiB JSON and disposes body", async () => {
    const string prefix = "{\"type\":\"search\",\"web\":null,\"pad\":\"";
    var body = prefix + new string('a', 1024 * 1024 - prefix.Length - 2) + "\"}";
    using var stream = new TrackedStream(Encoding.UTF8.GetBytes(body));
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }));
    using var provider = new BraveSearchProvider(Key, handler);
    Check((await provider.SearchAsync("valid", "en")).Count == 0 && stream.Disposed && stream.BytesRead == 1024 * 1024);
});
foreach (var kind in new[] { "length", "encoding", "status" }) Test("rejects headers without reading response body " + kind, async () => {
    using var stream = new TrackedStream(Encoding.UTF8.GetBytes(Key));
    using var handler = new SyntheticHandler((_, _) => {
        var content = new StreamContent(stream);
        if (kind == "length") content.Headers.ContentLength = 1024 * 1024 + 1;
        if (kind == "encoding") content.Headers.ContentEncoding.Add("gzip");
        return Task.FromResult(new HttpResponseMessage(kind == "status" ? HttpStatusCode.TooManyRequests : HttpStatusCode.OK) { Content = content });
    });
    using var provider = new BraveSearchProvider(Key, handler);
    await Throws<BraveSearchException>(() => provider.SearchAsync("valid", "en"));
    Check(stream.Disposed && stream.BytesRead == 0);
});
Test("caller cancellation while body stalled propagates without secret diagnostics", async () => {
    using var stream = new TrackedStream([], stall: true);
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }));
    using var provider = new BraveSearchProvider(Key, handler); using var stop = new CancellationTokenSource();
    var pending = provider.SearchAsync("valid", "en", stop.Token); await stream.Started.Task.WaitAsync(TimeSpan.FromSeconds(2)); stop.Cancel();
    try { await pending; throw new Exception("Expected cancellation."); }
    catch (OperationCanceledException ex) { Check(ex.CancellationToken == stop.Token && !ex.ToString().Contains(Key)); }
    Check(stream.Disposed && handler.Calls == 1);
});
Test("ten-second deadline covers stalled response body", async () => {
    using var stream = new TrackedStream([], stall: true);
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }));
    using var provider = new BraveSearchProvider(Key, handler); var watch = System.Diagnostics.Stopwatch.StartNew();
    try { await provider.SearchAsync("valid", "en").WaitAsync(TimeSpan.FromSeconds(15)); throw new Exception("Expected timeout."); }
    catch (BraveSearchException ex) { Check(ex.Failure == BraveSearchFailure.Timeout && watch.Elapsed >= TimeSpan.FromSeconds(9) && watch.Elapsed < TimeSpan.FromSeconds(15)); }
    Check(stream.Disposed && handler.Calls == 1);
});
foreach (var json in new[] { "{\"type\":\"search\",\"extra\":" + new string('[', 35) + "0" + new string(']', 35) + "}", "{\"type\":\"search\",\"web\":{\"type\":\"search\",\"results\":[],\"results\":[]}}" }) Test("rejects deep or nested duplicate JSON " + tests.Count, async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json(json))); using var provider = new BraveSearchProvider(Key, handler);
    try { await provider.SearchAsync("valid", "en"); throw new Exception("Expected failure."); }
    catch (BraveSearchException ex) { Check(ex.Failure == BraveSearchFailure.InvalidResponse); }
});
Test("ignores videos and news rather than mislabelling them as Web", async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json("{\"type\":\"search\",\"videos\":{\"results\":[{\"title\":\"Other\",\"url\":\"https://example.org/video\"}]}}")));
    using var provider = new BraveSearchProvider(Key, handler); Check((await provider.SearchAsync("valid", "en")).Count == 0);
});
Test("refuses credential echoed in results", async () => {
    using var handler = new SyntheticHandler((_, _) => Task.FromResult(Json(Payload(Item(title: Key)))));
    using var provider = new BraveSearchProvider(Key, handler);
    try { await provider.SearchAsync("valid", "en"); throw new Exception("Expected failure."); }
    catch (BraveSearchException ex) { Check(ex.Failure == BraveSearchFailure.InvalidResponse && !ex.ToString().Contains(Key)); }
});
Test("real production handler refuses redirects cookies and ambient proxy", async () => {
    using var stop = new CancellationTokenSource(TimeSpan.FromSeconds(5));
    using var listener = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0); listener.Start();
    using var redirectTrap = new System.Net.Sockets.TcpListener(IPAddress.Loopback, 0); redirectTrap.Start();
    var port = ((IPEndPoint)listener.LocalEndpoint).Port; var trapPort = ((IPEndPoint)redirectTrap.LocalEndpoint).Port;
    var server = Task.Run(async () => {
        for (var i = 0; i < 2; i++) {
            using var socket = await listener.AcceptTcpClientAsync(stop.Token); await using var stream = socket.GetStream();
            using var reader = new StreamReader(stream, Encoding.ASCII, false, leaveOpen: true);
            var headers = new List<string>(); string? line;
            while (!string.IsNullOrEmpty(line = await reader.ReadLineAsync(stop.Token))) headers.Add(line);
            Check(!headers.Any(h => h.StartsWith("Cookie:", StringComparison.OrdinalIgnoreCase)));
            var status = i == 0 ? "302 Found" : "200 OK";
            var response = $"HTTP/1.1 {status}\r\nContent-Length: 2\r\nConnection: close\r\nSet-Cookie: trap=secret\r\nLocation: http://127.0.0.1:{trapPort}/\r\n\r\n{{}}";
            await stream.WriteAsync(Encoding.ASCII.GetBytes(response), stop.Token);
        }
    });
    var priorProxy = HttpClient.DefaultProxy; var proxy = new RejectingProxy();
    try {
        HttpClient.DefaultProxy = proxy;
        using var client = new HttpClient(BraveSearchProvider.CreateHandler());
        using var first = await client.GetAsync($"http://127.0.0.1:{port}/first", stop.Token);
        Check(first.StatusCode == HttpStatusCode.Found);
        using var second = await client.GetAsync($"http://127.0.0.1:{port}/second", stop.Token);
        Check(second.StatusCode == HttpStatusCode.OK); await server;
        Check(!redirectTrap.Pending() && proxy.Calls == 0);
    }
    finally { HttpClient.DefaultProxy = priorProxy; stop.Cancel(); listener.Stop(); redirectTrap.Stop(); try { await server; } catch (OperationCanceledException) { } }
});
var failed = 0;
foreach (var test in tests) { try { await test.Run(); Console.WriteLine("PASS " + test.Name); } catch (Exception ex) { failed++; Console.WriteLine("FAIL " + test.Name + " (" + ex.GetType().Name + ")"); } }
Console.WriteLine($"{tests.Count - failed}/{tests.Count} passed"); return failed == 0 ? 0 : 1;

sealed class SyntheticHandler(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send) : HttpMessageHandler
{
    public int Calls { get; private set; }
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) { Calls++; return send(request, cancellationToken); }
}

sealed class TrackedStream(byte[] bytes, bool stall = false) : Stream
{
    private readonly MemoryStream inner = new(bytes);
    public bool Disposed { get; private set; }
    public int BytesRead { get; private set; }
    public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
    public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default) {
        Started.TrySetResult(); if (stall) await Task.Delay(Timeout.Infinite, cancellationToken);
        var read = await inner.ReadAsync(buffer, cancellationToken); BytesRead += read; return read;
    }
    protected override void Dispose(bool disposing) { Disposed = true; if (disposing) inner.Dispose(); base.Dispose(disposing); }
    public override bool CanRead => true;
    public override bool CanSeek => false;
    public override bool CanWrite => false;
    public override long Length => throw new NotSupportedException();
    public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
    public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    public override void Flush() => throw new NotSupportedException();
    public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
    public override void SetLength(long value) => throw new NotSupportedException();
    public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
}

sealed class RejectingProxy : IWebProxy
{
    public int Calls { get; private set; }
    public ICredentials? Credentials { get; set; }
    public Uri GetProxy(Uri destination) { Calls++; throw new InvalidOperationException("Ambient proxy must not be used."); }
    public bool IsBypassed(Uri host) { Calls++; return false; }
}
