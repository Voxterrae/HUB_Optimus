using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Threading;
using Microsoft.Web.WebView2.Core;
using Optimus.Core;
namespace Optimus.App;
public partial class MainWindow : Window
{
 private readonly SettingsStore settingsStore=new(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Optimus","private-pilot","settings-v02.json"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Optimus","private-pilot","settings.json"));
 private BrowserSettings settings=new();
 private readonly System.Net.Http.HttpClient searchConnectionClient = new(new System.Net.Http.HttpClientHandler { AllowAutoRedirect=false, UseCookies=false, UseDefaultCredentials=false, Credentials=null, UseProxy=false });
 private readonly SearchHostLauncher searchHost;

 private readonly HelpController help=new();
 private readonly PermissionController permissions;
 private readonly DownloadController downloads;
 private readonly Stack<string?> closedTabs=new();
 private CoreWebView2Environment? environment;
 private bool ready,closing,closed;
 private PrivacyPolicy privacy=new(PrivacyPolicy.Seeds());
 private long policyGeneration;
 private readonly PrivateSessionIdentity privateSession=new();
 private readonly HashSet<string> historyClearedProfiles=[];
 private (BrowserTab Tab,string Url,NavigationLease Lease)? pendingPrivate;
 private readonly AsyncOperationQueue tabOperations=new();
 private readonly OperationLifetime lifetime=new();
 private readonly ProfileOperationGate profileGate=new();
 private Task<CoreWebView2Environment>? environmentCreation;
 private BrowserContext? previewContext;
 private long sharingGeneration;
 private bool clearingData;
 private BrowserTab? Active=>Tabs.SelectedItem is TabItem {Tag:BrowserTab tab}?tab:null;
 private readonly DispatcherTimer timer=new() {Interval=TimeSpan.FromMilliseconds(500)};
 public MainWindow()
 {
  searchHost=new(searchConnectionClient,AppContext.BaseDirectory,Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData));
  InitializeComponent();Width=Math.Min(1400,SystemParameters.WorkArea.Width);Height=Math.Min(920,SystemParameters.WorkArea.Height);permissions=new(this,SetStatus);downloads=new(this,SetStatus);
  var loaded=settingsStore.Load();settings=loaded.Settings;privacy=new(settings.PrivacyRules);
  SearchChoice.SelectedValue=settings.SearchProvider;ScaleChoice.SelectedIndex=ScaleIndex(settings.TextScale);ContrastChoice.IsChecked=settings.HighContrast;RestoreChoice.IsChecked=settings.RestoreSession;
  ApplyAppearance();ready=true;
  if(loaded.Error!=null)SetStatus(loaded.Error);
  Loaded+=async(_,_)=>await StartAsync(loaded.Error);
  Closing+=Window_Closing;
  Address.TextChanged+=(_,_)=>{if(ready&&Address.IsKeyboardFocusWithin)Active?.CancelSearch();};
  timer.Tick+=(_,_)=>{if(help.Expired) {Revoke();SetStatus("La propuesta caducó a los 60 segundos. Vuelve a consultar la guía para revisarla.");}};timer.Start();
  CommandBindings.Add(new CommandBinding(ApplicationCommands.New,async(_,_)=>await AddTabAsync()));
  PreviewKeyDown+=(_,e)=>
  {
   if(Keyboard.Modifiers==(ModifierKeys.Control|ModifierKeys.Shift)&&e.Key==Key.N){_=AddTabAsync(null,true);e.Handled=true;}
   if(Keyboard.Modifiers==ModifierKeys.Control && e.Key==Key.L){Address.Focus();Address.SelectAll();e.Handled=true;}
   if(e.Key==Key.F1){ShowHelp();e.Handled=true;}
   if(e.Key==Key.Escape){Revoke();ClearPreview();SetStatus("Acción y vista previa canceladas.");}
  };
 }
 private async Task StartAsync(string? loadError)
 {
  try
  {
   if(settings.RestoreSession&&settings.SessionUrls.Count>0)
   {foreach(var url in settings.SessionUrls.ToArray()){if(closing)return;await AddTabAsync(url);}}
   else await AddTabAsync();
   if(loadError!=null)SetStatus(loadError);
  }
  catch(Exception e) when(IsEngineError(e)) {RuntimeError();}
 }
 private async Task<CoreWebView2Environment> EnsureEnvironmentAsync()
 {
  lifetime.Check();
  if(environment!=null)return environment;
  var folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Optimus","private-pilot","WebView2");
  environmentCreation??=CoreWebView2Environment.CreateAsync(null,folder,new CoreWebView2EnvironmentOptions {AreBrowserExtensionsEnabled=false,AllowSingleSignOnUsingOSPrimaryAccount=false});
  var created=await environmentCreation.WaitAsync(lifetime.Token);
  lifetime.Check();
  environment=created;
  environment.NewBrowserVersionAvailable+=(_,_)=>SetStatus("Hay una actualización del motor. Cierra y vuelve a abrir Optimus para adoptarla. Activa Restaurar direcciones si quieres conservar las pestañas.");
  return created;
 }
 private bool Owns(BrowserTab tab)=>!tab.IsDisposed&&Tabs.Items.Contains(tab.Item);
 private void CheckOwned(BrowserTab tab)
 {lifetime.Check();if(closing||!Owns(tab))throw new OperationCanceledException("La pestaña ya no pertenece a esta ventana.");}
 private async Task RunTabOperationAsync(Func<Task> operation)
 {
  if(closing)return;
  if(profileGate.IsBlocked){SetStatus("El perfil está bloqueado. Cierra Optimus y vuelve a abrirlo antes de navegar.");return;}
  try
  {
   await tabOperations.RunAsync(async()=>
   {lifetime.Check();if(profileGate.IsBlocked)return;await operation();},lifetime.Token);
  }
  catch(OperationCanceledException){ /* Closing cancels stale work; no disposed continuation resumes. */ }
  catch(Exception e) when(IsEngineError(e)){if(!closing)RuntimeError();}
 }
 private Task AddTabAsync(string? url=null,bool isPrivate=false)=>RunTabOperationAsync(()=>CreateTabAsync(url,isPrivate));
 private async Task<BrowserTab?> CreateTabAsync(string? url=null,bool isPrivate=false,bool cleanupOwner=false)
 {
  lifetime.Check();if(closing||(clearingData&&!cleanupOwner)||profileGate.IsBlocked)return null;
  if(url!=null&&Uri.TryCreate(url,UriKind.Absolute,out var target))
  {var decision=privacy.Evaluate(target,isPrivate);if(decision==PrivacyAction.Block){SetStatus("Destino bloqueado por una regla local.");return null;}isPrivate=decision==PrivacyAction.Private;}
  var creationPolicy=policyGeneration;
  var tab=new BrowserTab(t=>_=RecoverAsync(t),isPrivate,()=>privacy,()=>policyGeneration,()=>settings.Bookmarks,isPrivate?privateSession.Name:"Default",t=>Owns(t)&&Active==t&&!closing&&!clearingData&&!profileGate.IsBlocked,lifetime.Token,token=>searchHost.ConnectAsync(settings.SearxEndpoint,token));
  tab.Changed+=TabChanged;tab.Invalidated+=t=>{if(Active==t){Revoke();ClearPreview();ClearPendingPrivate();ClearHelpContent();}};tab.Notice+=SetStatus;tab.SafetyFailed+=_=>BlockAllTabsForRestart();
  tab.OpenRequested+=(t,address)=>{if(Active==t)NavigateKnownGet(t,address);};
  tab.PrivateOpeningOffered+=(t,address,lease)=>{if(Owns(t)&&Active==t&&t.IsCurrent(lease)){pendingPrivate=(t,address,lease);OpenPendingPrivate.ToolTip=address;OpenPendingPrivate.Visibility=Visibility.Visible;SetStatus("Destino protegido cancelado. Abrir destino en privado inicia una navegación nueva GET; no repite el formulario o redirección.");}};
  Tabs.Items.Add(tab.Item);Tabs.SelectedItem=tab.Item;
  try
  {
   var env=await EnsureEnvironmentAsync();CheckOwned(tab);
   await tab.InitializeAsync(env,permissions,downloads,()=>Owns(tab)&&Active==tab&&!closing&&!clearingData&&!profileGate.IsBlocked,lifetime.Token);CheckOwned(tab);
   var core=tab.Core??throw new InvalidOperationException("La pestaña no terminó de inicializarse.");
   var profileKey=isPrivate?privateSession.Name:"normal";
   if(!historyClearedProfiles.Contains(profileKey))
   {
    await core.Profile.ClearBrowsingDataAsync(CoreWebView2BrowsingDataKinds.BrowsingHistory).WaitAsync(lifetime.Token);CheckOwned(tab);
    historyClearedProfiles.Add(profileKey);
   }
   tab.NavigationReady=!cleanupOwner&&creationPolicy==policyGeneration;tab.View.ZoomFactor=settings.TextScale;
   if(url!=null&&!cleanupOwner&&creationPolicy==policyGeneration)tab.Navigate(url);TabChanged(tab);return tab;
  }
  catch(OperationCanceledException)
  {if(Tabs.Items.Contains(tab.Item))Tabs.Items.Remove(tab.Item);tab.Dispose();throw;}
  catch(Exception e) when(IsEngineError(e)){tab.RetireController();if(environmentCreation?.IsFaulted==true||environmentCreation?.IsCanceled==true)environmentCreation=null;if(!closing)SetStatus("No se pudo verificar el perfil y su barrera de privacidad. Esta pestaña no navegará. Recupera la pestaña o reinicia Optimus y revisa los requisitos de WebView2.");return null;}
 }
 private static bool IsEngineError(Exception e)=>e is WebView2RuntimeNotFoundException or COMException or InvalidOperationException or IOException or UnauthorizedAccessException or ArgumentException or TimeoutException or NotSupportedException or NotImplementedException;
 private void RuntimeError()=>SetStatus("No se pudo iniciar WebView2. Revisa los requisitos en PILOTO.md y el espacio del perfil. Instala el runtime Evergreen desde Microsoft solo por decisión propia; después pulsa Nueva pestaña o reinicia Optimus. La guía local sigue disponible.");
 private Task RecoverAsync(BrowserTab tab)=>RunTabOperationAsync(async()=>
 {
  if(!Owns(tab))return;
  var url=tab.IsHome?null:tab.LastAddress;var isPrivate=tab.IsPrivate;
  if(isPrivate&&!Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag).Any(t=>t!=tab&&t.IsPrivate))privateSession.Retire();
  Tabs.Items.Remove(tab.Item);tab.Dispose();await CreateTabAsync(url,isPrivate);
 });
 private void TabChanged(BrowserTab tab)
 {
  if(Active!=tab)return;
  ModeLabel.Text=tab.IsPrivate?"Privado · no se restauran direcciones":"Normal";
  if(!Address.IsKeyboardFocusWithin)Address.Text=tab.IsHome?"":tab.CurrentUri?.AbsoluteUri??tab.LastAddress??"";
 }
 private void Tabs_Changed(object sender,SelectionChangedEventArgs e)
 {
  if(e.Source!=Tabs)return;
  foreach(var removed in e.RemovedItems.OfType<TabItem>())if(removed.Tag is BrowserTab previous)previous.CancelSearch();
  Revoke();ClearPreview();ClearPendingPrivate();ClearHelpContent();if(Active!=null) {Address.Text=Active.IsHome?"":Active.CurrentUri?.AbsoluteUri??Active.LastAddress??"";TabChanged(Active);}
 }
 private void Go()
 {
  if(closing||clearingData||profileGate.IsBlocked){SetStatus("El perfil está ocupado o requiere reiniciar antes de buscar o navegar.");return;}
  var input=Address.Text;
  var result=NavigationPolicy.Resolve(input,settings.SearchProvider==SearchProvider.Optimus?SearchProvider.DuckDuckGo:settings.SearchProvider);
  if(settings.SearchProvider==SearchProvider.Optimus&&result.IsSearch)
  {if(input.Trim().Length>500){SetStatus("La consulta admite hasta 500 caracteres.");return;}if(Active is {} searchTab)_=searchTab.SearchAsync(input.Trim(),OptimusSearchScope.Web);return;}
  if(!result.Allowed){SetStatus(result.Error!);return;}
  if(Active==null){_=AddTabAsync(result.Uri!.AbsoluteUri);return;}
  NavigateKnownGet(Active,result.Uri!.AbsoluteUri);if(Active.IsFullyInitialized)Active.View.Focus();
 }
 private void NavigateKnownGet(BrowserTab tab,string address)
 {
  if(closing||clearingData||profileGate.IsBlocked||!Owns(tab))return;
  var resolved=NavigationPolicy.Resolve(address,SearchProvider.DuckDuckGo);if(!resolved.Allowed||resolved.IsSearch){SetStatus("Dirección HTTP o HTTPS no válida.");return;}
  var decision=privacy.DecideNavigation(resolved.Uri!,tab.IsPrivate,true);
  if(decision==NavigationDisposition.Block){SetStatus("Destino bloqueado por una regla local.");return;}
  if(decision==NavigationDisposition.OpenPrivate)
  {
   var lease=tab.Capture();_=RunTabOperationAsync(async()=>{if(!Owns(tab)||!tab.IsCurrent(lease)||Active!=tab)return;var current=privacy.Evaluate(resolved.Uri!);if(current==PrivacyAction.Block)return;await CreateTabAsync(resolved.Uri!.AbsoluteUri,true);});return;
  }
  tab.Navigate(resolved.Uri!.AbsoluteUri);
 }
 private void BlockAllTabsForRestart()
 {
  if(!profileGate.IsBlocked)_=profileGate.RunAsync(Task.FromException(new InvalidOperationException("La barrera de privacidad no está disponible.")),()=>{},TimeSpan.FromSeconds(1));
  permissions.Revoke();downloads.CancelAll();Revoke();ClearPreview();ClearPendingPrivate();
  foreach(var item in Tabs.Items.Cast<TabItem>()){var tab=(BrowserTab)item.Tag;tab.NavigationReady=false;tab.DisableSearch();try{tab.StopController();}catch(Exception ex) when(IsEngineError(ex)){}}
 }
 private void ClearPendingPrivate(){pendingPrivate=null;if(OpenPendingPrivate!=null){OpenPendingPrivate.Visibility=Visibility.Collapsed;OpenPendingPrivate.ToolTip=null;}}
 private void OpenPendingPrivate_Click(object sender,RoutedEventArgs e)
 {
  var pending=pendingPrivate;ClearPendingPrivate();if(pending is not {} p||!Owns(p.Tab)||Active!=p.Tab||!p.Tab.IsCurrent(p.Lease))return;
  NavigateKnownGet(p.Tab,p.Url);
 }
 private async void NewPrivate_Click(object sender,RoutedEventArgs e)=>await AddTabAsync(null,true);
 private async void CurrentPrivate_Click(object sender,RoutedEventArgs e)
 {var tab=Active;if(tab?.CurrentUri is not {} uri||tab.IsHome){SetStatus("Abre primero una página para iniciar una navegación nueva en privado.");return;}var lease=tab.Capture();await RunTabOperationAsync(async()=>{if(Owns(tab)&&Active==tab&&tab.IsCurrent(lease))await CreateTabAsync(uri.AbsoluteUri,true);});}
 private async void PrivacySettings_Click(object sender,RoutedEventArgs e)
 {
  if(closing||clearingData||profileGate.IsBlocked){SetStatus("El perfil está ocupado o requiere reiniciar Optimus.");return;}
  var dialog=new PrivacySettingsDialog(this,settings);if(dialog.ShowDialog()!=true||dialog.Rules==null)return;
  // Invalidate immediately, including creation already awaiting the engine in the serialized queue.
  policyGeneration++;privacy=new(dialog.Rules);clearingData=true;permissions.Revoke();downloads.CancelAll();Revoke();ClearPreview();ClearPendingPrivate();
  foreach(var tab in Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag)){tab.NavigationReady=false;tab.Invalidate();try{tab.StopController();}catch(Exception ex) when(IsEngineError(ex)){}}
  await RunTabOperationAsync(async()=>
  {
   var tabs=Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag).ToArray();
   try
   {
    await Task.WhenAll(tabs.Select(t=>t.QuiesceAsync())).WaitAsync(lifetime.Token);lifetime.Check();
    settings=settings with {PrivacyRules=dialog.Rules,SearxEndpoint=dialog.Endpoint};closedTabs.Clear();
    foreach(var tab in tabs){CheckOwned(tab);tab.PolicyChanged();tab.NavigationReady=tab.IsFullyInitialized;}
    if(SaveSettings())SetStatus("Reglas actualizadas. Los documentos y búsquedas se cerraron. " + searchHost.ConfigureUpstream(settings.SearxEndpoint));
   }
   catch(Exception ex) when(IsEngineError(ex)){await profileGate.RunAsync(Task.FromException(ex),()=>{},TimeSpan.FromSeconds(1));foreach(var tab in tabs){if(Tabs.Items.Contains(tab.Item))Tabs.Items.Remove(tab.Item);tab.Dispose();}SetStatus("No se pudo detener todos los documentos. Se cerraron las pestañas; vuelve a abrir Optimus antes de continuar.");}
   finally{clearingData=false;}
  });
 }
 private void Go_Click(object sender,RoutedEventArgs e)=>Go();
 private void Address_KeyDown(object sender,KeyEventArgs e){if(e.Key==Key.Enter){Go();e.Handled=true;}}
 private void Back_Click(object sender,RoutedEventArgs e)=>EngineAction(()=>{if(Active?.Core?.CanGoBack==true)Active.Core.GoBack();else SetStatus("No hay una página anterior en esta pestaña.");});
 private void Forward_Click(object sender,RoutedEventArgs e)=>EngineAction(()=>{if(Active?.Core?.CanGoForward==true)Active.Core.GoForward();else SetStatus("No hay una página siguiente.");});
 private void Reload_Click(object sender,RoutedEventArgs e)=>EngineAction(()=>{if(Active?.Core!=null&&!Active.IsHome)Active.Core.Reload();else SetStatus("Abre una página o usa Nueva pestaña para reintentar el motor.");});
 private void Home_Click(object sender,RoutedEventArgs e)=>EngineAction(()=>Active?.GoHome());
 private async void NewTab_Click(object sender,RoutedEventArgs e)=>await AddTabAsync();
 private async void RecoverTab_Click(object sender,RoutedEventArgs e){if(closedTabs.TryPop(out var url))await AddTabAsync(url);else SetStatus("No hay pestañas cerradas en esta sesión.");}
 private async void CloseTab_Click(object sender,RoutedEventArgs e)
 {
  var tab=Active;if(tab==null)return;
  await RunTabOperationAsync(async()=>
  {
   if(!Owns(tab))return;
   if(!tab.IsPrivate&&!tab.IsSearch&&(tab.IsHome||tab.PersistableAddress!=null))closedTabs.Push(tab.IsHome?null:tab.PersistableAddress);
   var lastInMode=!Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag).Any(t=>t!=tab&&t.IsPrivate==tab.IsPrivate&&t.Core!=null);
   if(lastInMode&&tab.Core!=null)
   {
    permissions.Revoke();downloads.CancelAll();tab.Invalidate();
    var ok=await profileGate.RunAsync(ClearLastProfileAsync(tab),()=>{if(Owns(tab)&&!closing)tab.ApplySafetySettings();},TimeSpan.FromSeconds(15));
    if(!ok){BlockAllTabsForRestart();SetStatus("No se verificó el borrado al cerrar el último documento del perfil. Reinicia Optimus; no se reutilizará el perfil en esta sesión.");}
   }
   if(lastInMode&&tab.IsPrivate)privateSession.Retire();
   Tabs.Items.Remove(tab.Item);tab.Dispose();
   if(Tabs.Items.Count==0&&!profileGate.IsBlocked){await CreateTabAsync();lifetime.Check();}
   SaveSettings();
  });
 }
 private static async Task ClearLastProfileAsync(BrowserTab tab)
 {
  await tab.QuiesceAsync();
  var profile=tab.Core?.Profile??throw new InvalidOperationException("No hay control vivo para borrar el perfil.");
  await profile.ClearBrowsingDataAsync(tab.IsPrivate?CoreWebView2BrowsingDataKinds.AllProfile:CoreWebView2BrowsingDataKinds.BrowsingHistory);
 }
 private static async Task ClearLiveProfileAsync(BrowserTab tab,CoreWebView2BrowsingDataKinds kinds)
 {var profile=tab.Core?.Profile??throw new InvalidOperationException("No hay control vivo para borrar el perfil.");await profile.ClearBrowsingDataAsync(kinds);}
 private void Help_Click(object sender,RoutedEventArgs e)=>ShowHelp();
 private void ShowHelp(){HelpColumn.Width=new GridLength(Math.Min(480,Math.Max(240,ActualWidth*0.36)));HelpPanel.Visibility=Visibility.Visible;Question.Focus();}
 private void HideHelp_Click(object sender,RoutedEventArgs e){Revoke();ClearPreview();HelpColumn.Width=new GridLength(0);HelpPanel.Visibility=Visibility.Collapsed;Address.Focus();}
 private void Ask_Click(object sender,RoutedEventArgs e)
 {
  var context=Active?.Context??new BrowserContext(Guid.Empty,0,"inicio");
  var reply=help.Ask(Question.Text,context);GuideAnswer.Text=reply.Text;
  ProposalText.Text=help.Pending is {} p?$"Acción: {Describe(p.Action)}\nPestaña actual · caduca en 60 segundos.":"No hay una acción pendiente.";ConfirmProposal.IsEnabled=help.Pending!=null;
 }
 private static string Describe(AssistantAction action)=>action.Kind switch
 {ActionKind.OpenUrl=>"Abrir "+action.Value,ActionKind.BookmarkCurrent=>"Guardar esta página como marcador",ActionKind.SetTextScale=>"Cambiar tamaño y zoom a "+(double.Parse(action.Value!,CultureInfo.InvariantCulture)*100).ToString(CultureInfo.InvariantCulture)+" %",ActionKind.SetContrast=>"Contraste alto: "+(action.Value=="true"?"activado":"desactivado"),_=>"No permitida"};
 private void Confirm_Click(object sender,RoutedEventArgs e)
 {
  if(Active==null||!help.Confirm(Active.Context,out var action)) {Revoke();SetStatus("La propuesta caducó o cambió su contexto. Vuelve a pedirla.");return;}
  Revoke();
  EngineAction(()=>
  {
   switch(action!.Kind)
   {
    case ActionKind.OpenUrl:NavigateKnownGet(Active,action.Value!);break;
    case ActionKind.BookmarkCurrent:AddBookmark();break;
    case ActionKind.SetTextScale:settings=settings with {TextScale=double.Parse(action.Value!,CultureInfo.InvariantCulture)};ScaleChoice.SelectedIndex=ScaleIndex(settings.TextScale);ApplyAppearance();if(SaveSettings())SetStatus("Tamaño actualizado. Puedes revertirlo desde Tamaño de texto y zoom.");break;
    case ActionKind.SetContrast:settings=settings with {HighContrast=action.Value=="true"};ContrastChoice.IsChecked=settings.HighContrast;ApplyAppearance();if(SaveSettings())SetStatus("Contraste actualizado. Puedes revertirlo con Contraste alto.");break;
   }
  });
 }
 private void Cancel_Click(object sender,RoutedEventArgs e){Revoke();SetStatus("Propuesta cancelada.");}
 private void ClearHelpContent(){if(Question!=null)Question.Clear();if(GuideAnswer!=null)GuideAnswer.Clear();}
 private void Revoke(){help.Revoke();if(ConfirmProposal==null)return;ConfirmProposal.IsEnabled=false;ProposalText.Text="No hay una acción pendiente.";}
 private async void PreviewSelection_Click(object sender,RoutedEventArgs e)
 {
  var tab=Active;if(tab==null)return;var context=tab.Context;var generation=sharingGeneration;
  try
  {
   var result=await HelpController.ReadSelectionAsync(tab).WaitAsync(TimeSpan.FromSeconds(5));
   if(Active!=tab||tab.Context!=context||HelpPanel.Visibility!=Visibility.Visible||sharingGeneration!=generation){SetStatus("Cambió la pestaña o la ayuda. Vuelve a seleccionar el texto.");return;}
   if(result.Error!=null){SetStatus(result.Error);return;}
   Preview(result.Text??"",tab,context);
  }
  catch(Exception ex) when(IsEngineError(ex)||ex is System.Text.Json.JsonException or TimeoutException) {SetStatus("No se pudo leer la selección. Reintenta o pega un fragmento para revisarlo.");}
 }
 private void PreviewPaste_Click(object sender,RoutedEventArgs e)
 {
  if(Active==null||Active.CurrentUri==null||Active.IsHome){SetStatus("Abre la página de origen antes de revisar texto pegado.");return;}
  if(previewContext!=null && previewContext!=Active.Context){ClearPreview();SetStatus("La página cambió. Vuelve a pegar el fragmento.");return;}
  Preview(ShareText.Text,Active,Active.Context);
 }
 private void Preview(string text,BrowserTab tab,BrowserContext context)
 {
  if(tab.CurrentUri==null||tab.IsHome)return;var shared=SharedExcerpt.Create(text,tab.CurrentUri);
  if(shared.Error!=null){SetStatus(shared.Error);return;}
  ShareText.Text=shared.Text;previewContext=context;
  ShareAttribution.Text=$"Origen: {shared.Origin}\nDestinatario: ninguno. IA remota no conectada. Conexión privada pendiente de validar.\n{(shared.WasTruncated?"Se recortó el fragmento a un máximo de 8.000 caracteres. Revisa el texto exacto.":"Revisa el texto exacto; puedes editarlo.")}";
  SetStatus(shared.WasTruncated?"Fragmento recortado; revisa los primeros 8.000 caracteres. No se ha enviado.":"Vista previa preparada. No se ha enviado ningún texto.");
 }
 private void ShareText_Changed(object sender,TextChangedEventArgs e){sharingGeneration++;previewContext=null;if(ShareAttribution!=null)ShareAttribution.Text="Texto editado; usa Revisar texto pegado para comprobar el origen. Destinatario: ninguno; envío desactivado.";}
 private void CancelShare_Click(object sender,RoutedEventArgs e)=>ClearPreview();
 private void ClearPreview(){sharingGeneration++;previewContext=null;if(ShareText==null)return;ShareText.Clear();ShareAttribution.Text="Destinatario: ninguno; envío desactivado.";}
 private void AddBookmark()
 {
  if(Active?.CurrentUri==null||Active.IsHome){SetStatus("Abre primero una página HTTP o HTTPS para guardarla.");return;}
  var tab=Active;var context=tab.Context;
  if(tab.IsPrivate&&(MessageBox.Show(this,"Este marcador conservará la dirección privada en los ajustes normales de Optimus, incluso después de cerrar la pestaña. ¿Guardarlo?","Marcador desde Privado",MessageBoxButton.YesNo,MessageBoxImage.Question,MessageBoxResult.No)!=MessageBoxResult.Yes||Active!=tab||tab.Context!=context))return;
  var result=BookmarkPersistence.TryAdd(settings.Bookmarks,new(Active.Title,Active.CurrentUri.AbsoluteUri),SaveSettings);
  if(result==BookmarkSaveResult.Saved)SetStatus("Marcador guardado. Ábrelo desde Marcadores.");
  else if(result==BookmarkSaveResult.AlreadyExists)SetStatus("Esta página ya está en Marcadores.");
 }
 private void Bookmarks_Click(object sender,RoutedEventArgs e)=>NativeDialogs.ShowBookmarks(this,settings.Bookmarks,AddBookmark,url=>{if(Active is {} tab)NavigateKnownGet(tab,url);},()=>{SaveSettings();});
 private void Search_Changed(object sender,SelectionChangedEventArgs e){if(!ready)return;settings=settings with {SearchProvider=(SearchProvider)SearchChoice.SelectedValue};SaveSettings();}
 private void Scale_Changed(object sender,SelectionChangedEventArgs e){if(!ready)return;settings=settings with {TextScale=new[]{1d,1.25,1.5,2}[Math.Max(0,ScaleChoice.SelectedIndex)]};ApplyAppearance();SaveSettings();}
 private void Appearance_Click(object sender,RoutedEventArgs e){settings=settings with {HighContrast=ContrastChoice.IsChecked==true};ApplyAppearance();SaveSettings();}
 private static int ScaleIndex(double value)=>value>=2?3:value>=1.5?2:value>=1.25?1:0;
 private void ApplyAppearance()
 {
  FontSize=18*settings.TextScale;
  NativeDialogs.ApplyContrast(this,settings.HighContrast);
  foreach(TabItem item in Tabs.Items){if(item.Tag is BrowserTab {IsFullyInitialized:true} t)t.View.ZoomFactor=settings.TextScale;}
 }
 private void Restore_Click(object sender,RoutedEventArgs e)
 {
  settings=settings with {RestoreSession=RestoreChoice.IsChecked==true};if(!SaveSettings())return;
  SetStatus(settings.RestoreSession?"Restauración activada: se guardan localmente las direcciones abiertas. Desactívala para borrarlas de los ajustes.":"Restauración desactivada: las direcciones abiertas no se guardan en los ajustes.");
 }
 private bool SaveSettings()
 {
  settings=settings with {SessionUrls=settings.RestoreSession?Tabs.Items.Cast<TabItem>().Select(i=>i.Tag).OfType<BrowserTab>().Select(t=>t.PersistableAddress).Where(url=>url!=null).Cast<string>().Take(100).ToList():[]};
  var error=settingsStore.Save(settings);if(error!=null)SetStatus(error);return error==null;
 }
 private void Downloads_Click(object sender,RoutedEventArgs e)=>downloads.Show();
 private async void RevokePermissions_Click(object sender,RoutedEventArgs e)=>await RunTabOperationAsync(RevokePermissionsAsync);
 private async Task RevokePermissionsAsync()
 {
  if(MessageBox.Show(this,"Se cerrarán y volverán a abrir los documentos para detener los permisos concedidos. Puedes perder texto no guardado. Las cookies y los marcadores se conservan. ¿Continuar?","Revocar permisos",MessageBoxButton.YesNo,MessageBoxImage.Question,MessageBoxResult.No)!=MessageBoxResult.Yes)return;
  permissions.Revoke();downloads.CancelAll();Revoke();ClearPreview();
  var originals=Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag).Select(t=>(Tab:t,Url:t.IsHome?null:t.LastAddress,Private:t.IsPrivate)).ToArray();
  try{await Task.WhenAll(originals.Select(t=>t.Tab.QuiesceAsync())).WaitAsync(lifetime.Token);lifetime.Check();}
  catch(Exception ex) when(IsEngineError(ex)){BlockAllTabsForRestart();SetStatus("No se verificó la detención de los documentos. Reinicia Optimus antes de reutilizar el perfil.");return;}
  bool restored=true;foreach(var original in originals)
  {
   // A live controller retains each shared InPrivate profile until its replacement exists.
   await CreateTabAsync(original.Url,original.Private);lifetime.Check();
   if((Tabs.Items.Cast<TabItem>().LastOrDefault()?.Tag as BrowserTab)?.NavigationReady!=true)restored=false;
   Tabs.Items.Remove(original.Tab.Item);original.Tab.Dispose();
  }
  SetStatus(restored?"Se revocaron las decisiones de permiso de la sesión y se reabrieron los documentos. Cada solicitud volverá a revisarse.":"Se revocaron los permisos, pero no se pudieron reabrir todos los documentos. Revisa los requisitos y recupera las pestañas.");
 }
 private async void ClearData_Click(object sender,RoutedEventArgs e)=>await RunTabOperationAsync(ClearDataAsync);
 private async Task ClearDataAsync()
 {
  if(Active?.Core==null){SetStatus("Inicia el motor antes de borrar sus datos.");return;}
  if(MessageBox.Show(this,"Se borrarán TODOS los datos del perfil del motor: incluidos cookies, caché, almacenamiento, permisos, historial, registro de descargas y autocompletar. Se cancelarán descargas y se cerrarán las páginas. Los marcadores y ajustes de Optimus se conservan. Perderás sesiones abiertas y texto no guardado. ¿Borrar?","Borrar datos de todos los sitios",MessageBoxButton.YesNo,MessageBoxImage.Warning,MessageBoxResult.No)!=MessageBoxResult.Yes)return;
  permissions.Revoke();Revoke();ClearPreview();downloads.CancelAll();
  var tabs=Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag).ToArray();
  var expected=ProfileCleanupCoordinator.ExpectedProfiles(historyClearedProfiles.Contains("normal"),tabs.Select(t=>t.IsPrivate));
  clearingData=true;bool safeToResume=false;
  try
  {
   async Task<BrowserTab?> AcquireOwner(bool isPrivate)
   {
    var owner=Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag).FirstOrDefault(t=>t.IsPrivate==isPrivate&&t.IsFullyInitialized&&t.Core!=null);
    return owner??await CreateTabAsync(null,isPrivate,true);
   }
   async Task QuiesceAll()
   {
    tabs=Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag).ToArray();
    await Task.WhenAll(tabs.Select(t=>t.QuiesceAsync())).WaitAsync(lifetime.Token);lifetime.Check();foreach(var tab in tabs)CheckOwned(tab);
   }
   safeToResume=await ProfileCleanupCoordinator.ClearAsync(expected,AcquireOwner,(mode,owner)=>Owns(owner)&&owner.IsPrivate==mode&&owner.IsFullyInitialized&&owner.Core!=null,QuiesceAll,owner=>ClearLiveProfileAsync(owner,CoreWebView2BrowsingDataKinds.AllProfile),()=>
   {
    lifetime.Check();foreach(var tab in tabs){CheckOwned(tab);if(tab.IsFullyInitialized)tab.ApplySafetySettings();}
   },profileGate,TimeSpan.FromSeconds(15));
   lifetime.Check();
   if(!safeToResume){BlockAllTabsForRestart();SetStatus("No se verificó el borrado de todos los perfiles. No se confirma la eliminación; reinicia Optimus antes de continuar.");return;}
   closedTabs.Clear();settings=settings with {SessionUrls=[]};
   if(SaveSettings())SetStatus("Datos del perfil del motor borrados. Se conservaron marcadores y ajustes de Optimus.");
  }
  catch(Exception ex) when(IsEngineError(ex)){BlockAllTabsForRestart();SetStatus("No se completó la preparación del borrado. No se confirma la eliminación; reinicia Optimus antes de reutilizar el perfil.");}
  finally {clearingData=false;foreach(var tab in Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag))if(Owns(tab))tab.NavigationReady=tab.IsFullyInitialized&&safeToResume&&!profileGate.IsBlocked;}
 }

 private async void Window_Closing(object? sender,CancelEventArgs e)
 {
  if(closed)return;e.Cancel=true;if(closing)return;
  closing=true;searchHost.Dispose();if(searchHost.ShutdownError is {} shutdownError)MessageBox.Show(this,shutdownError,"Cierre de Optimus Search",MessageBoxButton.OK,MessageBoxImage.Warning);searchConnectionClient.Dispose();foreach(var item in Tabs.Items.Cast<TabItem>())if(item.Tag is BrowserTab tab)tab.DisableSearch();lifetime.Dispose();timer.Stop();permissions.Revoke();Revoke();ClearPreview();downloads.CancelAll();
  // Creation/destruction serialize, while cancellation prevents late creation from resuming.
  await tabOperations.RunAsync(async()=>
  {
   SaveSettings();
   var tabs=Tabs.Items.Cast<TabItem>().Select(i=>(BrowserTab)i.Tag).ToArray();
   try
   {
    foreach(var tab in tabs)tab.StopController();

    // Never start another operation on a profile whose clear is still pending/unknown.
    if(!profileGate.IsBlocked)await Task.WhenAll(tabs.Where(t=>t.Core!=null).GroupBy(t=>t.IsPrivate).Select(group=>ClearLiveProfileAsync(group.First(),group.Key?CoreWebView2BrowsingDataKinds.AllProfile:CoreWebView2BrowsingDataKinds.BrowsingHistory))).WaitAsync(TimeSpan.FromSeconds(10));
   }
   catch(Exception ex) when(IsEngineError(ex)){MessageBox.Show(this,"No se pudo borrar el historial del motor al cerrar. Se reintentará antes de navegar al abrir de nuevo Optimus.","Cierre de Optimus",MessageBoxButton.OK,MessageBoxImage.Warning);}
   finally{foreach(var tab in tabs)tab.Dispose();closed=true;Close();}
  });
 }

 private void EngineAction(Action action){if(closing||clearingData||profileGate.IsBlocked){SetStatus("El perfil está ocupado o requiere reiniciar Optimus antes de navegar.");return;}try{action();}catch(Exception e) when(IsEngineError(e)){SetStatus("El motor no pudo completar la acción. Reintenta o recupera la pestaña.");}}
 private void SetStatus(string text){if(!Dispatcher.CheckAccess()){Dispatcher.Invoke(()=>SetStatus(text));return;}Status.Text=text;}
}
