namespace Optimus.Core;
public record SharedExcerpt(string Text,string Origin,bool WasTruncated,string? Error)
{
 public const int Limit=8000;
 public static SharedExcerpt Create(string text,Uri source)
 {
  if(!NavigationPolicy.IsAllowed(source)) return new("","",false,"Solo puedes compartir texto de una página HTTP o HTTPS sin credenciales.");
  if(string.IsNullOrWhiteSpace(text)) return new("","",false,"Selecciona o pega el texto que quieres revisar.");
  var length=Math.Min(text.Length,Limit);
  if(length<text.Length && char.IsHighSurrogate(text[length-1])) length--;
  return new(text[..length],source.GetLeftPart(UriPartial.Authority),length<text.Length,null);
 }
}
