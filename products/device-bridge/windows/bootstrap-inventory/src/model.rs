//! Diagnostic data only. None of these values is authority or a live capability.
macro_rules! names {
    ($name:ident { $($variant:ident => $text:literal),+ $(,)? }) => {
        #[derive(Clone, Copy, Debug, PartialEq, Eq)]
        pub enum $name { $($variant),+ }
        impl $name { pub const fn as_str(self) -> &'static str { match self { $(Self::$variant => $text),+ } } }
    };
}
names!(Kind { Primary=>"primary", Cleanup=>"cleanup", Receipt=>"receipt" });
names!(Phase { Initial=>"initial", Capture=>"capture", Recheck=>"recheck", Cleanup=>"cleanup", Serialize=>"serialize" });
names!(Domain { Win32=>"win32", Hresult=>"hresult", Ntstatus=>"ntstatus", Internal=>"internal" });
names!(Reason { Unsupported=>"unsupported", Malformed=>"malformed", Bound=>"bound", Policy=>"policy", Impersonation=>"impersonation", AppContainer=>"app_container", TokenChanged=>"token_changed", Drift=>"drift", Budget=>"budget", ReceiptBound=>"receipt_bound" });
names!(Operation {
 DuplicateHandle=>"DuplicateHandle", GetHandleInformation=>"GetHandleInformation",
 GetProcessId=>"GetProcessId", GetProcessTimes=>"GetProcessTimes", QueryFullProcessImageNameW=>"QueryFullProcessImageNameW", IsWow64Process2=>"IsWow64Process2",
 OpenProcessToken=>"OpenProcessToken", OpenThreadToken=>"OpenThreadToken", GetTokenInformation=>"GetTokenInformation",
 CoInitializeEx=>"CoInitializeEx", SHGetKnownFolderPath=>"SHGetKnownFolderPath", CreateFileW=>"CreateFileW", NtCreateFile=>"NtCreateFile", NtQueryInformationFile=>"NtQueryInformationFile",
 GetFileInformationByHandleEx=>"GetFileInformationByHandleEx", GetFileType=>"GetFileType", GetVolumeInformationByHandleW=>"GetVolumeInformationByHandleW", GetFinalPathNameByHandleW=>"GetFinalPathNameByHandleW",
 GetVolumeNameForVolumeMountPointW=>"GetVolumeNameForVolumeMountPointW", GetDriveTypeW=>"GetDriveTypeW", GetSecurityInfo=>"GetSecurityInfo", LookupPrivilegeNameW=>"LookupPrivilegeNameW", CompareStringOrdinal=>"CompareStringOrdinal",
 CloseHandle=>"CloseHandle", LocalFree=>"LocalFree", Validate=>"validate", Serialize=>"serialize"
});
names!(ThreadContext { NoToken=>"no_token", Present=>"present", Unknown=>"unknown" });
names!(Recheck { Equal=>"equal", Changed=>"changed", NotCompleted=>"not_completed" });
names!(Cleanup { Complete=>"complete", Failed=>"failed" });
names!(Outcome { Observed=>"observed", Refused=>"refused" });
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Completion { pub call:u32, pub io_status:u32, pub information:u64 }
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Error {
 pub kind:Kind, pub phase:Phase, pub operation:Operation, pub domain:Domain,
 pub code:Option<u32>, pub reason:Option<Reason>, pub ancestor_index:Option<u32>, pub completion:Option<Completion>
}
impl Error {
 pub const fn internal(phase:Phase, operation:Operation, reason:Reason)->Self { Self {kind:Kind::Primary,phase,operation,domain:Domain::Internal,code:None,reason:Some(reason),ancestor_index:None,completion:None} }
 pub const fn native(phase:Phase, operation:Operation, domain:Domain,code:u32)->Self { Self {kind:Kind::Primary,phase,operation,domain,code:Some(code),reason:None,ancestor_index:None,completion:None} }
 pub fn at(mut self,index:usize)->Self { self.ancestor_index=Some(index as u32); self }
}
pub type Result<T> = std::result::Result<T,Error>;
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Path<'a> { pub text:&'a str, pub utf16:&'a [u16] }
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Luid { pub low:u32, pub high:i32 }
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct SidAttributes<'a> { pub sid:&'a [u8], pub attributes:u32 }
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Privilege<'a> { pub luid:Luid, pub name:&'a str, pub attributes:u32 }
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Token<'a> {
 pub token_type:u32, pub impersonation_level:Option<u32>,
 pub user:&'a[u8], pub owner:&'a[u8], pub primary_group:&'a[u8], pub integrity:SidAttributes<'a>,
 pub groups:&'a[SidAttributes<'a>], pub restricted_sids:&'a[SidAttributes<'a>], pub capabilities:&'a[SidAttributes<'a>], pub privileges:&'a[Privilege<'a>],
 pub token_id:Luid, pub authentication_id:Luid, pub modified_id:Luid,
 pub session_id:u32, pub elevation_type:u32, pub elevation:u32, pub has_restrictions:u32, pub is_app_container:u32,
 pub mandatory_policy:u32, pub ui_access:u32, pub virtualization_allowed:u32, pub virtualization_enabled:u32
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Process<'a> { pub pid:u32, pub creation_utc:u64, pub process_machine:u16, pub native_machine:u16, pub image_win32:Path<'a>, pub image_native:Path<'a> }
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Anchor<'a> {
 pub known_folder_id:&'a str, pub resolved_path:Path<'a>, pub volume_guid:Path<'a>, pub native_root:Path<'a>,
 pub volume_serial64:u64, pub filesystem_serial32:u32, pub filesystem:&'a str, pub drive_type:u32
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Ancestor<'a> {
 pub index:u32, pub path:Path<'a>, pub native_path:Path<'a>, pub volume_serial64:u64, pub file_id:[u8;16],
 pub attributes:u32, pub reparse_tag:u32, pub delete_pending:bool, pub owner_dacl:&'a[u8], pub policy_match:bool
}
#[derive(Clone, Copy)]
pub struct Stamp<'a> { pub source_commit:&'a str, pub policy_sha256:&'a str, pub target:&'a str }
pub struct Receipt<'a> {
 pub outcome:Outcome, pub collector:Stamp<'a>, pub started_utc:u64, pub finished_utc:u64, pub elapsed_ms:u64,
 pub process:Option<Process<'a>>, pub primary_token:Option<Token<'a>>, pub thread_token:Option<Token<'a>>,
 pub thread_context:ThreadContext, pub anchor:Option<Anchor<'a>>, pub ancestors:Option<&'a[Ancestor<'a>]>,
 pub recheck:Recheck, pub errors:&'a[Error], pub cleanup:Cleanup
}
