using System.Text.Json;
using Optimus.Core;
namespace Optimus.App;
internal sealed class HelpController
{
 private readonly ProposalStore store=new(TimeProvider.System);
 public ActionProposal? Pending {get;private set;}
 private long proposedAt;
 public GuideReply Ask(string question,BrowserContext context)
 {
  Revoke();var reply=LocalGuide.Respond(question,context);if(reply.Action!=null){Pending=store.Propose(reply.Action,context);proposedAt=TimeProvider.System.GetTimestamp();}return reply;
 }
 public bool Confirm(BrowserContext context,out AssistantAction? action)
 {
  var proposal=Pending;Pending=null;action=null;return proposal!=null&&store.TryConsume(proposal.Id,context,out action);
 }
 public void Revoke() {store.RevokeAll();Pending=null;}
 public bool Expired=>Pending!=null&&(TimeProvider.System.GetUtcNow()>=Pending.ExpiresAt||TimeProvider.System.GetElapsedTime(proposedAt,TimeProvider.System.GetTimestamp())>=TimeSpan.FromSeconds(60));
 // Fixed, user-initiated only; no iframes, forms, active editable elements or editable descendants.
 internal const string SelectionScript="""
 (() => {
  if (window !== window.top || document.activeElement?.tagName === 'IFRAME') return {error:'Solo se admite el documento principal.'};
  const editable = n => n && (n.nodeType === 1 ? n : n.parentElement)?.closest('input,textarea,select,[contenteditable]');
  const s=window.getSelection();
  if (!s || !s.rangeCount || s.isCollapsed) return {error:'Selecciona texto del documento principal o pega un fragmento.'};
  if (editable(document.activeElement)||editable(s.anchorNode)||editable(s.focusNode)) return {error:'No se capturan campos editables.'};
  for (let i=0;i<s.rangeCount;i++) {
   const r=s.getRangeAt(i);
   if (r.startContainer.ownerDocument!==document || r.endContainer.ownerDocument!==document) return {error:'El documento no coincide.'};
   for (const el of document.querySelectorAll('input,textarea,select,[contenteditable]')) {
    if (r.intersectsNode(el)) return {error:'La selección incluye campos editables. Selecciona otro fragmento.'};
   }
  }
  const text=s.toString();return {text:text.slice(0,8001)};
 })()
 """;
 public static async Task<SelectionResult> ReadSelectionAsync(BrowserTab tab)
 {
  if(tab.Core==null||tab.IsHome) return new(null,"Abre una página y selecciona texto.");
  var context=tab.Context;var json=await tab.Core.ExecuteScriptAsync(SelectionScript);
  if(tab.Context!=context) return new(null,"La página cambió. Vuelve a seleccionar el texto.");
  using var result=JsonDocument.Parse(json);
  if(result.RootElement.TryGetProperty("error",out var error))return new(null,error.GetString());
  if(!result.RootElement.TryGetProperty("text",out var text))return new(null,"No se pudo leer la selección. Puedes pegar un fragmento.");
  return new(text.GetString(),null);
 }
}
internal record SelectionResult(string? Text,string? Error);
