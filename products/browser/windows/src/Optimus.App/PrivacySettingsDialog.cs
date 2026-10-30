using System.Windows;
using System.Windows.Controls;
using Optimus.Core;
namespace Optimus.App;
internal sealed class PrivacySettingsDialog : Window
{
 public List<PrivacyRule>? Rules {get;private set;}
 public string? Endpoint {get;private set;}
 public PrivacySettingsDialog(Window owner,BrowserSettings settings)
 {
  Owner=owner;Title="Privacidad y búsqueda · Optimus";Width=Math.Min(760,SystemParameters.WorkArea.Width);Height=Math.Min(820,SystemParameters.WorkArea.Height);FontSize=owner.FontSize;
  var body=new StackPanel {Margin=new Thickness(16)};Content=new ScrollViewer {Content=body,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
  body.Children.Add(new TextBlock {Text="Elige qué sitios se abren en privado o se bloquean. Bloquear tiene prioridad. Guardar cierra las páginas actuales y cancela ayuda y búsquedas; puedes perder texto no guardado.",TextWrapping=TextWrapping.Wrap});
  body.Children.Add(new TextBlock {Text="Lista inicial editable: pornhub.com, xvideos.com y xnxx.com se abren en privado, incluidos sus subdominios. No es una lista completa ni una clasificación; configurar una regla no visita el sitio.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,10,0,10)});
  var candidate=settings.PrivacyRules.ToList();var list=new ListBox {Height=190};System.Windows.Automation.AutomationProperties.SetName(list,"Reglas de sitios web");body.Children.Add(list);
  void Refresh(){list.Items.Clear();foreach(var rule in candidate)list.Items.Add(new ListBoxItem {MinHeight=44,Content=new TextBlock {Text=$"{rule.Domain} · {(rule.Action==PrivacyAction.Block?"Bloquear":"Abrir en privado")} · {(rule.IncludeSubdomains?"incluye subdominios":"solo este dominio")}",TextWrapping=TextWrapping.Wrap},Tag=rule});}
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
  body.Children.Add(new TextBlock {Text="Búsqueda web opcional · servidor SearXNG del operador",FontWeight=FontWeights.Bold,TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,16,0,0)});
  body.Children.Add(new TextBlock {Text="Déjalo vacío para usar Wikipedia y marcadores. Un servidor configurado recibe tus consultas y conexión. Se admite HTTPS; HTTP solo en este equipo (localhost). Optimus no elige un servidor público por ti.",TextWrapping=TextWrapping.Wrap});
  var endpoint=new TextBox {Text=settings.SearxEndpoint??""};System.Windows.Automation.AutomationProperties.SetName(endpoint,"Servidor SearXNG opcional");body.Children.Add(endpoint);body.Children.Add(error);
  var save=new Button {Content="Guardar y cerrar páginas actuales"};body.Children.Add(save);save.Click+=(_,_)=>
  {
   try{PrivacyPolicy.ValidateRules(candidate);var address=string.IsNullOrWhiteSpace(endpoint.Text)?null:endpoint.Text.Trim();if(address!=null&&!OptimusSearchService.IsValidEndpoint(address))throw new ArgumentException("Servidor no válido: usa HTTPS sin usuario, contraseña, consulta ni fragmento. HTTP solo localhost.");Rules=candidate;Endpoint=address;DialogResult=true;}
   catch(ArgumentException e){error.Text=e.Message;}
  };
  var cancel=new Button {Content="Cancelar"};cancel.Click+=(_,_)=>DialogResult=false;body.Children.Add(cancel);Refresh();NativeDialogs.ApplyContrast(this,settings.HighContrast);
 }
}
