namespace Optimus.Core;
public static class LocalGuide
{
 public const string Label="Guía local basada en reglas";
 public static GuideReply Respond(string question,BrowserContext context)
 {
  var q=question.Trim();var lower=q.ToLowerInvariant();
  GuideReply Reply(string text,AssistantAction? action=null)=>new($"{Label}. {text}",action);
  if(lower.StartsWith("abre "))
  {
   var n=NavigationPolicy.Resolve(q[5..],SearchProvider.DuckDuckGo);
   return n.Allowed&&!n.IsSearch?Reply("Puedo proponer abrir "+n.Uri!.AbsoluteUri+". Revisa y confirma el destino.",new(ActionKind.OpenUrl,n.Uri.AbsoluteUri)):Reply(n.Error??"Escribe una dirección HTTP o HTTPS después de «abre».");
  }
  if(lower.Contains("marcador") || lower.Contains("guardar")) return NavigationPolicy.IsAllowed(Uri.TryCreate(context.Origin,UriKind.Absolute,out var uri)?uri:null)?Reply("Puedo guardar la página actual en Marcadores si confirmas.",new(ActionKind.BookmarkCurrent)):Reply("Abre primero una página; luego usa Guardar marcador. Para recuperarla, abre Marcadores.");
  if(lower.Contains("zoom")||lower.Contains("letra")) return Reply("Propongo un tamaño del 125 %. Puedes cambiarlo entre 100 y 200 % en la barra.",new(ActionKind.SetTextScale,"1.25"));
  if(lower.Contains("contraste")) return Reply("Propongo activar el contraste alto de los controles de Optimus.",new(ActionKind.SetContrast,"true"));
  if(lower.Contains("permiso")||lower.Contains("cámara")||lower.Contains("camara")||lower.Contains("micrófono")) return Reply("Un permiso permite a un sitio usar un recurso. Comprueba el origen en el aviso nativo. Puedes denegar; no concedo permisos. «Revocar permisos» elimina las decisiones de esta sesión.");
  if(lower.Contains("naveg")||lower.Contains("buscar")||lower.Contains("dirección")) return Reply("Escribe una dirección arriba y pulsa Ir o Intro. Para buscar, escribe palabras. El proveedor elegido aparece en la barra. Atrás vuelve a la página anterior.");
  return Reply("Puedo orientar sobre navegar, marcadores, permisos, zoom y contraste, o proponer «abre https://…». Para otras tareas sigue los controles del sitio. La IA remota está desactivada; no he ejecutado ninguna acción.");
 }
}
