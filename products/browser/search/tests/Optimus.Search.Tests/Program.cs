using System.Text;
using System.Net;
using System.Net.Sockets;
using System.Diagnostics;
using System.Net.Http.Headers;
using System.Text.Json;
using Optimus.Search;

var tests = new List<(string Name, Func<Task> Run)>();
void Test(string name, Func<Task> run) => tests.Add((name, run));
void Equal<T>(T want, T got) { if (!EqualityComparer<T>.Default.Equals(want, got)) throw new Exception($"Expected {want}; got {got}"); }
void True(bool value) { if (!value) throw new Exception("Expected true"); }
async Task Reject(Func<Task> action) { try { await action(); } catch (InvalidDataException) { return; } throw new Exception("Expected rejected input"); }
var temp = Path.Combine(Path.GetTempPath(), "optimus-search-test-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(temp);
string FilePath(string name) => Path.Combine(temp, name);
string Catalog(params object[] docs) => JsonSerializer.Serialize(new { schemaVersion = 1, documents = docs });
object Doc(string url, string title, string content) => new { url, title, content, source = "Public help", updatedUtc = "2026-10-30T00:00:00Z" };
async Task<LocalSearchIndex> Import(string json) {
    await File.WriteAllTextAsync(FilePath("input.json"), json);
    await CatalogStore.ImportAsync(FilePath("input.json"), FilePath("index.json"));
    return new LocalSearchIndex(await CatalogStore.LoadAsync(FilePath("index.json")));
}
Test("own index matches Unicode tokens, title ranks ahead, no-match stays empty", async () => {
    var index = await Import(Catalog(Doc("https://example.org/body", "Manual", "BÚSQUEDA útil"), Doc("https://example.org/title", "Búsqueda", "útil manual")));
    Equal(2, index.DocumentCount); Equal("https://example.org/title", index.Search("búsqueda")[0].Url);
    Equal(2, index.Search("BÚSQUEDA").Count); Equal(0, index.Search("missing").Count);
    Equal(0, index.Search("!!!").Count);
});
Test("index ties sort URL ordinal and snippets and result count are bounded", async () => {
    var index = await Import(Catalog(Enumerable.Range(0, 25).Reverse().Select(i => Doc($"https://example.org/{i:00}", "Shared", new string('x', 1500) + " shared")).ToArray()));
    var results = index.Search("shared"); Equal(20, results.Count); Equal("https://example.org/00", results[0].Url); Equal(1200, results[0].Content.Length);
});
Test("catalog import is all-or-nothing and normalizes fragment; duplicate rejected", async () => {
    await Import(Catalog(Doc("https://EXAMPLE.org:443/a#fragment", "Good", "text")));
    var before = await File.ReadAllTextAsync(FilePath("index.json"));
    True(before.Contains("https://example.org/a")); True(!before.Contains("fragment"));
    await File.WriteAllTextAsync(FilePath("input.json"), Catalog(Doc("https://example.org/a", "One", "text"), Doc("https://example.org/a#other", "Two", "text")));
    await Reject(() => CatalogStore.ImportAsync(FilePath("input.json"), FilePath("index.json")));
    Equal(before, await File.ReadAllTextAsync(FilePath("index.json")));
});
Test("catalog rejects malformed fields, controls, credentials, non-UTC dates, bounds", async () => {
    foreach (var doc in new object[] { Doc("file:///tmp/file", "Bad", "text"), Doc("https://u:p@example.org/", "Bad", "text"), Doc("https://example.org/\\evil", "Bad", "text"), Doc("https://example.org/\n", "Bad", "text"), Doc("https://example.org/", new string('t',241), "text"), Doc("https://example.org/", "Title", new string('é',32769)), new {url="https://example.org/",title="Title",content="text",source="Public",updatedUtc="2026-10-30T00:00:00+01:00"} }) {
        await File.WriteAllTextAsync(FilePath("input.json"), Catalog(doc));
        await Reject(() => CatalogStore.ImportAsync(FilePath("input.json"), FilePath("index.json")));
    }
    foreach (var json in new[]{"{}", "{\"schemaVersion\":2,\"documents\":[]}", "{broken", Catalog(Enumerable.Range(0,1001).Select(i=>Doc($"https://example.org/{i}","Title","text")).ToArray())}) {
        await File.WriteAllTextAsync(FilePath("input.json"), json); await Reject(() => CatalogStore.ImportAsync(FilePath("input.json"), FilePath("index.json")));
    }
    await File.WriteAllBytesAsync(FilePath("input.json"), new byte[16*1024*1024+1]);
    await Reject(() => CatalogStore.ImportAsync(FilePath("input.json"), FilePath("index.json")));
});

Test("web provider emits fixed query without bearer, filters URLs, deduplicates and bounds text", async () => {
    string? request = null;
    var results = new List<object> { new {url="https://EXAMPLE.org:443/a#one",title=new string('t',250),content=new string('c',1300)}, new {url="https://example.org/a#two",title="Duplicate",content="text"}, new {url="javascript:alert(1)",title="Bad",content="bad"}, new {url="https://u:p@example.org/",title="Bad",content="bad"}, new {url="https://example.org/\\bad",title="Bad",content="bad"} };
    results.AddRange(Enumerable.Range(0,30).Select(i => new {url=$"https://example.org/{i}",title=$"Result {i}",content="text"}));
    await using var upstream = new Upstream(async (stream, headers) => { request = headers; await Upstream.Json(stream, JsonSerializer.Serialize(new {results})); });
    using var provider = new SearxSearchProvider(upstream.Url);
    var found = await provider.SearchAsync("á &?", "es", default);
    Equal(20, found.Count); Equal("https://example.org/a", found[0].Url); Equal(240, found[0].Title.Length); Equal(1200, found[0].Content.Length);
    True(request!.StartsWith("GET /search?format=json&q=%C3%A1%20%26%3F&language=es&categories=general HTTP/1.1"));
    True(!request.Contains("Authorization", StringComparison.OrdinalIgnoreCase)); True(!request.Contains("Cookie:", StringComparison.OrdinalIgnoreCase));
});
Test("provider rejects unsafe endpoint configuration before network", async () => {
    foreach(var endpoint in new[]{"https://user:pass@example.org", "https://example.org/?x=y", "https://example.org/#frag", "http://example.org", "file:///tmp/file", "https://example.org/\\bad"}) {
        try { using var provider = new SearxSearchProvider(endpoint); throw new Exception("Unsafe endpoint accepted"); } catch(ArgumentException) {}
    }
    await Task.CompletedTask;
});
Test("provider rejects malformed JSON shape and redirect rather than following it", async () => {
    foreach(var body in new[]{"{broken", "{}", "{\"results\":{}}", "[]"}) {
        await using var upstream = new Upstream((stream, _) => Upstream.Json(stream,body)); using var provider = new SearxSearchProvider(upstream.Url);
        try { await provider.SearchAsync("query","es",default); throw new Exception("Malformed response accepted"); } catch(SearchProviderException ex) { True(!ex.TimedOut); }
    }
    await using var redirect = new Upstream(async (stream,_) => await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:1/search\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")));
    using var redirectProvider = new SearxSearchProvider(redirect.Url);
    try { await redirectProvider.SearchAsync("query","es",default); throw new Exception("Redirect accepted"); } catch(SearchProviderException ex) { True(!ex.TimedOut); }
});
Test("provider bounds unknown-length streamed bytes and disposes late body on cancellation", async () => {
    await using(var upstream = new Upstream(async (stream, _) => { await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n")); await stream.WriteAsync(new byte[1024*1024+1]); })) {
        using var provider = new SearxSearchProvider(upstream.Url);
        try { await provider.SearchAsync("query","es",default); throw new Exception("Oversized stream accepted"); } catch(SearchProviderException ex) { True(!ex.TimedOut); }
    }
    var disconnected = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
    await using var slow = new Upstream(async(stream,headers) => { await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Length: 30\r\n\r\n{\"results\":")); if(await stream.ReadAsync(new byte[1])==0) disconnected.TrySetResult(); });
    using var slowProvider = new SearxSearchProvider(slow.Url); using var cancel = new CancellationTokenSource(TimeSpan.FromMilliseconds(150));
    var watch = Stopwatch.StartNew();
    try { await slowProvider.SearchAsync("query","es",cancel.Token); throw new Exception("Cancelled read applied"); } catch(OperationCanceledException) {}
    True(watch.Elapsed < TimeSpan.FromSeconds(3)); await disconnected.Task.WaitAsync(TimeSpan.FromSeconds(3));
});
Test("API maps ten-second upstream body deadline to sanitized 504 without fallback", async () => {
    await using var upstream = new Upstream(async(stream,headers) => { await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Length: 30\r\n\r\n{\"results\":")); _ = await stream.ReadAsync(new byte[1]); });
    using var provider = new SearxSearchProvider(upstream.Url);
    await using var server=await SearchServer.StartAsync(new ServerOptions(0,new string('a',64)),new LocalSearchIndex([]),provider);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};client.DefaultRequestHeaders.Authorization=new("Bearer",new string('a',64));
    var watch=Stopwatch.StartNew();using var response=await client.GetAsync("/search?format=json&q=help&scope=web&language=es");Equal(HttpStatusCode.GatewayTimeout,response.StatusCode);
    using var json=JsonDocument.Parse(await response.Content.ReadAsStringAsync());Equal("upstream-timeout",json.RootElement.GetProperty("error").GetString());Equal(0,json.RootElement.GetProperty("results").GetArrayLength());
    True(watch.Elapsed >= TimeSpan.FromSeconds(9)); True(watch.Elapsed < TimeSpan.FromSeconds(13));
});


Test("token creation is stable, private and invalid existing file fails closed", async () => {
    var path=FilePath("profile/service.token"); var token=await TokenStore.LoadOrCreateAsync(path);
    Equal(64,token.Length); True(token.All(Uri.IsHexDigit)); Equal(token,await TokenStore.LoadOrCreateAsync(path));
    True(TokenStore.Matches(token,token)); True(!TokenStore.Matches(token,new string('0',64))); True(!TokenStore.Matches(token,"short"));
    if(!OperatingSystem.IsWindows()) Equal(UnixFileMode.UserRead|UnixFileMode.UserWrite,File.GetUnixFileMode(path));
    await File.WriteAllTextAsync(path,"invalid"); await Reject(()=>TokenStore.LoadOrCreateAsync(path)); Equal("invalid",await File.ReadAllTextAsync(path));
});
Test("loopback health minimal, auth and origin/host enforced, no writes and hardened headers", async () => {
    var index=await Import(Catalog(Doc("https://example.org/help","Optimus help","offline catalog")));
    var token=new string('a',64); await using var server=await SearchServer.StartAsync(new ServerOptions(0,token),index);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};
    using var health=await client.GetAsync("/health"); Equal(HttpStatusCode.OK,health.StatusCode);
    var healthText=await health.Content.ReadAsStringAsync(); using var healthJson=JsonDocument.Parse(healthText);
    Equal(2,healthJson.RootElement.EnumerateObject().Count()); Equal("OptimusSearch",healthJson.RootElement.GetProperty("name").GetString()); Equal(1,healthJson.RootElement.GetProperty("version").GetInt32());
    Equal("no-store",health.Headers.CacheControl!.ToString()); Equal("nosniff",health.Headers.GetValues("X-Content-Type-Options").Single()); Equal("no-referrer",health.Headers.GetValues("Referrer-Policy").Single());
    True(!health.Headers.Contains("Access-Control-Allow-Origin"));
    Equal(HttpStatusCode.Unauthorized,(await client.GetAsync("/search?format=json&q=help&scope=index&language=es")).StatusCode);
    client.DefaultRequestHeaders.Authorization=new AuthenticationHeaderValue("Bearer",token);
    foreach(var header in new[]{("Origin","https://evil.example"),("Origin",""),("Host","evil.example"),("Host","127.0.0.1:1")}) {
        using var request=new HttpRequestMessage(HttpMethod.Get,"/search?format=json&q=help&scope=index&language=es"); request.Headers.TryAddWithoutValidation(header.Item1,header.Item2);
        Equal(HttpStatusCode.Forbidden,(await client.SendAsync(request)).StatusCode);
    }
    using var wrong=new HttpRequestMessage(HttpMethod.Get,"/search?format=json&q=help&scope=index&language=es"); wrong.Headers.Authorization=new("Bearer",new string('b',64));
    Equal(HttpStatusCode.Unauthorized,(await client.SendAsync(wrong)).StatusCode);
    Equal(HttpStatusCode.MethodNotAllowed,(await client.PostAsync("/search",new StringContent("{}"))).StatusCode);
    Equal(HttpStatusCode.NotFound,(await client.GetAsync("/unknown")).StatusCode);
});
Test("index API is offline, web unconfigured explicitly fails, malformed queries reject", async () => {
    var index=await Import(Catalog(Doc("https://example.org/help","Optimus help","offline catalog"))); var token=new string('a',64);
    await using var server=await SearchServer.StartAsync(new ServerOptions(0,token),index);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)}; client.DefaultRequestHeaders.Authorization=new("Bearer",token);
    using var response=await client.GetAsync("/search?format=json&q=help&scope=index&language=es"); Equal(HttpStatusCode.OK,response.StatusCode);
    using var json=JsonDocument.Parse(await response.Content.ReadAsStringAsync()); Equal(1,json.RootElement.GetProperty("results").GetArrayLength());
    Equal("index",json.RootElement.GetProperty("optimus").GetProperty("scope").GetString()); Equal(1,json.RootElement.GetProperty("optimus").GetProperty("indexedDocuments").GetInt32()); True(!json.RootElement.GetProperty("optimus").GetProperty("webConfigured").GetBoolean());
    using var web=await client.GetAsync("/search?format=json&q=help&scope=web&language=es"); Equal(HttpStatusCode.ServiceUnavailable,web.StatusCode);
    using var webJson=JsonDocument.Parse(await web.Content.ReadAsStringAsync()); Equal("web-not-configured",webJson.RootElement.GetProperty("error").GetString()); Equal(0,webJson.RootElement.GetProperty("results").GetArrayLength());
    foreach(var path in new[]{"/search?format=json&q=&scope=index&language=es","/search?format=json&q="+new string('x',501)+"&scope=index&language=es","/search?format=xml&q=help&scope=index&language=es","/search?format=json&q=help&scope=wikipedia&language=es","/search?format=json&q=help&q=other&scope=index&language=es","/search?format=json&q=help&scope=index&language=es%0A"}) Equal(HttpStatusCode.BadRequest,(await client.GetAsync(path)).StatusCode);
});
Test("configured index never contacts upstream, API web returns protocol and sanitized failure", async () => {
    var index=await Import(Catalog(Doc("https://example.org/help","Optimus help","offline catalog"))); var token=new string('a',64);
    int calls=0; await using var upstream=new Upstream(async(stream,headers)=>{Interlocked.Increment(ref calls); await Upstream.Json(stream,"{broken");}); using var provider=new SearxSearchProvider(upstream.Url);
    await using var server=await SearchServer.StartAsync(new ServerOptions(0,token),index,provider);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};client.DefaultRequestHeaders.Authorization=new("Bearer",token);
    Equal(HttpStatusCode.OK,(await client.GetAsync("/search?format=json&q=help&scope=index&language=es")).StatusCode); Equal(0,calls);
    using var response=await client.GetAsync("/search?format=json&q=help&scope=web&language=es"); Equal(HttpStatusCode.BadGateway,response.StatusCode);Equal(1,calls);
    var body=await response.Content.ReadAsStringAsync();True(!body.Contains(upstream.Url));True(!body.Contains(token));True(!body.Contains("Exception"));
    using var json=JsonDocument.Parse(body);Equal("upstream-failed",json.RootElement.GetProperty("error").GetString());Equal(0,json.RootElement.GetProperty("results").GetArrayLength());True(json.RootElement.GetProperty("optimus").GetProperty("webConfigured").GetBoolean());
});


