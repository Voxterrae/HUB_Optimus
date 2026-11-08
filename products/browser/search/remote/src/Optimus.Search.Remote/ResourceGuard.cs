namespace Optimus.Search.Remote;

public static class RemoteLimits
{
    public const int BodyBytes=2048,QueryUtf16=500,Results=8,ResponseBytes=65536,Concurrent=4,GlobalPerMinute=120,ClientPerMinute=30;
    public static readonly TimeSpan Deadline=TimeSpan.FromSeconds(2);
}
internal sealed class ResourceGuard:IDisposable
{
    private sealed class Window(long started){public long Started=started;public int Count;}
    private readonly TimeProvider time;
    private readonly object gate=new();
    private readonly Window global;
    private readonly Dictionary<string,Window> clients=new(StringComparer.Ordinal);
    private readonly SemaphoreSlim concurrency=new(RemoteLimits.Concurrent,RemoteLimits.Concurrent);
    public ResourceGuard(TimeProvider clock){time=clock;global=new(time.GetTimestamp());}
    public bool GlobalAdmission(){lock(gate)return Consume(global,RemoteLimits.GlobalPerMinute);}
    public bool ClientAdmission(string id){lock(gate){if(!clients.TryGetValue(id,out var window))clients.Add(id,window=new(time.GetTimestamp()));return Consume(window,RemoteLimits.ClientPerMinute);}}
    private bool Consume(Window window,int limit)
    {
        var now=time.GetTimestamp();if(time.GetElapsedTime(window.Started,now)>=TimeSpan.FromMinutes(1)){window.Started=now;window.Count=0;}if(window.Count>=limit)return false;window.Count++;return true;
    }
    public bool Enter()=>concurrency.Wait(0);
    public void Exit()=>concurrency.Release();
    public void Dispose()=>concurrency.Dispose();
}
