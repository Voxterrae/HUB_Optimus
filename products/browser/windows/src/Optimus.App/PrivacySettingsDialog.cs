using System.Windows;
using System.Windows.Controls;
using Optimus.Core;
namespace Optimus.App;
internal sealed class PrivacySettingsDialog : Window
{
 public List<PrivacyRule>? Rules {get;private set;}
 public string? Endpoint {get;private set;}
 public WebProvider Provider {get;private set;}
 public PrivacySettingsDialog(Window owner,BrowserSettings settings)
 {
  Owner=owner;Title="Privacidad y búsqueda · Optimus";Width=Math.Min(760,SystemParameters.WorkArea.Width);Height=Math.Min(820,SystemParameters.WorkArea.Height);FontSize=owner.FontSize;
  var body=new StackPanel {Margin=new Thickness(16)};Content=new ScrollViewer {Content=body,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  body.Children.Add(new TextBlock {Text="Elige qué sitios se abren en privado o se bloquean. Bloquear tiene prioridad. Guardar cierra las páginas actuales y cancela ayuda y búsquedas; puedes perder texto no guardado.",TextWrapping=TextWrapping.Wrap});
  body.Children.Add(new TextBlock {Text="Lista inicial editable: pornhub.com, xvideos.com y xnxx.com se abren en privado, incluidos sus subdominios. No es una lista completa ni una clasificación; configurar una regla no visita el sitio.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,10,0,10)});
  var candidate=settings.PrivacyRules.ToList();var list=new ListBox {Height=190};System.Windows.Automation.AutomationProperties.SetName(list,"Reglas de sitios web");body.Children.Add(list);
  void Refresh(){list.Items.Clear();foreach(var rule in candidate)list.Items.Add(new ListBoxItem {MinHeight=44,Content=NativeDialogs.ListRowText($"{rule.Domain} · {(rule.Action==PrivacyAction.Block?"Bloquear":"Abrir en privado")} · {(rule.IncludeSubdomains?"incluye subdominios":"solo este dominio")}"),Tag=rule});}
  body.Children.Add(new TextBlock {Text="Sitio web",Margin=new Thickness(0,10,0,0)});
  var site=new TextBox {ToolTip="Por ejemplo: example.org o https://example.org"};System.Windows.Automation.AutomationProperties.SetName(site,"Sitio web para la regla");body.Children.Add(site);
  var destination=new TextBlock {Text="Escribe un sitio para revisar el dominio antes de añadirlo.",TextWrapping=TextWrapping.Wrap};body.Children.Add(destination);
  var action=new ComboBox {SelectedIndex=0};action.Items.Add("Abrir en privado");action.Items.Add("Bloquear");System.Windows.Automation.AutomationProperties.SetName(action,"Qué hacer con este sitio");body.Children.Add(action);
  var subdomains=new CheckBox {Content="Incluir subdominios",IsChecked=true};body.Children.Add(subdomains);
  body.Children.Add(new TextBlock {Text="Por ejemplo, una regla para example.org también cubre ayuda.example.org cuando activas esta opción.",TextWrapping=TextWrapping.Wrap});
  var error=new TextBlock {TextWrapping=TextWrapping.Wrap};
  string? Domain()
  {
   var text=site.Text.Trim();
   if(text.StartsWith("http://",StringComparison.OrdinalIgnoreCase)||text.StartsWith("https://",StringComparison.OrdinalIgnoreCase))
   {if(!Uri.TryCreate(text,UriKind.Absolute,out var uri)||!NavigationPolicy.IsAllowed(uri))throw new ArgumentException("Usa una dirección HTTP o HTTPS sin usuario ni contraseña.");try{text=uri.IdnHost;}catch(UriFormatException){throw new ArgumentException("Dominio no válido.");}}
   return string.IsNullOrEmpty(text)?null:PrivacyPolicy.NormalizeDomain(text);
  }
  site.TextChanged+=(_,_)=>{try{var host=Domain();destination.Text=host==null?"Escribe un sitio para revisar el dominio antes de añadirlo.":"La regla se aplicará al dominio: "+host;}catch(ArgumentException e){destination.Text=e.Message;}};
  list.SelectionChanged+=(_,_)=>{if(list.SelectedItem is ListBoxItem {Tag:PrivacyRule rule}){site.Text=rule.Domain;action.SelectedIndex=rule.Action==PrivacyAction.Block?1:0;subdomains.IsChecked=rule.IncludeSubdomains;}};
  var editing=new StackPanel {Orientation=Orientation.Horizontal};body.Children.Add(editing);var add=new Button {Content="Añadir regla"};editing.Children.Add(add);var remove=new Button {Content="Quitar regla seleccionada"};editing.Children.Add(remove);
  add.Click+=(_,_)=>
  {
   try
   {
    var host=Domain()??throw new ArgumentException("Escribe primero un sitio web.");var rule=new PrivacyRule(host,action.SelectedIndex==1?PrivacyAction.Block:PrivacyAction.Private,subdomains.IsChecked==true);
    var replacement=candidate.FindIndex(r=>r.Domain==rule.Domain&&r.IncludeSubdomains==rule.IncludeSubdomains);var updated=candidate.ToList();if(replacement>=0)updated[replacement]=rule;else updated.Add(rule);PrivacyPolicy.ValidateRules(updated);candidate=updated;Refresh();error.Text="Regla preparada para "+host+". Pulsa Guardar para aplicarla.";
   }catch(ArgumentException e){error.Text=e.Message;}
  };
  remove.Click+=(_,_)=>{if(list.SelectedIndex>=0){candidate.RemoveAt(list.SelectedIndex);Refresh();error.Text="Regla quitada de la lista. Pulsa Guardar para aplicar el cambio.";}else error.Text="Selecciona una regla para quitarla.";};
  body.Children.Add(new TextBlock {Text="Búsqueda en la Web",FontWeight=FontWeights.Bold,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,16,0,8)});
  var source=new ComboBox {MinHeight=44,SelectedValuePath="Tag"};
  System.Windows.Automation.AutomationProperties.SetName(source,"Fuente Web de Optimus");
  foreach(var option in new[]{(WebProvider.None,"Web sin configurar"),(WebProvider.Mwmbl,"Mwmbl · piloto privado"),(WebProvider.Searx,"SearXNG · servidor del operador")})
  {
   var item=new ComboBoxItem {Tag=option.Item1,Content=NativeDialogs.ListRowText(option.Item2),MinHeight=44};
   System.Windows.Automation.AutomationProperties.SetName(item,option.Item2);source.Items.Add(item);
  }
  source.SelectedValue=WebSearchConfiguration.FromSettings(settings).Provider;body.Children.Add(source);
  var sourceNote=new TextBlock {TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,8)};body.Children.Add(sourceNote);
  var server=new StackPanel();server.Children.Add(new TextBlock {Text="Servidor SearXNG"});
  var endpoint=new TextBox {Text=settings.SearxEndpoint??"",MinHeight=44};System.Windows.Automation.AutomationProperties.SetName(endpoint,"Servidor SearXNG");server.Children.Add(endpoint);body.Children.Add(server);
  void DescribeSource()
  {
   var selected=source.SelectedValue is WebProvider value?value:WebProvider.None;
   server.Visibility=selected==WebProvider.Searx?Visibility.Visible:Visibility.Collapsed;
   sourceNote.Text=selected switch
   {
    WebProvider.Mwmbl=>"Piloto privado. Al buscar, Mwmbl recibe tu consulta y la IP de tu conexión. Tiene límites y su uso empresarial está pendiente de aclaración. Los resultados proceden de fuentes externas; no cubren toda la web.",
    WebProvider.Searx=>"El servidor del operador recibe la consulta y puede consultar otras fuentes. Usa HTTPS; HTTP solo se admite en este equipo.",
    _=>"La búsqueda Web queda desactivada. El índice Optimus sigue disponible sin conexión, entre los documentos importados."
   };
  }
  source.SelectionChanged+=(_,_)=>DescribeSource();DescribeSource();body.Children.Add(error);
  var save=new Button {Content="Guardar y cerrar páginas actuales"};body.Children.Add(save);save.Click+=(_,_)=>
  {
   try
   {
    PrivacyPolicy.ValidateRules(candidate);
    if(source.SelectedValue is not WebProvider selected)throw new ArgumentException("Elige una fuente Web.");
    var address=selected==WebProvider.Searx?(string.IsNullOrWhiteSpace(endpoint.Text)?null:endpoint.Text.Trim()):settings.SearxEndpoint;
    _=new WebSearchConfiguration(selected,address);
    Rules=candidate;Endpoint=address;Provider=selected;DialogResult=true;
   }
   catch(ArgumentException e){error.Text=e.Message;}
  };
  var cancel=new Button {Content="Cancelar"};cancel.Click+=(_,_)=>DialogResult=false;body.Children.Add(cancel);Refresh();NativeTheme.Inherit(this,owner);
 }
}
