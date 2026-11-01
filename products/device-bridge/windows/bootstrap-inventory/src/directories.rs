//! Fixed ProgramFiles metadata inventory. No selectors, scanning or authority.
//! Initial observations and equality do not exclude privileged mutation or ABA.
use crate::model::{Anchor, Ancestor, Completion, Domain, Error, Operation, Phase, Reason, Result};
pub const MAX_PATH_UNITS: usize=32_767;
pub const MAX_ANCESTORS: usize=128;
pub const METADATA_RIGHTS: u32=0x0012_0080;
const MAX_COMPONENTS: usize=MAX_ANCESTORS-1;
const UNWRITTEN_STATUS: u32=0xc000_0001;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub enum CompletionClass { Complete, Reject, FatalPending }
/// Keep the native call status, IOSB status and Information independent.
pub fn classify_completion(c: Completion, expected_information: u64, valid: bool) -> CompletionClass {
    if c.call==0x103 || c.io_status==0x103 || ((c.call as i32)>=0 && c.io_status==UNWRITTEN_STATUS && c.information==usize::MAX as u64) { return CompletionClass::FatalPending; }
    if c.call==0 && c.io_status==0 && c.information==expected_information && valid { CompletionClass::Complete } else { CompletionClass::Reject }
}
pub fn completion_error(phase: Phase, operation: Operation, c: Completion) -> Error {
    let mut error=if c.call!=0 || c.io_status!=0 { Error::native(phase,operation,Domain::Ntstatus,c.call) } else { Error::internal(phase,operation,Reason::Malformed) };
    error.completion=Some(c); error
}
fn malformed() -> Error { Error::internal(Phase::Capture,Operation::Validate,Reason::Malformed) }
fn bound() -> Error { Error::internal(Phase::Capture,Operation::Validate,Reason::Bound) }
fn valid_utf16(units: &[u16]) -> Result<()> {
    if units.iter().any(|&u|u==0) || char::decode_utf16(units.iter().copied()).any(|c|c.is_err()) { return Err(malformed()); }
    Ok(())
}
fn ascii_equal(a: &[u16], b: &[u8]) -> bool {
    a.len()==b.len() && a.iter().zip(b).all(|(&x,&y)|x<=127 && (x as u8).eq_ignore_ascii_case(&y))
}
fn component(units: &[u16]) -> Result<()> {
    if units.is_empty() || units.len()>255 { return Err(bound()); }
    valid_utf16(units)?;
    if units==[46] || units==[46,46] || matches!(units.last(),Some(46|32)) || units.iter().any(|&u|u<32 || [92,47,58,42,63,34,60,62,124,126].contains(&u)) { return Err(malformed()); }
    let base=units.split(|&u|u==46).next().ok_or_else(malformed)?;
    if [b"CON".as_slice(),b"PRN",b"AUX",b"NUL",b"CLOCK$",b"CONIN$",b"CONOUT$"].iter().any(|s|ascii_equal(base,s))
        || (base.len()==4 && (ascii_equal(&base[..3],b"COM") || ascii_equal(&base[..3],b"LPT")) && matches!(base[3],49..=57|0xb9|0xb2|0xb3)) { return Err(malformed()); }
    Ok(())
}
#[derive(Debug)]
pub struct ParsedPath<'a> { units: &'a[u16], ranges: [(usize,usize);MAX_COMPONENTS], count: usize, prefix: usize }
impl<'a> ParsedPath<'a> {
    pub fn component_count(&self) -> usize { self.count }
    pub fn component(&self,index: usize) -> Option<&'a[u16]> { if index>=self.count { None } else { let (a,b)=self.ranges[index]; Some(&self.units[a..b]) } }
    pub fn root(&self) -> &'a[u16] { &self.units[..self.prefix] }
}
fn parsed(units: &[u16], prefix: usize) -> Result<ParsedPath<'_>> {
    valid_utf16(units)?;
    let mut path=ParsedPath {units,ranges:[(0,0);MAX_COMPONENTS],count:0,prefix};
    if units.len()==prefix { return Ok(path); }
    let mut start=prefix;
    for part in units[prefix..].split(|&u|u==92) {
        if path.count==MAX_COMPONENTS { return Err(bound()); }
        component(part)?; let end=start+part.len(); path.ranges[path.count]=(start,end); path.count+=1; start=end+1;
    }
    Ok(path)
}
/// Refuse remote/device/relative syntax before any mapping or open is attempted.
pub fn parse_drive_path(units: &[u16]) -> Result<ParsedPath<'_>> {
    if units.len()>MAX_PATH_UNITS { return Err(bound()); }
    if units.len()<3 || units[0]>127 || !(units[0] as u8).is_ascii_alphabetic() || units[1..3]!=[58,92] { return Err(malformed()); }
    parsed(units,3)
}
pub fn parse_guid_path(units: &[u16]) -> Result<ParsedPath<'_>> {
    if units.len()>MAX_PATH_UNITS { return Err(bound()); }
    const PREFIX: &[u16]=&[92,92,63,92,86,111,108,117,109,101,123];
    if units.len()<49 || &units[..11]!=PREFIX || units[47..49]!=[125,92]
        || !units[11..47].iter().enumerate().all(|(i,&u)|if [8,13,18,23].contains(&i) {u==45} else {u<=127 && (u as u8).is_ascii_hexdigit()}) { return Err(malformed()); }
    parsed(units,49)
}
/// Conservative portable binding: ASCII ordinal case fold; other UTF16 exact.
/// Windows acquisition additionally requires CompareStringOrdinal agreement.
pub fn portable_path_equal(a: &[u16],b: &[u16]) -> bool {
    a.len()==b.len() && a.iter().zip(b).all(|(&x,&y)|x==y || (x<=127 && y<=127 && (x as u8).eq_ignore_ascii_case(&(y as u8))))
}

