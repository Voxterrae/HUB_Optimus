namespace Optimus.Core;
/// <summary>Every native search entry point shares host eligibility, cancellation and terminal disable.</summary>
public sealed class SearchSubmissionGate(OptimusSearchService service,Func<bool> eligible,CancellationToken hostLifetime) : IDisposable
{
 private readonly CancellationTokenSource disabledLifetime=new();
 private bool disabled,disposed;
 public bool CanSubmit=>!disabled&&!disposed&&!hostLifetime.IsCancellationRequested&&eligible();
 public async Task<SearchResponse?> SearchAsync(string query,IReadOnlyList<Bookmark> bookmarks,string? endpoint,CancellationToken token=default)
 {
  if(!CanSubmit)return null;
  using var request=CancellationTokenSource.CreateLinkedTokenSource(hostLifetime,disabledLifetime.Token,token);
  if(!CanSubmit||request.IsCancellationRequested)return null;
  try
  {
   var response=await service.SearchAsync(query,bookmarks,endpoint,request.Token);
   return CanSubmit&&!request.IsCancellationRequested?response:null;
  }
  catch(OperationCanceledException) when(!CanSubmit){return null;}
 }
 public void Disable(){if(disabled)return;disabled=true;disabledLifetime.Cancel();}
 public void Dispose(){if(disposed)return;Disable();disposed=true;disabledLifetime.Dispose();}
}
