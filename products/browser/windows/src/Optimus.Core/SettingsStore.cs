using System.Text.Json;
namespace Optimus.Core;
public sealed class SettingsStore(string path,string? legacyPath=null)
{
 private static readonly JsonSerializerOptions JsonOptions=new() {WriteIndented=true};
 public SettingsResult Load()
 {
  var source=File.Exists(path)?path:legacyPath;
  if(source==null||!File.Exists(source))return new(new());
  try
  {
   var settings=JsonSerializer.Deserialize<BrowserSettings>(File.ReadAllText(source)) ?? throw new JsonException();
   Validate(settings);
   return new(Sanitize(settings));
  }
  catch(Exception e) when(e is IOException or UnauthorizedAccessException or JsonException or ArgumentException)
  {return new(new(),"No se pudieron leer los ajustes. El archivo original se conserva. Haz una copia o renómbralo para recuperar los valores iniciales.");}
 }
 public string? Save(BrowserSettings settings)
 {
  if(Load().Error!=null) return "No se guardaron los ajustes para conservar el archivo dañado. Haz una copia o renómbralo y reintenta.";
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
 private static void Validate(BrowserSettings s)
 {
  if(!Enum.IsDefined(s.SearchProvider)||!double.IsFinite(s.TextScale)||s.TextScale<1||s.TextScale>2||s.Bookmarks==null||s.SessionUrls==null || s.Bookmarks.Count>5000||s.SessionUrls.Count>100) throw new ArgumentException("Ajustes inválidos");
  if(s.PrivacyRules==null)throw new ArgumentException("Reglas inválidas");
  PrivacyPolicy.ValidateRules(s.PrivacyRules);
  if(s.SearxEndpoint!=null&&!OptimusSearchService.IsValidEndpoint(s.SearxEndpoint))throw new ArgumentException("Endpoint de búsqueda no válido.");
  foreach(var b in s.Bookmarks) if(b==null||b.Title==null || b.Url==null || !Uri.TryCreate(b.Url,UriKind.Absolute,out var u)||!NavigationPolicy.IsAllowed(u)) throw new ArgumentException("Marcador inválido");
  foreach(var url in s.SessionUrls) if(!Uri.TryCreate(url,UriKind.Absolute,out var u)||!NavigationPolicy.IsAllowed(u)) throw new ArgumentException("Sesión inválida");
 }
}
