using System.Net;
using System.Text.Json;
namespace Optimus.Core;
public sealed class SettingsStore(string path,string? legacyPath=null)
{
 private static readonly JsonSerializerOptions JsonOptions=new() {WriteIndented=true};
 public SettingsResult Load()=>Read().Result;
 private (SettingsResult Result,bool CanSave) Read()
 {
  var source=File.Exists(path)?path:legacyPath;
  if(source==null||!File.Exists(source))return (new(new()),true);
  try
  {
   var settings=JsonSerializer.Deserialize<BrowserSettings>(File.ReadAllText(source)) ?? throw new JsonException();
   var disabledEndpoint=IsOversizedLegacyEndpoint(settings.SearxEndpoint);
   if(disabledEndpoint)settings=settings with {SearxEndpoint=null};
   Validate(settings);
   var notice=disabledEndpoint?"El servidor Web guardado se desactivó porque supera el límite de longitud. Se conservaron los demás ajustes y el archivo original. Revisa el servidor Web antes de buscar.":null;
   return (new(Sanitize(settings),notice),true);
  }
  catch(Exception e) when(e is IOException or UnauthorizedAccessException or JsonException or ArgumentException)
  {return (new(new(),"No se pudieron leer los ajustes. El archivo original se conserva. Haz una copia o renómbralo para recuperar los valores iniciales."),false);}
 }
 public string? Save(BrowserSettings settings)
 {
  if(!Read().CanSave) return "No se guardaron los ajustes para conservar el archivo dañado. Haz una copia o renómbralo y reintenta.";
  string? temporary=null;
  try
  {
   Validate(settings);Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
   temporary=path+"."+Guid.NewGuid().ToString("N")+".tmp";
   using(var stream=new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.None))
   {JsonSerializer.Serialize(stream,Sanitize(settings),JsonOptions);stream.Flush(true);}
   File.Move(temporary,path,true);return null;
  }
  catch(Exception e) when(e is IOException or UnauthorizedAccessException or ArgumentException)
  {return "No se pudieron guardar los ajustes. Revisa el espacio y los permisos del perfil y reintenta.";}
  finally {if(temporary!=null && File.Exists(temporary)) {try{File.Delete(temporary);}catch(Exception e) when(e is IOException or UnauthorizedAccessException){ /* Original remains untouched; temporary can be removed manually. */ }}}
 }
 private static BrowserSettings Sanitize(BrowserSettings s)
 {var policy=new PrivacyPolicy(s.PrivacyRules);return s with {SessionUrls=s.RestoreSession?s.SessionUrls.Where(url=>policy.CanPersist(url)).ToList():[]};}
 private static bool IsOversizedLegacyEndpoint(string? endpoint)
 {
  // Load-only migration: match current endpoint policy except its two length
  // bounds, then disable the endpoint. Save and network validation stay strict.
  if(string.IsNullOrWhiteSpace(endpoint)||endpoint.Any(char.IsControl)||endpoint.Contains('\\')
   ||!Uri.TryCreate(endpoint,UriKind.Absolute,out var uri)||uri.Host.Length==0||uri.UserInfo.Length!=0
   ||uri.Query.Length!=0||uri.Fragment.Length!=0)return false;
  return (endpoint.Length>2048||uri.AbsoluteUri.Length>2048)
   &&(uri.Scheme==Uri.UriSchemeHttps||uri.Scheme==Uri.UriSchemeHttp&&(uri.Host.Equals("localhost",StringComparison.OrdinalIgnoreCase)
    ||IPAddress.TryParse(uri.Host.Trim('[',']'),out var ip)&&IPAddress.IsLoopback(ip)));
 }
 private static void Validate(BrowserSettings s)
 {
  if(!Enum.IsDefined(s.Theme)||!Enum.IsDefined(s.SearchProvider)||!double.IsFinite(s.TextScale)||s.TextScale<1||s.TextScale>2||s.Bookmarks==null||s.SessionUrls==null || s.Bookmarks.Count>5000||s.SessionUrls.Count>100) throw new ArgumentException("Ajustes inválidos");
  if(s.PrivacyRules==null)throw new ArgumentException("Reglas inválidas");
  PrivacyPolicy.ValidateRules(s.PrivacyRules);
  if(s.SearxEndpoint!=null&&!OptimusSearchService.IsValidEndpoint(s.SearxEndpoint))throw new ArgumentException("Endpoint de búsqueda no válido.");
  foreach(var b in s.Bookmarks) if(b==null||b.Title==null || b.Url==null || !Uri.TryCreate(b.Url,UriKind.Absolute,out var u)||!NavigationPolicy.IsAllowed(u)) throw new ArgumentException("Marcador inválido");
  foreach(var url in s.SessionUrls) if(!Uri.TryCreate(url,UriKind.Absolute,out var u)||!NavigationPolicy.IsAllowed(u)) throw new ArgumentException("Sesión inválida");
 }
}
