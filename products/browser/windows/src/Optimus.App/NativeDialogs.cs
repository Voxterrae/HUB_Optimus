using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Optimus.Core;
namespace Optimus.App;
internal static class NativeDialogs
{
 public static TextBlock ListRowText(string text)
 {
  var block=new TextBlock {Text=text,TextWrapping=TextWrapping.Wrap};
  // Follow the native item's selected/unselected foreground instead of the global text style.
  block.SetBinding(TextBlock.ForegroundProperty,new Binding(nameof(Control.Foreground)) {RelativeSource=new RelativeSource(RelativeSourceMode.FindAncestor,typeof(ListBoxItem),1)});
  return block;
 }
 public static void ShowBookmarks(Window owner,List<Bookmark> bookmarks,Action add,Action<string> open,Action save)
 {
  var panel=new DockPanel {Margin=new Thickness(10)};
  var list=new ListBox {MinHeight=100};
  void Refresh(){list.Items.Clear();foreach(var b in bookmarks)list.Items.Add(new ListBoxItem {Tag=b,Content=ListRowText(b.Title+"\n"+b.Url)});}
  var controls=new StackPanel {Orientation=Orientation.Horizontal};DockPanel.SetDock(controls,Dock.Bottom);
  var window=new Window {Owner=owner,Title="Marcadores · Optimus",Width=Math.Min(800,SystemParameters.WorkArea.Width),Height=Math.Min(500,SystemParameters.WorkArea.Height),FontSize=owner.FontSize,Content=panel};
  var addButton=new Button {Content="Guardar página actual"};addButton.Click+=(_,_)=>{add();Refresh();};controls.Children.Add(addButton);
  var openButton=new Button {Content="Abrir seleccionado"};openButton.Click+=(_,_)=>{if(list.SelectedItem is ListBoxItem {Tag:Bookmark b}){window.Close();open(b.Url);}};controls.Children.Add(openButton);
  var remove=new Button {Content="Eliminar seleccionado"};remove.Click+=(_,_)=>{if(list.SelectedItem is ListBoxItem {Tag:Bookmark b}){bookmarks.Remove(b);save();Refresh();}};controls.Children.Add(remove);
  var actions=new ScrollViewer {Content=controls,HorizontalScrollBarVisibility=ScrollBarVisibility.Auto,VerticalScrollBarVisibility=ScrollBarVisibility.Disabled};DockPanel.SetDock(actions,Dock.Bottom);panel.Children.Add(actions);panel.Children.Add(list);NativeTheme.Inherit(window,owner);Refresh();window.ShowDialog();
 }
}
