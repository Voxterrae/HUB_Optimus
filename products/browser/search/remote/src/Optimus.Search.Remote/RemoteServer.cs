using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.Server.Kestrel.Core;
using Optimus.Search;
namespace Optimus.Search.Remote;

public sealed record RemoteOptions(string CatalogPath,string ProvenancePath,string CredentialsPath)
{
    public TimeProvider TimeProvider{get;init;}=TimeProvider.System;
    public int Port{get;init;}=8080;
    public bool ContainerPrivateHttp{get;init;}
}
public sealed class RemoteServer:IAsyncDisposable
{
    private readonly WebApplication app;
    private readonly ResourceGuard guard;
    public string Address{get;}
    private RemoteServer(WebApplication application,ResourceGuard resources,string address){app=application;guard=resources;Address=address;}
    public static async Task<RemoteServer> StartAsync(RemoteOptions options)
    {
        if(options.Port is <0 or >65535||(options.ContainerPrivateHttp&&options.Port!=8080))throw new InvalidDataException("Invalid remote configuration.");
        var catalog=await PinnedCatalog.Load(options.CatalogPath,options.ProvenancePath);
        var registry=await CredentialRegistry.Load(options.CredentialsPath,options.TimeProvider);
        var builder=WebApplication.CreateSlimBuilder(new WebApplicationOptions{Args=[],EnvironmentName="Production",ContentRootPath=AppContext.BaseDirectory});
        builder.Configuration.Sources.Clear();builder.Logging.ClearProviders();builder.Logging.SetMinimumLevel(LogLevel.None);
        builder.WebHost.ConfigureKestrel(server=>{
            server.AddServerHeader=false;server.Limits.MaxRequestBodySize=RemoteLimits.BodyBytes;server.Limits.MaxRequestHeadersTotalSize=8192;server.Limits.MaxRequestHeaderCount=24;server.Limits.MaxRequestLineSize=1024;server.Limits.RequestHeadersTimeout=TimeSpan.FromSeconds(5);server.Limits.KeepAliveTimeout=TimeSpan.FromSeconds(5);server.Limits.MaxConcurrentConnections=32;
            server.Listen(options.ContainerPrivateHttp?IPAddress.Any:IPAddress.Loopback,options.Port,listen=>listen.Protocols=HttpProtocols.Http1);
        });
        var app=builder.Build();var guard=new ResourceGuard(options.TimeProvider);
        app.Run(async context=>{
            context.Response.Headers.CacheControl="no-store";context.Response.Headers["X-Content-Type-Options"]="nosniff";context.Response.Headers["Referrer-Policy"]="no-referrer";
            if(!guard.GlobalAdmission()){await Error(context,429,"rate_limited",60);return;}
            if(!guard.Enter()){await Error(context,429,"busy",1);return;}
            using var deadline=new CancellationTokenSource(RemoteLimits.Deadline,options.TimeProvider);using var linked=CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted,deadline.Token);
            try{await Handle(context,catalog,registry,guard,linked.Token);}
            catch(OperationCanceledException)when(context.RequestAborted.IsCancellationRequested){context.Abort();}
            catch(OperationCanceledException){if(!context.Response.HasStarted)await Error(context,408,"deadline_exceeded");else context.Abort();}
            catch(Microsoft.AspNetCore.Http.BadHttpRequestException e){if(!context.Response.HasStarted)await Error(context,e.StatusCode==413?413:400,e.StatusCode==413?"too_large":"invalid_request");else context.Abort();}
            catch(Exception){if(!context.Response.HasStarted)await Error(context,500,"internal_error");else context.Abort();}
            finally{guard.Exit();}
        });
        try{await app.StartAsync();var addresses=app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses;return new(app,guard,addresses.Single());}
        catch{await app.DisposeAsync();guard.Dispose();throw;}
    }
    private static async Task Handle(HttpContext context,PinnedCatalog catalog,CredentialRegistry registry,ResourceGuard guard,CancellationToken cancel)
    {
        var request=context.Request;
        if(context.Features.Get<IHttpRequestFeature>()?.RawTarget.Contains('?',StringComparison.Ordinal)==true){await Error(context,400,"invalid_request");return;}
        if(request.Headers.ContainsKey("Origin")||request.Headers.ContainsKey("Cookie")){await Error(context,403,"forbidden");return;}
        var path=request.Path.Value;
        if(path!="/healthz"&&path!="/v1/catalog"&&path!="/v1/search"){await Error(context,404,"not_found");return;}
        if((path=="/v1/search"&&!HttpMethods.IsPost(request.Method))||(path!="/v1/search"&&!HttpMethods.IsGet(request.Method))){await Error(context,405,"method_not_allowed");return;}
        if(HttpMethods.IsGet(request.Method)&&(request.ContentLength>0||request.Headers.ContainsKey("Transfer-Encoding"))){await Error(context,400,"invalid_request");return;}
        if(path=="/healthz"){await Send(context,"{\"status\":\"ok\"}"u8.ToArray(),cancel);return;}
        var auth=request.Headers.Authorization;
        var client=auth.Count==1?registry.Authenticate(auth[0]??""):null;
        if(client is null){context.Response.Headers.WWWAuthenticate="Bearer";await Error(context,401,"unauthorized");return;}
        if(!guard.ClientAdmission(client.Id)){await Error(context,429,"rate_limited",60);return;}
        if(path=="/v1/catalog"){await Send(context,catalog.CatalogResponse,cancel);return;}
        if(request.Headers.ContainsKey("Content-Encoding")||!MediaTypeHeaderValue.TryParse(request.ContentType,out var media)||!string.Equals(media.MediaType,"application/json",StringComparison.OrdinalIgnoreCase)||media.Parameters.Any(p=>!string.Equals(p.Name,"charset",StringComparison.OrdinalIgnoreCase)||!string.Equals(p.Value?.Trim('"'),"utf-8",StringComparison.OrdinalIgnoreCase))){await Error(context,415,"unsupported_media_type");return;}
        if(request.ContentLength>RemoteLimits.BodyBytes){await Error(context,413,"too_large");return;}
        using var body=new MemoryStream();var buffer=new byte[512];int read;
        while((read=await request.Body.ReadAsync(buffer,cancel))!=0){if(body.Length+read>RemoteLimits.BodyBytes){await Error(context,413,"too_large");return;}body.Write(buffer,0,read);}
        string query;int limit;
        try{
            using var json=StrictJson.Parse(body.ToArray());var root=json.RootElement;StrictJson.Fields(root,"query","limit");query=root.GetProperty("query").GetString()!;var value=root.GetProperty("limit");if(value.ValueKind!=JsonValueKind.Number||value.GetRawText().Any(c=>!char.IsAsciiDigit(c))||!value.TryGetInt32(out limit)||limit is <1 or >RemoteLimits.Results||!SearchValidation.ValidQuery(query)||!StrictJson.ValidUnicode(query))throw new JsonException();
        }catch(Exception e)when(e is JsonException or InvalidOperationException or ArgumentException){await Error(context,400,"invalid_request");return;}
        cancel.ThrowIfCancellationRequested();var response=catalog.Search(query,limit);cancel.ThrowIfCancellationRequested();await Send(context,response,cancel);
    }
    private static Task Error(HttpContext context,int status,string code,int? retrySeconds=null)
    {
        context.Response.StatusCode=status;if(retrySeconds.HasValue)context.Response.Headers.RetryAfter=retrySeconds.Value.ToString(System.Globalization.CultureInfo.InvariantCulture);
        return Send(context,JsonSerializer.SerializeToUtf8Bytes(new{schemaVersion=1,error=code}),context.RequestAborted);
    }
    private static async Task Send(HttpContext context,byte[] bytes,CancellationToken cancel)
    {
        if(bytes.Length>RemoteLimits.ResponseBytes)throw new InvalidDataException();context.Response.ContentType="application/json; charset=utf-8";context.Response.ContentLength=bytes.Length;await context.Response.Body.WriteAsync(bytes,cancel);
    }
    public Task WaitForShutdownAsync(CancellationToken cancellationToken=default)=>app.WaitForShutdownAsync(cancellationToken);
    public async ValueTask DisposeAsync(){await app.StopAsync(TimeSpan.FromSeconds(3));await app.DisposeAsync();guard.Dispose();}
}
