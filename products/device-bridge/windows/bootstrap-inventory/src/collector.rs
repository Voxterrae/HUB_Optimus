//! Fixed-route diagnostic orchestration. Successful delivery is never activation.
use crate::arena::{Arena,PRODUCTION_CAPACITY,OUTPUT_CAPACITY};
use crate::errors::ErrorBag;
use crate::model::*;
use std::io::Write;

const REFUSAL_CAPACITY:usize=131_072;
fn stamp()->Stamp<'static>{Stamp{
 source_commit:env!("HUB_RELAY_BUILD_SOURCE"),policy_sha256:env!("HUB_RELAY_BUILD_POLICY"),target:env!("HUB_RELAY_BUILD_TARGET")
}}
#[derive(Clone,Copy)]
struct Observations<'a>{process:Option<Process<'a>>,primary:Option<Token<'a>>,thread:Option<Token<'a>>,thread_context:ThreadContext,anchor:Option<Anchor<'a>>,ancestors:Option<&'a[Ancestor<'a>]>,recheck:Recheck}
impl<'a> Observations<'a>{
 fn empty()->Self{Self{process:None,primary:None,thread:None,thread_context:ThreadContext::Unknown,anchor:None,ancestors:None,recheck:Recheck::NotCompleted}}
 fn clear(&mut self){self.process=None;self.primary=None;self.thread=None;self.anchor=None;self.ancestors=None;}
 fn complete(&self)->bool{self.process.is_some()&&self.primary.is_some()&&self.thread.is_none()&&self.thread_context==ThreadContext::NoToken&&self.anchor.is_some()&&self.ancestors.is_some()&&self.recheck==Recheck::Equal}
}
fn record<'a>(o:Observations<'a>,timings:[u64;3],errors:&'a[Error],outcome:Outcome,cleanup:Cleanup)->Receipt<'a>{Receipt{
 outcome,collector:stamp(),started_utc:timings[0],finished_utc:timings[1],elapsed_ms:timings[2],
 process:o.process,primary_token:o.primary,thread_token:o.thread,thread_context:o.thread_context,anchor:o.anchor,ancestors:o.ancestors,recheck:o.recheck,errors,cleanup
}}
fn emit<W:Write>(out:&mut W,mut observations:Observations<'_>,timings:[u64;3],errors:&mut ErrorBag,output:&mut[u8],refusal:&mut[u8;REFUSAL_CAPACITY])->std::result::Result<Outcome,()>{
 if errors.unrepresentable(){return Err(());}
 if errors.as_slice().is_empty()&&!observations.complete(){errors.primary(Error::internal(Phase::Recheck,Operation::Validate,Reason::Malformed));}
 let outcome=if errors.as_slice().is_empty(){Outcome::Observed}else{Outcome::Refused};
 let cleanup=if errors.cleanup_failed(){Cleanup::Failed}else{Cleanup::Complete};
 let length={let r=record(observations,timings,errors.as_slice(),outcome,cleanup);crate::wire::encoded_len(&r)};
 match length{
  Ok(length) if length<=output.len()=>{
   let r=record(observations,timings,errors.as_slice(),outcome,cleanup);
   let written=crate::wire::encode_into(&r,output).map_err(|_|())?;
   if written!=length{return Err(());}
   out.write_all(&output[..written]).map_err(|_|())?;out.flush().map_err(|_|())?;Ok(outcome)
  }
  Err(Error{reason:Some(Reason::Bound),..})|Ok(_)=>{
   observations.clear();
   if !errors.receipt_bound()||errors.unrepresentable(){return Err(());}
   let r=record(observations,timings,errors.as_slice(),Outcome::Refused,cleanup);
   let written=crate::wire::encode_into(&r,refusal).map_err(|_|())?;
   out.write_all(&refusal[..written]).map_err(|_|())?;out.flush().map_err(|_|())?;Ok(Outcome::Refused)
  }
  _=>Err(())
 }
}
#[cfg(all(windows,target_arch="x86_64",target_env="msvc"))]
fn utc()->u64{
 use windows_sys::Win32::Foundation::FILETIME;
 use windows_sys::Win32::System::SystemInformation::GetSystemTimeAsFileTime;
 let mut time=FILETIME{dwLowDateTime:0,dwHighDateTime:0};
 unsafe{GetSystemTimeAsFileTime(&mut time);}
 ((time.dwHighDateTime as u64)<<32)|time.dwLowDateTime as u64
}
#[cfg(all(windows,target_arch="x86_64",target_env="msvc"))]
fn pipeline<W:Write>(ctx:&mut crate::windows::Context<'_>,output:&mut[u8],refusal:&mut[u8;REFUSAL_CAPACITY],out:&mut W)->std::result::Result<Outcome,()>{
 let started=utc();
 let mut process=crate::process::State::new();let mut dirs=crate::directories::State::new();
 let mut recheck=Recheck::NotCompleted;
 let capture=(||{
  crate::process::capture(ctx,&mut process)?;
  if process.thread_context!=ThreadContext::NoToken{return Err(Error::internal(Phase::Capture,Operation::Validate,Reason::Impersonation));}
  crate::directories::capture(ctx,&mut dirs)?;
  crate::process::recheck(ctx,&mut process)?;
  crate::directories::recheck(ctx,&dirs)?;
  Ok::<(),Error>(())
 })();
 match capture{
  Ok(())=>recheck=Recheck::Equal,
  Err(error)=>{
   if error.phase==Phase::Recheck&&matches!(error.reason,Some(Reason::Drift|Reason::TokenChanged|Reason::Impersonation|Reason::Policy)){recheck=Recheck::Changed;}
   ctx.errors.primary(error);
  }
 }
 // No observation failure can bypass reverse checked cleanup.
 ctx.finish_cleanup();
 let finished=utc();let elapsed=ctx.elapsed_ms();
 if ctx.errors.as_slice().is_empty()&&(elapsed>10_000||finished<started){
  ctx.errors.primary(Error::internal(Phase::Recheck,Operation::Validate,if elapsed>10_000{Reason::Budget}else{Reason::Drift}));
 }
 let observations=Observations{process:process.process,primary:process.primary,thread:process.thread,thread_context:process.thread_context,anchor:dirs.anchor,ancestors:dirs.ancestors,recheck};
 emit(out,observations,[started,finished,elapsed],&mut ctx.errors,output,refusal)
}

/// Observe only the current native AMD64 process/thread and fixed ProgramFiles chain.
/// The output is private diagnostic evidence; even Observed leaves activation blocked.
pub fn run_to<W:Write>(out:&mut W)->std::result::Result<Outcome,()>{
 let arena=Arena::new(PRODUCTION_CAPACITY).map_err(|_|())?;
 if arena.allocated_capacity()!=PRODUCTION_CAPACITY{return Err(());}
 let output=arena.output(OUTPUT_CAPACITY).map_err(|_|())?;
 let mut refusal=[0u8;REFUSAL_CAPACITY];
 #[cfg(all(windows,target_arch="x86_64",target_env="msvc"))]{
  let mut ctx=crate::windows::Context::new(&arena);
  pipeline(&mut ctx,output,&mut refusal,out)
 }
 #[cfg(not(all(windows,target_arch="x86_64",target_env="msvc")))]{
  let mut errors=ErrorBag::new();errors.primary(Error::internal(Phase::Initial,Operation::Validate,Reason::Unsupported));
  emit(out,Observations::empty(),[0,0,0],&mut errors,output,&mut refusal)
 }
}

