namespace Optimus.Core;
/// <summary>Every native search entry point shares host eligibility, cancellation and terminal disable.</summary>
public sealed class SearchSubmissionGate(OptimusSearchService service,Func<bool> eligible,CancellationToken hostLifetime) : IDisposable
{
 private readonly CancellationTokenSource disabledLifetime=new();
 private bool disabled,disposed;
 private CancellationTokenSource epoch=new();
 public bool CanSubmit=>!disabled&&!disposed&&!hostLifetime.IsCancellationRequested&&eligible();
 public Task<SearchResponse?> SearchAsync(string query,IReadOnlyList<Bookmark> bookmarks,string? endpoint,CancellationToken token=default)
  => SubmitAsync(c=>service.SearchAsync(query,bookmarks,endpoint,c),token);
 public Task<SearchResponse?> SearchAsync(string query,IReadOnlyList<Bookmark> bookmarks,OptimusSearchTarget target,CancellationToken token=default)
  => SubmitAsync(c=>service.SearchAsync(query,bookmarks,target,c),token);
 private async Task<SearchResponse?> SubmitAsync(Func<CancellationToken,Task<SearchResponse>> submit,CancellationToken token)
 {
  if(!CanSubmit)return null;
  using var request=CancellationTokenSource.CreateLinkedTokenSource(hostLifetime,disabledLifetime.Token,epoch.Token,token);
  if(!CanSubmit||request.IsCancellationRequested)return null;
  try
  {
   var response=await submit(request.Token);
   return CanSubmit&&!request.IsCancellationRequested?response:null;
  }
  catch(OperationCanceledException) when(!CanSubmit||request.IsCancellationRequested){return null;}
 }
 public void Invalidate(){if(disposed)return;var previous=epoch;epoch=new();previous.Cancel();previous.Dispose();}
 public void Disable(){if(disabled)return;disabled=true;disabledLifetime.Cancel();}
 public void Dispose(){if(disposed)return;Disable();disposed=true;disabledLifetime.Dispose();epoch.Dispose();}
}
