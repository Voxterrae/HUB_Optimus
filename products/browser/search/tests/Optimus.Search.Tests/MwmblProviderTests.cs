using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Optimus.Search;

static class MwmblProviderTests
{
    public static void Register(Action<string, Func<Task>> test)
    {
        test("Mwmbl filters and bounds actual parsed rows and labels external provenance", async () =>
        {
            var rows = new List<object> { new { title = new string('t', 250), url = "https://EXAMPLE.org:443/a#one", content = new string('c', 1300), engine = "mwmbl" }, new { title = "duplicate", url = "https://example.org/a#two", engine = "mwmbl" }, new { title = "", url = "https://example.org/empty", engine = "user" }, new { title = "Bad", url = "javascript:alert(1)", engine = "google" }, new { title = "Bad", url = "https://u:p@example.org/", engine = "mwmbl" }, new { title = "Community", url = "https://example.org/community", engine = "user" }, new { title = "Wiki", url = "https://example.org/wiki", engine = "wikipedia" }, new { title = "Google", url = "https://example.org/google", engine = "google" }, new { title = "Unknown", url = "https://example.org/unknown", engine = "<private-detail>" } };
            rows.AddRange(Enumerable.Range(0, 25).Select(i => new { title = "Result " + i, url = "https://example.org/" + i, engine = "mwmbl" }));
            var calls = 0;
            using var provider = new MwmblSearchProvider(new Fixture((request, _) =>
            {
                calls++;
                Require(request.Method == HttpMethod.Get && request.RequestUri!.AbsoluteUri == "https://api.mwmbl.org/api/v2/search/?q=%C3%A1%20%26%3F", "Fixed HTTPS URL and encoded query; no invented locale filter");
                Require(request.Headers.Authorization is null && !request.Headers.Contains("Cookie"), "Local identity must not reach the external source");
                return Task.FromResult(Reply(JsonSerializer.Serialize(new { query = "á &?", results = rows })));
            }));
            var results = await provider.SearchAsync("á &?", "es", default);
            Require(calls == 1 && results.Count == 20, "One request and max20 valid results");
            Require(results[0].Url == "https://example.org/a" && results[0].Title.Length == 240 && results[0].Content.Length == 1200 && results[0].Source == "Mwmbl · índice", "Canonical bounded first result");
            Require(results[1].Source == "Mwmbl · comunidad" && results[2].Source == "Mwmbl · Wikipedia" && results[3].Source == "Mwmbl · Google" && results[4].Source == "Mwmbl · origen no especificado", "External sub-source must not be passed off as the Optimus index");
        });
        test("Mwmbl rejects malformed schemas and provider errors but accepts a healthy empty list", async () =>
        {
            foreach (var body in new[] { "{broken", "[]", "{}", "{\"results\":{}}", "{\"results\":[],\"error\":\"private detail\"}", "{\"results\":[],\"error\":false}", "{\"results\":[],\"nested\":" + new string('[', 33) + "0" + new string(']', 33) + "}" })
            {
                using var provider = new MwmblSearchProvider(new Fixture((_, _) => Task.FromResult(Reply(body))));
                var error = await Failed(provider);
                Require(!error.TimedOut && !error.RateLimited && !error.Message.Contains("private"), "Only generic upstream failure");
            }
            using var empty = new MwmblSearchProvider(new Fixture((_, _) => Task.FromResult(Reply("{\"results\":[]}"))));
            Require((await empty.SearchAsync("q", "es", default)).Count == 0, "Healthy zero matches remains an honest empty result");
        });
        test("Mwmbl HTTP failures do not retry and quota is distinguished", async () =>
        {
            foreach (var status in new[] { HttpStatusCode.MovedPermanently, HttpStatusCode.Forbidden, HttpStatusCode.TooManyRequests, HttpStatusCode.InternalServerError })
            {
                var calls = 0;
                using var provider = new MwmblSearchProvider(new Fixture((_, _) => { calls++; var r = Reply("private upstream detail", status); r.Headers.Location = new Uri("https://other.invalid/"); return Task.FromResult(r); }));
                var error = await Failed(provider);
                Require(error.RateLimited == (status == HttpStatusCode.TooManyRequests) && !error.TimedOut && calls == 1, "Generic error without retry or fallback;429 is quota");
            }
        });
        test("Mwmbl bounds both declared and streaming response lengths", async () =>
        {
            using (var declared = new MwmblSearchProvider(new Fixture((_, _) => { var r = Reply("{}"); r.Content.Headers.ContentLength = 1048577; return Task.FromResult(r); }))) await Failed(declared);
            var stream = new UnknownLengthStream(new byte[1048577]);
            using (var streamed = new MwmblSearchProvider(new Fixture((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) })))) await Failed(streamed);
            Require(stream.BytesRead == 1048577 && stream.Closed, "Read at most cap plus one and dispose the oversized stream");
        });
        test("Mwmbl user cancellation closes the pending body", async () =>
        {
            var stream = new PendingStream();
            using var provider = new MwmblSearchProvider(new Fixture((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) })));
            using var cancel = new CancellationTokenSource();
            var pending = provider.SearchAsync("q", "es", cancel.Token);
            await stream.Started.Task.WaitAsync(TimeSpan.FromSeconds(3)); cancel.Cancel();
            try { await pending.WaitAsync(TimeSpan.FromSeconds(1)); throw new Exception("Canceled data accepted"); } catch (OperationCanceledException) { }
            Require(stream.Closed, "Cancellation releases body ownership");
        });
        test("Mwmbl header deadline is bounded and never becomes a successful empty result", async () =>
        {
            using var provider = new MwmblSearchProvider(new Fixture(async (_, token) => { await Task.Delay(Timeout.Infinite, token); return Reply("{}"); }));
            var elapsed = Stopwatch.StartNew(); var error = await Failed(provider);
            Require(error.TimedOut && elapsed.Elapsed < TimeSpan.FromSeconds(12), "Ten-second deadline covers headers");
        });
        test("Mwmbl body deadline closes a stalled stream without a successful empty result", async () =>
        {
            var stream = new PendingStream();
            using var provider = new MwmblSearchProvider(new Fixture((_, _) => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) })));
            var elapsed = Stopwatch.StartNew(); var error = await Failed(provider);
            Require(error.TimedOut && stream.Started.Task.IsCompleted && stream.Closed && elapsed.Elapsed < TimeSpan.FromSeconds(12), "Ten-second deadline includes the body and releases it");
        });
        test("Mwmbl spacing applies across instances and canceled waiters never dispatch", async () =>
        {
            var times = new List<long>(); var canceledCalls = 0;
            using var first = new MwmblSearchProvider(new Fixture((_, _) => { times.Add(Stopwatch.GetTimestamp()); return Task.FromResult(Reply("{\"results\":[]}")); }));
            using var second = new MwmblSearchProvider(new Fixture((_, _) => { times.Add(Stopwatch.GetTimestamp()); return Task.FromResult(Reply("{\"results\":[]}")); }));
            using var canceled = new MwmblSearchProvider(new Fixture((_, _) => { canceledCalls++; return Task.FromResult(Reply("{\"results\":[]}")); }));
            await first.SearchAsync("q", "es", default);
            using var cancel = new CancellationTokenSource(TimeSpan.FromMilliseconds(50));
            try { await canceled.SearchAsync("q", "es", cancel.Token); throw new Exception("Canceled waiter accepted"); } catch (OperationCanceledException) { }
            await second.SearchAsync("q", "es", default);
            Require(canceledCalls == 0 && Stopwatch.GetElapsedTime(times[0], times[1]) >= TimeSpan.FromSeconds(1.05), "At least1.1s configured spacing shared by instances, with scheduler tolerance");
        });
        test("Mwmbl invalid queries never dispatch", async () =>
        {
            using var provider = new MwmblSearchProvider(new Fixture((_, _) => throw new Exception("Invalid query reached network")));
            foreach (var q in new[] { "", " ", new string('q', 501), "q\n" })
                try { await provider.SearchAsync(q, "es", default); throw new Exception("Invalid query accepted"); } catch (ArgumentException) { }
        });
        test("real Optimus API confines Mwmbl to authenticated Web and presents generic429", async () =>
        {
            var calls = 0;
            using var provider = new MwmblSearchProvider(new Fixture((_, _) => { calls++; return Task.FromResult(Reply("private quota detail", HttpStatusCode.TooManyRequests)); }));
            const string token = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
            await using var server = await SearchServer.StartAsync(new(0, token), new LocalSearchIndex([]), provider);
            using var client = new HttpClient(TestTls.Handler(() => token)) { BaseAddress = new Uri(server.Address) };
            using (var unauthenticated = await client.GetAsync("/search?format=json&q=q&scope=web&language=es")) Require(unauthenticated.StatusCode == HttpStatusCode.Unauthorized && calls == 0, "No external request before authentication");
            client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
            using (var index = await client.GetAsync("/search?format=json&q=q&scope=index&language=es")) Require(index.StatusCode == HttpStatusCode.OK && calls == 0, "Index stays offline");
            using var response = await client.GetAsync("/search?format=json&q=q&scope=web&language=es");
            var text = await response.Content.ReadAsStringAsync(); using var json = JsonDocument.Parse(text);
            Require(response.StatusCode == HttpStatusCode.TooManyRequests && calls == 1 && json.RootElement.GetProperty("error").GetString() == "upstream-rate-limited" && json.RootElement.GetProperty("results").GetArrayLength() == 0 && !text.Contains("private"), "One external request; generic429 and no fallback");
        });
    }
    private static void Require(bool value, string message) { if (!value) throw new Exception(message); }
    private static HttpResponseMessage Reply(string body, HttpStatusCode status = HttpStatusCode.OK) => new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
    private static async Task<SearchProviderException> Failed(MwmblSearchProvider provider)
    {
        try { await provider.SearchAsync("q", "es", default); } catch (SearchProviderException error) { return error; }
        throw new Exception("Expected generic provider failure");
    }
    private sealed class Fixture(Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send) : HttpMessageHandler
    { protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token) => send(request, token); }
    private sealed class UnknownLengthStream(byte[] bytes) : Stream
    {
        private readonly MemoryStream source = new(bytes);
        public int BytesRead { get; private set; }
        public bool Closed { get; private set; }
        public override bool CanRead => true; public override bool CanSeek => false; public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException(); public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override int Read(byte[] buffer, int offset, int count) { var n = source.Read(buffer, offset, count); BytesRead += n; return n; }
        public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken token = default) { var n = await source.ReadAsync(buffer, token); BytesRead += n; return n; }
        protected override void Dispose(bool disposing) { Closed = true; if (disposing) source.Dispose(); base.Dispose(disposing); }
        public override void Flush() => throw new NotSupportedException(); public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException(); public override void SetLength(long value) => throw new NotSupportedException(); public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }
    private sealed class PendingStream : Stream
    {
        public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public bool Closed { get; private set; }
        public override bool CanRead => true; public override bool CanSeek => false; public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException(); public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken token = default) { Started.TrySetResult(); await Task.Delay(Timeout.Infinite, token); return 0; }
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        protected override void Dispose(bool disposing) { Closed = true; base.Dispose(disposing); }
        public override void Flush() => throw new NotSupportedException(); public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException(); public override void SetLength(long value) => throw new NotSupportedException(); public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }
}