pub struct State<'a> {
    pub anchor: Option<Anchor<'a>>,
    pub ancestors: Option<&'a[Ancestor<'a>]>,
    #[cfg(windows)] slots: [usize;MAX_ANCESTORS],
    #[cfg(windows)] facts: [native::Facts;MAX_ANCESTORS],
    #[cfg(windows)] count: usize,
    #[cfg(windows)] attempted: bool,
}
impl<'a> State<'a> {
    pub fn new() -> Self { Self {anchor:None,ancestors:None,#[cfg(windows)] slots:[usize::MAX;MAX_ANCESTORS],#[cfg(windows)] facts:[native::Facts::EMPTY;MAX_ANCESTORS],#[cfg(windows)] count:0,#[cfg(windows)] attempted:false} }
}
impl Default for State<'_> { fn default() -> Self { Self::new() } }
#[cfg(windows)] pub use native::{capture,recheck};

#[cfg(windows)]
mod native {
    use super::*;
    use crate::os_policy::{MAX_DESCRIPTOR_BYTES,validate_descriptor};
    use crate::windows::{Context,ResourceKind};
    use std::mem::{MaybeUninit,size_of};
    use std::ptr::{null,null_mut};
    use windows_sys::Wdk::Foundation::OBJECT_ATTRIBUTES;
    use windows_sys::Wdk::Storage::FileSystem as nt;
    use windows_sys::Win32::Foundation::*;
    use windows_sys::Win32::Globalization::CompareStringOrdinal;
    use windows_sys::Win32::Security::Authorization::{GetSecurityInfo,SE_FILE_OBJECT};
    use windows_sys::Win32::Security::{DACL_SECURITY_INFORMATION,GetSecurityDescriptorLength,OWNER_SECURITY_INFORMATION,PSECURITY_DESCRIPTOR};
    use windows_sys::Win32::Storage::FileSystem::*;
    use windows_sys::Win32::System::Com::{CoInitializeEx,CoUninitialize,CoTaskMemFree,COINIT_MULTITHREADED};
    use windows_sys::Win32::System::IO::IO_STATUS_BLOCK;
    use windows_sys::Win32::System::Threading::GetCurrentProcess;
    use windows_sys::Win32::UI::Shell::{SHGetKnownFolderPath,FOLDERID_ProgramFiles,KF_FLAG_DONT_VERIFY};
    const FOLDER_ID: &str="905e63b6-c1bf-494e-b29c-65b732d3d21a";
    #[derive(Clone,Copy)]
    struct Scope { phase: Phase, index: Option<usize> }
    impl Scope {
        fn error(self,operation: Operation,reason: Reason) -> Error { self.attach(Error::internal(self.phase,operation,reason)) }
        fn native(self,operation: Operation,domain: Domain,code: u32) -> Error { self.attach(Error::native(self.phase,operation,domain,code)) }
        fn last(self,operation: Operation) -> Error { self.native(operation,Domain::Win32,unsafe {GetLastError()}) }
        fn attach(self,mut e: Error) -> Error { if e.phase!=Phase::Cleanup {e.phase=self.phase;} if let Some(i)=self.index {e.ancestor_index=Some(i as u32);} e }
        fn check(self,ctx: &mut Context<'_>,op: Operation) -> Result<()> { ctx.check(op,self.phase).map_err(|e|self.attach(e)) }
    }
    fn finish<T>(ctx: &mut Context<'_>,result: Result<T>,cleanup: Result<()>) -> Result<T> {
        match (result,cleanup) {
            (result,Ok(()))=>result,
            (Ok(_),Err(e))=>Err(e),
            (Err(primary),Err(cleanup))=>{ ctx.errors.primary(primary); ctx.errors.cleanup(cleanup); Err(primary) }
        }
    }
    fn iosb() -> IO_STATUS_BLOCK { let mut io=IO_STATUS_BLOCK::default(); io.Anonymous.Status=UNWRITTEN_STATUS as i32; io.Information=usize::MAX; io }
    fn completion(call: i32,io: &IO_STATUS_BLOCK) -> Completion { Completion {call:call as u32,io_status:unsafe {io.Anonymous.Status} as u32,information:io.Information as u64} }
    fn terminal(scope: Scope,op: Operation,c: Completion,information: u64,valid: bool) -> Result<()> {
        match classify_completion(c,information,valid) {
            // Do not unwind, format, close or free while NT may own native storage.
            CompletionClass::FatalPending=>std::process::abort(),
            CompletionClass::Complete=>Ok(()),
            CompletionClass::Reject=>Err(scope.attach(completion_error(scope.phase,op,c))),
        }
    }
    fn noninheritable(ctx: &mut Context<'_>,slot: usize,scope: Scope) -> Result<()> {
        scope.check(ctx,Operation::GetHandleInformation)?;
        let mut flags=0;
        if unsafe {GetHandleInformation(ctx.raw(slot),&mut flags)}==0 { return Err(scope.last(Operation::GetHandleInformation)); }
        if flags&HANDLE_FLAG_INHERIT!=0 { return Err(scope.error(Operation::Validate,Reason::Policy)); }
        Ok(())
    }
    fn granted(ctx: &mut Context<'_>,slot: usize,scope: Scope) -> Result<u32> {
        scope.check(ctx,Operation::NtQueryInformationFile)?;
        let mut access=nt::FILE_ACCESS_INFORMATION::default(); let mut io=iosb();
        let call=unsafe {nt::NtQueryInformationFile(ctx.raw(slot),&mut io,(&mut access as *mut nt::FILE_ACCESS_INFORMATION).cast(),size_of::<nt::FILE_ACCESS_INFORMATION>() as u32,nt::FileAccessInformation)};
        terminal(scope,Operation::NtQueryInformationFile,completion(call,&io),size_of::<nt::FILE_ACCESS_INFORMATION>() as u64,true)?;
        Ok(access.AccessFlags)
    }
    fn reduced(ctx: &mut Context<'_>,source: usize,scope: Scope) -> Result<usize> {
        let result=(|| {
            if granted(ctx,source,scope)?&METADATA_RIGHTS!=METADATA_RIGHTS { return Err(scope.error(Operation::Validate,Reason::Policy)); }
            scope.check(ctx,Operation::DuplicateHandle)?;
            let mut raw=null_mut();
            if unsafe {DuplicateHandle(GetCurrentProcess(),ctx.raw(source),GetCurrentProcess(),&mut raw,METADATA_RIGHTS,0,0)}==0 { return Err(scope.last(Operation::DuplicateHandle)); }
            if raw.is_null() || raw==INVALID_HANDLE_VALUE { return Err(scope.error(Operation::DuplicateHandle,Reason::Malformed)); }
            let slot=ctx.acquire(raw,ResourceKind::Directory).map_err(|e|scope.attach(e))?;
            noninheritable(ctx,slot,scope)?;
            if granted(ctx,slot,scope)?!=METADATA_RIGHTS { return Err(scope.error(Operation::Validate,Reason::Policy)); }
            Ok(slot)
        })();
        let cleanup=ctx.close(source).map_err(|e|scope.attach(e));
        finish(ctx,result,cleanup)
    }
    fn open_root(ctx: &mut Context<'_>,root: &[u16;50],scope: Scope) -> Result<usize> {
        scope.check(ctx,Operation::CreateFileW)?;
        let raw=unsafe {CreateFileW(root.as_ptr(),METADATA_RIGHTS,FILE_SHARE_READ|FILE_SHARE_DELETE,null(),OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT,null_mut())};
        if raw==INVALID_HANDLE_VALUE { return Err(scope.last(Operation::CreateFileW)); }
        if raw.is_null() { return Err(scope.error(Operation::CreateFileW,Reason::Malformed)); }
        let source=ctx.acquire(raw,ResourceKind::Directory).map_err(|e|scope.attach(e))?;
        reduced(ctx,source,scope)
    }
    fn open_child(ctx: &mut Context<'_>,parent: usize,name: &[u16],scope: Scope) -> Result<usize> {
        component(name).map_err(|e|scope.attach(e))?;
        let mut buffer=[0u16;255]; buffer[..name.len()].copy_from_slice(name);
        let bytes=u16::try_from(name.len()*2).map_err(|_|scope.error(Operation::NtCreateFile,Reason::Bound))?;
        let unicode=UNICODE_STRING {Length:bytes,MaximumLength:bytes,Buffer:buffer.as_mut_ptr()};
        let attrs=OBJECT_ATTRIBUTES {Length:size_of::<OBJECT_ATTRIBUTES>() as u32,RootDirectory:ctx.raw(parent),ObjectName:&unicode,Attributes:OBJ_CASE_INSENSITIVE|OBJ_DONT_REPARSE,SecurityDescriptor:null(),SecurityQualityOfService:null()};
        let mut raw=null_mut(); let mut io=iosb();
        scope.check(ctx,Operation::NtCreateFile)?;
        let call=unsafe {nt::NtCreateFile(&mut raw,METADATA_RIGHTS,&attrs,&mut io,null(),0,FILE_SHARE_READ|FILE_SHARE_DELETE,nt::FILE_OPEN,nt::FILE_SYNCHRONOUS_IO_NONALERT|nt::FILE_OPEN_REPARSE_POINT,null(),0)};
        let c=completion(call,&io); let valid=!raw.is_null() && raw!=INVALID_HANDLE_VALUE;
        // A rejected terminal call can still return an owned handle. Register it
        // without further queries, preserve its first completion error, and close
        // it once during reverse cleanup. Pending aborts before that registration.
        match classify_completion(c,1,valid) {
            CompletionClass::FatalPending=>std::process::abort(),
            CompletionClass::Reject=>{ if valid {ctx.defer(raw,ResourceKind::Directory);} return Err(scope.attach(completion_error(scope.phase,Operation::NtCreateFile,c))); }
            CompletionClass::Complete=>{}
        }
        let source=ctx.acquire(raw,ResourceKind::Directory).map_err(|e|scope.attach(e))?;
        reduced(ctx,source,scope)
    }
    fn known_folder(ctx: &mut Context<'_>,out: &mut [u16;MAX_PATH_UNITS+1],scope: Scope) -> Result<usize> {
        // The collector's own-process stage must already establish native AMD64.
        if !cfg!(target_arch="x86_64") { return Err(scope.error(Operation::Validate,Reason::Unsupported)); }
        scope.check(ctx,Operation::CoInitializeEx)?;
        let init=unsafe {CoInitializeEx(null(),COINIT_MULTITHREADED as u32)};
        if init!=0 && init!=1 { return Err(scope.native(Operation::CoInitializeEx,Domain::Hresult,init as u32)); }
        let result=(|| {
            scope.check(ctx,Operation::SHGetKnownFolderPath)?;
            let mut raw=null_mut();
            let status=unsafe {SHGetKnownFolderPath(&FOLDERID_ProgramFiles,KF_FLAG_DONT_VERIFY as u32,null_mut(),&mut raw)};
            let copied=(|| {
                if status!=0 { return Err(scope.native(Operation::SHGetKnownFolderPath,Domain::Hresult,status as u32)); }
                if raw.is_null() { return Err(scope.error(Operation::SHGetKnownFolderPath,Reason::Malformed)); }
                for i in 0..=MAX_PATH_UNITS {
                    // Only Shell's NUL-terminated allocation reaches pointer reads.
                    let unit=unsafe {*raw.add(i)};
                    if unit==0 {out[i]=0; return Ok(i);}
                    if i==MAX_PATH_UNITS { return Err(scope.error(Operation::SHGetKnownFolderPath,Reason::Bound)); }
                    out[i]=unit;
                }
                Err(scope.error(Operation::SHGetKnownFolderPath,Reason::Bound))
            })();
            // A failure may still have returned an allocation. Free any nonnull
            // output; this void API has no cleanup success status to invent.
            if !raw.is_null() {unsafe {CoTaskMemFree(raw.cast())};}
            copied
        })();
        unsafe {CoUninitialize()}; // S_OK and S_FALSE are both balanced.
        result
    }
    fn mapping(ctx: &mut Context<'_>,drive: &[u16],out: &mut [u16;50],scope: Scope) -> Result<()> {
        // The complete drive route is validated before this name-based call.
        let path=parse_drive_path(drive).map_err(|e|scope.attach(e))?;
        let mut root=[0u16;4]; root[..3].copy_from_slice(path.root());
        scope.check(ctx,Operation::GetVolumeNameForVolumeMountPointW)?;
        out.fill(0xffff);
        if unsafe {GetVolumeNameForVolumeMountPointW(root.as_ptr(),out.as_mut_ptr(),out.len() as u32)}==0 { return Err(scope.last(Operation::GetVolumeNameForVolumeMountPointW)); }
        let end=out.iter().position(|&u|u==0).ok_or_else(||scope.error(Operation::GetVolumeNameForVolumeMountPointW,Reason::Malformed))?;
        let mapped=parse_guid_path(&out[..end]).map_err(|e|scope.attach(e))?;
        if mapped.component_count()!=0 { return Err(scope.error(Operation::Validate,Reason::Policy)); }
        scope.check(ctx,Operation::GetDriveTypeW)?;
        if unsafe {GetDriveTypeW(out.as_ptr())}!=3 { return Err(scope.error(Operation::GetDriveTypeW,Reason::Policy)); }
        Ok(())
    }
    fn final_path(ctx: &mut Context<'_>,slot: usize,format: u32,out: &mut [u16;MAX_PATH_UNITS+1],scope: Scope) -> Result<usize> {
        scope.check(ctx,Operation::GetFinalPathNameByHandleW)?;
        out.fill(0xffff);
        let n=unsafe {GetFinalPathNameByHandleW(ctx.raw(slot),out.as_mut_ptr(),out.len() as u32,FILE_NAME_NORMALIZED|format)} as usize;
        if n==0 { return Err(scope.last(Operation::GetFinalPathNameByHandleW)); }
        if n>MAX_PATH_UNITS { return Err(scope.error(Operation::GetFinalPathNameByHandleW,Reason::Bound)); }
        if out[n]!=0 { return Err(scope.error(Operation::GetFinalPathNameByHandleW,Reason::Malformed)); }
        valid_utf16(&out[..n]).map_err(|e|scope.attach(e))?; Ok(n)
    }
    fn equal_paths(ctx: &mut Context<'_>,a: &[u16],b: &[u16],scope: Scope) -> Result<()> {
        if a.is_empty() || b.is_empty() || a.len()>MAX_PATH_UNITS || b.len()>MAX_PATH_UNITS { return Err(scope.error(Operation::Validate,Reason::Bound)); }
        scope.check(ctx,Operation::CompareStringOrdinal)?;
        let equal=unsafe {CompareStringOrdinal(a.as_ptr(),a.len() as i32,b.as_ptr(),b.len() as i32,1)};
        if equal==0 { return Err(scope.last(Operation::CompareStringOrdinal)); }
        if equal!=2 { return Err(scope.error(Operation::Validate,Reason::Policy)); }
        // Offline comparison deliberately supports less than Windows Unicode
        // ordinal folding. Refuse that discrepancy rather than invent names.
        if !portable_path_equal(a,b) { return Err(scope.error(Operation::Validate,Reason::Unsupported)); }
        Ok(())
    }
    fn native_root(units: &[u16],scope: Scope) -> Result<()> {
        const DEVICE: &[u16]=&[92,68,101,118,105,99,101,92];
        if units.len()<=DEVICE.len() || !units.starts_with(DEVICE) { return Err(scope.error(Operation::Validate,Reason::Malformed)); }
        let end=units.len()-usize::from(units.last()==Some(&92));
        component(&units[DEVICE.len()..end]).map_err(|e|scope.attach(e))
    }
    #[derive(Clone,Copy,PartialEq,Eq)]
    pub(super) struct Facts { volume: u64,id: [u8;16],attributes: u32,tag: u32,pending: bool,directory: bool,links: u32,size: i64,allocated: i64,serial32: u32 }
    impl Facts { pub(super) const EMPTY: Self=Self {volume:0,id:[0;16],attributes:0,tag:0,pending:false,directory:false,links:0,size:0,allocated:0,serial32:0}; }
    fn facts(ctx: &mut Context<'_>,slot: usize,scope: Scope) -> Result<Facts> {
        let mut id=FILE_ID_INFO::default(); let mut standard=FILE_STANDARD_INFO::default(); let mut tag=FILE_ATTRIBUTE_TAG_INFO::default();
        for (class,ptr,length) in [(FileIdInfo,(&mut id as *mut FILE_ID_INFO).cast(),size_of::<FILE_ID_INFO>()),(FileStandardInfo,(&mut standard as *mut FILE_STANDARD_INFO).cast(),size_of::<FILE_STANDARD_INFO>()),(FileAttributeTagInfo,(&mut tag as *mut FILE_ATTRIBUTE_TAG_INFO).cast(),size_of::<FILE_ATTRIBUTE_TAG_INFO>())] {
            scope.check(ctx,Operation::GetFileInformationByHandleEx)?;
            if unsafe {GetFileInformationByHandleEx(ctx.raw(slot),class,ptr,length as u32)}==0 { return Err(scope.last(Operation::GetFileInformationByHandleEx)); }
        }
        scope.check(ctx,Operation::GetFileType)?;
        // FILE_TYPE_UNKNOWN can be a successful classification; clear stale
        // thread error state before distinguishing it from native failure.
        unsafe {SetLastError(0)};
        let file_type=unsafe {GetFileType(ctx.raw(slot))};
        if file_type!=FILE_TYPE_DISK {
            let code=unsafe {GetLastError()};
            return Err(if file_type==FILE_TYPE_UNKNOWN && code!=0 {scope.native(Operation::GetFileType,Domain::Win32,code)} else {scope.error(Operation::GetFileType,Reason::Policy)});
        }
        let mut filesystem=[0xffffu16;32]; let mut serial32=0;
        scope.check(ctx,Operation::GetVolumeInformationByHandleW)?;
        if unsafe {GetVolumeInformationByHandleW(ctx.raw(slot),null_mut(),0,&mut serial32,null_mut(),null_mut(),filesystem.as_mut_ptr(),filesystem.len() as u32)}==0 { return Err(scope.last(Operation::GetVolumeInformationByHandleW)); }
        if filesystem[..5]!=[78,84,70,83,0] { return Err(scope.error(Operation::GetVolumeInformationByHandleW,Reason::Policy)); }
        let f=Facts {volume:id.VolumeSerialNumber,id:id.FileId.Identifier,attributes:tag.FileAttributes,tag:tag.ReparseTag,pending:standard.DeletePending,directory:standard.Directory,links:standard.NumberOfLinks,size:standard.EndOfFile,allocated:standard.AllocationSize,serial32};
        if !f.directory || f.attributes&FILE_ATTRIBUTE_DIRECTORY==0 || f.pending || f.tag!=0 || f.attributes&FILE_ATTRIBUTE_REPARSE_POINT!=0 || f.size<0 || f.allocated<0 { return Err(scope.error(Operation::Validate,Reason::Policy)); }
        Ok(f)
    }
    fn with_descriptor<T>(ctx: &mut Context<'_>,slot: usize,scope: Scope,transform: impl FnOnce(&[u8])->Result<T>) -> Result<T> {
        scope.check(ctx,Operation::GetSecurityInfo)?;
        let mut raw: PSECURITY_DESCRIPTOR=null_mut();
        let status=unsafe {GetSecurityInfo(ctx.raw(slot),SE_FILE_OBJECT,OWNER_SECURITY_INFORMATION|DACL_SECURITY_INFORMATION,null_mut(),null_mut(),null_mut(),null_mut(),&mut raw)};
        let result=(|| {
            if status!=0 { return Err(scope.native(Operation::GetSecurityInfo,Domain::Win32,status)); }
            if raw.is_null() { return Err(scope.error(Operation::GetSecurityInfo,Reason::Malformed)); }
            let length=unsafe {GetSecurityDescriptorLength(raw)} as usize;
            if !(20..=MAX_DESCRIPTOR_BYTES).contains(&length) { return Err(scope.error(Operation::GetSecurityInfo,Reason::Bound)); }
            // The OS API supplies this live allocation. All untrusted offsets and
            // lengths are parsed only within the bounded borrowed byte slice.
            let bytes=unsafe {std::slice::from_raw_parts(raw.cast::<u8>(),length)};
            validate_descriptor(bytes).map_err(|e|scope.attach(e))?;
            transform(bytes).map_err(|e|scope.attach(e))
        })();
        let cleanup=if raw.is_null() {Ok(())} else {
            // Never let a budget/test hook prevent the real owned free.
            let freed=unsafe {LocalFree(raw)};
            let native_failure=if freed.is_null() {None} else {Some(unsafe {GetLastError()})};
            let injected=ctx.check(Operation::LocalFree,Phase::Cleanup).map_err(|e|scope.attach(e));
            match native_failure {Some(code)=>Err(scope.attach(Error::native(Phase::Cleanup,Operation::LocalFree,Domain::Win32,code))),None=>injected}
        };
        finish(ctx,result,cleanup)
    }
    fn check_one(ctx: &mut Context<'_>,slot: usize,saved: Facts,record: &Ancestor<'_>,scope: Scope) -> Result<()> {
        noninheritable(ctx,slot,scope)?;
        let now=facts(ctx,slot,scope)?;
        if now!=saved { return Err(scope.error(Operation::Validate,Reason::Drift)); }
        if granted(ctx,slot,scope)?!=METADATA_RIGHTS { return Err(scope.error(Operation::Validate,Reason::Drift)); }
        let mut path=[0u16;MAX_PATH_UNITS+1]; let mut native=[0u16;MAX_PATH_UNITS+1];
        let length=final_path(ctx,slot,VOLUME_NAME_GUID,&mut path,scope)?;
        parse_guid_path(&path[..length]).map_err(|e|scope.attach(e))?;
        let nlength=final_path(ctx,slot,VOLUME_NAME_NT,&mut native,scope)?;
        if &path[..length]!=record.path.utf16 || &native[..nlength]!=record.native_path.utf16 { return Err(scope.error(Operation::Validate,Reason::Drift)); }
        let mut root=[0u16;50]; root[..49].copy_from_slice(&path[..49]);
        scope.check(ctx,Operation::GetDriveTypeW)?;
        if unsafe {GetDriveTypeW(root.as_ptr())}!=3 { return Err(scope.error(Operation::GetDriveTypeW,Reason::Drift)); }
        with_descriptor(ctx,slot,scope,|bytes|if bytes==record.owner_dacl {Ok(())} else {Err(scope.error(Operation::Validate,Reason::Drift))})
    }
    fn joined(root: &[u16],suffix: &[u16],out: &mut [u16;MAX_PATH_UNITS+1],scope: Scope) -> Result<usize> {
        let extra=usize::from(!suffix.is_empty() && root.last()!=Some(&92));
        let length=root.len().checked_add(extra).and_then(|n|n.checked_add(suffix.len())).ok_or_else(||scope.error(Operation::Validate,Reason::Bound))?;
        if length>MAX_PATH_UNITS { return Err(scope.error(Operation::Validate,Reason::Bound)); }
        out[..root.len()].copy_from_slice(root); if extra!=0 {out[root.len()]=92;}
        out[root.len()+extra..length].copy_from_slice(suffix); out[length]=0; Ok(length)
    }
    fn check_mapping(ctx: &mut Context<'_>,anchor: Anchor<'_>,phase: Phase) -> Result<()> {
        let scope=Scope {phase,index:None}; let mut drive=[0u16;MAX_PATH_UNITS+1];
        let n=known_folder(ctx,&mut drive,scope)?;
        parse_drive_path(&drive[..n]).map_err(|e|scope.attach(e))?;
        if &drive[..n]!=anchor.resolved_path.utf16 { return Err(scope.error(Operation::Validate,Reason::Drift)); }
        let mut mapped=[0u16;50]; mapping(ctx,&drive[..n],&mut mapped,scope)?;
        equal_paths(ctx,&mapped[..49],anchor.volume_guid.utf16,scope)
    }
    fn check_parts(ctx: &mut Context<'_>,state: &State<'_>,anchor: Anchor<'_>,records: &[Ancestor<'_>],phase: Phase) -> Result<()> {
        check_mapping(ctx,anchor,phase)?;
        for (index,record) in records.iter().enumerate() { check_one(ctx,state.slots[index],state.facts[index],record,Scope {phase,index:Some(index)})?; }
        check_mapping(ctx,anchor,phase)?; ctx.check(Operation::Validate,phase)
    }
    pub fn capture<'a>(ctx: &mut Context<'a>,state: &mut State<'a>) -> Result<()> {
        let initial=Scope {phase:Phase::Capture,index:None};
        if state.attempted { return Err(initial.error(Operation::Validate,Reason::Malformed)); }
        state.attempted=true;
        let arena=ctx.arena;
        let mut drive=[0u16;MAX_PATH_UNITS+1]; let length=known_folder(ctx,&mut drive,initial)?;
        let route=parse_drive_path(&drive[..length]).map_err(|e|initial.attach(e))?;
        let mut mapped=[0u16;50]; mapping(ctx,&drive[..length],&mut mapped,initial)?;
        let resolved=arena.path(&drive[..length]).map_err(|e|initial.attach(e))?;
        let mut storage=[MaybeUninit::<Ancestor<'a>>::uninit();MAX_ANCESTORS];
        let mut root_record: Option<Ancestor<'a>>=None;
        for index in 0..=route.component_count() {
            let scope=Scope {phase:Phase::Capture,index:Some(index)};
            let slot=if index==0 {open_root(ctx,&mapped,scope)?} else {
                let parent=unsafe {storage[index-1].assume_init_ref()};
                check_one(ctx,state.slots[index-1],state.facts[index-1],parent,Scope {phase:Phase::Capture,index:Some(index-1)})?;
                let name=route.component(index-1).ok_or_else(||scope.error(Operation::Validate,Reason::Malformed))?;
                open_child(ctx,state.slots[index-1],name,scope)?
            };
            state.slots[index]=slot;
            let observed=facts(ctx,slot,scope)?;
            if index!=0 && observed.volume!=state.facts[0].volume { return Err(scope.error(Operation::Validate,Reason::Policy)); }
            let mut path=[0u16;MAX_PATH_UNITS+1]; let mut native=[0u16;MAX_PATH_UNITS+1]; let mut expected=[0u16;MAX_PATH_UNITS+1];
            let plen=final_path(ctx,slot,VOLUME_NAME_GUID,&mut path,scope)?;
            let guid=parse_guid_path(&path[..plen]).map_err(|e|scope.attach(e))?;
            if guid.component_count()!=index { return Err(scope.error(Operation::Validate,Reason::Policy)); }
            let suffix=if index==0 {&[][..]} else {&drive[3..route.ranges[index-1].1]};
            let elen=joined(&mapped[..49],suffix,&mut expected,scope)?;
            equal_paths(ctx,&path[..plen],&expected[..elen],scope)?;
            let nlen=final_path(ctx,slot,VOLUME_NAME_NT,&mut native,scope)?;
            if let Some(root)=root_record {
                let elen=joined(root.native_path.utf16,suffix,&mut expected,scope)?;
                equal_paths(ctx,&native[..nlen],&expected[..elen],scope)?;
            } else {native_root(&native[..nlen],scope)?;}
            let owner_dacl=with_descriptor(ctx,slot,scope,|bytes|arena.bytes(bytes))?;
            let record=Ancestor {index:index as u32,path:arena.path(&path[..plen]).map_err(|e|scope.attach(e))?,native_path:arena.path(&native[..nlen]).map_err(|e|scope.attach(e))?,volume_serial64:observed.volume,file_id:observed.id,attributes:observed.attributes,reparse_tag:observed.tag,delete_pending:observed.pending,owner_dacl,policy_match:true};
            check_one(ctx,slot,observed,&record,scope)?;
            if index>0 { let parent=unsafe {storage[index-1].assume_init_ref()}; check_one(ctx,state.slots[index-1],state.facts[index-1],parent,Scope {phase:Phase::Capture,index:Some(index-1)})?; }
            state.facts[index]=observed; storage[index].write(record); state.count=index+1;
            if index==0 {root_record=Some(record);}
        }
        let root=root_record.ok_or_else(||initial.error(Operation::Validate,Reason::Malformed))?;
        // Each slot before count was written only after a complete record and
        // checked capture. The stack slice is copied before it can escape.
        let complete=unsafe {std::slice::from_raw_parts(storage.as_ptr().cast::<Ancestor<'a>>(),state.count)};
        let records=arena.slice(complete).map_err(|e|initial.attach(e))?;
        let anchor=Anchor {known_folder_id:FOLDER_ID,resolved_path:resolved,volume_guid:root.path,native_root:root.native_path,volume_serial64:state.facts[0].volume,filesystem_serial32:state.facts[0].serial32,filesystem:"NTFS",drive_type:3};
        check_parts(ctx,state,anchor,records,Phase::Capture)?;
        // No fallible operation separates publication of these complete records.
        state.anchor=Some(anchor); state.ancestors=Some(records); Ok(())
    }
    pub fn recheck(ctx: &mut Context<'_>,state: &State<'_>) -> Result<()> {
        let scope=Scope {phase:Phase::Recheck,index:None};
        let anchor=state.anchor.ok_or_else(||scope.error(Operation::Validate,Reason::Malformed))?;
        let records=state.ancestors.ok_or_else(||scope.error(Operation::Validate,Reason::Malformed))?;
        if records.len()!=state.count || records.is_empty() || records.len()>MAX_ANCESTORS { return Err(scope.error(Operation::Validate,Reason::Malformed)); }
        check_parts(ctx,state,anchor,records,Phase::Recheck)
    }
}

#[cfg(all(test,windows,target_arch="x86_64"))]
mod native_tests {
    use super::*;
    use crate::arena::{Arena,OUTPUT_CAPACITY,PRODUCTION_CAPACITY};
    use crate::process;
    use crate::windows::Context;

    #[test]
    fn fixed_route_private_native_capture_recheck_and_checked_cleanup() {
        // The runner separately enforces its disposable-host capacity floor.
        // No path, SID, file ID, token or descriptor is printed by this test.
        let arena=Arena::new(PRODUCTION_CAPACITY).unwrap();
        let _output=arena.output(OUTPUT_CAPACITY).unwrap();
        arena.copy_iter(128*1024,std::iter::repeat_n(0u8,128*1024)).unwrap();
        let mut ctx=Context::new(&arena);
        let mut process_state=process::State::new(); let mut directories=State::new();
        let mut stable_arena=false;
        let result=(|| {
            process::capture(&mut ctx,&mut process_state)?;
            capture(&mut ctx,&mut directories)?;
            let before=arena.used();
            recheck(&mut ctx,&directories)?;
            stable_arena=before==arena.used();
            process::recheck(&mut ctx,&process_state)
        })();
        if let Err(error)=result {ctx.errors.primary(error);}
        let _=ctx.finish_cleanup();
        assert!(result.is_ok(),"fixed read-only route refused: {:?}",result.err());
        assert!(stable_arena,"directory recheck must not allocate retained arena data");
        assert!(!ctx.errors.cleanup_failed());
        assert!(!ctx.errors.unrepresentable());
        assert!(directories.anchor.is_some());
        assert!(directories.ancestors.is_some_and(|records|!records.is_empty() && records.len()<=MAX_ANCESTORS));
    }
}
