using Optimus.Core;
using System.Net;
using System.Text;
using System.Text.Json;

var tests = new List<(string Name, Func<Task> Run)>();
void Test(string name, Func<Task> run) => tests.Add((name, run));
void Check(bool value, string message) { if (!value) throw new Exception(message); }
const string wiki = """
{"batchcomplete":"","query":{"searchinfo":{"totalhits":1},"search":[{"ns":0,"title":"Madrid &amp; región","pageid":19,"size":1234,"wordcount":100,"snippet":"La <span class=\"searchmatch\">capital</span> &amp; ciudad","timestamp":"2026-10-29T00:00:00Z"}]}}
""";
Test("empty and 501-character input never sends a request", async () => {
    using var h = new Fixture(_ => throw new Exception("Input reached network"));
    using var c = new HttpClient(h); var s = new OptimusSearchService(c);
    foreach (var q in new[] { "", " \t", new string('a', 501) })
        Check((await s.SearchAsync(q, [], null, default)).Error != null, "Invalid input needs visible error");
});
Test("Wikipedia receives escaped query and yields plain text from validated pageid", async () => {
    using var h = new Fixture(r => {
        Check(r.RequestUri!.Host == "es.wikipedia.org" && r.RequestUri.AbsolutePath == "/w/api.php", "Fixed official endpoint");
        var q = r.RequestUri.Query;
        Check(q.Contains("action=query") && q.Contains("list=search") && q.Contains("format=json") && q.Contains("utf8=1") && q.Contains("srlimit=20") && q.Contains("srsearch=Madrid%20%26%20sol"), "Wikipedia documented parameters and escaped query");
        return Reply(wiki);
    });
    using var c = new HttpClient(h);
    var r = await new OptimusSearchService(c).SearchAsync("Madrid & sol", [], null, default);
    Check(r.Error == null && r.Provider.Contains("Wikipedia") && r.Results.Count == 1, "Wikipedia provenance");
    Check(r.Results[0] == new SearchResult("Madrid & región", "https://es.wikipedia.org/?curid=19", "La capital & ciudad", "Wikipedia"), "Plain text and pageid URL");
});
Test("bookmarks are matched locally validated deduplicated and never leak when omitted", async () => {
    using var h = new Fixture(_ => Reply(wiki)); using var c = new HttpClient(h); var s = new OptimusSearchService(c);
    Bookmark[] b = [new("Madrid favorito", "https://example.org"), new("Madrid duplicate", "https://example.org/"), new("Madrid credential", "https://a:b@example.org"), new("Madrid script", "javascript:alert(1)"), new("Other", "https://other.org")];
    var r = await s.SearchAsync("Madrid", b, null, default);
    Check(r.Results.Count == 2 && r.Results[0].Source == "Marcadores" && r.Results[0].Url == "https://example.org/", "Only safe matching unique bookmark plus Wiki");
    Check((await s.SearchAsync("Madrid", [], null, default)).Results.All(x => x.Source != "Marcadores"), "Host omission excludes normal bookmarks in private context");
});
Test("optional SearXNG returns documented JSON results and no Wikipedia fallback", async () => {
    const string json = """{"query":"sol & luna","number_of_results":6,"results":[{"url":"https://news.example/a","title":"<b>Sol</b>","content":"Texto &amp; luz","engine":"fixture","engines":["fixture"],"positions":[1],"score":1.0,"category":"general","template":"default.html","parsed_url":["https","news.example","/a","","",""]},{"url":"https://news.example/a","title":"Duplicate","content":"copy"},{"url":"https://user:pass@bad.example","title":"Bad","content":"bad"},{"url":"file:///secret","title":"Bad","content":"bad"},{"url":"javascript:alert(1)","title":"Bad","content":"bad"},{"url":"https://good.example/","title":"<img src=x onerror=alert(1)>Safe","content":"<script>alert(1)</script>"}],"answers":[],"corrections":[],"infoboxes":[],"suggestions":[],"unresponsive_engines":[]}""";
    using var h = new Fixture(r => {
        Check(r.RequestUri!.Host == "search.example" && r.RequestUri.AbsolutePath == "/instance/search", "Explicit backend only");
        Check(r.RequestUri.Query.Contains("q=sol%20%26%20luna") && r.RequestUri.Query.Contains("format=json"), "Documented SearXNG parameters");
        return Reply(json);
    }); using var c = new HttpClient(h);
    var r = await new OptimusSearchService(c).SearchAsync("sol & luna", [], "https://search.example/instance", default);
    Check(r.Error == null && r.Provider.Contains("SearXNG") && r.Results.Count == 2, "Safe unique SearXNG results");
    Check(r.Results[0].Title == "Sol" && r.Results[0].Snippet == "Texto & luz" && r.Results[1].Title == "Safe" && !r.Results[1].Snippet.Contains('<'), "Markup becomes plain text");
});
Test("endpoint policy rejects credentials remote HTTP and malformed destinations", async () => {
    foreach (var value in new[] { "https://search.example", "https://search.example/search", "http://localhost:8080", "http://127.0.0.1:8080", "http://[::1]:8080" })
        Check(OptimusSearchService.IsValidEndpoint(value), "Valid endpoint " + value);
    using var h = new Fixture(_ => throw new Exception("Invalid endpoint reached network")); using var c = new HttpClient(h);
    foreach (var value in new[] { "", "http://search.example", "http://localhost.evil.test", "https://a:b@search.example", "file:///x", "https://search.example/?q=secret", "https://search.example/#x", "https://search.example/\nsecret", "https://search.example\\evil" }) {
        Check(!OptimusSearchService.IsValidEndpoint(value), "Rejected endpoint " + value);
        Check((await new OptimusSearchService(c).SearchAsync("x", [], value, default)).Error != null, "Visible endpoint error without fallback");
    }
});
Test("malformed API error and redirects remain visible with local results", async () => {
    foreach (var body in new[] { "{broken", "{}", "{\"error\":{\"code\":\"badvalue\",\"info\":\"invalid request\"}}" }) {
        using var h = new Fixture(_ => Reply(body)); using var c = new HttpClient(h);
        var r = await new OptimusSearchService(c).SearchAsync("x", [new("x local", "https://local.example")], null, default);
        Check(r.Error != null && r.Results.Count == 1 && r.Provider.Contains("Wikipedia"), "Visible provider failure and preserved local result");
    }
    foreach (var code in new[] { HttpStatusCode.Redirect, HttpStatusCode.Forbidden, HttpStatusCode.InternalServerError }) {
        using var h = new Fixture(_ => new HttpResponseMessage(code) { Headers = { Location = new Uri("https://other.example") } }); using var c = new HttpClient(h);
        Check((await new OptimusSearchService(c).SearchAsync("x", [], null, default)).Error != null, "HTTP failures cannot become empty success");
    }
});
Test("invalid Wikipedia pageids are excluded and all sources share limit20", async () => {
    var body = "{\"query\":{\"search\":[{\"pageid\":0,\"title\":\"bad\"},{\"pageid\":-1,\"title\":\"bad\"},{\"pageid\":\"https://evil.example\",\"title\":\"bad\"},{\"pageid\":12,\"title\":\"good\",\"snippet\":\"text\"}]}}";
    using var h = new Fixture(_ => Reply(body)); using var c = new HttpClient(h); var s = new OptimusSearchService(c);
    var r = await s.SearchAsync("x", [], null, default);
    Check(r.Results.Count == 1 && r.Results[0].Url == "https://es.wikipedia.org/?curid=12", "Validated positive integer pageid only");
    var bookmarks = Enumerable.Range(0, 30).Select(i => new Bookmark("x " + i, "https://example.org/" + i)).ToArray();
    Check((await s.SearchAsync("x", bookmarks, null, default)).Results.Count == 20, "20 total results");
});
Test("a chunked response stops reading at1MiB without buffering whole body", async () => {
    var stream = new EndlessStream(); using var h = new Fixture(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }); using var c = new HttpClient(h);
    var r = await new OptimusSearchService(c).SearchAsync("x", [], null, default);
    Check(r.Error != null && stream.BytesRead <= 1024 * 1024 + 1 && stream.BytesRead > 0 && stream.Closed, "Actual bounded read and stream disposal");
});
Test("known oversized content is rejected before opening its stream", async () => {
    var stream = new EndlessStream(); var content = new StreamContent(stream); content.Headers.ContentLength = 1024 * 1024 + 1;
    using var h = new Fixture(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = content }); using var c = new HttpClient(h);
    Check((await new OptimusSearchService(c).SearchAsync("x", [], null, default)).Error != null && stream.BytesRead == 0, "Header bound");
});
Test("caller cancellation interrupts a pending body read", async () => {
    var stream = new PendingStream(); using var h = new Fixture(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }); using var c = new HttpClient(h); using var cancel = new CancellationTokenSource();
    var pending = new OptimusSearchService(c).SearchAsync("x", [], null, cancel.Token);
    await stream.Started.Task.WaitAsync(TimeSpan.FromSeconds(1)); cancel.Cancel(); bool canceled = false;
    try { await pending.WaitAsync(TimeSpan.FromSeconds(1)); } catch (OperationCanceledException) { canceled = true; }
    Check(canceled && stream.Closed, "Cancellation propagates and closes body");
});
Test("ten second deadline includes body streaming and surfaces timeout", async () => {
    var stream = new PendingStream(); using var h = new Fixture(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }); using var c = new HttpClient(h);
    var watch = System.Diagnostics.Stopwatch.StartNew(); var r = await new OptimusSearchService(c).SearchAsync("x", [], null, default).WaitAsync(TimeSpan.FromSeconds(12));
    Check(r.Error != null && watch.Elapsed >= TimeSpan.FromSeconds(9) && stream.Closed, "10s deadline cancels streaming with visible timeout");
});
foreach(var reason in new[]{"restart gate blocked","window closing"})Test("Embedded Buscar and Enter shared submission rejects "+reason,async()=>{int requests=0;using var handler=new Fixture(_=>{requests++;return Reply(wiki);});using var client=new HttpClient(handler);using var hostLifetime=new CancellationTokenSource();bool eligible=true;using var submissions=new SearchSubmissionGate(new OptimusSearchService(client),()=>eligible,hostLifetime.Token);if(reason=="restart gate blocked")eligible=false;else hostLifetime.Cancel();submissions.Disable();var button=await submissions.SearchAsync("Madrid",[],null);var enter=await submissions.SearchAsync("Madrid",[],null);Check(button==null&&enter==null&&requests==0,"Button and Enter must not reach HTTP or yield displayable results");eligible=true;Check(await submissions.SearchAsync("Madrid",[],null)==null&&requests==0,"Permanent disable cannot be revived by later host predicate changes");});
Test("Search host lifetime cancels pending embedded submission",async()=>{var stream=new PendingStream();using var handler=new Fixture(_=>new HttpResponseMessage(HttpStatusCode.OK){Content=new StreamContent(stream)});using var client=new HttpClient(handler);using var hostLifetime=new CancellationTokenSource();using var submissions=new SearchSubmissionGate(new OptimusSearchService(client),()=>true,hostLifetime.Token);var pending=submissions.SearchAsync("Madrid",[],null);await stream.Started.Task.WaitAsync(TimeSpan.FromSeconds(1));hostLifetime.Cancel();bool canceled=false;try{var response=await pending.WaitAsync(TimeSpan.FromSeconds(1));canceled=response==null;}catch(OperationCanceledException){canceled=true;}Check(canceled&&stream.Closed,"Owning host lifetime cancels body read even when form caller passes no token");});
Test("Shared native form sends only while host is eligible and may resume after temporary suspension",async()=>{int requests=0;using var handler=new Fixture(_=>{requests++;return Reply(wiki);});using var client=new HttpClient(handler);bool eligible=true;using var submissions=new SearchSubmissionGate(new OptimusSearchService(client),()=>eligible,default);Check((await submissions.SearchAsync("Madrid",[],null))?.Results.Count==1&&requests==1,"Eligible native search uses actual provider service");eligible=false;Check(await submissions.SearchAsync("Madrid",[],null)==null&&await submissions.SearchAsync("Madrid",[],null)==null&&requests==1,"Both shared form submissions reject temporary host suspension without depending on Disable");eligible=true;Check((await submissions.SearchAsync("Madrid",[],null))?.Results.Count==1&&requests==2,"A temporary clear gate may release without permanently disabling search");});
int failed = 0;
foreach (var t in tests) { try { await t.Run(); Console.WriteLine("PASS " + t.Name); } catch (Exception e) { failed++; Console.WriteLine("FAIL " + t.Name + ": " + e.Message); } }
Console.WriteLine($"{tests.Count - failed}/{tests.Count} checks PASS"); return failed == 0 ? 0 : 1;

