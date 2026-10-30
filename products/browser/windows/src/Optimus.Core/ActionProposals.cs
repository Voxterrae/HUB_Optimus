using System.Globalization;
namespace Optimus.Core;
public sealed class ProposalStore(TimeProvider clock)
{
 private readonly Dictionary<Guid,(ActionProposal Proposal,long Timestamp)> pending=[];
 private readonly object gate=new();
 public ActionProposal Propose(AssistantAction action,BrowserContext context)
 {
  action=Normalize(action);
  var proposal=new ActionProposal(Guid.NewGuid(),action,context,clock.GetUtcNow().AddSeconds(60));
  lock(gate) { pending.Clear();pending.Add(proposal.Id,(proposal,clock.GetTimestamp())); }
  return proposal;
 }
 public bool TryConsume(Guid id,BrowserContext context,out AssistantAction? action)
 {
  action=null;
  lock(gate)
  {
   if(!pending.Remove(id,out var stored))return false;
   var proposal=stored.Proposal;
   if(proposal.Context!=context || clock.GetUtcNow()>=proposal.ExpiresAt || clock.GetElapsedTime(stored.Timestamp,clock.GetTimestamp())>=TimeSpan.FromSeconds(60))return false;
   action=Normalize(proposal.Action);return true;
  }
 }
 public void RevokeAll() {lock(gate) pending.Clear();}
 private static AssistantAction Normalize(AssistantAction action)
 {
  switch(action.Kind)
  {
   case ActionKind.OpenUrl:
    var result=NavigationPolicy.Resolve(action.Value??"",SearchProvider.DuckDuckGo);
    if(!result.Allowed || result.IsSearch) break;
    return action with {Value=result.Uri!.AbsoluteUri};
   case ActionKind.BookmarkCurrent when action.Value==null:return action;
   case ActionKind.SetTextScale when double.TryParse(action.Value,NumberStyles.AllowDecimalPoint,CultureInfo.InvariantCulture,out var scale) && scale>=1 && scale<=2:
    return action with {Value=scale.ToString(CultureInfo.InvariantCulture)};
   case ActionKind.SetContrast when action.Value is "true" or "false":return action;
  }
  throw new ArgumentException("La acción propuesta no está permitida.",nameof(action));
 }
}
