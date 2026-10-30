namespace Optimus.Core;
/// <summary>Owns one engine deferral. Production supplies a UI dispatcher that always posts.</summary>
public sealed class DeferredRequest(Func<bool> current,Action prompt,Action complete,Action<Exception> failed)
{
 private int completed;
 public void Post(Action<Action> post)
 {try{post(Run);}catch(Exception e){try{failed(e);}finally{Cancel();}}}
 public void Run()
 {
  if(Volatile.Read(ref completed)!=0)return;
  try{if(current())prompt();}catch(Exception e){failed(e);}finally{Cancel();}
 }
 public void Cancel(){if(Interlocked.Exchange(ref completed,1)==0)complete();}
}
/// <summary>Serializes creation and destructive tab operations, including their awaits.</summary>
public sealed class AsyncOperationQueue
{
 private readonly SemaphoreSlim serial=new(1,1);
 public async Task RunAsync(Func<Task> operation,CancellationToken cancellationToken=default)
 {await serial.WaitAsync(cancellationToken);try{cancellationToken.ThrowIfCancellationRequested();await operation();}finally{serial.Release();}}
}
public sealed class OperationLifetime : IDisposable
{
 private readonly CancellationTokenSource source=new();
 private readonly CancellationToken token;
 public OperationLifetime(){token=source.Token;}
 public bool IsDisposed {get;private set;}
 public CancellationToken Token=>token;
 public void Check()=>token.ThrowIfCancellationRequested();
 public void Dispose(){if(IsDisposed)return;IsDisposed=true;source.Cancel();source.Dispose();}
}
/// <summary>A bounded UI wait never cancels or abandons the owned profile operation.
/// Timeout/fault keeps this process blocked until a controlled restart, even after late settlement.</summary>
public sealed class ProfileOperationGate
{
 public bool IsBlocked {get;private set;}
 public bool RequiresRestart {get;private set;}
 public Task? UnderlyingTask {get;private set;}
 public Task<bool>? SettlementTask {get;private set;}
 public async Task<bool> RunAsync(Task operation,Action restoreSafety,TimeSpan wait)
 {
  if(IsBlocked)throw new InvalidOperationException("El perfil no está disponible hasta reiniciar.");
  IsBlocked=true;UnderlyingTask=operation;SettlementTask=SettleAsync(operation,restoreSafety);
  try{return await SettlementTask.WaitAsync(wait);}
  catch(TimeoutException){IsBlocked=true;RequiresRestart=true;return false;}
 }
 private async Task<bool> SettleAsync(Task operation,Action restoreSafety)
 {
  try{await operation;restoreSafety();if(RequiresRestart)return false;IsBlocked=false;return true;}
  catch(Exception){IsBlocked=true;RequiresRestart=true;return false;}
 }
}
public enum BookmarkSaveResult { Saved, AlreadyExists, Failed }
public static class BookmarkPersistence
{
 public static BookmarkSaveResult TryAdd(List<Bookmark> bookmarks,Bookmark bookmark,Func<bool> save)
 {
  if(bookmarks.Any(b=>b.Url==bookmark.Url))return BookmarkSaveResult.AlreadyExists;
  bookmarks.Add(bookmark);bool saved=false;
  try{saved=save();return saved?BookmarkSaveResult.Saved:BookmarkSaveResult.Failed;}
  finally{if(!saved)bookmarks.Remove(bookmark);}
 }
}
