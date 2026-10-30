using System.Windows;
using System.Windows.Controls;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;
using Optimus.Core;
namespace Optimus.App;
/// <summary>One isolated document epoch. Pages receive no native object or message channel.</summary>
internal sealed class BrowserTab : IDisposable
{
 public Guid Id {get;}=Guid.NewGuid();
 public long Epoch {get;private set;}
 public bool IsPrivate {get;}
 public bool IsSearch {get;private set;}
 private readonly Func<PrivacyPolicy> policy;
 private readonly Func<long> policyGeneration;
 private readonly string profileName;
 private readonly NavigationEpoch navigationEpoch=new();
 private readonly ControllerReadiness readiness=new();
 private readonly ControllerOwnership controllerOwnership;
 public bool IsFullyInitialized=>readiness.IsInitialized;
 private readonly OptimusSearchView search;
 public NavigationLease Capture()=>navigationEpoch.Capture(policyGeneration());
 public bool IsCurrent(NavigationLease lease)=>navigationEpoch.IsCurrent(lease,policyGeneration());
 public WebView2 View {get;}=new();
 public Grid Host {get;}=new();
 public TabItem Item {get;}
 public CoreWebView2? Core=>readiness.IsInitialized?CleanupCore:null;
 private CoreWebView2? CleanupCore=>disposed||!controllerOwnership.HasController?null:View.CoreWebView2;
 public void StopController()=>CleanupCore?.Stop();
 public Uri? CurrentUri
 {
  get
  {
   try{return !IsHome&&!IsSearch&&Uri.TryCreate(Core?.Source,UriKind.Absolute,out var uri)&&NavigationPolicy.IsAllowed(uri)&&policy().Evaluate(uri,IsPrivate)!=PrivacyAction.Block&&(IsPrivate||policy().Evaluate(uri)!=PrivacyAction.Private)?uri:null;}
   catch(Exception e) when(e is InvalidOperationException or System.Runtime.InteropServices.COMException){return null;}
  }
 }
 public BrowserContext Context=>new(Id,Epoch,CurrentUri?.GetLeftPart(UriPartial.Authority)??"inicio");
 public bool IsHome {get;private set;}=true;
 public bool NavigationReady {get=>readiness.CanNavigate;set=>readiness.RequestResume(value);}
 public string Title=>IsSearch?"Optimus Search":IsHome?"Inicio":Core?.DocumentTitle??"Página";
 private NavigationSnapshot addressSnapshot=new();
 public string? LastAddress=>IsSearch?null:addressSnapshot.LastAddress is {} address&&Uri.TryCreate(address,UriKind.Absolute,out var u)&&policy().Evaluate(u,IsPrivate)!=PrivacyAction.Block&&(IsPrivate||policy().Evaluate(u)!=PrivacyAction.Private)?address:null;
 public string? PersistableAddress=>!IsHome&&policy().CanPersist(LastAddress,IsPrivate,IsSearch)?LastAddress:null;
 public event Action<BrowserTab>? Changed;
 public event Action<BrowserTab>? Invalidated;
 public event Action<string>? Notice;
 public event Action<BrowserTab>? SafetyFailed;
 public event Action<BrowserTab,string>? OpenRequested;
 public event Action<BrowserTab,string,NavigationLease>? PrivateOpeningOffered;
 private readonly StackPanel home=new() {Margin=new Thickness(30)};
 private readonly StackPanel failure=new() {Margin=new Thickness(30),Visibility=Visibility.Collapsed};
 private bool disposed,internalBlank;
 private readonly OperationLifetime lifetime=new();
 public bool IsDisposed=>lifetime.IsDisposed;
 public BrowserTab(Action<BrowserTab> recover,bool isPrivate,Func<PrivacyPolicy> policy,Func<long> policyGeneration,Func<IReadOnlyList<Bookmark>> bookmarks,string profileName,Func<BrowserTab,bool> searchEligible,CancellationToken hostLifetime,Func<CancellationToken,Task<SearchHostConnection>> connectSearch)
 {
  controllerOwnership=new ControllerOwnership(()=>View.Dispose());
  this.profileName=profileName;IsPrivate=isPrivate;this.policy=policy;this.policyGeneration=policyGeneration;
  search=new OptimusSearchView(url=>OpenRequested?.Invoke(this,url),()=>IsPrivate?Array.Empty<Bookmark>():bookmarks(),()=>!IsDisposed&&searchEligible(this),hostLifetime,connectSearch) {Visibility=Visibility.Collapsed};
  Item=new TabItem {Header=ModeTitle("Inicio"),Content=Host,Tag=this};Host.Children.Add(View);Host.Children.Add(home);Host.Children.Add(failure);Host.Children.Add(search);
  home.Children.Add(new System.Windows.Controls.Image {Source=(System.Windows.Media.ImageSource)Application.Current.FindResource("OptimusLogo"),Height=72,HorizontalAlignment=HorizontalAlignment.Left,Margin=new Thickness(0,0,0,16)});
  home.Children.Add(new TextBlock {Text="Bienvenido a Optimus",FontSize=30,TextWrapping=TextWrapping.Wrap});
  home.Children.Add(new TextBlock {Text="Escribe una dirección o una búsqueda arriba. La ayuda local funciona sin cuenta. Optimus Search permite elegir Web, Índice Optimus o Wikipedia; la Web requiere el servidor del operador.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,14,0,14)});
  var openSearch=new Button {Content="Abrir Optimus Search",MinHeight=44,HorizontalAlignment=HorizontalAlignment.Left};openSearch.Click+=(_,_)=>ShowSearch();home.Children.Add(openSearch);
  home.Children.Add(new TextBlock {Text="Enlaces de inicio · candidatos sin atribución oficial",FontWeight=FontWeights.Bold,TextWrapping=TextWrapping.Wrap});
  foreach(var (label,url) in new[]{("Portal de administración · administracion.gob.es","https://administracion.gob.es/")})
  {var b=new Button {Content=label,HorizontalAlignment=HorizontalAlignment.Left};b.Click+=(_,_)=>OpenRequested?.Invoke(this,url);home.Children.Add(b);}
  home.Children.Add(new TextBlock {Text=(IsPrivate?"Privado: no se guardan direcciones en la sesión. No ofrece anonimato; marcadores y descargas explícitos pueden conservarse. ":"Normal: cookies y datos de sitios pueden persistir. ")+" Optimus no guarda un historial general; la restauración de direcciones requiere activar la opción. La comprobación de reputación se solicita al motor; Windows puede modificar su funcionamiento.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,20,0,0)});
  failure.Children.Add(new TextBlock {Text="El motor de esta pestaña se detuvo. Recuperarla vuelve a abrir la última dirección; el texto no guardado puede perderse.",TextWrapping=TextWrapping.Wrap});
  var retry=new Button {Content="Recuperar esta pestaña"};retry.Click+=(_,_)=>recover(this);failure.Children.Add(retry);
  View.Visibility=Visibility.Hidden;
 }
 public async Task InitializeAsync(CoreWebView2Environment environment,PermissionController permissions,DownloadController downloads,Func<bool> active,CancellationToken cancellationToken)
 {
  try{await readiness.InitializeAsync(()=>InitializeControllerAsync(environment,permissions,downloads,active,cancellationToken));}
  catch{RetireController();throw;}
 }
 public void RetireController()
 {
  readiness.Fail();NavigationReady=false;Invalidate();View.Visibility=Visibility.Hidden;home.Visibility=Visibility.Collapsed;failure.Visibility=Visibility.Visible;
  try{DisposeController();}catch(Exception e) when(e is InvalidOperationException or System.Runtime.InteropServices.COMException){SafetyFailed?.Invoke(this);Notice?.Invoke("No se verificó el cierre del controlador. Reinicia Optimus antes de continuar.");}
 }

 private void RequestControllerRetirement()
 {
  readiness.Fail();NavigationReady=false;Invalidate();View.Visibility=Visibility.Hidden;home.Visibility=Visibility.Collapsed;failure.Visibility=Visibility.Visible;
  // ProcessFailed also covers frame-only failure/unresponsive pages: retire the actual controller after callback return.
  controllerOwnership.RequestRetirement(action=>View.Dispatcher.BeginInvoke(action),_=>{SafetyFailed?.Invoke(this);Notice?.Invoke("No se verificó el cierre del controlador. Reinicia Optimus antes de continuar.");});
 }

 private async Task InitializeControllerAsync(CoreWebView2Environment environment,PermissionController permissions,DownloadController downloads,Func<bool> active,CancellationToken cancellationToken)
 {
  lifetime.Check();cancellationToken.ThrowIfCancellationRequested();
  var controllerOptions=environment.CreateCoreWebView2ControllerOptions();
  controllerOptions.ProfileName=profileName;controllerOptions.IsInPrivateModeEnabled=IsPrivate;
  await View.EnsureCoreWebView2Async(environment,controllerOptions).WaitAsync(cancellationToken);
  controllerOwnership.Attach();
  lifetime.Check();cancellationToken.ThrowIfCancellationRequested();
  var core=View.CoreWebView2??throw new InvalidOperationException("La pestaña no terminó de inicializarse.");
  if(core.Profile.IsInPrivateModeEnabled!=IsPrivate)throw new InvalidOperationException("El motor no confirmó el modo de privacidad solicitado. No se navegará.");
  _=new PrivacyBarrier(environment,core,policy,IsPrivate,()=>{RequestControllerRetirement();SafetyFailed?.Invoke(this);try{core.Stop();}catch(Exception e) when(e is InvalidOperationException or System.Runtime.InteropServices.COMException){}Notice?.Invoke("La barrera no pudo verificar una solicitud. Esta pestaña se detuvo; cierra Optimus y vuelve a abrirlo.");});
  ApplySafetySettings(core);
  core.NavigationStarting+=(_,e)=>
  {
   if(internalBlank && e.Uri=="about:blank") {internalBlank=false;return;}
   internalBlank=false;Invalidate();
   if(!NavigationReady) {e.Cancel=true;Notice?.Invoke("Espera a que termine la preparación del perfil o recupera la pestaña.");return;}
   var n=NavigationPolicy.Resolve(e.Uri,SearchProvider.DuckDuckGo);
   if(!n.Allowed||n.IsSearch) {e.Cancel=true;Notice?.Invoke(n.Error??"No se abrió este destino. Usa una dirección HTTP o HTTPS.");return;}
   var decision=policy().DecideNavigation(n.Uri!,IsPrivate,false);
   if(decision is NavigationDisposition.Block or NavigationDisposition.OfferPrivate)
   {e.Cancel=true;if(decision==NavigationDisposition.OfferPrivate)OfferPrivate(n.Uri!.AbsoluteUri);else Notice?.Invoke("Destino bloqueado por una regla local.");return;}
   addressSnapshot.TryRefresh(()=>n.Uri!.AbsoluteUri);ShowPage();Changed?.Invoke(this);
  };
  core.SourceChanged+=(_,_)=> {if(IsHome)return;if(CurrentUri!=null)addressSnapshot.TryRefresh(()=>core.Source);Invalidate();Changed?.Invoke(this);};
  core.HistoryChanged+=(_,_)=>Changed?.Invoke(this);
  core.DocumentTitleChanged+=(_,_)=> {Item.Header=ModeTitle(Title);Changed?.Invoke(this);};
  core.NavigationCompleted+=(_,e)=> {if(e.IsSuccess&&!IsHome&&CurrentUri!=null)Notice?.Invoke(new OfficialSiteRegistry([]).Describe(CurrentUri,DateOnly.FromDateTime(DateTime.UtcNow))+". Comprueba la dirección antes de actuar.");if(!e.IsSuccess && e.WebErrorStatus!=CoreWebView2WebErrorStatus.OperationCanceled) Notice?.Invoke("No se cargó la página ("+e.WebErrorStatus+"). Puedes recargar, volver o abrir Inicio.");Changed?.Invoke(this);};
  core.ServerCertificateErrorDetected+=(_,e)=> {e.Action=CoreWebView2ServerCertificateErrorAction.Cancel;Notice?.Invoke("El certificado del sitio no es válido. La conexión se ha bloqueado. Comprueba la dirección o vuelve atrás.");};
  core.NewWindowRequested+=(_,e)=>
  {e.Handled=true;var n=NavigationPolicy.Resolve(e.Uri,SearchProvider.DuckDuckGo);if(e.IsUserInitiated&&active()&&n.Allowed&&!n.IsSearch&&policy().Evaluate(n.Uri!,IsPrivate)==PrivacyAction.Private&&!IsPrivate)OfferPrivate(n.Uri!.AbsoluteUri);else Notice?.Invoke("Ventana emergente bloqueada. Su método no se repite; abre la dirección manualmente con Optimus.");};
  core.LaunchingExternalUriScheme+=(_,e)=> {e.Cancel=true;Notice?.Invoke("Este piloto no abre aplicaciones externas. Continúa con una dirección HTTP o HTTPS.");};
  core.PermissionRequested+=(_,e)=>permissions.Request(this,e,active);
  core.ScreenCaptureStarting+=(_,e)=>{e.Cancel=true;e.Handled=true;Notice?.Invoke("La captura de pantalla no está disponible en este piloto.");};
  core.DownloadStarting+=(_,e)=>downloads.Request(this,e,active);
  core.ProcessFailed+=(_,_)=> {RequestControllerRetirement();Notice?.Invoke("El motor se detuvo. Usa Recuperar esta pestaña.");};
 }
 public void ApplySafetySettings()
 {
  lifetime.Check();
  var core=Core??throw new InvalidOperationException("El motor no está preparado.");
  ApplySafetySettings(core);
 }
 private static void ApplySafetySettings(CoreWebView2 core)
 {
  var settings=core.Settings;
  settings.AreHostObjectsAllowed=false;settings.IsWebMessageEnabled=false;
  settings.IsPasswordAutosaveEnabled=false;settings.IsGeneralAutofillEnabled=false;
  core.Profile.IsPasswordAutosaveEnabled=false;core.Profile.IsGeneralAutofillEnabled=false;
  settings.IsReputationCheckingRequired=true;settings.AreDevToolsEnabled=false;
 }
 private void OfferPrivate(string address)
 {
  var lease=Capture();View.Dispatcher.BeginInvoke(new Action(()=>{if(IsCurrent(lease)&&!IsDisposed)PrivateOpeningOffered?.Invoke(this,address,lease);}));
  Notice?.Invoke("Navegación protegida cancelada. El método es desconocido; usa Abrir destino en privado para iniciar una navegación nueva.");
 }
 public void Navigate(string url)
 {
  if(Core==null || !NavigationReady) {Notice?.Invoke("La pestaña aún no está preparada. Espera o recupera la pestaña.");return;}
  var n=NavigationPolicy.Resolve(url,SearchProvider.DuckDuckGo);
  if(!n.Allowed||n.IsSearch) {Notice?.Invoke(n.Error??"Dirección no válida.");return;}
  var decision=policy().Evaluate(n.Uri!,IsPrivate);
  if(decision==PrivacyAction.Block||(!IsPrivate&&decision==PrivacyAction.Private)){Notice?.Invoke("Usa los controles de Optimus para elegir el perfil antes de abrir este destino.");return;}
  Invalidate();
  try {Core.Navigate(n.Uri!.AbsoluteUri);} catch(Exception e) when(e is InvalidOperationException or ArgumentException or System.Runtime.InteropServices.COMException) {Notice?.Invoke("El motor no pudo abrir la dirección. Recupera la pestaña.");}
 }
 public void GoHome()
 {
  Invalidate();IsSearch=false;search.Visibility=Visibility.Collapsed;IsHome=true;Item.Header=ModeTitle("Inicio");home.Visibility=Visibility.Visible;View.Visibility=Visibility.Hidden;failure.Visibility=Visibility.Collapsed;
  if(Core!=null) {Core.Stop();internalBlank=true;Core.Navigate("about:blank");}
  Changed?.Invoke(this);
 }
 public async Task QuiesceAsync()
 {
  NavigationReady=false;Invalidate();
  await controllerOwnership.QuiesceAsync(QuiesceLiveControllerAsync);
  if(!controllerOwnership.HasController)GoHome();
 }
 private async Task QuiesceLiveControllerAsync()
 {
  var core=CleanupCore??throw new InvalidOperationException("No hay controlador vivo para detener el documento.");core.Stop();
  if(core.Source=="about:blank"&&IsHome){GoHome();return;}
  var completion=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
  void Completed(object? sender,CoreWebView2NavigationCompletedEventArgs e)
  {if(e.IsSuccess&&core.Source=="about:blank")completion.TrySetResult();}
  core.NavigationCompleted+=Completed;
  try {GoHome();await completion.Task.WaitAsync(TimeSpan.FromSeconds(5));}
  finally {core.NavigationCompleted-=Completed;}
 }
 public void ShowSearch()
 {
  if(!search.CanSubmit)return;
  GoHome();IsSearch=true;home.Visibility=Visibility.Collapsed;search.Visibility=Visibility.Visible;Item.Header=ModeTitle("Optimus Search");Changed?.Invoke(this);search.FocusQuery();
 }
 public async Task SearchAsync(string query,OptimusSearchScope scope=OptimusSearchScope.Web)
 {
  if(!search.CanSubmit)return;
  ShowSearch();await search.SearchAsync(query,scope,lifetime.Token);
 }
 public void CancelSearch()=>Invalidate();
 public void DisableSearch(){search.Disable();Invalidate();}
 public void PolicyChanged(){Invalidate();addressSnapshot=new();GoHome();}
 private string ModeTitle(string title)=>(IsPrivate?"Privado · ":"Normal · ")+ShortTitle(title);
 private void ShowPage() {IsSearch=false;search.Visibility=Visibility.Collapsed;IsHome=false;home.Visibility=Visibility.Collapsed;failure.Visibility=Visibility.Collapsed;View.Visibility=Visibility.Visible;}
 public void Invalidate() {Epoch++;navigationEpoch.Invalidate();search.Cancel();Invalidated?.Invoke(this);}
 private static string ShortTitle(string text)=>text.Length>24?text[..24]+"…":text;
 private void DisposeController()=>controllerOwnership.Retire();
 public void Dispose() {if(disposed)return;readiness.Dispose();lifetime.Dispose();navigationEpoch.Dispose();NavigationReady=false;Invalidate();search.Dispose();disposed=true;DisposeController();}
}
