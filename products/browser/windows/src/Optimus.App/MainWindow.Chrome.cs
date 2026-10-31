using System.ComponentModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using Microsoft.Win32;
namespace Optimus.App;
public partial class MainWindow
{
 private IInputElement? panelReturnFocus;
 private void InitializeChrome()
 {
  SizeChanged+=(_,_)=>UpdateChromeLayout();
  SystemParameters.StaticPropertyChanged+=SystemAppearanceChanged;
  SystemEvents.UserPreferenceChanged+=SystemThemeChanged;
  Closed+=(_,_)=>{SystemParameters.StaticPropertyChanged-=SystemAppearanceChanged;SystemEvents.UserPreferenceChanged-=SystemThemeChanged;};
  UpdateChromeLayout();
 }
 private bool appearanceRefreshQueued;
 private void SystemAppearanceChanged(object? sender,PropertyChangedEventArgs e)=>QueueAppearanceRefresh();
 private void SystemThemeChanged(object sender,UserPreferenceChangedEventArgs e)=>QueueAppearanceRefresh();
 private void QueueAppearanceRefresh()
 {
  if(!Dispatcher.CheckAccess()){Dispatcher.BeginInvoke(QueueAppearanceRefresh);return;}
  if(closing||closed||appearanceRefreshQueued)return;
  appearanceRefreshQueued=true;
  Dispatcher.BeginInvoke(()=>{appearanceRefreshQueued=false;if(!closing&&!closed)ApplyAppearance();});
 }
 private void RefreshOwnedAppearance(Window owner)
 {
  foreach(Window child in owner.OwnedWindows)
  {
   NativeTheme.Inherit(child,owner);
   RefreshOwnedAppearance(child);
  }
 }
 private void UpdateChromeLayout()
 {
  if(SidebarColumn is null)return;
  var effective=ActualWidth/CurrentAppearance.TextScale;
  var compact=effective<980;
  SidebarColumn.Width=new GridLength(compact?0:176);
  Sidebar.Visibility=compact?Visibility.Collapsed:Visibility.Visible;
  var small=effective<680;
  BrandWord.Visibility=small?Visibility.Collapsed:Visibility.Visible;
  ForwardButton.Visibility=small?Visibility.Collapsed:Visibility.Visible;
  ReloadButton.Visibility=small?Visibility.Collapsed:Visibility.Visible;
  HomeButton.Visibility=small?Visibility.Collapsed:Visibility.Visible;
  PrivateButton.Visibility=small?Visibility.Collapsed:Visibility.Visible;
  if(HelpPanel.Visibility==Visibility.Visible)
  {
   // A WebView2 owns an HWND: replace its region on narrow windows instead of drawing over it.
   if(compact){HelpColumn.Width=new GridLength(0);Grid.SetColumn(HelpPanel,0);Tabs.Visibility=Visibility.Collapsed;}
   else{Grid.SetColumn(HelpPanel,1);HelpColumn.Width=new GridLength(Math.Min(400,Math.Max(300,ActualWidth*0.29)));Tabs.Visibility=Visibility.Visible;}
  }
  else{HelpColumn.Width=new GridLength(0);Tabs.Visibility=SettingsPanel.Visibility==Visibility.Visible?Visibility.Collapsed:Visibility.Visible;}
 }
 private void RememberPanelFocus(){if(HelpPanel.Visibility!=Visibility.Visible&&SettingsPanel.Visibility!=Visibility.Visible)panelReturnFocus=Keyboard.FocusedElement is MenuItem||MenuButton.ContextMenu?.IsOpen==true?MenuButton:Keyboard.FocusedElement;}
 private void RestorePanelFocus()
 {
  if(panelReturnFocus is UIElement {IsVisible:true,IsEnabled:true} element)element.Focus();else Address.Focus();
  panelReturnFocus=null;
 }
 private void ClosePanels(bool restoreFocus=true)
 {
  var wasOpen=HelpPanel.Visibility==Visibility.Visible||SettingsPanel.Visibility==Visibility.Visible;
  if(HelpPanel.Visibility==Visibility.Visible){Revoke();ClearPreview();}
  HelpPanel.Visibility=Visibility.Collapsed;SettingsPanel.Visibility=Visibility.Collapsed;HelpColumn.Width=new GridLength(0);Tabs.Visibility=Visibility.Visible;
  if(restoreFocus&&wasOpen)RestorePanelFocus();else if(!restoreFocus)panelReturnFocus=null;
 }
 private void Settings_Click(object sender,RoutedEventArgs e)
 {
  RememberPanelFocus();Revoke();ClearPreview();HelpPanel.Visibility=Visibility.Collapsed;HelpColumn.Width=new GridLength(0);SettingsPanel.Visibility=Visibility.Visible;Tabs.Visibility=Visibility.Collapsed;
  ScaleChoice.Focus();
 }
 private void Theme_Click(object sender,RoutedEventArgs e)
 {Settings_Click(sender,e);panelReturnFocus=ThemeButton;ThemeChoice.Focus();}
 private void CloseSettings_Click(object sender,RoutedEventArgs e)=>ClosePanels();
 private void Menu_Click(object sender,RoutedEventArgs e)
 {
  var menu=MenuButton.ContextMenu!;
  RefreshMenuAppearance();
  menu.PlacementTarget=MenuButton;menu.Placement=PlacementMode.Bottom;menu.IsOpen=true;
 }
 private void RefreshMenuAppearance()
 {
  var menu=MenuButton.ContextMenu!;
  foreach(var key in new[]{"OptimusPageBrush","OptimusPanelBrush","OptimusRaisedBrush","OptimusBorderBrush","OptimusTextBrush","OptimusMutedBrush","OptimusWarmBrush","OptimusAccentBrush","OptimusOnAccentBrush","OptimusBodySize","OptimusSmallSize","OptimusTitleSize"})menu.Resources[key]=FindResource(key);
 }
}
