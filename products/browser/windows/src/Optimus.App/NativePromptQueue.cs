using System.Windows;
using System.Windows.Threading;
using Optimus.Core;
namespace Optimus.App;
/// <summary>Modal UI runs in a later dispatcher turn, after the WebView2 callback unwinds.</summary>
internal sealed class NativePromptQueue(Window owner)
{
 private readonly HashSet<DeferredRequest> pending=[];
 public long Generation {get;private set;}
 public void Revoke(){Generation++;foreach(var request in pending.ToArray())request.Cancel();}
 public void Post(Func<bool> current,Action prompt,Action complete,Action<Exception> failed)
 {
  DeferredRequest? request=null;
  request=new(current,prompt,()=>{try{complete();}finally{pending.Remove(request!);}},failed);
  pending.Add(request);
  request.Post(run=>
  {
   if(owner.Dispatcher.HasShutdownStarted){request.Cancel();return;}
   var operation=owner.Dispatcher.BeginInvoke(DispatcherPriority.Normal,run);
   operation.Aborted+=(_,_)=>request.Cancel();
  });
 }
}
