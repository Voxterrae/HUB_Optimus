using System.Windows;
using Microsoft.Web.WebView2.Core;
using Optimus.Core;
namespace Optimus.App;
internal sealed class PermissionController(Window owner,Action<string> status)
{
 private readonly NativePromptQueue prompts=new(owner);
 public void Revoke()=>prompts.Revoke();
 public void Request(BrowserTab tab,CoreWebView2PermissionRequestedEventArgs e,Func<bool> active)
 {
  e.State=CoreWebView2PermissionState.Deny;e.SavesInProfile=false;e.Handled=true;
  if(!active()||!e.IsUserInitiated||!Uri.TryCreate(e.Uri,UriKind.Absolute,out var uri)||!NavigationPolicy.IsAllowed(uri)) {status("Permiso denegado. Solo se revisan solicitudes iniciadas por ti en la pestaña visible.");return;}
  var kind=e.PermissionKind switch
  {
   CoreWebView2PermissionKind.Camera=>"usar la cámara",
   CoreWebView2PermissionKind.Microphone=>"usar el micrófono",
   CoreWebView2PermissionKind.Geolocation=>"conocer tu ubicación",
   CoreWebView2PermissionKind.Notifications=>"mostrar notificaciones",
   _=>null
  };
  if(kind==null) {status("Este tipo de permiso no está disponible en el piloto.");return;}
  var deferral=e.GetDeferral();
  var context=tab.Context;var epoch=prompts.Generation;
  bool Current()=>!tab.IsDisposed&&active()&&tab.Context==context&&epoch==prompts.Generation;
  prompts.Post(Current,()=>
  {
   // Posted by BeginInvoke: no WebView2 event callback remains on this stack.
   var result=MessageBox.Show(owner,$"El sitio {uri.GetLeftPart(UriPartial.Authority)} solicita {kind}.\n\nPermitir se aplica a esta solicitud. Puedes revocar permisos y recargar los documentos con «Revocar permisos».\n\n¿Permitir?","Permiso de sitio · Optimus",MessageBoxButton.YesNo,MessageBoxImage.Question,MessageBoxResult.No);
   if(result==MessageBoxResult.Yes&&Current())e.State=CoreWebView2PermissionState.Allow;
   status(e.State==CoreWebView2PermissionState.Allow?"Permiso concedido para esta solicitud.":"Permiso denegado.");
  },()=>
  {
   // Dispose completes the native deferral; DeferredRequest invokes this exactly once.
   try{deferral.Dispose();}catch(Exception error) when(error is InvalidOperationException or System.Runtime.InteropServices.COMException){status("La solicitud de permiso terminó con el documento.");}
  },_=>status("No se pudo revisar el permiso. Se ha denegado; reintenta desde la página."));
 }
}