#[cfg(test)]
mod tests{
 use super::*;
 struct Broken;impl Write for Broken{fn write(&mut self,_:&[u8])->std::io::Result<usize>{Err(std::io::ErrorKind::BrokenPipe.into())}fn flush(&mut self)->std::io::Result<()>{Ok(())}}
 #[test]fn output_failure_never_reports_complete_delivery(){
  let mut errors=ErrorBag::new();errors.primary(Error::internal(Phase::Initial,Operation::Validate,Reason::Unsupported));
  let mut output=vec![0;REFUSAL_CAPACITY];let mut refusal=[0;REFUSAL_CAPACITY];
  assert!(emit(&mut Broken,Observations::empty(),[0,0,0],&mut errors,&mut output,&mut refusal).is_err());
 }
 #[cfg(all(windows,target_arch="x86_64",target_env="msvc"))]
 #[test]fn native_fixed_collection_finishes_checked_and_reports_complete_json(){
  let arena=Arena::new(PRODUCTION_CAPACITY).unwrap();let output=arena.output(OUTPUT_CAPACITY).unwrap();let mut refusal=[0;REFUSAL_CAPACITY];let mut ctx=crate::windows::Context::new(&arena);
  let result=pipeline(&mut ctx,output,&mut refusal,&mut std::io::sink());
  assert!(result.is_ok(),"fixed diagnostic must produce a complete receipt, including refusal");
  assert_eq!(ctx.resources.live(crate::windows::ResourceKind::Directory),0);
  assert_eq!(ctx.resources.live(crate::windows::ResourceKind::ProcessToken),0);
  assert!(!ctx.errors.unrepresentable());
 }
 #[cfg(all(windows,target_arch="x86_64",target_env="msvc"))]
 #[test]fn every_checked_native_boundary_refuses_and_consumes_owned_handles(){
  let steps={
   let arena=Arena::new(PRODUCTION_CAPACITY).unwrap();let output=arena.output(OUTPUT_CAPACITY).unwrap();
   let mut refusal=[0;REFUSAL_CAPACITY];let mut ctx=crate::windows::Context::new(&arena);
   assert!(pipeline(&mut ctx,output,&mut refusal,&mut std::io::sink()).is_ok());ctx.operation_count()
  };
  assert!(steps>0&&steps<=1024);
  for step in 1..=steps {
   let arena=Arena::new(PRODUCTION_CAPACITY).unwrap();let output=arena.output(OUTPUT_CAPACITY).unwrap();
   let mut refusal=[0;REFUSAL_CAPACITY];let mut ctx=crate::windows::Context::new(&arena);ctx.fail_on(step);
   assert_eq!(pipeline(&mut ctx,output,&mut refusal,&mut std::io::sink()),Ok(Outcome::Refused));
   assert_eq!(ctx.resources.live(crate::windows::ResourceKind::Directory),0);
   assert_eq!(ctx.resources.live(crate::windows::ResourceKind::ProcessToken),0);
   assert!(!ctx.errors.unrepresentable());
  }
 }
 #[cfg(all(windows,target_arch="x86_64",target_env="msvc"))]
 #[test]fn reported_close_failure_never_becomes_observed_or_retried(){
  let arena=Arena::new(PRODUCTION_CAPACITY).unwrap();let output=arena.output(OUTPUT_CAPACITY).unwrap();
  let mut refusal=[0;REFUSAL_CAPACITY];let mut ctx=crate::windows::Context::new(&arena);ctx.inject_reported_close_failure();
  assert_eq!(pipeline(&mut ctx,output,&mut refusal,&mut std::io::sink()),Ok(Outcome::Refused));
  assert!(ctx.errors.cleanup_failed());
  assert_eq!(ctx.resources.live(crate::windows::ResourceKind::Directory),0);
  assert_eq!(ctx.resources.live(crate::windows::ResourceKind::ProcessToken),0);
  let count=ctx.errors.as_slice().len();ctx.finish_cleanup();assert_eq!(ctx.errors.as_slice().len(),count);
 }

}