Test("environment URLs and Kestrel endpoints cannot override IPv4 loopback binding", async () => {
    var oldUrls=Environment.GetEnvironmentVariable("ASPNETCORE_URLS"); var oldEndpoint=Environment.GetEnvironmentVariable("Kestrel__Endpoints__External__Url");
    Environment.SetEnvironmentVariable("ASPNETCORE_URLS","http://192.0.2.1:1234"); Environment.SetEnvironmentVariable("Kestrel__Endpoints__External__Url","http://192.0.2.1:1234");
    try { await using var server=await SearchServer.StartAsync(new ServerOptions(0,new string('a',64)),new LocalSearchIndex([]));True(server.Address.StartsWith("https://127.0.0.1:")); }
    finally { Environment.SetEnvironmentVariable("ASPNETCORE_URLS",oldUrls);Environment.SetEnvironmentVariable("Kestrel__Endpoints__External__Url",oldEndpoint); }
});
Test("CLI rejects unknown, duplicate, malformed and incomplete options without leaking input", async () => {
    foreach(var args in new[]{new[]{"--host","sensitive-test"},new[]{"--port","-1"},new[]{"--port","65536"},new[]{"--port","abc"},new[]{"--port"},new[]{"--port","1","--port","2"},new[]{"index","--input","sensitive-test"}}) {
        var result=await RunCli(args);Equal(2,result.Code);True(!result.Output.Contains("sensitive-test"));
    }
});
Test("CLI import actually normalizes catalog, invalid input preserves output", async () => {
    await File.WriteAllTextAsync(FilePath("cli-input.json"),Catalog(Doc("https://EXAMPLE.org:443/help#part","Help","public help")));
    var result=await RunCli(["index","--input",FilePath("cli-input.json"),"--output",FilePath("cli-output.json")]);Equal(0,result.Code);
    var before=await File.ReadAllTextAsync(FilePath("cli-output.json"));True(before.Contains("https://example.org/help"));
    await File.WriteAllTextAsync(FilePath("cli-input.json"),"invalid");result=await RunCli(["index","--input",FilePath("cli-input.json"),"--output",FilePath("cli-output.json")]);Equal(2,result.Code);Equal(before,await File.ReadAllTextAsync(FilePath("cli-output.json")));
});


