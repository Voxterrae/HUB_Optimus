namespace Optimus.Core;
/// <summary>All expected profiles require verified live owners before any deletion can succeed.</summary>
public static class ProfileCleanupCoordinator
{
 public static bool[] ExpectedProfiles(bool normalUsed,IEnumerable<bool> presentModes)=>presentModes.Concat(normalUsed?[false]:Array.Empty<bool>()).Distinct().ToArray();
 public static async Task<bool> ClearAsync<T>(IReadOnlyCollection<bool> expected,Func<bool,Task<T?>> acquire,Func<bool,T,bool> verified,Func<Task> quiesce,Func<T,Task> clear,Action restoreSafety,ProfileOperationGate gate,TimeSpan wait) where T:class
 {
  try
  {
   await quiesce();
   List<(bool Mode,T Owner)> owners=[];
   foreach(var mode in expected)
   {
    var owner=await acquire(mode);
    if(owner==null||!verified(mode,owner))throw new InvalidOperationException("Falta un controlador verificado para uno de los perfiles que se deben borrar.");
    owners.Add((mode,owner));
   }
   await quiesce();
   async Task ClearOwner(bool mode,T owner)
   {if(!verified(mode,owner))throw new InvalidOperationException("El perfil perdió su controlador antes del borrado.");await clear(owner);}
   var deletion=Task.WhenAll(owners.Select(item=>ClearOwner(item.Mode,item.Owner)));
   return await gate.RunAsync(deletion,()=>
   {
    if(owners.Any(item=>!verified(item.Mode,item.Owner)))throw new InvalidOperationException("El controlador del perfil terminó durante el borrado.");
    restoreSafety();
   },wait);
  }
  catch(Exception error)
  {
   if(!gate.IsBlocked)await gate.RunAsync(Task.FromException(error),()=>{},wait);
   return false;
  }
 }
}
