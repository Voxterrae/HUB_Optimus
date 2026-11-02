//! Owned read-only Windows resources; never serializable identities or authority.
use crate::arena::Arena;
use crate::errors::ErrorBag;
use crate::model::{Domain,Error,Operation,Phase,Reason,Result};
use std::time::Instant;
use windows_sys::Win32::Foundation::{HANDLE,CloseHandle,GetHandleInformation,GetLastError,HANDLE_FLAG_INHERIT};

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub enum ResourceKind { ProcessToken, Directory }
#[derive(Clone,Copy)]
struct Slot { raw:usize,kind:ResourceKind,order:u64 }
const EMPTY:Slot=Slot{raw:0,kind:ResourceKind::ProcessToken,order:0};
pub struct Resources { slots:[Slot;133], serial:u64, live:[usize;2], peak:[usize;2] }
fn key(kind:ResourceKind)->usize { match kind{ResourceKind::ProcessToken=>0,ResourceKind::Directory=>1} }
fn cap(kind:ResourceKind)->usize { match kind{ResourceKind::ProcessToken=>4,ResourceKind::Directory=>129} }
impl Resources {
 pub const fn new()->Self {Self{slots:[EMPTY;133],serial:0,live:[0;2],peak:[0;2]}}
 pub fn live(&self,kind:ResourceKind)->usize {self.live[key(kind)]}
 pub fn peak(&self,kind:ResourceKind)->usize {self.peak[key(kind)]}
 pub fn can_acquire(&self,kind:ResourceKind)->bool {self.live(kind)<cap(kind)&&self.slots.iter().any(|x|x.raw==0)}
 pub fn register(&mut self,raw:usize,kind:ResourceKind)->Result<usize>{
  if raw==0||raw>=usize::MAX-8{return Err(Error::internal(Phase::Capture,Operation::Validate,Reason::Malformed));}
  if !self.can_acquire(kind){return Err(Error::internal(Phase::Capture,Operation::Validate,Reason::Bound));}
  if self.slots.iter().any(|x|x.raw==raw){return Err(Error::internal(Phase::Capture,Operation::Validate,Reason::Malformed));}
  let order=self.serial.checked_add(1).ok_or_else(||Error::internal(Phase::Capture,Operation::Validate,Reason::Bound))?;
  let index=self.slots.iter().position(|x|x.raw==0).ok_or_else(||Error::internal(Phase::Capture,Operation::Validate,Reason::Bound))?;
  self.serial=order;self.slots[index]=Slot{raw,kind,order};
  let k=key(kind);self.live[k]+=1;self.peak[k]=self.peak[k].max(self.live[k]);Ok(index)
 }
 pub fn contains(&self,raw:usize)->bool{self.slots.iter().any(|s|s.raw!=0&&s.raw==raw)}
 pub fn raw(&self,index:usize)->usize{self.slots.get(index).map_or(0,|x|x.raw)}
 pub fn take(&mut self,index:usize)->Option<usize>{
  let slot=self.slots.get_mut(index)?;if slot.raw==0{return None;}
  let old=*slot;*slot=EMPTY;self.live[key(old.kind)]-=1;Some(old.raw)
 }
 pub fn take_reverse(&mut self)->Option<usize>{
  let index=self.slots.iter().enumerate().filter(|(_,s)|s.raw!=0).max_by_key(|(_,s)|s.order).map(|(i,_)|i)?;
  self.take(index)
 }
}
impl Default for Resources {fn default()->Self{Self::new()}}