Test("provider accepts exactly one MiB and rejects larger declared body", async () => {
    var prefix="{\"results\":[]}";var body=prefix+new string(' ',1024*1024-prefix.Length);
    await using(var upstream=new Upstream((stream,headers)=>Upstream.Json(stream,body))) {using var provider=new SearxSearchProvider(upstream.Url);Equal(0,(await provider.SearchAsync("help","es",default)).Count);}
    await using var declared=new Upstream(async(stream,headers)=>await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Length: 1048577\r\nConnection: close\r\n\r\n")));
    using var bounded=new SearxSearchProvider(declared.Url);try {await bounded.SearchAsync("help","es",default);throw new Exception("Declared oversize accepted");} catch(SearchProviderException ex){True(!ex.TimedOut);}
});
Test("web API successful loopback provider fixture returns Optimus protocol and fixed source", async () => {
    await using var upstream=new Upstream((stream,headers)=>Upstream.Json(stream,"{\"results\":[{\"url\":\"https://example.org/result#part\",\"title\":\"Public result\",\"content\":\"<b>inert remote text</b>\"}]}"));
    using var provider=new SearxSearchProvider(upstream.Url);await using var server=await SearchServer.StartAsync(new ServerOptions(0,new string('a',64)),new LocalSearchIndex([]),provider);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};client.DefaultRequestHeaders.Authorization=new("Bearer",new string('a',64));
    using var response=await client.GetAsync("/search?format=json&q=help&scope=web&language=es");Equal(HttpStatusCode.OK,response.StatusCode);
    using var json=JsonDocument.Parse(await response.Content.ReadAsStringAsync());Equal("help",json.RootElement.GetProperty("query").GetString());Equal(1,json.RootElement.GetProperty("optimus").GetProperty("version").GetInt32());Equal("web",json.RootElement.GetProperty("optimus").GetProperty("scope").GetString());
    var result=json.RootElement.GetProperty("results")[0];Equal("https://example.org/result",result.GetProperty("url").GetString());Equal("SearXNG",result.GetProperty("source").GetString());Equal("<b>inert remote text</b>",result.GetProperty("content").GetString());
});
Test("token concurrent creation converges and never overwrites invalid files", async () => {
    var path=FilePath("race/service.token");var tokens=await Task.WhenAll(Enumerable.Range(0,8).Select(_=>TokenStore.LoadOrCreateAsync(path)));True(tokens.All(t=>t==tokens[0]));
    await File.WriteAllTextAsync(path,new string('x',65));await Reject(()=>TokenStore.LoadOrCreateAsync(path));Equal(65,(await File.ReadAllTextAsync(path)).Length);
});
Test("CLI starts real loopback service and explicit missing index fails closed", async () => {
    var missing=await RunCli(["--index-file",FilePath("not-present.json"),"--token-file",FilePath("missing/service.token")]);Equal(2,missing.Code);True(!File.Exists(FilePath("missing/service.token")));
    var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();var port=((IPEndPoint)listener.LocalEndpoint).Port;listener.Stop();
    var start=CliStart(["--port",port.ToString(System.Globalization.CultureInfo.InvariantCulture),"--index-file",FilePath("cli-output.json"),"--token-file",FilePath("cli-profile/service.token")]);
    using var process=Process.Start(start)!;var output=process.StandardOutput.ReadToEndAsync();var errors=process.StandardError.ReadToEndAsync();
    try {
        using var client=new HttpClient(TestTls.Handler(() => File.ReadAllText(FilePath("cli-profile/service.token")))){BaseAddress=new Uri($"https://127.0.0.1:{port}")};
        var ready=false;for(var attempt=0;attempt<80;attempt++){try{using var health=await client.GetAsync("/health");if(health.IsSuccessStatusCode){ready=true;break;}}catch(HttpRequestException){}await Task.Delay(50);}
        True(ready);var token=await File.ReadAllTextAsync(FilePath("cli-profile/service.token"));client.DefaultRequestHeaders.Authorization=new("Bearer",token);
        using var result=await client.GetAsync("/search?format=json&q=help&scope=index&language=es");Equal(HttpStatusCode.OK,result.StatusCode);using var json=JsonDocument.Parse(await result.Content.ReadAsStringAsync());Equal(1,json.RootElement.GetProperty("results").GetArrayLength());
    }finally{if(!process.HasExited)process.Kill(true);await process.WaitForExitAsync();var logged=await output+await errors;True(!logged.Contains("/search"));True(!logged.Contains("help"));True(!logged.Contains(await File.ReadAllTextAsync(FilePath("cli-profile/service.token"))));True(!logged.Contains(FilePath("cli-profile/service.token")));}
});


