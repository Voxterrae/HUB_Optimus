using System.Runtime.InteropServices;
namespace Optimus.Core;
/// <summary>Last validated native address, including same-document path/query/fragment changes.
/// Cleanup destinations and failed native reads never replace the recovery snapshot.</summary>
public sealed class NavigationSnapshot
{
 public string? LastAddress {get;private set;}
 public bool TryRefresh(Func<string?> readNativeSource)
 {
  try
  {
   var source=readNativeSource();
   if(source==null||!Uri.TryCreate(source,UriKind.Absolute,out var uri)||!NavigationPolicy.IsAllowed(uri))return false;
   var result=NavigationPolicy.Resolve(source,SearchProvider.DuckDuckGo);
   if(!result.Allowed||result.IsSearch)return false;
   LastAddress=result.Uri!.AbsoluteUri;return true;
  }
  catch(Exception e) when(e is InvalidOperationException or COMException){return false;}
 }
}
