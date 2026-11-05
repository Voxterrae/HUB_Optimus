using Optimus.Search.Remote;

try
{
    if(args.Length!=0)throw new InvalidDataException();
    var registry=Environment.GetEnvironmentVariable("OPTIMUS_REMOTE_CREDENTIALS_FILE");
    var mode=Environment.GetEnvironmentVariable("OPTIMUS_REMOTE_CONTAINER_HTTP");
    if(string.IsNullOrWhiteSpace(registry)||(mode is not null and not "" and not "true"))throw new InvalidDataException();
    var data=Path.Combine(AppContext.BaseDirectory,"catalog");
    await using var server=await RemoteServer.StartAsync(new(Path.Combine(data,"public-pilot-v0.1.json"),Path.Combine(data,"public-pilot-v0.1.provenance.json"),registry){ContainerPrivateHttp=mode=="true"});
    await server.WaitForShutdownAsync();
    return 0;
}
catch
{
    Console.Error.WriteLine("Remote search startup failed.");
    return 2;
}
