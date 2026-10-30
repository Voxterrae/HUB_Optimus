namespace Optimus.Core;
/// <summary>Resume requests never establish the full initialization invariant or revive a retired controller.</summary>
public sealed class ControllerReadiness : IDisposable
{
 private bool started,initialized,failed,disposed,resumeRequested;
 public bool IsInitialized=>initialized&&!failed&&!disposed;
 public bool CanNavigate=>IsInitialized&&resumeRequested;
 public async Task InitializeAsync(Func<Task> initialize)
 {
  if(started||failed||disposed)throw new InvalidOperationException("El controlador requiere una instancia nueva.");
  started=true;
  try
  {
   await initialize();
   if(failed||disposed)throw new InvalidOperationException("El controlador se retiró durante la inicialización.");
   initialized=true;
  }
  catch{Fail();throw;}
 }
 public void RequestResume(bool requested)=>resumeRequested=requested;
 public void Fail(){failed=true;initialized=false;resumeRequested=false;}
 public void Dispose(){disposed=true;Fail();}
}
