using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Optimus.Core;
namespace Optimus.App;
internal static class NativeDialogs
{
 public static void ShowBookmarks(Window owner,List<Bookmark> bookmarks,Action add,Action<string> open,Action save)
 {
  var panel=new DockPanel {Margin=new Thickness(10)};
  var list=new ListBox {MinHeight=100};
  void Refresh(){list.Items.Clear();foreach(var b in bookmarks)list.Items.Add(new ListBoxItem {Tag=b,Content=new TextBlock {Text=b.Title+"\n"+b.Url,TextWrapping=TextWrapping.Wrap}});}
  var controls=new StackPanel {Orientation=Orientation.Horizontal};DockPanel.SetDock(controls,Dock.Bottom);
  var window=new Window {Owner=owner,Title="Marcadores · Optimus",Width=Math.Min(800,SystemParameters.WorkArea.Width),Height=Math.Min(500,SystemParameters.WorkArea.Height),FontSize=owner.FontSize,Content=panel};
  var addButton=new Button {Content="Guardar página actual"};addButton.Click+=(_,_)=>{add();Refresh();};controls.Children.Add(addButton);
  var openButton=new Button {Content="Abrir seleccionado"};openButton.Click+=(_,_)=>{if(list.SelectedItem is ListBoxItem {Tag:Bookmark b}){window.Close();open(b.Url);}};controls.Children.Add(openButton);
  var remove=new Button {Content="Eliminar seleccionado"};remove.Click+=(_,_)=>{if(list.SelectedItem is ListBoxItem {Tag:Bookmark b}){bookmarks.Remove(b);save();Refresh();}};controls.Children.Add(remove);
  var actions=new ScrollViewer {Content=controls,HorizontalScrollBarVisibility=ScrollBarVisibility.Auto,VerticalScrollBarVisibility=ScrollBarVisibility.Disabled};DockPanel.SetDock(actions,Dock.Bottom);panel.Children.Add(actions);panel.Children.Add(list);ApplyContrast(window,owner.Resources.Contains(SystemColors.WindowBrushKey));Refresh();window.ShowDialog();
 }
 public static void ApplyContrast(Window window,bool enabled)
 {
  // Scoped resources affect native controls; site colors remain under site/Windows control.
  foreach(var (key,normal,high) in new[]{(SystemColors.WindowBrushKey,SystemColors.WindowBrush,Brushes.Black),(SystemColors.WindowTextBrushKey,SystemColors.WindowTextBrush,Brushes.White),(SystemColors.ControlBrushKey,SystemColors.ControlBrush,Brushes.Black),(SystemColors.ControlTextBrushKey,SystemColors.ControlTextBrush,Brushes.White),(SystemColors.HighlightBrushKey,SystemColors.HighlightBrush,Brushes.Yellow),(SystemColors.HighlightTextBrushKey,SystemColors.HighlightTextBrush,Brushes.Black)})
  {if(enabled)window.Resources[key]=high;else window.Resources.Remove(key);}
 }
}
