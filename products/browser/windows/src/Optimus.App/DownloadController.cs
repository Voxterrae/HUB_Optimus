using System.Windows;
using System.Windows.Controls;
using Microsoft.Web.WebView2.Core;
using Microsoft.Win32;
namespace Optimus.App;
internal sealed class DownloadController(Window owner,Action<string> status)
{
 private readonly List<(CoreWebView2DownloadOperation Operation,TextBlock Label)> downloads=[];
 private Window? window;
 private readonly NativePromptQueue prompts=new(owner);
 private readonly StackPanel rows=new();
 public void Request(BrowserTab tab,CoreWebView2DownloadStartingEventArgs e,Func<bool> active)
 {
  e.Handled=true;e.Cancel=true;
  if(!active()) {e.Cancel=true;status("Descarga de una pestaña no visible bloqueada.");return;}
  var deferral=e.GetDeferral();var context=tab.Context;var generation=prompts.Generation;
  bool Current()=>!tab.IsDisposed&&active()&&tab.Context==context&&generation==prompts.Generation;
  prompts.Post(Current,()=>
  {
   var dialog=new SaveFileDialog {Title=(tab.IsPrivate?"Descarga privada: el archivo se conserva · ":"Guardar descarga de ")+context.Origin,FileName=SafeName(e.ResultFilePath),CheckPathExists=true,OverwritePrompt=true,Filter="Todos los archivos|*.*"};
   if(dialog.ShowDialog(owner)!=true||!Current()) {e.Cancel=true;status("Descarga cancelada.");return;}
   e.ResultFilePath=dialog.FileName;e.Cancel=false;var op=e.DownloadOperation;
   var row=new StackPanel {Margin=new Thickness(8)};var label=new TextBlock {TextWrapping=TextWrapping.Wrap};var cancel=new Button {Content="Cancelar esta descarga",HorizontalAlignment=HorizontalAlignment.Left};
   cancel.Click+=(_,_)=>{try{if(op.State==CoreWebView2DownloadState.InProgress)op.Cancel();}catch(Exception error) when(error is InvalidOperationException or System.Runtime.InteropServices.COMException){status("No se pudo cancelar desde el motor. Cierra la pestaña y revisa el archivo de destino.");}};row.Children.Add(label);row.Children.Add(cancel);rows.Children.Add(row);downloads.Add((op,label));
   void Update()
   {
    try
    {
    var state=op.State switch {CoreWebView2DownloadState.Completed=>"Completada · no se abrirá automáticamente",CoreWebView2DownloadState.Interrupted=>"Interrumpida: "+op.InterruptReason,_=>"En curso"};
    label.Text=$"{dialog.FileName}\n{op.BytesReceived:N0} bytes recibidos · {state}";cancel.IsEnabled=op.State==CoreWebView2DownloadState.InProgress;
    }catch(Exception error) when(error is InvalidOperationException or System.Runtime.InteropServices.COMException) {label.Text=dialog.FileName+"\nEl motor no responde; comprueba el archivo antes de usarlo.";cancel.IsEnabled=false;}
   }
   op.BytesReceivedChanged+=(_,_)=>Update();op.StateChanged+=(_,_)=>Update();Update();status("Descarga iniciada. Destino: "+dialog.FileName);Show();
  },()=>
  {
   try{deferral.Dispose();}catch(Exception error) when(error is InvalidOperationException or System.Runtime.InteropServices.COMException){status("La solicitud de descarga terminó con el documento.");}
  },_=>{try{e.Cancel=true;}catch(Exception error) when(error is InvalidOperationException or System.Runtime.InteropServices.COMException){}status("No se pudo preparar la descarga. Reintenta desde la página.");});
 }

 public void Show()
 {
  if(window==null)
  {
   window=new Window {Owner=owner,Title="Descargas · Optimus",Width=Math.Min(800,SystemParameters.WorkArea.Width),Height=Math.Min(500,SystemParameters.WorkArea.Height),FontSize=owner.FontSize,Content=new ScrollViewer {Content=rows,VerticalScrollBarVisibility=ScrollBarVisibility.Auto}};
   window.Closing+=(_,e)=>{e.Cancel=true;window.Hide();};
  }
  window.FontSize=owner.FontSize;NativeTheme.Inherit(window,owner);window.Show();window.Activate();
 }
 public void CancelAll() {prompts.Revoke();foreach(var (op,_) in downloads) {try{if(op.State==CoreWebView2DownloadState.InProgress)op.Cancel();}catch(Exception e) when(e is InvalidOperationException or System.Runtime.InteropServices.COMException){}}}
 private static string SafeName(string path)
 {
  var name=System.IO.Path.GetFileName(path);return string.IsNullOrWhiteSpace(name)?"descarga":name;
 }
}
