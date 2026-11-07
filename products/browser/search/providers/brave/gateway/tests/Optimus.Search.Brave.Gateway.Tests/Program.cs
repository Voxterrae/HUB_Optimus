using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Optimus.Search.Brave;
using Optimus.Search.Brave.Gateway;

if (args is ["--try-quota", var workerPath]) { try { using var lease = PilotQuota.Open(workerPath); return 0; } catch (IOException) { return 23; } }
if (args is ["--crash-reservation", var registryPath, var quotaPath, var marker]) {
    await using var server=await GatewayServer.StartAsync(registryPath,quotaPath,async(_,_,token)=>{File.WriteAllText(marker,"entered");await Task.Delay(Timeout.Infinite,token);return [];});
    using var client=new HttpClient(new SocketsHttpHandler{UseProxy=false});using var request=new HttpRequestMessage(HttpMethod.Post,server.Address+"/v1/web/search"){Content=new StringContent("{\"query\":\"valid\",\"language\":\"en\"}",Encoding.UTF8,"application/json")};
    request.Headers.Authorization=new AuthenticationHeaderValue("Bearer",Fixture.Token);using var response=await client.SendAsync(request);return 1;
}
var tests = new List<(string Name, Func<Task> Run)>();
void Test(string name, Func<Task> run) => tests.Add((name, run));
void Check(bool value) { if (!value) throw new Exception("Assertion failed."); }
async Task Reject<T>(Func<Task> run) where T:Exception { try { await run(); } catch(T) { return; } throw new Exception("Expected " + typeof(T).Name); }
Test("quota persists reservations and stops at100 across reopen", () => {
    using var dir = new TempDirectory(); var path = Path.Combine(dir.Path, "quota"); PilotQuota.Initialize(path);
    using (var quota = PilotQuota.Open(path)) for (var i=0;i<37;i++) Check(quota.TryReserve());
    using (var quota = PilotQuota.Open(path)) { for(var i=37;i<100;i++) Check(quota.TryReserve()); Check(!quota.TryReserve()); }
    using(var quota = PilotQuota.Open(path)) Check(!quota.TryReserve()); return Task.CompletedTask;
});
Test("initialization never resets existing state", async () => {
    using var dir = new TempDirectory(); var path = Path.Combine(dir.Path,"quota"); PilotQuota.Initialize(path);
    using(var quota=PilotQuota.Open(path)) Check(quota.TryReserve());
    await Reject<IOException>(()=>{PilotQuota.Initialize(path);return Task.CompletedTask;});
    using(var quota=PilotQuota.Open(path)) {for(var i=1;i<100;i++)Check(quota.TryReserve());Check(!quota.TryReserve());}
});
Test("missing quota never auto-initializes", async () => {
    using var dir = new TempDirectory(); var path=Path.Combine(dir.Path,"missing");
    await Reject<IOException>(()=>{using var quota=PilotQuota.Open(path);return Task.CompletedTask;}); Check(!File.Exists(path));
});
foreach(var text in new[]{"", "garbage", "OptimusBraveQuota/v1\n100\n-1\n", "OptimusBraveQuota/v1\n100\n101\n", "OptimusBraveQuota/v1\n101\n0\n"}) Test("corrupt quota blocks startup " + tests.Count, async()=>{
    using var dir = new TempDirectory();var path=Path.Combine(dir.Path,"quota");File.WriteAllText(path,text);
    await Reject<IOException>(()=>{using var quota=PilotQuota.Open(path);return Task.CompletedTask;});
});
Test("quota lease excludes second independent process", async()=>{
    using var dir = new TempDirectory();var path=Path.Combine(dir.Path,"quota");PilotQuota.Initialize(path);
    using var quota=PilotQuota.Open(path);
    var start=new ProcessStartInfo("dotnet"){RedirectStandardOutput=true,RedirectStandardError=true};
    start.ArgumentList.Add(typeof(TempDirectory).Assembly.Location);start.ArgumentList.Add("--try-quota");start.ArgumentList.Add(path);
    using var worker=Process.Start(start)!;using var deadline=new CancellationTokenSource(TimeSpan.FromSeconds(10));
    try {await worker.WaitForExitAsync(deadline.Token);} finally {if(!worker.HasExited)worker.Kill(entireProcessTree:true);}
    Check(worker.ExitCode==23 && (await worker.StandardOutput.ReadToEndAsync()).Length==0 && (await worker.StandardError.ReadToEndAsync()).Length==0);
});
Test("process death after upstream entry leaves a blocked pending pilot",async()=>{
    await using var fixture=await Fixture.Create();await fixture.Stop();var marker=fixture.QuotaPath+".entered";
    var start=new ProcessStartInfo("dotnet"){RedirectStandardOutput=true,RedirectStandardError=true};
    foreach(var value in new[]{typeof(TempDirectory).Assembly.Location,"--crash-reservation",fixture.CredentialPath,fixture.QuotaPath,marker})start.ArgumentList.Add(value);
    using var worker=Process.Start(start)!;using var deadline=new CancellationTokenSource(TimeSpan.FromSeconds(10));
    try{while(!File.Exists(marker)){Check(!worker.HasExited);await Task.Delay(20,deadline.Token);}}
    finally{if(!worker.HasExited)worker.Kill(entireProcessTree:true);await worker.WaitForExitAsync();}
    await Reject<IOException>(()=>{using var quota=PilotQuota.Open(fixture.QuotaPath);return Task.CompletedTask;});
});
Test("real HTTP authenticates and returns bounded Brave source without query echo", async()=>{
    await using var fixture=await Fixture.Create();using var response=await fixture.Send();
    Check(response.StatusCode==HttpStatusCode.OK && fixture.Calls==1);
    var body=await response.Content.ReadAsStringAsync();using var json=JsonDocument.Parse(body);
    Check(json.RootElement.GetProperty("version").GetInt32()==1 && json.RootElement.GetProperty("source").GetString()=="Brave");
    Check(json.RootElement.GetProperty("results")[0].GetProperty("title").GetString()=="Synthetic help");
    Check(!body.Contains("query") && response.Headers.CacheControl?.NoStore==true && !response.Headers.Contains("Set-Cookie") && !response.Headers.Contains("Access-Control-Allow-Origin"));
});
foreach(var token in new string?[]{null,"bad",new string('b',64)}) Test("rejects invalid bearer before forwarding " + tests.Count,async()=>{
    await using var fixture=await Fixture.Create();using var response=await fixture.Send(token:token);
    Check(response.StatusCode==HttpStatusCode.Unauthorized && fixture.Calls==0);
});
Test("expiry and registry revocation take effect on next request",async()=>{
    await using var fixture=await Fixture.Create();
    fixture.Registry(DateTimeOffset.UtcNow.AddMinutes(-1));using(var response=await fixture.Send())Check(response.StatusCode==HttpStatusCode.Unauthorized);
    fixture.Registry(DateTimeOffset.UtcNow.AddMinutes(5));using(var response=await fixture.Send())Check(response.StatusCode==HttpStatusCode.OK);
    File.WriteAllText(fixture.CredentialPath,"invalid");using(var response=await fixture.Send())Check(response.StatusCode==HttpStatusCode.Unauthorized);
    File.Delete(fixture.CredentialPath);using(var response=await fixture.Send())Check(response.StatusCode==HttpStatusCode.Unauthorized);Check(fixture.Calls==1);
});
foreach(var body in new[]{"{}","[]","{\"query\":\"valid\",\"query\":\"other\",\"language\":\"en\"}","{\"query\":\"valid\",\"language\":\"it\"}","{\"query\":\"bad\\nquery\",\"language\":\"en\"}","{\"query\":\"valid\",\"language\":\"en\",\"endpoint\":\"https://example.org\"}",JsonSerializer.Serialize(new{query=new string('a',501),language="en"}),JsonSerializer.Serialize(new{query=string.Join(' ',Enumerable.Repeat("a",76)),language="en"})})Test("malformed input consumes no reservation " + tests.Count,async()=>{
    await using var fixture=await Fixture.Create();using(var response=await fixture.Send(body:body))Check(response.StatusCode==HttpStatusCode.BadRequest);
    Check(fixture.Calls==0);await fixture.Stop();using var quota=PilotQuota.Open(fixture.QuotaPath);for(var i=0;i<100;i++)Check(quota.TryReserve());Check(!quota.TryReserve());
});
Test("unsupported content type and oversized body never forward",async()=>{
    await using var fixture=await Fixture.Create();using(var response=await fixture.Send(mediaType:"text/plain"))Check(response.StatusCode==HttpStatusCode.UnsupportedMediaType);
    using(var response=await fixture.Send(body:new string('x',4097)))Check(response.StatusCode==HttpStatusCode.RequestEntityTooLarge);Check(fixture.Calls==0);
});
Test("origin host method and URL query are rejected",async()=>{
    await using var fixture=await Fixture.Create();
    using(var response=await fixture.Send(origin:"https://example.org"))Check(response.StatusCode==HttpStatusCode.Forbidden);
    using(var response=await fixture.Send(host:"example.org"))Check(response.StatusCode==HttpStatusCode.Forbidden);
    using(var response=await fixture.Send(method:HttpMethod.Get))Check(response.StatusCode==HttpStatusCode.MethodNotAllowed);
    using(var response=await fixture.Send(path:"/v1/web/search?query=private"))Check(response.StatusCode==HttpStatusCode.BadRequest);Check(fixture.Calls==0);
});
Test("upstream failure spends one durable attempt and error stays generic",async()=>{
    await using var fixture=await Fixture.Create((_,_,_)=>throw new BraveSearchException(BraveSearchFailure.Transport));
    using(var response=await fixture.Send()){Check(response.StatusCode==HttpStatusCode.BadGateway);Check((await response.Content.ReadAsStringAsync())=="{\"error\":\"upstream-failed\"}");}
    Check(fixture.Calls==1);await fixture.Stop();using var quota=PilotQuota.Open(fixture.QuotaPath);for(var i=1;i<100;i++)Check(quota.TryReserve());Check(!quota.TryReserve());
});
Test("exhausted durable quota prevents any provider call",async()=>{
    await using var fixture=await Fixture.Create(exhausted:true);using var response=await fixture.Send();Check(response.StatusCode==HttpStatusCode.TooManyRequests && fixture.Calls==0);
});
Test("only one in-flight call is admitted and busy request costs nothing",async()=>{
    var started=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);var release=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
    await using var fixture=await Fixture.Create(async(_,_,token)=>{started.TrySetResult();await release.Task.WaitAsync(token);return [];});
    var first=fixture.Send();await started.Task.WaitAsync(TimeSpan.FromSeconds(3));
    using(var second=await fixture.Send())Check(second.StatusCode==HttpStatusCode.TooManyRequests);
    Check(fixture.Calls==1);release.TrySetResult();using(var response=await first)Check(response.StatusCode==HttpStatusCode.OK);
    await fixture.Stop();using var quota=PilotQuota.Open(fixture.QuotaPath);for(var i=1;i<100;i++)Check(quota.TryReserve());Check(!quota.TryReserve());
});
Test("caller disconnect cancels provider but never refunds the attempt",async()=>{
    var started=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);var cancelled=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
    await using var fixture=await Fixture.Create(async(_,_,token)=>{started.TrySetResult();try{await Task.Delay(Timeout.Infinite,token);}finally{cancelled.TrySetResult();}return [];});
    using var stop=new CancellationTokenSource();var pending=fixture.Send(cancellationToken:stop.Token);await started.Task.WaitAsync(TimeSpan.FromSeconds(3));stop.Cancel();await Reject<OperationCanceledException>(async()=>{using var response=await pending;});await cancelled.Task.WaitAsync(TimeSpan.FromSeconds(3));
    await fixture.Stop();using var quota=PilotQuota.Open(fixture.QuotaPath);for(var i=1;i<100;i++)Check(quota.TryReserve());Check(!quota.TryReserve());
});
foreach(var kind in new[]{"io","argument"})Test("provider exception cannot be misclassified as client or ledger error "+kind,async()=>{
    await using var fixture=await Fixture.Create((_,_,_)=>kind=="io"?throw new IOException("synthetic-private-detail"):throw new ArgumentException("synthetic-private-detail"));
    using var response=await fixture.Send();Check(response.StatusCode==HttpStatusCode.BadGateway && (await response.Content.ReadAsStringAsync())=="{\"error\":\"upstream-failed\"}");
});
Test("noncooperative provider times out and poisons pilot before another admission",async()=>{
    var release=new TaskCompletionSource<IReadOnlyList<BraveSearchResult>>(TaskCreationOptions.RunContinuationsAsynchronously);
    await using var fixture=await Fixture.Create((_,_,_)=>release.Task);
    try{
        using(var response=await fixture.Send().WaitAsync(TimeSpan.FromSeconds(13)))Check(response.StatusCode==HttpStatusCode.GatewayTimeout);
        using(var response=await fixture.Send())Check(response.StatusCode==HttpStatusCode.ServiceUnavailable);
        Check(fixture.Calls==1);await fixture.Stop();await Reject<IOException>(()=>{using var quota=PilotQuota.Open(fixture.QuotaPath);return Task.CompletedTask;});
    }finally{release.TrySetResult([]);}
});
Test("request body deadline prevents slow authorized upload from reserving",async()=>{
    await using var fixture=await Fixture.Create();var uri=new Uri(fixture.Address);
    using var socket=new System.Net.Sockets.TcpClient();await socket.ConnectAsync(IPAddress.Loopback,uri.Port);
    await using var stream=socket.GetStream();var request=$"POST /v1/web/search HTTP/1.1\r\nHost: 127.0.0.1:{uri.Port}\r\nAuthorization: Bearer {Fixture.Token}\r\nContent-Type: application/json\r\nContent-Length: 100\r\n\r\n{{";
    await stream.WriteAsync(Encoding.ASCII.GetBytes(request));using var reader=new StreamReader(stream,Encoding.ASCII);
    var status=await reader.ReadLineAsync().WaitAsync(TimeSpan.FromSeconds(5));Check(status?.Contains("504")==true && fixture.Calls==0);
});
foreach(var registry in new[]{"{\"version\":1,\"version\":1,\"credentials\":[]}","{\"version\":\"1\",\"credentials\":[]}","{\"version\":1,\"credentials\":[]}",new string('x',8193)})Test("malformed registry fails closed "+tests.Count,async()=>{
    await using var fixture=await Fixture.Create();File.WriteAllText(fixture.CredentialPath,registry);using var response=await fixture.Send();Check(response.StatusCode==HttpStatusCode.Unauthorized && fixture.Calls==0);
});
if(!OperatingSystem.IsWindows()){
    Test("symlink quota file is rejected",async()=>{
        using var dir=new TempDirectory();var path=Path.Combine(dir.Path,"quota");PilotQuota.Initialize(path);var link=Path.Combine(dir.Path,"alias");File.CreateSymbolicLink(link,path);
        await Reject<IOException>(()=>{using var quota=PilotQuota.Open(link);return Task.CompletedTask;});
    });
    Test("unlinked live quota stops all further reservations",async()=>{
        using var dir=new TempDirectory();var path=Path.Combine(dir.Path,"quota");PilotQuota.Initialize(path);using var quota=PilotQuota.Open(path);Check(quota.TryReserve());File.Delete(path);
        await Reject<IOException>(()=>{quota.TryReserve();return Task.CompletedTask;});Check(!File.Exists(path));
    });
}
var failures=0;foreach(var test in tests){try{await test.Run();Console.WriteLine("PASS "+test.Name);}catch(Exception ex){failures++;Console.WriteLine("FAIL "+test.Name+" ("+ex.GetType().Name+")");}}
Console.WriteLine($"{tests.Count-failures}/{tests.Count} passed");return failures==0?0:1;

