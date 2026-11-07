namespace Optimus.Core;
/// <summary>Cleanup owns the actual native controller even after navigation readiness is revoked.</summary>
public sealed class ControllerOwnership(Action dispose)
{
 private bool attached,retirementRequested,retired;
 public bool HasController=>attached&&!retired;
 public void Attach(){if(retirementRequested||retired)throw new InvalidOperationException("El controlador ya se retiró.");attached=true;}
 public void RequestRetirement(Action<Action> post,Action<Exception> failure)
 {
  retirementRequested=true;if(retired)return;
  try{post(()=>{try{Retire();}catch(Exception error){failure(error);}});}
  catch(Exception error){failure(error);}
 }
 public async Task QuiesceAsync(Func<Task> quiesce)
 {
  if(retirementRequested){Retire();return;}
  if(HasController)await quiesce();
  if(retirementRequested)Retire();
 }
 public void Retire()
 {
  if(retired)return;retirementRequested=true;
  // Disposal failure retains ownership; callers cannot confirm quiescence or deletion.
  dispose();attached=false;retired=true;
 }
}