Test("failed catalog output write preserves previous index and leaves no partial file", async () => {
    var output=FilePath(new string('o',240)+".json");var previous=Catalog(Doc("https://example.org/old","Old help","previous content"));await File.WriteAllTextAsync(output,previous);
    await File.WriteAllTextAsync(FilePath("write-input.json"),Catalog(Doc("https://example.org/new","New help","new content")));
    try{await CatalogStore.ImportAsync(FilePath("write-input.json"),output);throw new Exception("Expected filesystem output failure");}catch(IOException){}
    Equal(previous,await File.ReadAllTextAsync(output));Equal(0,Directory.GetFiles(temp,"*.tmp").Length);
});
Test("forbidden and unauthorized oversized queries never reach configured provider", async () => {
    int calls=0;await using var upstream=new Upstream(async(stream,headers)=>{Interlocked.Increment(ref calls);await Upstream.Json(stream,"{\"results\":[]}");});using var provider=new SearxSearchProvider(upstream.Url);
    await using var server=await SearchServer.StartAsync(new ServerOptions(0,new string('a',64)),new LocalSearchIndex([]),provider);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};
    var path="/search?format=json&q="+new string('x',4000)+"&scope=web&language=es";
    Equal(HttpStatusCode.Unauthorized,(await client.GetAsync(path)).StatusCode);
    foreach(var header in new[]{("Origin","https://evil.example"),("Host","evil.example")}) {
        using var request=new HttpRequestMessage(HttpMethod.Get,path);request.Headers.Authorization=new("Bearer",new string('a',64));request.Headers.TryAddWithoutValidation(header.Item1,header.Item2);Equal(HttpStatusCode.Forbidden,(await client.SendAsync(request)).StatusCode);
    }
    client.DefaultRequestHeaders.Authorization=new("Bearer",new string('a',64));Equal(HttpStatusCode.BadRequest,(await client.GetAsync(path)).StatusCode);Equal(0,calls);
});


