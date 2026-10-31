using System.Windows;
using System.Windows.Media;
using Microsoft.Win32;
using Optimus.Core;
namespace Optimus.App;
internal static class NativeTheme
{
 private const string StateKey="OptimusAppearanceState";
 public static bool SystemDark()
 {
  try {using var key=Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",false);return key?.GetValue("AppsUseLightTheme") is not int value||value!=1;}
  catch(Exception e) when(e is System.Security.SecurityException or UnauthorizedAccessException or System.IO.IOException){return true;}
 }
 public static void Inherit(Window window,Window owner)
 {if(owner.Resources[StateKey] is AppearanceState state)Apply(window,state);}
 public static void Apply(Window window,AppearanceState state)
 {
  window.Resources[StateKey]=state;
  var keys=new[]{"OptimusPageBrush","OptimusPanelBrush","OptimusRaisedBrush","OptimusBorderBrush","OptimusTextBrush","OptimusMutedBrush","OptimusWarmBrush","OptimusAccentBrush","OptimusOnAccentBrush"};
  var colors=state.Palette==AppearancePalette.Light?new[]{"#FAF9F6","#F0F2F3","#FFFFFF","#677180","#18212B","#495665","#805018","#006957","#FFFFFF"}:new[]{"#0F1217","#171C24","#202731","#46505F","#F5F2EC","#B7BEC9","#EDB77D","#54E0C1","#17120C"};
  Brush[] brushes=colors.Select(c=>(Brush)new SolidColorBrush((Color)ColorConverter.ConvertFromString(c))).ToArray();
  if(state.Palette==AppearancePalette.HighContrast)brushes=[Brushes.Black,Brushes.Black,Brushes.Black,Brushes.White,Brushes.White,Brushes.White,Brushes.Yellow,Brushes.Yellow,Brushes.Black];
  if(state.Palette==AppearancePalette.SystemHighContrast)brushes=[SystemColors.WindowBrush,SystemColors.WindowBrush,SystemColors.ControlBrush,SystemColors.WindowTextBrush,SystemColors.WindowTextBrush,SystemColors.WindowTextBrush,SystemColors.HighlightBrush,SystemColors.HighlightBrush,SystemColors.HighlightTextBrush];
  for(int i=0;i<keys.Length;i++)window.Resources[keys[i]]=brushes[i];
  // Native controls and custom surfaces share the resolved palette, including dialogs.
  foreach(var (key,index) in new[]{(SystemColors.WindowBrushKey,0),(SystemColors.WindowTextBrushKey,4),(SystemColors.ControlBrushKey,2),(SystemColors.ControlTextBrushKey,4),(SystemColors.HighlightBrushKey,7),(SystemColors.HighlightTextBrushKey,8)})window.Resources[key]=brushes[index];
  window.FontSize=18*state.TextScale;
  window.Resources["OptimusBodySize"]=18*state.TextScale;window.Resources["OptimusSmallSize"]=15*state.TextScale;window.Resources["OptimusTitleSize"]=48*state.TextScale;
  window.SetResourceReference(Window.BackgroundProperty,"OptimusPageBrush");window.SetResourceReference(Window.ForegroundProperty,"OptimusTextBrush");
 }
}