sealed class TempDirectory:IDisposable{
    public string Path{get;}=Directory.CreateTempSubdirectory("optimus-gateway-test-").FullName;
    public void Dispose()=>Directory.Delete(Path,recursive:true);
}
sealed class Fixture:IAsyncDisposable{
    private readonly TempDirectory directory=new();private GatewayServer? server;
    public const string Token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    public string CredentialPath=>Path.Combine(directory.Path,"credentials.json");public string QuotaPath=>Path.Combine(directory.Path,"quota");
    public string Address=>server!.Address;
    public int Calls{get;private set;}
    private readonly HttpClient client=new(new SocketsHttpHandler{UseProxy=false,AllowAutoRedirect=false}){Timeout=TimeSpan.FromSeconds(15)};
    public void Registry(DateTimeOffset expiry)=>File.WriteAllText(CredentialPath,JsonSerializer.Serialize(new{version=1,credentials=new[]{new{sha256=Convert.ToHexStringLower(SHA256.HashData(Encoding.ASCII.GetBytes(Token))),expiresUtc=expiry.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'",CultureInfo.InvariantCulture)}}}));
    public static async Task<Fixture>Create(Func<string,string,CancellationToken,Task<IReadOnlyList<BraveSearchResult>>>? search=null,bool exhausted=false){
        var fixture=new Fixture();try{fixture.Registry(DateTimeOffset.UtcNow.AddMinutes(5));PilotQuota.Initialize(fixture.QuotaPath);
            if(exhausted){using var quota=PilotQuota.Open(fixture.QuotaPath);for(var i=0;i<100;i++)quota.TryReserve();}
            fixture.server=await GatewayServer.StartAsync(fixture.CredentialPath,fixture.QuotaPath,(query,language,token)=>{fixture.Calls++;return search?.Invoke(query,language,token)??Task.FromResult<IReadOnlyList<BraveSearchResult>>([new("Synthetic help","https://example.org/help","Synthetic text","Brave")]);});return fixture;
        }catch{fixture.client.Dispose();fixture.directory.Dispose();throw;}
    }
    public async Task<HttpResponseMessage>Send(string? token=Token,string body="{\"query\":\"valid\",\"language\":\"en\"}",string mediaType="application/json",string? origin=null,string? host=null,HttpMethod? method=null,string path="/v1/web/search",CancellationToken cancellationToken=default){
        using var request=new HttpRequestMessage(method??HttpMethod.Post,server!.Address+path){Content=new StringContent(body,Encoding.UTF8,mediaType)};
        if(token!=null)request.Headers.TryAddWithoutValidation("Authorization","Bearer "+token);if(origin!=null)request.Headers.Add("Origin",origin);if(host!=null)request.Headers.Host=host;
        return await client.SendAsync(request,cancellationToken);
    }
    public async Task Stop(){if(server!=null){await server.DisposeAsync();server=null;}}
    public async ValueTask DisposeAsync(){await Stop();client.Dispose();directory.Dispose();}
}