foreach(var (field,body) in new[]{
    ("url", """{"results":[{"url":"https://example.org/\uD800","title":"Public result","content":"Public content"}]}"""),
    ("title", """{"results":[{"url":"https://example.org/result","title":"Public \uD800","content":"Public content"}]}"""),
    ("content", """{"results":[{"url":"https://example.org/result","title":"Public result","content":"Public \uD800"}]}""")
}) {
    Test($"API normalizes invalid escaped Unicode in upstream {field} to sanitized 502", async () => {
        await using var upstream=new Upstream((stream,headers)=>Upstream.Json(stream,body));using var provider=new SearxSearchProvider(upstream.Url);
        var token=new string('a',64);await using var server=await SearchServer.StartAsync(new ServerOptions(0,token),new LocalSearchIndex([]),provider);
        using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};client.DefaultRequestHeaders.Authorization=new("Bearer",token);
        using var response=await client.GetAsync("/search?format=json&q=help&scope=web&language=es");Equal(HttpStatusCode.BadGateway,response.StatusCode);
        var responseBody=await response.Content.ReadAsStringAsync();using var json=JsonDocument.Parse(responseBody);
        Equal("upstream-failed",json.RootElement.GetProperty("error").GetString());Equal(0,json.RootElement.GetProperty("results").GetArrayLength());Equal("",json.RootElement.GetProperty("query").GetString());
        Equal(1,json.RootElement.GetProperty("optimus").GetProperty("version").GetInt32());Equal("web",json.RootElement.GetProperty("optimus").GetProperty("scope").GetString());
        True(!responseBody.Contains(upstream.Url));True(!responseBody.Contains(token));True(!responseBody.Contains("Exception"));True(!responseBody.Contains("D800",StringComparison.OrdinalIgnoreCase));
    });
}
Test("API preserves valid escaped Unicode pairs from upstream strings", async () => {
    const string body="""{"results":[{"url":"https://example.org/\uD83D\uDE00","title":"Public \uD83D\uDE00","content":"Content \uD83D\uDE00"}]}""";
    await using var upstream=new Upstream((stream,headers)=>Upstream.Json(stream,body));using var provider=new SearxSearchProvider(upstream.Url);
    await using var server=await SearchServer.StartAsync(new ServerOptions(0,new string('a',64)),new LocalSearchIndex([]),provider);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};client.DefaultRequestHeaders.Authorization=new("Bearer",new string('a',64));
    using var response=await client.GetAsync("/search?format=json&q=help&scope=web&language=es");Equal(HttpStatusCode.OK,response.StatusCode);
    using var json=JsonDocument.Parse(await response.Content.ReadAsStringAsync());var result=json.RootElement.GetProperty("results")[0];
    Equal("https://example.org/%F0%9F%98%80",result.GetProperty("url").GetString());Equal("Public \U0001F600",result.GetProperty("title").GetString());Equal("Content \U0001F600",result.GetProperty("content").GetString());
});

