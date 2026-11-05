using System.Diagnostics;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Sockets;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Optimus.Search.Remote;

var tests = new List<(string Name, Func<Task> Run)>();
void Test(string name, Func<Task> run) => tests.Add((name, run));
void Equal<T>(T expected,T actual) { if(!EqualityComparer<T>.Default.Equals(expected,actual)) throw new Exception($"Expected {expected}; got {actual}"); }
void True(bool value) { if(!value) throw new Exception("Assertion failed"); }
async Task Reject(Func<Task> run) {try {await run();}catch(InvalidDataException){return;}throw new Exception("Expected invalid configuration rejection");}

Test("minimal loopback health and authenticated routes have safe headers",async()=>{
    await using var f=await Fixture.Start();
    using var h=await f.Client.GetAsync("/healthz"); Equal(HttpStatusCode.OK,h.StatusCode); Equal("{\"status\":\"ok\"}",await h.Content.ReadAsStringAsync());
    Equal("no-store",h.Headers.CacheControl!.ToString());Equal("nosniff",h.Headers.GetValues("X-Content-Type-Options").Single());Equal("no-referrer",h.Headers.GetValues("Referrer-Policy").Single());True(!h.Headers.Contains("Access-Control-Allow-Origin"));True(!h.Headers.Contains("Set-Cookie"));
    Equal(HttpStatusCode.Unauthorized,(await f.Client.GetAsync("/v1/catalog")).StatusCode);
    Equal(HttpStatusCode.Unauthorized,(await f.Search("contraste",auth:false)).StatusCode);
    True(f.Server.Address.StartsWith("http://127.0.0.1:",StringComparison.Ordinal));
});
Test("all eight topic mappings return authored full source and provenance without query echo",async()=>{
    await using var f=await Fixture.Start();
    foreach(var (query,urlSuffix) in new[]{("fuentes catálogo","README.md"),("token perfil","PROTOCOL.md"),("contraste","change-color-contrast-in-windows"),("atajos teclado","keyboard-shortcuts-in-windows"),("Container Apps","container-apps/overview"),("Blob Storage","storage-blobs-introduction"),("Entra autenticación","authentication-vs-authorization"),("presupuestos coste","tutorial-acm-create-budgets")}){
        using var r=await f.Search(query);Equal(HttpStatusCode.OK,r.StatusCode);var bytes=await r.Content.ReadAsByteArrayAsync();True(bytes.Length<=65536);
        using var json=JsonDocument.Parse(bytes);var root=json.RootElement;Equal(1,root.GetProperty("schemaVersion").GetInt32());True(!root.TryGetProperty("query",out _));
        var first=root.GetProperty("results")[0];True(first.GetProperty("url").GetString()!.EndsWith(urlSuffix,StringComparison.Ordinal));
        var doc=f.Documents.Single(x=>x.GetProperty("url").GetString()==first.GetProperty("url").GetString());Equal(doc.GetProperty("content").GetString(),first.GetProperty("content").GetString());Equal(doc.GetProperty("updatedUtc").GetString(),first.GetProperty("updatedUtc").GetString());True(first.GetProperty("source").GetString()!.StartsWith("Optimus"));
        Equal(Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(first.GetProperty("content").GetString()!))),first.GetProperty("provenance").GetProperty("summarySha256").GetString());
    }
    using var empty=await f.Search("zzzzunrelatedsyntheticneedle");using var emptyJson=JsonDocument.Parse(await empty.Content.ReadAsStringAsync());Equal(0,emptyJson.RootElement.GetProperty("results").GetArrayLength());
});
Test("catalog endpoint preserves reviewed exact raw source bytes and sidecar",async()=>{
    await using var f=await Fixture.Start();using var r=await f.GetCatalog();Equal(HttpStatusCode.OK,r.StatusCode);var bytes=await r.Content.ReadAsByteArrayAsync();True(bytes.Length<=65536);using var j=JsonDocument.Parse(bytes);var root=j.RootElement;
    foreach(var (file,base64,hash) in new[]{("public-pilot-v0.1.json","catalogBytesBase64","catalogSha256"),("public-pilot-v0.1.provenance.json","provenanceBytesBase64","provenanceSha256")}){
        var raw=Convert.FromBase64String(root.GetProperty(base64).GetString()!);var expected=await File.ReadAllBytesAsync(Path.Combine(Fixture.CatalogDirectory,file));True(raw.SequenceEqual(expected));Equal(Convert.ToHexStringLower(SHA256.HashData(raw)),root.GetProperty(hash).GetString());
    }
});
Test("strict auth rejects local, malformed, padded, duplicate and revoked credentials",async()=>{
    await using var f=await Fixture.Start();
    foreach(var auth in new[]{"", "Bearer "+new string('a',64),"Basic "+f.Secrets[0],"Bearer "+f.Secrets[0]+"=","Bearer  "+f.Secrets[0],"Bearer "+f.Secrets[0]+"x","Bearer "+Fixture.Secret(),"bearer "+f.Secrets[0]}){
        using var q=new HttpRequestMessage(HttpMethod.Get,"/v1/catalog");q.Headers.TryAddWithoutValidation("Authorization",auth);Equal(HttpStatusCode.Unauthorized,(await f.Client.SendAsync(q)).StatusCode);
    }
    using var duplicate=new HttpRequestMessage(HttpMethod.Get,"/v1/catalog");duplicate.Headers.TryAddWithoutValidation("Authorization",new[]{"Bearer "+f.Secrets[0],"Bearer "+f.Secrets[0]});Equal(HttpStatusCode.Unauthorized,(await f.Client.SendAsync(duplicate)).StatusCode);
    using var ok=await f.GetCatalog();Equal(HttpStatusCode.OK,ok.StatusCode);
    f.Clock.Advance(TimeSpan.FromHours(1));Equal(HttpStatusCode.Unauthorized,(await f.GetCatalog()).StatusCode);
    await using var revoked=await Fixture.Start();using var old=new HttpRequestMessage(HttpMethod.Get,"/v1/catalog");old.Headers.Authorization=new("Bearer",f.Secrets[0]);Equal(HttpStatusCode.Unauthorized,(await revoked.Client.SendAsync(old)).StatusCode);
});
Test("credential digest contract hashes canonical ASCII bearer text",async()=>{
    await using var f=await Fixture.Start();using var r=await f.GetCatalog();Equal(HttpStatusCode.OK,r.StatusCode);
});
Test("concurrent monotonic authentication samples cannot look like UTC rollback",async()=>{
    await using var f=new Fixture();using var clock=new OrderedAuthenticationClock(f.Clock.GetUtcNow());
    var type=typeof(RemoteServer).Assembly.GetType("Optimus.Search.Remote.CredentialRegistry",throwOnError:true)!;
    var loading=(Task)type.GetMethod("Load",BindingFlags.Public|BindingFlags.Static)!.Invoke(null,[f.RegistryPath,clock])!;
    await loading;var registry=loading.GetType().GetProperty("Result")!.GetValue(loading)!;
    var gate=type.GetField("gate",BindingFlags.NonPublic|BindingFlags.Instance)!.GetValue(registry)!;
    var authenticate=type.GetMethod("Authenticate",BindingFlags.Public|BindingFlags.Instance)!;
    clock.Arm(gate);
    Task<object?> RunAuthentication(bool second)=>Task.Factory.StartNew(()=>{
        try{return authenticate.Invoke(registry,["Bearer "+f.Secrets[0]]);}
        finally{if(second)clock.SecondCompleted.Set();}
    },CancellationToken.None,TaskCreationOptions.LongRunning,TaskScheduler.Default);
    var first=RunAuthentication(false);
    try{
        await clock.FirstSampled.Task.WaitAsync(TimeSpan.FromSeconds(5));
        var second=RunAuthentication(true);
        var results=await Task.WhenAll(first,second).WaitAsync(TimeSpan.FromSeconds(5));
        True(results.All(result=>result is not null));
    }finally{clock.SecondCompleted.Set();await first.WaitAsync(TimeSpan.FromSeconds(5));}
});
Test("actual UTC rollback still rejects an otherwise valid remote credential",async()=>{
    await using var f=await Fixture.Start();Equal(HttpStatusCode.OK,(await f.GetCatalog()).StatusCode);
    f.Clock.Advance(TimeSpan.FromSeconds(1));Equal(HttpStatusCode.OK,(await f.GetCatalog()).StatusCode);
    f.Clock.Advance(TimeSpan.FromSeconds(-1));Equal(HttpStatusCode.Unauthorized,(await f.GetCatalog()).StatusCode);
});
Test("GET endpoints reject supplied bodies before returning public or catalog content",async()=>{
    await using var f=await Fixture.Start();foreach(var path in new[]{"/healthz","/v1/catalog"}){using var q=new HttpRequestMessage(HttpMethod.Get,path);q.Headers.Authorization=new("Bearer",f.Secrets[0]);q.Content=new StringContent("synthetic_body");Equal(HttpStatusCode.BadRequest,(await f.Client.SendAsync(q)).StatusCode);}
});
Test("strict search JSON rejects missing, duplicate, unknown, types, depth and malformed Unicode",async()=>{
    await using var f=await Fixture.Start();
    foreach(var body in new[]{"{}","[]","null","{broken","{\"query\":\"help\"}","{\"query\":\"help\",\"limit\":1,\"limit\":2}","{\"query\":\"help\",\"query\":\"other\",\"limit\":1}","{\"query\":\"help\",\"limit\":1,\"extra\":true}","{\"Query\":\"help\",\"limit\":1}","{\"query\":true,\"limit\":1}","{\"query\":\"help\",\"limit\":1.0}","{\"query\":\"help\",\"limit\":\"1\"}","{\"query\":{\"a\":{\"b\":{\"c\":{\"d\":1}}}},\"limit\":1}","{\"query\":\"\\uD800\",\"limit\":1}","{\"query\":\"help\",\"limit\":1} {}","{\"query\":\"help\",\"limit\":1,}","{/*comment*/\"query\":\"help\",\"limit\":1}"}){
        using var r=await f.Body(body);Equal(HttpStatusCode.BadRequest,r.StatusCode);var text=await r.Content.ReadAsStringAsync();True(!text.Contains("help",StringComparison.Ordinal));
    }
    using var invalidUtf8=await f.Bytes([123,34,113,117,101,114,121,34,58,34,0xFF,34,44,34,108,105,109,105,116,34,58,49,125]);Equal(HttpStatusCode.BadRequest,invalidUtf8.StatusCode);
});
Test("query, result, declared and streamed body bounds are enforced",async()=>{
    await using var f=await Fixture.Start();
    foreach(var query in new[]{""," ",new string('x',501),"a\nb","a\0b"}) Equal(HttpStatusCode.BadRequest,(await f.Search(query)).StatusCode);
    foreach(var limit in new[]{-1,0,9,100}) Equal(HttpStatusCode.BadRequest,(await f.Search("Azure",limit)).StatusCode);
    Equal(HttpStatusCode.OK,(await f.Search(new string('x',500),8)).StatusCode);
    using var max=await f.Search("Azure",1);using var json=JsonDocument.Parse(await max.Content.ReadAsStringAsync());Equal(1,json.RootElement.GetProperty("results").GetArrayLength());
    Equal(HttpStatusCode.RequestEntityTooLarge,(await f.Body(new string(' ',2049))).StatusCode);
    Equal(413,await f.Raw("POST /v1/search HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer "+f.Secrets[0]+"\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n801\r\n"+new string(' ',2049)+"\r\n0\r\n\r\n"));
});
Test("HTTP boundary rejects query strings, origins, cookies, methods and content encodings",async()=>{
    await using var f=await Fixture.Start();
    foreach(var path in new[]{"/healthz?q=syntheticquery","/v1/catalog?x=1","/v1/search?query=secret"}){
        using var q=new HttpRequestMessage(HttpMethod.Get,path);q.Headers.Authorization=new("Bearer",f.Secrets[0]);Equal(HttpStatusCode.BadRequest,(await f.Client.SendAsync(q)).StatusCode);
    }
    Equal(400,await f.Raw("GET /healthz? HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"));
    foreach(var header in new[]{("Origin","https://example.test"),("Cookie","private=value")}){
        using var q=new HttpRequestMessage(HttpMethod.Get,"/v1/catalog");q.Headers.Authorization=new("Bearer",f.Secrets[0]);q.Headers.TryAddWithoutValidation(header.Item1,header.Item2);Equal(HttpStatusCode.Forbidden,(await f.Client.SendAsync(q)).StatusCode);
    }
    using var spoof=new HttpRequestMessage(HttpMethod.Get,"/v1/catalog");spoof.Headers.TryAddWithoutValidation("X-Forwarded-Proto","https");spoof.Headers.TryAddWithoutValidation("X-Forwarded-For","192.0.2.66");Equal(HttpStatusCode.Unauthorized,(await f.Client.SendAsync(spoof)).StatusCode);
    using var preflight=new HttpRequestMessage(HttpMethod.Options,"/v1/search");Equal(HttpStatusCode.MethodNotAllowed,(await f.Client.SendAsync(preflight)).StatusCode);
    using var badType=await f.Body("{}","text/plain");Equal(HttpStatusCode.UnsupportedMediaType,badType.StatusCode);
    using var encoded=new HttpRequestMessage(HttpMethod.Post,"/v1/search");encoded.Headers.Authorization=new("Bearer",f.Secrets[0]);encoded.Content=new StringContent("{}",Encoding.UTF8,"application/json");encoded.Content.Headers.ContentEncoding.Add("gzip");Equal(HttpStatusCode.UnsupportedMediaType,(await f.Client.SendAsync(encoded)).StatusCode);
});
Test("per client rate limit is 30 inclusive and deterministic minute reset",async()=>{
    await using var f=await Fixture.Start();for(var i=0;i<30;i++)Equal(HttpStatusCode.OK,(await f.GetCatalog()).StatusCode);Equal(HttpStatusCode.TooManyRequests,(await f.GetCatalog()).StatusCode);Equal(HttpStatusCode.OK,(await f.GetCatalog(1)).StatusCode);
    f.Clock.Advance(TimeSpan.FromSeconds(59));Equal(HttpStatusCode.TooManyRequests,(await f.GetCatalog()).StatusCode);f.Clock.Advance(TimeSpan.FromSeconds(1));Equal(HttpStatusCode.OK,(await f.GetCatalog()).StatusCode);
    f.Clock.Advance(TimeSpan.FromMinutes(-1));Equal(HttpStatusCode.Unauthorized,(await f.GetCatalog()).StatusCode);
});
Test("global rate limit includes health and unauthenticated traffic",async()=>{
    await using var f=await Fixture.Start();for(var i=0;i<120;i++)Equal(i%2==0?HttpStatusCode.OK:HttpStatusCode.Unauthorized,(await f.Client.GetAsync(i%2==0?"/healthz":"/v1/catalog")).StatusCode);Equal(HttpStatusCode.TooManyRequests,(await f.Client.GetAsync("/healthz")).StatusCode);f.Clock.Advance(TimeSpan.FromMinutes(1));Equal(HttpStatusCode.OK,(await f.Client.GetAsync("/healthz")).StatusCode);
});
Test("fifth request has no queue and disconnect releases active permits",async()=>{
    await using var f=await Fixture.Start();var held=new List<TcpClient>();try{
        for(var i=0;i<4;i++)held.Add(await f.HoldBody());
        await Task.Delay(150);var watch=Stopwatch.StartNew();Equal(HttpStatusCode.TooManyRequests,(await f.Client.GetAsync("/healthz")).StatusCode);True(watch.Elapsed<TimeSpan.FromSeconds(1));
    }finally{foreach(var s in held)s.Dispose();}
    var recovered=false;for(var i=0;i<15;i++){if((await f.Client.GetAsync("/healthz")).StatusCode==HttpStatusCode.OK){recovered=true;break;}await Task.Delay(20);}True(recovered);
});
Test("two second application deadline cancels slow chunked input",async()=>{
    await using var f=await Fixture.Start();using var tcp=await f.HoldBody();var watch=Stopwatch.StartNew();var status=await Fixture.ReadStatus(tcp.GetStream());Equal(408,status);True(watch.Elapsed>=TimeSpan.FromSeconds(1.5));True(watch.Elapsed<TimeSpan.FromSeconds(4));Equal(HttpStatusCode.OK,(await f.Client.GetAsync("/healthz")).StatusCode);
});
Test("catalog or provenance byte tampering fails before server bind",async()=>{
    foreach(var file in new[]{"public-pilot-v0.1.json","public-pilot-v0.1.provenance.json"}){
        await using var f=new Fixture();File.Copy(Path.Combine(Fixture.CatalogDirectory,file),Path.Combine(f.Directory,file));await File.AppendAllTextAsync(Path.Combine(f.Directory,file)," ");
        var cat=file.EndsWith("provenance.json",StringComparison.Ordinal)?Path.Combine(Fixture.CatalogDirectory,"public-pilot-v0.1.json"):Path.Combine(f.Directory,file);
        var prov=file.EndsWith("provenance.json",StringComparison.Ordinal)?Path.Combine(f.Directory,file):Path.Combine(Fixture.CatalogDirectory,"public-pilot-v0.1.provenance.json");
        await Reject(async()=>await RemoteServer.StartAsync(new(cat,prov,f.RegistryPath)));
    }
});
Test("invalid registries fail closed with unique bounded IDs hashes expiry and row count",async()=>{
    await using var f=new Fixture();var valid=new {clientId="client-a",secretSha256=Fixture.Hash(f.Secrets[0]),expiresUtc=f.Clock.GetUtcNow().AddHours(1)};
    var cases=new object[]{new{schemaVersion=1,clients=Array.Empty<object>()},new{schemaVersion=1,clients=new[]{valid,valid}},new{schemaVersion=1,clients=new[]{new{clientId="bad id",secretSha256=Fixture.Hash(f.Secrets[0]),expiresUtc=f.Clock.GetUtcNow().AddHours(1)}}},new{schemaVersion=1,clients=new[]{new{clientId="a",secretSha256="x",expiresUtc=f.Clock.GetUtcNow().AddHours(1)}}},new{schemaVersion=1,clients=new[]{new{clientId="a",secretSha256=Fixture.Hash(f.Secrets[0]),expiresUtc=f.Clock.GetUtcNow()}}},new{schemaVersion=1,clients=new[]{new{clientId="a",secretSha256=Fixture.Hash(f.Secrets[0]),expiresUtc=f.Clock.GetUtcNow().AddDays(7).AddSeconds(1)}}},new{schemaVersion=1,clients=Enumerable.Range(0,65).Select(i=>new{clientId="c"+i,secretSha256=Fixture.Hash(Fixture.Secret()),expiresUtc=f.Clock.GetUtcNow().AddHours(1)}).ToArray()},new{schemaVersion=1,clients=new[]{valid,new{clientId="client-b",secretSha256=Fixture.Hash(f.Secrets[0]),expiresUtc=f.Clock.GetUtcNow().AddHours(1)}}}};
    foreach(var c in cases){await File.WriteAllTextAsync(f.RegistryPath,JsonSerializer.Serialize(c));await Reject(async()=>await f.StartServer());}
    foreach(var text in new[]{"{broken","{\"schemaVersion\":1,\"schemaVersion\":1,\"clients\":[]}","{\"schemaVersion\":1,\"clients\":[],\"unknown\":1}"}){await File.WriteAllTextAsync(f.RegistryPath,text);await Reject(async()=>await f.StartServer());}
    File.Delete(f.RegistryPath);await Reject(async()=>await f.StartServer());
});
Test("CLI missing credentials fails with generic error and no private data",async()=>{
    var dll=typeof(RemoteServer).Assembly.Location;var start=new ProcessStartInfo(Environment.GetEnvironmentVariable("DOTNET_HOST_PATH")??"dotnet"){RedirectStandardOutput=true,RedirectStandardError=true,UseShellExecute=false};start.ArgumentList.Add(dll);start.Environment.Remove("OPTIMUS_REMOTE_CREDENTIALS_FILE");using var process=Process.Start(start)!;await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(10));Equal(2,process.ExitCode);Equal("",await process.StandardOutput.ReadToEndAsync());Equal("Remote search startup failed.\n",(await process.StandardError.ReadToEndAsync()).Replace("\r\n","\n",StringComparison.Ordinal));
});
Test("valid CLI ignores ambient network configuration and emits no private request diagnostics",async()=>{
    await using var f=new Fixture();var start=new ProcessStartInfo(Environment.GetEnvironmentVariable("DOTNET_HOST_PATH")??"dotnet"){RedirectStandardOutput=true,RedirectStandardError=true,UseShellExecute=false};start.ArgumentList.Add(typeof(RemoteServer).Assembly.Location);start.Environment["OPTIMUS_REMOTE_CREDENTIALS_FILE"]=f.RegistryPath;start.Environment.Remove("OPTIMUS_REMOTE_CONTAINER_HTTP");start.Environment["ASPNETCORE_URLS"]="http://0.0.0.0:18999";start.Environment["Kestrel__Endpoints__Injected__Url"]="http://0.0.0.0:18998";start.Environment["ASPNETCORE_ENVIRONMENT"]="Development";
    // CLI uses real UTC; give its synthetic registry a real one-hour lifetime.
    await File.WriteAllTextAsync(f.RegistryPath,JsonSerializer.Serialize(new{schemaVersion=1,clients=new[]{new{clientId="cli-client",secretSha256=Fixture.Hash(f.Secrets[0]),expiresUtc=DateTimeOffset.UtcNow.AddHours(1)}}}));
    using var process=Process.Start(start)!;var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
    try{
        using var client=new HttpClient(new SocketsHttpHandler{UseProxy=false,UseCookies=false}){BaseAddress=new Uri("http://127.0.0.1:8080"),Timeout=TimeSpan.FromSeconds(3)};var ready=false;for(var i=0;i<100;i++){try{if((await client.GetAsync("/healthz")).IsSuccessStatusCode){ready=true;break;}}catch(HttpRequestException){}if(process.HasExited)break;await Task.Delay(30);}True(ready);
        using var search=new HttpRequestMessage(HttpMethod.Post,"/v1/search");search.Headers.Authorization=new("Bearer",f.Secrets[0]);search.Content=new StringContent("{\"query\":\"synthetic_private_query_37\",\"limit\":1}",Encoding.UTF8,"application/json");Equal(HttpStatusCode.OK,(await client.SendAsync(search)).StatusCode);
        Equal(HttpStatusCode.BadRequest,(await client.GetAsync("/healthz?synthetic_private_query_37")).StatusCode);
        using var malformed=new TcpClient();await malformed.ConnectAsync(IPAddress.Loopback,8080);await malformed.GetStream().WriteAsync(Encoding.ASCII.GetBytes("INVALID /synthetic_private_query_37 HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer "+f.Secrets[0]+"\r\n\r\n"));_ = await Fixture.ReadStatus(malformed.GetStream());
        foreach(var port in new[]{18998,18999}){using var probe=new TcpClient();var listening=false;try{await probe.ConnectAsync(IPAddress.Loopback,port);listening=true;}catch(SocketException){}True(!listening);}
    }finally{
        if(!process.HasExited){if(!OperatingSystem.IsWindows()){using var signal=Process.Start(new ProcessStartInfo("kill"){ArgumentList={"-TERM",process.Id.ToString(System.Globalization.CultureInfo.InvariantCulture)},UseShellExecute=false})!;await signal.WaitForExitAsync();await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5));}else {process.Kill(true);await process.WaitForExitAsync();}}
    }
    if(!OperatingSystem.IsWindows())Equal(0,process.ExitCode);var logs=await stdout+await stderr;Equal("",logs);foreach(var secret in f.Secrets)True(!logs.Contains(secret,StringComparison.Ordinal));True(!logs.Contains("127.0.0.1",StringComparison.Ordinal));True(!logs.Contains("synthetic_private_query_37",StringComparison.Ordinal));
});
var failed=0;foreach(var test in tests){try{await test.Run();Console.WriteLine("PASS "+test.Name);}catch(Exception e){failed++;Console.WriteLine("FAIL "+test.Name+": "+e.GetType().Name+": "+e.Message);}}Console.WriteLine($"{tests.Count-failed}/{tests.Count} passed");return failed==0?0:1;

