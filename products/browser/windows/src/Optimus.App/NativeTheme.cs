using System.Windows;
using System.Windows.Media;
namespace Optimus.App;
internal static class NativeTheme
{
 public static void Apply(Window window,bool highContrast,double scale=1)
 {
  highContrast|=SystemParameters.HighContrast;
  // All visual surfaces use the same semantic palette; site content keeps its own colors.
  foreach(var (key,brush) in new (string,Brush)[]{("OptimusPageBrush",SystemColors.WindowBrush),("OptimusPanelBrush",SystemColors.WindowBrush),("OptimusRaisedBrush",SystemColors.ControlBrush),("OptimusBorderBrush",SystemColors.WindowTextBrush),("OptimusTextBrush",SystemColors.WindowTextBrush),("OptimusMutedBrush",SystemColors.WindowTextBrush),("OptimusWarmBrush",SystemColors.HighlightBrush),("OptimusAccentBrush",SystemColors.HighlightBrush),("OptimusOnAccentBrush",SystemColors.HighlightTextBrush)})
  {if(highContrast)window.Resources[key]=brush;else window.Resources.Remove(key);}
  if(highContrast&&!SystemParameters.HighContrast)
  {
   foreach(var key in new[]{"OptimusPageBrush","OptimusPanelBrush","OptimusRaisedBrush"})window.Resources[key]=Brushes.Black;
   foreach(var key in new[]{"OptimusBorderBrush","OptimusTextBrush","OptimusMutedBrush"})window.Resources[key]=Brushes.White;
   window.Resources["OptimusWarmBrush"]=Brushes.Yellow;window.Resources["OptimusAccentBrush"]=Brushes.Yellow;window.Resources["OptimusOnAccentBrush"]=Brushes.Black;
  }
  window.Resources["OptimusBodySize"]=18*scale;window.Resources["OptimusSmallSize"]=15*scale;window.Resources["OptimusTitleSize"]=48*scale;
  window.SetResourceReference(Window.BackgroundProperty,"OptimusPageBrush");window.SetResourceReference(Window.ForegroundProperty,"OptimusTextBrush");
 }
}