// Removing prefix preservation would route accepted configurations to the wrong instance.
foreach(var suffix in new[]{"/instance","/instance/","/instance/search",""})
Test("provider preserves accepted base prefix " + suffix, async () => {
    string? received=null;
    await using var upstream=new Upstream(async(stream,headers)=>{received=headers;await Upstream.Json(stream,"{\"results\":[]}");});
    using var provider=new SearxSearchProvider(upstream.Url.TrimEnd('/')+suffix);
    await provider.SearchAsync("help","es",default);
    var expected=suffix.Length==0?"/search":"/instance/search";
    True(received!.StartsWith("GET "+expected+"?",StringComparison.Ordinal));
});
Test("native accepted localhost configuration constructs and starts actual host", async () => {
    await using var upstream=new Upstream((stream,headers)=>Upstream.Json(stream,"{\"results\":[]}"));
    using var provider=new SearxSearchProvider(upstream.Url.Replace("127.0.0.1","localhost"));
    await using var server=await SearchServer.StartAsync(new(0,new string('a',64)),new LocalSearchIndex([]),provider);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};client.DefaultRequestHeaders.Authorization=new("Bearer",new string('a',64));
    using var response=await client.GetAsync("/search?format=json&q=help&scope=web&language=es");Equal(HttpStatusCode.OK,response.StatusCode);
});
foreach(var partial in new[]{false,true})
Test("provider rejects engine failure " + (partial?"with partial results":"with empty results"), async () => {
    var body=partial?"{\"results\":[{\"title\":\"Help\",\"url\":\"https://example.org\"}],\"unresponsive_engines\":[[\"secret engine\",\"secret failure\"]]}":"{\"results\":[],\"unresponsive_engines\":[[\"secret engine\",\"secret failure\"]]}";
    await using var upstream=new Upstream((stream,headers)=>Upstream.Json(stream,body));
    using var provider=new SearxSearchProvider(upstream.Url);
    try {await provider.SearchAsync("help","es",default);throw new Exception("Engine failure accepted as success");}catch(SearchProviderException ex){True(!ex.TimedOut);True(!ex.Message.Contains("secret"));}
});
foreach(var state in new[]{"healthy-empty","failed-empty","partial-failure"})
Test("actual API reports " + state + " without engine detail", async () => {
    var results=state=="partial-failure"?"[{\"title\":\"Help\",\"url\":\"https://example.org\"}]":"[]";
    var failures=state=="healthy-empty"?"[]":"[[\"private-engine\",\"private-error\"]]";
    await using var upstream=new Upstream((stream,headers)=>Upstream.Json(stream,"{\"results\":"+results+",\"unresponsive_engines\":"+failures+"}"));
    using var provider=new SearxSearchProvider(upstream.Url);
    await using var server=await SearchServer.StartAsync(new(0,new string('a',64)),new LocalSearchIndex([]),provider);
    using var client=new HttpClient(TestTls.Handler()){BaseAddress=new Uri(server.Address)};client.DefaultRequestHeaders.Authorization=new("Bearer",new string('a',64));
    using var response=await client.GetAsync("/search?format=json&q=help&scope=web&language=es");
    Equal(state=="healthy-empty"?HttpStatusCode.OK:HttpStatusCode.BadGateway,response.StatusCode);
    var body=await response.Content.ReadAsStringAsync();True(!body.Contains("private-engine"));True(!body.Contains("private-error"));
    using var json=JsonDocument.Parse(body);Equal(0,json.RootElement.GetProperty("results").GetArrayLength());
});
Test("service exposes HTTPS only including actual ephemeral port", async () => {
    await using var server=await SearchServer.StartAsync(new(0,new string('a',64)),new LocalSearchIndex([]));
    True(server.Address.StartsWith("https://127.0.0.1:"));True(new Uri(server.Address).Port>0);
});

