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
    using var c = new HttpClient(h); var s = new OptimusSearchService(c, _ => TestTransport.Borrow(c));
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
    var r = await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("Madrid & sol", [], null, default);
    Check(r.Error == null && r.Provider.Contains("Wikipedia") && r.Results.Count == 1, "Wikipedia provenance");
    Check(r.Results[0] == new SearchResult("Madrid & región", "https://es.wikipedia.org/?curid=19", "La capital & ciudad", "Wikipedia"), "Plain text and pageid URL");
});
Test("bookmarks are matched locally validated deduplicated and never leak when omitted", async () => {
    using var h = new Fixture(_ => Reply(wiki)); using var c = new HttpClient(h); var s = new OptimusSearchService(c, _ => TestTransport.Borrow(c));
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
    var r = await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("sol & luna", [], "https://search.example/instance", default);
    Check(r.Error == null && r.Provider.Contains("SearXNG") && r.Results.Count == 2, "Safe unique SearXNG results");
    Check(r.Results[0].Title == "Sol" && r.Results[0].Snippet == "Texto & luz" && r.Results[1].Title == "Safe" && !r.Results[1].Snippet.Contains('<'), "Markup becomes plain text");
});
Test("endpoint policy rejects credentials remote HTTP and malformed destinations", async () => {
    foreach (var value in new[] { "https://search.example", "https://search.example/search", "http://localhost:8080", "http://127.0.0.1:8080", "http://[::1]:8080" })
        Check(OptimusSearchService.IsValidEndpoint(value), "Valid endpoint " + value);
    using var h = new Fixture(_ => throw new Exception("Invalid endpoint reached network")); using var c = new HttpClient(h);
    foreach (var value in new[] { "", "http://search.example", "http://localhost.evil.test", "https://a:b@search.example", "file:///x", "https://search.example/?q=secret", "https://search.example/#x", "https://search.example/\nsecret", "https://search.example\\evil" }) {
        Check(!OptimusSearchService.IsValidEndpoint(value), "Rejected endpoint " + value);
        Check((await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x", [], value, default)).Error != null, "Visible endpoint error without fallback");
    }
});
Test("malformed API error and redirects remain visible with local results", async () => {
    foreach (var body in new[] { "{broken", "{}", "{\"error\":{\"code\":\"badvalue\",\"info\":\"invalid request\"}}" }) {
        using var h = new Fixture(_ => Reply(body)); using var c = new HttpClient(h);
        var r = await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x", [new("x local", "https://local.example")], null, default);
        Check(r.Error != null && r.Results.Count == 1 && r.Provider.Contains("Wikipedia"), "Visible provider failure and preserved local result");
    }
    foreach (var code in new[] { HttpStatusCode.Redirect, HttpStatusCode.Forbidden, HttpStatusCode.InternalServerError }) {
        using var h = new Fixture(_ => new HttpResponseMessage(code) { Headers = { Location = new Uri("https://other.example") } }); using var c = new HttpClient(h);
        Check((await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x", [], null, default)).Error != null, "HTTP failures cannot become empty success");
    }
});
Test("invalid Wikipedia pageids are excluded and all sources share limit20", async () => {
    var body = "{\"query\":{\"search\":[{\"pageid\":0,\"title\":\"bad\"},{\"pageid\":-1,\"title\":\"bad\"},{\"pageid\":\"https://evil.example\",\"title\":\"bad\"},{\"pageid\":12,\"title\":\"good\",\"snippet\":\"text\"}]}}";
    using var h = new Fixture(_ => Reply(body)); using var c = new HttpClient(h); var s = new OptimusSearchService(c, _ => TestTransport.Borrow(c));
    var r = await s.SearchAsync("x", [], null, default);
    Check(r.Results.Count == 1 && r.Results[0].Url == "https://es.wikipedia.org/?curid=12", "Validated positive integer pageid only");
    var bookmarks = Enumerable.Range(0, 30).Select(i => new Bookmark("x " + i, "https://example.org/" + i)).ToArray();
    Check((await s.SearchAsync("x", bookmarks, null, default)).Results.Count == 20, "20 total results");
});
Test("a chunked response stops reading at1MiB without buffering whole body", async () => {
    var stream = new EndlessStream(); using var h = new Fixture(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }); using var c = new HttpClient(h);
    var r = await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x", [], null, default);
    Check(r.Error != null && stream.BytesRead <= 1024 * 1024 + 1 && stream.BytesRead > 0 && stream.Closed, "Actual bounded read and stream disposal");
});
Test("known oversized content is rejected before opening its stream", async () => {
    var stream = new EndlessStream(); var content = new StreamContent(stream); content.Headers.ContentLength = 1024 * 1024 + 1;
    using var h = new Fixture(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = content }); using var c = new HttpClient(h);
    Check((await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x", [], null, default)).Error != null && stream.BytesRead == 0, "Header bound");
});
Test("caller cancellation interrupts a pending body read", async () => {
    var stream = new PendingStream(); using var h = new Fixture(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }); using var c = new HttpClient(h); using var cancel = new CancellationTokenSource();
    var pending = new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x", [], null, cancel.Token);
    await stream.Started.Task.WaitAsync(TimeSpan.FromSeconds(1)); cancel.Cancel(); bool canceled = false;
    try { await pending.WaitAsync(TimeSpan.FromSeconds(1)); } catch (OperationCanceledException) { canceled = true; }
    Check(canceled && stream.Closed, "Cancellation propagates and closes body");
});
Test("ten second deadline includes body streaming and surfaces timeout", async () => {
    var stream = new PendingStream(); using var h = new Fixture(_ => new HttpResponseMessage(HttpStatusCode.OK) { Content = new StreamContent(stream) }); using var c = new HttpClient(h);
    var watch = System.Diagnostics.Stopwatch.StartNew(); var r = await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x", [], null, default).WaitAsync(TimeSpan.FromSeconds(12));
    Check(r.Error != null && watch.Elapsed >= TimeSpan.FromSeconds(9) && stream.Closed, "10s deadline cancels streaming with visible timeout");
});
foreach(var reason in new[]{"restart gate blocked","window closing"})Test("Embedded Buscar and Enter shared submission rejects "+reason,async()=>{int requests=0;using var handler=new Fixture(_=>{requests++;return Reply(wiki);});using var client=new HttpClient(handler);using var hostLifetime=new CancellationTokenSource();bool eligible=true;using var submissions=new SearchSubmissionGate(new OptimusSearchService(client, _ => TestTransport.Borrow(client)),()=>eligible,hostLifetime.Token);if(reason=="restart gate blocked")eligible=false;else hostLifetime.Cancel();submissions.Disable();var button=await submissions.SearchAsync("Madrid",[],null);var enter=await submissions.SearchAsync("Madrid",[],null);Check(button==null&&enter==null&&requests==0,"Button and Enter must not reach HTTP or yield displayable results");eligible=true;Check(await submissions.SearchAsync("Madrid",[],null)==null&&requests==0,"Permanent disable cannot be revived by later host predicate changes");});
Test("Search host lifetime cancels pending embedded submission",async()=>{var stream=new PendingStream();using var handler=new Fixture(_=>new HttpResponseMessage(HttpStatusCode.OK){Content=new StreamContent(stream)});using var client=new HttpClient(handler);using var hostLifetime=new CancellationTokenSource();using var submissions=new SearchSubmissionGate(new OptimusSearchService(client, _ => TestTransport.Borrow(client)),()=>true,hostLifetime.Token);var pending=submissions.SearchAsync("Madrid",[],null);await stream.Started.Task.WaitAsync(TimeSpan.FromSeconds(1));hostLifetime.Cancel();bool canceled=false;try{var response=await pending.WaitAsync(TimeSpan.FromSeconds(1));canceled=response==null;}catch(OperationCanceledException){canceled=true;}Check(canceled&&stream.Closed,"Owning host lifetime cancels body read even when form caller passes no token");});
Test("Shared native form sends only while host is eligible and may resume after temporary suspension",async()=>{int requests=0;using var handler=new Fixture(_=>{requests++;return Reply(wiki);});using var client=new HttpClient(handler);bool eligible=true;using var submissions=new SearchSubmissionGate(new OptimusSearchService(client, _ => TestTransport.Borrow(client)),()=>eligible,default);Check((await submissions.SearchAsync("Madrid",[],null))?.Results.Count==1&&requests==1,"Eligible native search uses actual provider service");eligible=false;Check(await submissions.SearchAsync("Madrid",[],null)==null&&await submissions.SearchAsync("Madrid",[],null)==null&&requests==1,"Both shared form submissions reject temporary host suspension without depending on Disable");eligible=true;Check((await submissions.SearchAsync("Madrid",[],null))?.Results.Count==1&&requests==2,"A temporary clear gate may release without permanently disabling search");});
// These checks catch default-source fallback, token disclosure and accepting arbitrary SearXNG as Optimus.
const string localBody = """{"query":"sol & luna","results":[{"title":"Sol","url":"https://example.org/a#part","content":"Luz","source":"Proveedor fixture"}],"optimus":{"version":1,"scope":"web","webConfigured":true,"indexedDocuments":3}}""";
var bearer = new string('a',64);
Test("typed Web defaults to authenticated local protocol without fallback",async()=>{
 using var h=new Fixture(r=>{Check(r.RequestUri!.AbsoluteUri=="https://127.0.0.1:17831/search?format=json&q=sol%20%26%20luna&scope=web&language=es","Fixed local Web URL");Check(r.Headers.Authorization?.ToString()=="Bearer "+bearer,"Local auth header");return Reply(localBody);});using var c=new HttpClient(h);
 var result=await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("sol & luna",[],new OptimusSearchTarget(OptimusSearchScope.Web,null,bearer),default);
 Check(result.Error==null&&result.Provider.Contains("Web")&&result.Results.Single().Source=="Proveedor fixture","Protocol validated result and provenance");
});
Test("typed Index stays local and Wikipedia is explicit without local bearer",async()=>{
 using var h=new Fixture(r=>{if(r.RequestUri!.Host=="es.wikipedia.org"){Check(r.Headers.Authorization==null,"Never leak local token to Wiki");return Reply(wiki);}Check(r.RequestUri.Query.Contains("scope=index"),"Index scope");return Reply(localBody.Replace("\"scope\":\"web\"","\"scope\":\"index\""));});using var c=new HttpClient(h);var s=new OptimusSearchService(c, _ => TestTransport.Borrow(c));
 Check((await s.SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Index,null,bearer),default)).Error==null,"Index response");
 Check((await s.SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Wikipedia,"https://ignored.example",bearer),default)).Results.Single().Source=="Wikipedia","Explicit Wikipedia");
});
Test("typed target rejects absent invalid token and nonfixed endpoints before sending",async()=>{
 using var h=new Fixture(_=>throw new Exception("Invalid configuration reached network"));using var c=new HttpClient(h);var s=new OptimusSearchService(c, _ => TestTransport.Borrow(c));
 foreach(var token in new string?[]{null,"",new string('a',63),new string('g',64),bearer+"\n"})Check((await s.SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Web,null,token),default)).Error!=null,"Token fail closed");
 foreach(var endpoint in new[]{"https://example.org","http://localhost:17831","http://127.0.0.1:17832","http://127.0.0.1:17831/path","http://127.0.0.1:17831/?x=1"})Check((await s.SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Web,endpoint,bearer),default)).Error!=null,"Fixed local endpoint only");
});
Test("typed client rejects missing wrong-scope malformed protocol and provider errors",async()=>{
 foreach(var body in new[]{"{\"results\":[]}",localBody.Replace("\"version\":1","\"version\":2"),localBody.Replace("\"scope\":\"web\"","\"scope\":\"index\""),localBody.Replace("\"indexedDocuments\":3","\"indexedDocuments\":-1"),localBody.Replace("\"query\":","\"error\":\"upstream-error\",\"query\":")}){using var h=new Fixture(_=>Reply(body));using var c=new HttpClient(h);Check((await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Web,null,bearer),default)).Error!=null,"Must show protocol/provider error");}
 foreach(var status in new[]{HttpStatusCode.Unauthorized,HttpStatusCode.ServiceUnavailable,HttpStatusCode.BadGateway,HttpStatusCode.GatewayTimeout}){using var h=new Fixture(_=>new HttpResponseMessage(status));using var c=new HttpClient(h);Check((await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Web,null,bearer),default)).Error!=null,"Provider errors visible");}
});
Test("typed gate invalidation cancels body and rejects stale results without resubmission",async()=>{
 var stream=new PendingStream();int requests=0;using var h=new Fixture(_=>{requests++;return new HttpResponseMessage(HttpStatusCode.OK){Content=new StreamContent(stream)};});using var c=new HttpClient(h);using var gate=new SearchSubmissionGate(new OptimusSearchService(c, _ => TestTransport.Borrow(c)),()=>true,default);
 var pending=gate.SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Web,null,bearer));await stream.Started.Task.WaitAsync(TimeSpan.FromSeconds(1));gate.Invalidate();Check(await pending.WaitAsync(TimeSpan.FromSeconds(1))==null&&stream.Closed&&requests==1,"Edit cancels without network submit");gate.Disable();Check(await gate.SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Web,null,bearer))==null&&requests==1,"Disable terminal");
});
Test("launcher validates profile token before any startup and never exposes secret in arguments",async()=>{
 var directory=Path.Combine(Path.GetTempPath(),"optimus-launch-"+Guid.NewGuid());Directory.CreateDirectory(Path.Combine(directory,"Optimus","Search"));
 try{var path=Path.Combine(directory,"Optimus","Search","service.token");await File.WriteAllTextAsync(path,"invalid");using var h=new Fixture(_=>throw new Exception("Invalid token reached health"));using var c=new HttpClient(h);using var launcher=new SearchHostLauncher(c,directory,directory, localClientFactory: _ => TestTransport.Borrow(c));
 var result=await launcher.ConnectAsync(null,default);Check(result.Error!=null,"Invalid token fails closed");
 var info=SearchHostLauncher.CreateStartInfo(directory,"https://search.example/instance",path);Check(info.FileName==Path.Combine(directory,"Search","Optimus.SearchHost.exe")&&!info.UseShellExecute&&info.ArgumentList.SequenceEqual(new[]{"--token-file",path,"--searx-url","https://search.example/instance"}),"Only bundled executable and separate arguments");Check(!info.Arguments.Contains(bearer)&&!info.ArgumentList.Contains(bearer),"Token contents never commandline");
 }finally{Directory.Delete(directory,true);}
});
Test("launcher connects independent host without owning or reconfiguring it",async()=>{
 var directory=Path.Combine(Path.GetTempPath(),"optimus-launch-"+Guid.NewGuid());Directory.CreateDirectory(Path.Combine(directory,"Optimus","Search"));
 try{await File.WriteAllTextAsync(Path.Combine(directory,"Optimus","Search","service.token"),bearer);using var h=new Fixture(r=>{Check(r.RequestUri!.AbsoluteUri=="https://127.0.0.1:17831/health"&&r.Headers.Authorization==null,"Health contains no secret");return IdentityReply(r,bearer);});using var c=new HttpClient(h);using var launcher=new SearchHostLauncher(c,directory,directory, localClientFactory: _ => TestTransport.Borrow(c));Check(launcher.ConfigureUpstream(null).Contains("independiente"),"Unknown ownership cannot claim settings applied to independent service");var result=await launcher.ConnectAsync(null,default);Check(result.Error==null&&result.Target.BearerToken==bearer&&!launcher.OwnsProcess,"Independent host reused");Check(launcher.ConfigureUpstream("https://new.example").Contains("independiente"),"Explicit external reconfiguration limit");using var cancel=new CancellationTokenSource();cancel.Cancel();bool stopped=false;try{await launcher.ConnectAsync(null,cancel.Token);}catch(OperationCanceledException){stopped=true;}Check(stopped&&!launcher.OwnsProcess,"Canceled connect cannot start");
 }finally{Directory.Delete(directory,true);}
});
Test("typed protocol rejects wrong JSON field kinds without throwing",async()=>{
 foreach(var body in new[]{localBody.Replace("\"version\":1","\"version\":\"1\""),localBody.Replace("\"indexedDocuments\":3","\"indexedDocuments\":\"3\""),localBody.Replace("\"webConfigured\":true","\"webConfigured\":null")}){using var h=new Fixture(_=>Reply(body));using var c=new HttpClient(h);Check((await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Web,null,bearer),default)).Error!=null,"Malformed protocol must yield visible error");}
});
Test("typed results enforce exact text and destination bounds with fragment deduplication",async()=>{
 var results=new[]{new{title=new string('t',300),url="https://example.org/a#one",content=new string('s',1300),source="Web fixture"},new{title="duplicate",url="https://example.org/a#two",content="copy",source="Web fixture"},new{title="long url",url="https://example.org/"+new string('u',2048),content="bad",source="Web fixture"},new{title="expanded url",url="https://example.org/"+new string('é',400),content="bad",source="Web fixture"}};
 var body=JsonSerializer.Serialize(new{query="x",results,optimus=new{version=1,scope="web",webConfigured=true,indexedDocuments=0}});using var h=new Fixture(_=>Reply(body));using var c=new HttpClient(h);var result=await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Web,null,bearer),default);
 Check(result.Results.Count==1&&result.Results[0].Title.Length<=240&&result.Results[0].Snippet.Length<=1200,"Visible text caps include ellipsis; bad URLs and duplicate fragments omitted");
});
if(!OperatingSystem.IsWindows())
{
 Test("launcher stops only its actual owned process on reconfiguration and close",async()=>{
  using var host=new LocalProcessHost(bearer);using var other=System.Diagnostics.Process.Start("/bin/sleep","30")!;
  try{using var h=new Fixture(r=>File.Exists(host.PidPath)?IdentityReply(r,bearer):new HttpResponseMessage(HttpStatusCode.ServiceUnavailable));using var c=new HttpClient(h);using var launcher=new SearchHostLauncher(c,host.Directory,host.Directory, localClientFactory: _ => TestTransport.Borrow(c));var result=await launcher.ConnectAsync(null,default);Check(result.Error==null&&launcher.OwnsProcess,"Real bundled process launches");using var process=System.Diagnostics.Process.GetProcessById(int.Parse(await File.ReadAllTextAsync(host.PidPath)));launcher.ConfigureUpstream("https://new.example");await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(2));Check(!launcher.OwnsProcess&&!other.HasExited,"Reconfigure stops owned only");File.Delete(host.PidPath);await launcher.ConnectAsync("https://new.example",default);using var next=System.Diagnostics.Process.GetProcessById(int.Parse(await File.ReadAllTextAsync(host.PidPath)));launcher.Dispose();await next.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(2));Check(!launcher.OwnsProcess&&!other.HasExited,"Close terminates only the restarted owned process");}
  finally{other.Kill();await other.WaitForExitAsync();}
 });
 Test("launcher cancellation during readiness closes stream and terminates started process",async()=>{
  using var host=new LocalProcessHost(bearer);var stream=new PendingStream();int calls=0;using var h=new Fixture(r=>++calls==1?new HttpResponseMessage(HttpStatusCode.ServiceUnavailable):IdentityReply(r,bearer,new StreamContent(stream)));using var c=new HttpClient(h);using var launcher=new SearchHostLauncher(c,host.Directory,host.Directory, localClientFactory: _ => TestTransport.Borrow(c));using var cancel=new CancellationTokenSource();var pending=launcher.ConnectAsync(null,cancel.Token);await stream.Started.Task.WaitAsync(TimeSpan.FromSeconds(2));for(var i=0;i<20&&!File.Exists(host.PidPath);i++)await Task.Delay(10);using var process=System.Diagnostics.Process.GetProcessById(int.Parse(await File.ReadAllTextAsync(host.PidPath)));cancel.Cancel();bool canceled=false;try{await pending;}catch(OperationCanceledException){canceled=true;}await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(2));Check(canceled&&stream.Closed&&!launcher.OwnsProcess,"Canceled startup cannot retain its process or response stream");
 });
}
Test("typed successful protocol permits null error and reports indexed corpus size",async()=>{
 using var h=new Fixture(_=>Reply(localBody.Replace("\"scope\":\"web\"","\"scope\":\"index\"").Replace("\"query\":","\"error\":null,\"query\":")));using var c=new HttpClient(h);var result=await new OptimusSearchService(c, _ => TestTransport.Borrow(c)).SearchAsync("x",[],new OptimusSearchTarget(OptimusSearchScope.Index,null,bearer),default);Check(result.Error==null&&result.Provider.Contains("3 documentos"),"Null error is success and bounded corpus visible");
});
Test("launcher retains ownership and reports termination failure before reconfiguration",async()=>{
 var directory=Path.Combine(Path.GetTempPath(),"optimus-failed-stop-"+Guid.NewGuid());Directory.CreateDirectory(Path.Combine(directory,"Search"));Directory.CreateDirectory(Path.Combine(directory,"Optimus","Search"));
 try{await File.WriteAllTextAsync(Path.Combine(directory,"Search","Optimus.SearchHost.exe"),"");await File.WriteAllTextAsync(Path.Combine(directory,"Optimus","Search","service.token"),bearer);var process=new RefusingProcess();int probes=0;using var h=new Fixture(r=>++probes==1?new HttpResponseMessage(HttpStatusCode.ServiceUnavailable):IdentityReply(r,bearer));using var c=new HttpClient(h);using var launcher=new SearchHostLauncher(c,directory,directory,_=>process, localClientFactory: _ => TestTransport.Borrow(c));Check((await launcher.ConnectAsync(null,default)).Error==null&&launcher.OwnsProcess,"Owned process prepared");Check(launcher.ConfigureUpstream("https://new.example").Contains("No se pudo detener")&&launcher.OwnsProcess,"Failed stop retains ownership and reports that configuration was not applied");Check((await launcher.ConnectAsync("https://new.example",default)).Error!=null&&launcher.OwnsProcess,"No restart or old-config success after failure");launcher.Dispose();Check(launcher.ShutdownError!=null&&launcher.OwnsProcess,"Close cannot claim successful cleanup");process.AllowStop=true;launcher.Dispose();Check(!launcher.OwnsProcess&&launcher.ShutdownError==null,"Repeated close can retry retained owned resource");}
 finally{Directory.Delete(directory,true);}
});
IdentityProofTests.Register(Test);
int failed = 0;
foreach (var t in tests) { try { await t.Run(); Console.WriteLine("PASS " + t.Name); } catch (Exception e) { failed++; Console.WriteLine("FAIL " + t.Name + ": " + e.Message); } }
Console.WriteLine($"{tests.Count - failed}/{tests.Count} checks PASS"); return failed == 0 ? 0 : 1;

