using System.Text.RegularExpressions;
namespace Optimus.Core;
public static partial class NavigationPolicy
{
 public static NavigationResult Resolve(string input, SearchProvider provider)
 {
  if(string.IsNullOrWhiteSpace(input)) return Deny("Escribe una dirección o una búsqueda.");
  if(input.Any(char.IsControl) || input.Contains('\\')) return Deny("La dirección contiene caracteres no permitidos.");
  input=input.Trim();
  if(Scheme().IsMatch(input))
  {
   if(!input.StartsWith("https://",StringComparison.OrdinalIgnoreCase) && !input.StartsWith("http://",StringComparison.OrdinalIgnoreCase)) return Deny("Solo se permiten direcciones completas HTTP o HTTPS.");
   return Direct(input);
  }
  if(!input.Any(char.IsWhiteSpace))
  {
   var candidate=Direct("https://"+input);
   if(candidate.Uri is {} uri && (uri.Host.Contains('.') || uri.Host=="localhost" || Uri.CheckHostName(uri.Host)==UriHostNameType.IPv6)) return candidate;
   if(input.Contains('/') || input.Contains('@')) return Deny("Comprueba la dirección; no se permiten credenciales en ella.");
  }
  var baseUrl=provider switch {SearchProvider.DuckDuckGo=>"https://duckduckgo.com/?q=",SearchProvider.Google=>"https://www.google.com/search?q=",_=>null};
  return baseUrl==null?Deny("El proveedor de búsqueda no es válido."):new(new Uri(baseUrl+Uri.EscapeDataString(input)),true,null);
 }
 public static bool IsAllowed(Uri? uri) => uri is {IsAbsoluteUri:true} && (uri.Scheme=="https"||uri.Scheme=="http") && !string.IsNullOrEmpty(uri.Host) && string.IsNullOrEmpty(uri.UserInfo);
 private static NavigationResult Direct(string text) => !text.Any(char.IsWhiteSpace) && Uri.TryCreate(text,UriKind.Absolute,out var uri) && IsAllowed(uri) ? new(uri,false,null):Deny("La dirección no es válida o incluye credenciales. Usa HTTP o HTTPS.");
 private static NavigationResult Deny(string error)=>new(null,false,error);
 [GeneratedRegex("^[a-zA-Z][a-zA-Z0-9+.-]*:")] private static partial Regex Scheme();
}