IdentityProofTests.Register(Test);
int failed = 0;
try { foreach (var (name, run) in tests) { try { await run(); Console.WriteLine("PASS " + name); } catch(Exception ex) { failed++; Console.WriteLine("FAIL " + name + ": " + ex.GetType().Name + ": " + ex.Message); } } }
finally { Directory.Delete(temp, true); }
Console.WriteLine($"{tests.Count-failed}/{tests.Count} passed");
return failed == 0 ? 0 : 1;

static async Task<(int Code,string Output)> RunCli(string[] args)
{
    using var process=Process.Start(CliStart(args))!; var output=process.StandardOutput.ReadToEndAsync(); var errors=process.StandardError.ReadToEndAsync();
    using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(5));
    try{await process.WaitForExitAsync(timeout.Token);}catch{process.Kill(true);throw;}
    return(process.ExitCode,await output+await errors);
}

static ProcessStartInfo CliStart(string[] args)
{
    var start=new ProcessStartInfo(Path.Combine(Environment.GetEnvironmentVariable("DOTNET_ROOT")!,OperatingSystem.IsWindows()?"dotnet.exe":"dotnet")) {RedirectStandardError=true,RedirectStandardOutput=true,UseShellExecute=false};
    start.ArgumentList.Add(typeof(SearchServer).Assembly.Location);foreach(var arg in args)start.ArgumentList.Add(arg);return start;
}