static HttpResponseMessage Reply(string body) => new(HttpStatusCode.OK) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
static HttpResponseMessage IdentityReply(HttpRequestMessage request, string token, HttpContent? content = null)
{
    var response = Reply("{\"name\":\"OptimusSearch\",\"version\":1}");
    if (content is not null) { response.Content.Dispose(); response.Content = content; }
    var nonce = request.Headers.GetValues("X-Optimus-Nonce").Single();
    var proof = System.Security.Cryptography.HMACSHA256.HashData(Encoding.ASCII.GetBytes(token), Encoding.ASCII.GetBytes($"OptimusSearch/v1|127.0.0.1:17831|{nonce}"));
    response.Headers.Add("X-Optimus-Proof", Convert.ToHexStringLower(proof));
    return response;
}
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

sealed class LocalProcessHost : IDisposable
{
 public string Directory {get;}=Path.Combine(Path.GetTempPath(),"optimus-owned-"+Guid.NewGuid());
 public string PidPath=>Path.Combine(Directory,"pid");
 public LocalProcessHost(string token)
 {
  System.IO.Directory.CreateDirectory(Path.Combine(Directory,"Search"));System.IO.Directory.CreateDirectory(Path.Combine(Directory,"Optimus","Search"));
  var executable=Path.Combine(Directory,"Search","Optimus.SearchHost.exe");
  File.WriteAllText(executable,"#!/bin/sh\nprintf '%s' '"+token+"' > \"$2\"\nprintf '%s' \"$$\" > '"+PidPath+"'\nexec /bin/sleep 30\n");
  if(!OperatingSystem.IsWindows())File.SetUnixFileMode(executable,UnixFileMode.UserRead|UnixFileMode.UserWrite|UnixFileMode.UserExecute);
 }
 public void Dispose()=>System.IO.Directory.Delete(Directory,true);
}

sealed class RefusingProcess : ISearchHostProcess
{
 public bool AllowStop {get;set;}
 public bool HasExited {get;private set;}
 public void Stop(){if(!AllowStop)throw new System.ComponentModel.Win32Exception("Synthetic OS termination denial");HasExited=true;}
 public void Dispose(){}
}

static class TestTransport
{
    public static HttpClient Borrow(HttpClient client) => new(new Forward(client));
    private sealed class Forward(HttpClient client) : HttpMessageHandler
    {
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            using var copy = new HttpRequestMessage(request.Method, request.RequestUri);
            foreach(var header in request.Headers) copy.Headers.TryAddWithoutValidation(header.Key,header.Value);
            return await client.SendAsync(copy, HttpCompletionOption.ResponseHeadersRead, token);
        }
    }
}