static HttpResponseMessage Reply(string body) => new(HttpStatusCode.OK) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
sealed class Fixture(Func<HttpRequestMessage, HttpResponseMessage> reply) : HttpMessageHandler
{
    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) { cancellationToken.ThrowIfCancellationRequested(); return Task.FromResult(reply(request)); }
}
class EndlessStream : Stream
{
    public long BytesRead { get; private set; }
    public bool Closed { get; private set; }
    public override bool CanRead => true; public override bool CanSeek => false; public override bool CanWrite => false;
    public override long Length => throw new NotSupportedException(); public override long Position { get => BytesRead; set => throw new NotSupportedException(); }
    public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken token = default) { token.ThrowIfCancellationRequested(); buffer.Span.Fill((byte)'x'); BytesRead += buffer.Length; return ValueTask.FromResult(buffer.Length); }
    public override int Read(byte[] buffer, int offset, int count) { Array.Fill(buffer, (byte)'x', offset, count); BytesRead += count; return count; }
    protected override void Dispose(bool disposing) { Closed = true; base.Dispose(disposing); }
    public override void Flush() => throw new NotSupportedException(); public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException(); public override void SetLength(long value) => throw new NotSupportedException(); public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
}
sealed class PendingStream : EndlessStream
{
    public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
    public override async ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken token = default) { Started.TrySetResult(); await Task.Delay(Timeout.InfiniteTimeSpan, token); return 0; }
}