sealed class Upstream : IAsyncDisposable
{
    private readonly TcpListener listener = new(IPAddress.Loopback,0);
    private readonly Task serving;
    public string Url {get;}
    public Upstream(Func<NetworkStream,string,Task> respond)
    {
        listener.Start(); Url=$"http://127.0.0.1:{((IPEndPoint)listener.LocalEndpoint).Port}";
        serving=Task.Run(async()=>{
            try {
                using var client=await listener.AcceptTcpClientAsync(); await using var stream=client.GetStream();
                var data=new List<byte>(); var one=new byte[1];
                while(data.Count<16384 && await stream.ReadAsync(one)>0) {data.Add(one[0]); if(data.Count>=4 && Encoding.ASCII.GetString(data.TakeLast(4).ToArray())=="\r\n\r\n") break;}
                await respond(stream,Encoding.ASCII.GetString(data.ToArray()));
            } catch(Exception ex) when(ex is IOException or ObjectDisposedException or SocketException) {}
        });
    }
    public static async Task Json(NetworkStream stream,string json) {
        var bytes=Encoding.UTF8.GetBytes(json); await stream.WriteAsync(Encoding.ASCII.GetBytes($"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {bytes.Length}\r\nConnection: close\r\n\r\n")); await stream.WriteAsync(bytes);
    }
    public async ValueTask DisposeAsync() {listener.Stop(); await serving.WaitAsync(TimeSpan.FromSeconds(4));}
}