sealed class ManualClock:TimeProvider {private DateTimeOffset now=new(2026,11,4,0,0,0,TimeSpan.Zero);private long stamp;public override DateTimeOffset GetUtcNow()=>now;public override long TimestampFrequency=>TimeSpan.TicksPerSecond;public override long GetTimestamp()=>stamp;public void Advance(TimeSpan value){now+=value;if(value>TimeSpan.Zero)stamp+=value.Ticks;}}
sealed class OrderedAuthenticationClock(DateTimeOffset origin):TimeProvider,IDisposable {
    private object gate=null!;private bool armed;private int reads;
    public TaskCompletionSource<bool> FirstSampled{get;}=new(TaskCreationOptions.RunContinuationsAsynchronously);
    public ManualResetEventSlim SecondCompleted{get;}=new(false);
    public void Arm(object registryGate){gate=registryGate;Volatile.Write(ref armed,true);}
    public override DateTimeOffset GetUtcNow(){
        if(!Volatile.Read(ref armed))return origin;
        var order=Interlocked.Increment(ref reads);var sampled=origin.AddSeconds(order);
        if(order==1){
            FirstSampled.SetResult(true);
            // A sample outside the registry gate can be delayed until a later
            // caller publishes its newer sample. Under the gate, that caller
            // cannot sample yet; return immediately so it can proceed next.
            if(!Monitor.IsEntered(gate)&&!SecondCompleted.Wait(TimeSpan.FromSeconds(5)))throw new TimeoutException("Controlled authentication ordering did not complete.");
        }
        return sampled;
    }
    public void Dispose()=>SecondCompleted.Dispose();
}
sealed class Fixture:IAsyncDisposable {
    public static string CatalogDirectory=>Path.Combine(AppContext.BaseDirectory,"catalog");
    public string Directory{get;}=Path.Combine(Path.GetTempPath(),"optimus-remote-test-"+Guid.NewGuid().ToString("N"));
    public string RegistryPath=>Path.Combine(Directory,"registry.json");
    public string[] Secrets{get;}=Enumerable.Range(0,5).Select(_=>Secret()).ToArray();
    public ManualClock Clock{get;}=new();
    public RemoteServer Server{get;private set;}=null!;
    public HttpClient Client{get;private set;}=null!;
    public JsonElement[] Documents{get;}
    public Fixture(){System.IO.Directory.CreateDirectory(Directory);File.WriteAllText(RegistryPath,JsonSerializer.Serialize(new{schemaVersion=1,clients=Secrets.Select((s,i)=>new{clientId="client-"+i,secretSha256=Hash(s),expiresUtc=Clock.GetUtcNow().AddHours(1)})}));using var json=JsonDocument.Parse(File.ReadAllBytes(Path.Combine(CatalogDirectory,"public-pilot-v0.1.json")));Documents=json.RootElement.GetProperty("documents").EnumerateArray().Select(d=>d.Clone()).ToArray();}
    public static string Secret()=>Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)).TrimEnd('=').Replace('+','-').Replace('/','_');
    public static string Hash(string secret)=>Convert.ToHexStringLower(SHA256.HashData(Encoding.ASCII.GetBytes(secret)));
    public Task<RemoteServer> StartServer()=>RemoteServer.StartAsync(new(Path.Combine(CatalogDirectory,"public-pilot-v0.1.json"),Path.Combine(CatalogDirectory,"public-pilot-v0.1.provenance.json"),RegistryPath){TimeProvider=Clock,Port=0});
    public static async Task<Fixture> Start(){var f=new Fixture();f.Server=await f.StartServer();f.Client=new(new SocketsHttpHandler{UseProxy=false,UseCookies=false,AllowAutoRedirect=false}){BaseAddress=new Uri(f.Server.Address),Timeout=TimeSpan.FromSeconds(8)};return f;}
    public Task<HttpResponseMessage> Search(string query,int limit=8,bool auth=true)=>Body(JsonSerializer.Serialize(new{query,limit}),auth:auth);
    public Task<HttpResponseMessage> Body(string body,string contentType="application/json",bool auth=true)=>Bytes(Encoding.UTF8.GetBytes(body),contentType,auth);
    public async Task<HttpResponseMessage> Bytes(byte[] bytes,string type="application/json",bool auth=true){using var q=new HttpRequestMessage(HttpMethod.Post,"/v1/search");if(auth)q.Headers.Authorization=new("Bearer",Secrets[0]);q.Content=new ByteArrayContent(bytes);q.Content.Headers.ContentType=MediaTypeHeaderValue.Parse(type);return await Client.SendAsync(q);}
    public async Task<HttpResponseMessage> GetCatalog(int index=0){using var q=new HttpRequestMessage(HttpMethod.Get,"/v1/catalog");q.Headers.Authorization=new("Bearer",Secrets[index]);return await Client.SendAsync(q);}
    public async Task<int> Raw(string request){using var tcp=new TcpClient();await tcp.ConnectAsync(IPAddress.Loopback,new Uri(Server.Address).Port);await tcp.GetStream().WriteAsync(Encoding.UTF8.GetBytes(request));return await ReadStatus(tcp.GetStream());}
    public async Task<TcpClient> HoldBody(){var tcp=new TcpClient();await tcp.ConnectAsync(IPAddress.Loopback,new Uri(Server.Address).Port);await tcp.GetStream().WriteAsync(Encoding.ASCII.GetBytes("POST /v1/search HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Bearer "+Secrets[0]+"\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n1\r\n{\r\n"));return tcp;}
    public static async Task<int> ReadStatus(NetworkStream stream){using var cts=new CancellationTokenSource(TimeSpan.FromSeconds(6));var buffer=new byte[1];var line=new StringBuilder();while(await stream.ReadAsync(buffer,cts.Token)>0){line.Append((char)buffer[0]);if(line.ToString().EndsWith("\r\n",StringComparison.Ordinal))break;}var parts=line.ToString().Split(' ');return parts.Length>=2?int.Parse(parts[1],System.Globalization.CultureInfo.InvariantCulture):0;}
    public async ValueTask DisposeAsync(){Client?.Dispose();if(Server is not null)await Server.DisposeAsync();System.IO.Directory.Delete(Directory,true);}
}
