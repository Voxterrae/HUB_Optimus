using System.IO;
using Microsoft.Web.WebView2.Core;
using Optimus.Core;
namespace Optimus.App;
/// <summary>Installed before navigation on every participating control. Worker decisions never infer tab mode.</summary>
internal sealed class PrivacyBarrier
{
 private readonly CoreWebView2Environment environment;
 private readonly Func<PrivacyPolicy> policy;
 private readonly bool isPrivate;
 private readonly Action failed;
 public PrivacyBarrier(CoreWebView2Environment environment,CoreWebView2 core,Func<PrivacyPolicy> policy,bool isPrivate,Action failed)
 {
  this.environment=environment;this.policy=policy;this.isPrivate=isPrivate;this.failed=failed;
  core.AddWebResourceRequestedFilter("*",CoreWebView2WebResourceContext.All,CoreWebView2WebResourceRequestSourceKinds.All);
  core.WebResourceRequested+=Requested;
 }
 private void Requested(object? sender,CoreWebView2WebResourceRequestedEventArgs e)
 {
  try
  {
  var worker=(e.RequestedSourceKind&(CoreWebView2WebResourceRequestSourceKinds.ServiceWorker|CoreWebView2WebResourceRequestSourceKinds.SharedWorker))!=0;
  var action=Uri.TryCreate(e.Request.Uri,UriKind.Absolute,out var uri)?policy().Evaluate(uri,isPrivate,worker):PrivacyAction.Block;
  if(action!=PrivacyAction.Block&&(isPrivate||action!=PrivacyAction.Private))return;
  // Context.Document can also mean a frame. Never reopen/replay from a resource callback.
  e.Response=environment.CreateWebResourceResponse(new MemoryStream(System.Text.Encoding.UTF8.GetBytes("Optimus: solicitud bloqueada por reglas locales. Abre el sitio manualmente en privado desde Optimus.")),403,"Blocked by local privacy policy","Content-Type: text/plain; charset=utf-8\r\nCache-Control: no-store");
  }
  catch(Exception error) when(error is ArgumentException or InvalidOperationException or NotImplementedException or NotSupportedException or System.Runtime.InteropServices.COMException or UriFormatException)
  {failed();}
 }
}