pub struct Context<'a>{
 pub arena:&'a Arena,pub errors:ErrorBag,pub resources:Resources,
 started:Instant,phase:Phase,operations:usize,
 #[cfg(test)] fail_at:Option<usize>,
 #[cfg(test)] close_failure:bool,
}
impl<'a> Context<'a>{
 pub fn new(arena:&'a Arena)->Self{Self{arena,errors:ErrorBag::new(),resources:Resources::new(),started:Instant::now(),phase:Phase::Initial,operations:0,#[cfg(test)]fail_at:None,#[cfg(test)]close_failure:false}}
 pub fn elapsed_ms(&self)->u64{self.started.elapsed().as_millis().min(u64::MAX as u128) as u64}
 pub fn operation_count(&self)->usize{self.operations}
 pub fn check(&mut self,operation:Operation,phase:Phase)->Result<()>{
  self.phase=phase;self.operations=self.operations.checked_add(1).ok_or_else(||Error::internal(phase,operation,Reason::Bound))?;
  #[cfg(test)] if self.fail_at==Some(self.operations){return Err(Error::internal(phase,operation,Reason::Unsupported));}
  // Checked cleanup must always run, even after the observation budget expires.
  if phase!=Phase::Cleanup && self.elapsed_ms()>10_000{return Err(Error::internal(phase,operation,Reason::Budget));}Ok(())
 }
 pub fn before_acquire(&self,kind:ResourceKind)->Result<()>{
  if self.resources.can_acquire(kind){Ok(())}else{Err(Error::internal(self.phase,Operation::Validate,Reason::Bound))}
 }
 fn close_raw(&self,raw:usize)->Result<()>{
  if unsafe{CloseHandle(raw as HANDLE)}==0 {return Err(Error::native(Phase::Cleanup,Operation::CloseHandle,Domain::Win32,unsafe{GetLastError()}));}
  #[cfg(test)] if self.close_failure{return Err(Error::internal(Phase::Cleanup,Operation::CloseHandle,Reason::Unsupported));}
  Ok(())
 }
 pub fn defer(&mut self,handle:HANDLE,kind:ResourceKind)->Option<usize>{
  let raw=handle as usize;
  match self.resources.register(raw,kind){
   Ok(index)=>Some(index),
   Err(error)=>{
    // This is an unrepresentable resource-ledger defect, not another accepted primary.
    self.errors.primary(error);
    self.errors.primary(Error::internal(Phase::Initial,Operation::Validate,Reason::Budget));
    if raw!=0&&raw<usize::MAX-8&&!self.resources.contains(raw) {if let Err(cleanup)=self.close_raw(raw){self.errors.cleanup(cleanup);}}
    None
   }
  }
 }
 pub fn acquire(&mut self,handle:HANDLE,kind:ResourceKind)->Result<usize>{
  let slot=match self.resources.register(handle as usize,kind){
   Ok(slot)=>slot,
   Err(mut error)=>{
    error.phase=self.phase;
    if handle as usize!=0&&(handle as usize)<usize::MAX-8&&!self.resources.contains(handle as usize) {
     if let Err(cleanup)=self.close_raw(handle as usize){self.errors.cleanup(cleanup);}
    }
    return Err(error)
   }
  };
  self.check(Operation::GetHandleInformation,self.phase)?;
  let mut flags=0;
  if unsafe{GetHandleInformation(handle,&mut flags)}==0{return Err(Error::native(self.phase,Operation::GetHandleInformation,Domain::Win32,unsafe{GetLastError()}));}
  if flags&HANDLE_FLAG_INHERIT!=0{return Err(Error::internal(self.phase,Operation::GetHandleInformation,Reason::Policy));}
  Ok(slot)
 }
 pub fn raw(&self,slot:usize)->HANDLE{self.resources.raw(slot) as HANDLE}
 pub fn close(&mut self,slot:usize)->Result<()>{
  let raw=self.resources.take(slot).ok_or_else(||Error::internal(Phase::Cleanup,Operation::CloseHandle,Reason::Malformed))?;
  self.close_raw(raw)
 }
 pub fn finish_cleanup(&mut self){
  while let Some(raw)=self.resources.take_reverse(){if let Err(error)=self.close_raw(raw){self.errors.cleanup(error);}}
 }
 #[cfg(test)]
 pub(crate) fn fail_on(&mut self,step:usize){self.fail_at=Some(step);}
 #[cfg(test)]
 pub(crate) fn inject_reported_close_failure(&mut self){self.close_failure=true;}
}
impl Drop for Context<'_>{
 fn drop(&mut self){
  // Fallback only: explicit finish_cleanup supplies evidence. A consumed failed
  // closer has already left the table and is never retried here.
  while let Some(raw)=self.resources.take_reverse(){unsafe{CloseHandle(raw as HANDLE);}}
 }
}
