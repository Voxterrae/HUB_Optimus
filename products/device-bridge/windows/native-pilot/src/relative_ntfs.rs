//! Private existing-child metadata agreement, never authority or containment.
//!
//! Exactly one validated component is opened relative to a retained directory:
//! OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE (never OBJ_INHERIT), FILE_OPEN,
//! FILE_SYNCHRONOUS_IO_NONALERT | FILE_OPEN_REPARSE_POINT; no type/backup flags.
//! Access is READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE. Sharing is READ |
//! DELETE, deliberately not WRITE. This does not freeze namespace membership or
//! prevent attribute/reparse mutation. Every reparse tag/attribute is rejected.
//!
//! A live independent expectation is mandatory and remains borrowed by every
//! result, including stepped directory conversion. IDs express agreement with
//! an observed object, not an authorized parent/name or traversal history.
//! Pre/post snapshots cannot detect ABA. No content operation or raw handle
//! export exists. Unexpected pending native work aborts with ABI storage live;
//! terminal failures retain NTSTATUS and IOSB separately. There is no fallback.
use std::os::windows::io::{AsRawHandle, FromRawHandle, IntoRawHandle, OwnedHandle};
use std::ptr::{null, null_mut};
use windows_sys::Wdk::Foundation::OBJECT_ATTRIBUTES;
use windows_sys::Wdk::Storage::FileSystem as nt;
use windows_sys::Win32::Foundation::*;
use windows_sys::Win32::Security::TOKEN_QUERY;
use windows_sys::Win32::Storage::FileSystem::*;
use windows_sys::Win32::System::IO::IO_STATUS_BLOCK;
use windows_sys::Win32::System::Threading::*;

const METADATA_RIGHTS: u32 = 0x0012_0080;
const UNWRITTEN: i32 = 0xc000_0001_u32 as i32;
const UNWRITTEN_INFO: usize = usize::MAX;
const MAX_PATH_UNITS: usize = 32767;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Completion {
    call: i32,
    io: i32,
    information: usize,
}
#[derive(Debug, PartialEq, Eq)]
enum Failure {
    Native(&'static str, u32),
    Completion(&'static str, Completion),
    Denied(&'static str),
    IdentityMismatch {
        expected: (u64, [u8; 16]),
        observed: (u64, [u8; 16]),
    },
}
#[derive(Debug, PartialEq, Eq)]
pub(super) struct Error {
    primary: Failure,
    cleanup: Vec<Failure>,
}
impl Error {
    pub(super) fn has_cleanup_failure(&self) -> bool {
        !self.cleanup.is_empty() || matches!(self.primary, Failure::Native("CloseHandle", _))
    }
}
type Result<T> = std::result::Result<T, Error>;
fn failure(primary: Failure) -> Error {
    Error {
        primary,
        cleanup: vec![],
    }
}
fn denial(reason: &'static str) -> Error {
    failure(Failure::Denied(reason))
}
fn last(op: &'static str) -> Error {
    failure(Failure::Native(op, unsafe { GetLastError() }))
}
// Success values used with finish own no unclosed native resource.
fn finish<T>(r: Result<T>, c: Result<()>) -> Result<T> {
    match (r, c) {
        (r, Ok(())) => r,
        (Ok(_), Err(e)) => Err(e),
        (Err(mut e), Err(c)) => {
            e.cleanup.push(c.primary);
            e.cleanup.extend(c.cleanup);
            Err(e)
        }
    }
}
fn close(h: OwnedHandle) -> Result<()> {
    if unsafe { CloseHandle(h.into_raw_handle()) } == 0 {
        Err(last("CloseHandle"))
    } else {
        Ok(())
    }
}
pub(super) fn no_impersonation() -> Result<()> {
    let mut raw = null_mut();
    if unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut raw) } != 0 {
        if raw.is_null() || raw == INVALID_HANDLE_VALUE {
            return Err(denial("invalid thread token output"));
        }
        return finish(
            Err(denial("calling-thread impersonation")),
            close(unsafe { OwnedHandle::from_raw_handle(raw) }),
        );
    }
    let code = unsafe { GetLastError() };
    if code == ERROR_NO_TOKEN {
        Ok(())
    } else {
        Err(failure(Failure::Native("OpenThreadToken", code)))
    }
}
#[derive(Debug, PartialEq, Eq)]
enum CompletionClass {
    Complete,
    Reject,
    FatalPending,
}
fn classify(c: Completion, expected_information: usize, valid: bool) -> CompletionClass {
    if c.call == STATUS_PENDING
        || c.io == STATUS_PENDING
        || (c.call >= 0 && c.io == UNWRITTEN && c.information == UNWRITTEN_INFO)
    {
        return CompletionClass::FatalPending;
    }
    if c.call == STATUS_SUCCESS
        && c.io == STATUS_SUCCESS
        && c.information == expected_information
        && valid
    {
        CompletionClass::Complete
    } else {
        CompletionClass::Reject
    }
}
fn initial_iosb() -> IO_STATUS_BLOCK {
    let mut io = IO_STATUS_BLOCK::default();
    io.Anonymous.Status = UNWRITTEN;
    io.Information = UNWRITTEN_INFO;
    io
}
fn completion(call: i32, io: &IO_STATUS_BLOCK) -> Completion {
    Completion {
        call,
        io: unsafe { io.Anonymous.Status },
        information: io.Information,
    }
}
fn abort_pending(_op: &str, _c: Completion) -> ! {
    // No formatting, fallible logging, unwinding, cancellation, handle close or
    // destructor may intervene while the kernel might still own these buffers.
    std::process::abort()
}
fn granted_access(h: HANDLE) -> Result<u32> {
    let mut access = nt::FILE_ACCESS_INFORMATION::default();
    let mut io = initial_iosb();
    let call = unsafe {
        nt::NtQueryInformationFile(
            h,
            &mut io,
            (&mut access as *mut nt::FILE_ACCESS_INFORMATION).cast(),
            size_of::<nt::FILE_ACCESS_INFORMATION>() as u32,
            nt::FileAccessInformation,
        )
    };
    let c = completion(call, &io);
    match classify(c, size_of::<nt::FILE_ACCESS_INFORMATION>(), true) {
        CompletionClass::FatalPending => abort_pending("NtQueryInformationFile", c),
        CompletionClass::Reject => Err(failure(Failure::Completion("NtQueryInformationFile", c))),
        CompletionClass::Complete => Ok(access.AccessFlags),
    }
}
fn duplicate_down(input: OwnedHandle) -> Result<OwnedHandle> {
    let result = (|| {
        no_impersonation()?;
        if granted_access(input.as_raw_handle())? & METADATA_RIGHTS != METADATA_RIGHTS {
            return Err(denial("input lacks metadata rights"));
        }
        let mut raw = null_mut();
        if unsafe {
            DuplicateHandle(
                GetCurrentProcess(),
                input.as_raw_handle(),
                GetCurrentProcess(),
                &mut raw,
                METADATA_RIGHTS,
                0,
                0,
            )
        } == 0
        {
            return Err(last("DuplicateHandle"));
        }
        if raw.is_null() || raw == INVALID_HANDLE_VALUE {
            return Err(denial("invalid duplicate output"));
        }
        let handle = unsafe { OwnedHandle::from_raw_handle(raw) };
        let checked = (|| {
            let mut flags = 0;
            if unsafe { GetHandleInformation(raw, &mut flags) } == 0 {
                return Err(last("GetHandleInformation"));
            }
            if flags & HANDLE_FLAG_INHERIT != 0 || granted_access(raw)? != METADATA_RIGHTS {
                return Err(denial("duplicate rights or inheritance"));
            }
            Ok(())
        })();
        match checked {
            Ok(()) => Ok(handle),
            Err(e) => finish(Err(e), close(handle)),
        }
    })();
    let closed = close(input);
    match (result, closed) {
        (Ok(h), Ok(())) => Ok(h),
        (Ok(h), Err(e)) => finish(Err(e), close(h)),
        (Err(e), c) => finish(Err(e), c),
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum ExpectedKind {
    File,
    Directory,
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct Facts {
    volume: u64,
    id: [u8; 16],
    kind: ExpectedKind,
    attributes: u32,
    tag: u32,
    links: u32,
    pending: bool,
    size: i64,
    allocated: i64,
}
impl Facts {
    fn identity(&self) -> (u64, [u8; 16]) {
        (self.volume, self.id)
    }
}
fn facts(h: HANDLE) -> Result<Facts> {
    let mut id = FILE_ID_INFO::default();
    let mut standard = FILE_STANDARD_INFO::default();
    let mut tag = FILE_ATTRIBUTE_TAG_INFO::default();
    for (class, ptr, len) in [
        (
            FileIdInfo,
            (&mut id as *mut FILE_ID_INFO).cast(),
            size_of::<FILE_ID_INFO>(),
        ),
        (
            FileStandardInfo,
            (&mut standard as *mut FILE_STANDARD_INFO).cast(),
            size_of::<FILE_STANDARD_INFO>(),
        ),
        (
            FileAttributeTagInfo,
            (&mut tag as *mut FILE_ATTRIBUTE_TAG_INFO).cast(),
            size_of::<FILE_ATTRIBUTE_TAG_INFO>(),
        ),
    ] {
        if unsafe { GetFileInformationByHandleEx(h, class, ptr, len as u32) } == 0 {
            return Err(last("GetFileInformationByHandleEx"));
        }
    }
    Ok(Facts {
        volume: id.VolumeSerialNumber,
        id: id.FileId.Identifier,
        kind: if standard.Directory {
            ExpectedKind::Directory
        } else {
            ExpectedKind::File
        },
        attributes: tag.FileAttributes,
        tag: tag.ReparseTag,
        links: standard.NumberOfLinks,
        pending: standard.DeletePending,
        size: standard.EndOfFile,
        allocated: standard.AllocationSize,
    })
}
fn validate(f: &Facts, kind: ExpectedKind, volume: Option<u64>) -> Result<()> {
    if f.tag != 0 || f.attributes & FILE_ATTRIBUTE_REPARSE_POINT != 0 {
        return Err(denial("reparse metadata"));
    }
    if f.kind != kind
        || (f.attributes & FILE_ATTRIBUTE_DIRECTORY != 0) != (f.kind == ExpectedKind::Directory)
    {
        return Err(denial("object type"));
    }
    if f.pending {
        return Err(denial("delete pending"));
    }
    if kind == ExpectedKind::File && f.links != 1 {
        return Err(denial("regular file links"));
    }
    if f.size < 0 || f.allocated < 0 {
        return Err(denial("negative size"));
    }
    if volume.is_some_and(|v| v != f.volume) {
        return Err(denial("volume mismatch"));
    }
    Ok(())
}
fn volume_root(path: &[u16], length: usize) -> Result<Vec<u16>> {
    if length == 0 || length > MAX_PATH_UNITS || length >= path.len() || path[length] != 0 {
        return Err(denial("final path bounds"));
    }
    let text = String::from_utf16(&path[..length]).map_err(|_| denial("final path UTF16"))?;
    let prefix = r"\\?\Volume{";
    if !text.starts_with(prefix) {
        return Err(denial("not a local volume GUID path"));
    }
    let end = text
        .find("}\\")
        .ok_or_else(|| denial("volume GUID terminator"))?;
    if end != prefix.len() + 36 {
        return Err(denial("volume GUID length"));
    }
    let guid = &text[prefix.len()..end];
    if !guid.bytes().enumerate().all(|(i, b)| {
        if [8, 13, 18, 23].contains(&i) {
            b == b'-'
        } else {
            b.is_ascii_hexdigit()
        }
    }) {
        return Err(denial("volume GUID shape"));
    }
    Ok(text[..end + 2].encode_utf16().chain(Some(0)).collect())
}
fn local_ntfs(h: HANDLE) -> Result<()> {
    if unsafe { GetFileType(h) } != FILE_TYPE_DISK {
        return Err(denial("not disk storage"));
    }
    let mut fs = [0u16; 32];
    if unsafe {
        GetVolumeInformationByHandleW(
            h,
            null_mut(),
            0,
            null_mut(),
            null_mut(),
            null_mut(),
            fs.as_mut_ptr(),
            fs.len() as u32,
        )
    } == 0
    {
        return Err(last("GetVolumeInformationByHandleW"));
    }
    if fs[..5] != [78, 84, 70, 83, 0] {
        return Err(denial("not NTFS"));
    }
    let mut path = vec![0u16; MAX_PATH_UNITS + 1];
    let length = unsafe {
        GetFinalPathNameByHandleW(
            h,
            path.as_mut_ptr(),
            path.len() as u32,
            VOLUME_NAME_GUID | FILE_NAME_NORMALIZED,
        )
    } as usize;
    if length == 0 {
        return Err(last("GetFinalPathNameByHandleW"));
    }
    let root = volume_root(&path, length)?;
    if unsafe { GetDriveTypeW(root.as_ptr()) } != 3 {
        return Err(denial("not a local fixed volume"));
    }
    // Solely a drive-type observation: never reopened, never prefix containment.
    Ok(())
}
fn unicode_bytes(units: usize) -> Result<u16> {
    units
        .checked_mul(2)
        .and_then(|n| u16::try_from(n).ok())
        .ok_or_else(|| denial("UNICODE_STRING length"))
}
struct InternalComponent(Vec<u16>);
impl InternalComponent {
    fn new(s: &'static str) -> Result<Self> {
        if s.is_empty()
            || s.len() > 64
            || !s
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b"_-.".contains(&b))
            || s.starts_with('.')
            || s.ends_with('.')
            || s.contains("..")
        {
            return Err(denial("component shape"));
        }
        let base = s.split('.').next().unwrap_or("").to_ascii_uppercase();
        if ["CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"].contains(&base.as_str())
            || (base.len() == 4
                && (base.starts_with("COM") || base.starts_with("LPT"))
                && matches!(base.as_bytes()[3], b'1'..=b'9'))
        {
            return Err(denial("DOS basename"));
        }
        let encoded: Vec<u16> = s.encode_utf16().collect();
        unicode_bytes(encoded.len())?;
        Ok(Self(encoded))
    }
}
struct Observation {
    handle: OwnedHandle,
    original: Facts,
}
impl Observation {
    fn capture(input: OwnedHandle, kind: Option<ExpectedKind>) -> Result<Self> {
        let handle = duplicate_down(input)?;
        let checked = (|| {
            local_ntfs(handle.as_raw_handle())?;
            let f = facts(handle.as_raw_handle())?;
            validate(&f, kind.unwrap_or(f.kind), None)?;
            Ok(f)
        })();
        match checked {
            Ok(original) => Ok(Self { handle, original }),
            Err(e) => finish(Err(e), close(handle)),
        }
    }
    fn recheck(&self) -> Result<()> {
        no_impersonation()?;
        local_ntfs(self.handle.as_raw_handle())?;
        let now = facts(self.handle.as_raw_handle())?;
        validate(&now, self.original.kind, Some(self.original.volume))?;
        if now != self.original {
            return Err(denial("observed metadata changed"));
        }
        Ok(())
    }
    fn close(self) -> Result<()> {
        close(self.handle)
    }
}
struct ObservedDirectory<'a> {
    observed: Observation,
    expectation: Option<&'a HeldObjectExpectation>,
}
impl ObservedDirectory<'static> {
    fn capture(h: OwnedHandle) -> Result<Self> {
        Ok(Self {
            observed: Observation::capture(h, Some(ExpectedKind::Directory))?,
            expectation: None,
        })
    }
}
impl ObservedDirectory<'_> {
    fn recheck(&self) -> Result<()> {
        finish(
            self.observed.recheck(),
            self.expectation
                .map_or(Ok(()), HeldObjectExpectation::recheck),
        )
    }
    fn close(self) -> Result<()> {
        self.observed.close()
    }
}
struct HeldObjectExpectation {
    observed: Observation,
}
impl HeldObjectExpectation {
    fn capture(h: OwnedHandle) -> Result<Self> {
        Ok(Self {
            observed: Observation::capture(h, None)?,
        })
    }
    fn recheck(&self) -> Result<()> {
        self.observed.recheck()
    }
    fn close(self) -> Result<()> {
        self.observed.close()
    }
}
struct HeldChildMetadata<'a> {
    observed: Observation,
    expectation: &'a HeldObjectExpectation,
}
impl<'a> HeldChildMetadata<'a> {
    fn recheck(&self) -> Result<()> {
        finish(self.observed.recheck(), self.expectation.recheck())
    }
    fn into_directory(self) -> Result<ObservedDirectory<'a>> {
        let checked = self
            .recheck()
            .and_then(|()| validate(&self.observed.original, ExpectedKind::Directory, None));
        match checked {
            Ok(()) => Ok(ObservedDirectory {
                observed: self.observed,
                expectation: Some(self.expectation),
            }),
            Err(e) => finish(Err(e), self.close()),
        }
    }
    fn close(self) -> Result<()> {
        self.observed.close()
    }
}
fn native_open(
    parent: &ObservedDirectory<'_>,
    component: &InternalComponent,
) -> Result<OwnedHandle> {
    native_open_units(&parent.observed, &component.0)
}
fn native_open_units(parent: &Observation, component: &[u16]) -> Result<OwnedHandle> {
    let mut name = component.to_vec();
    let bytes = unicode_bytes(name.len())?;
    let unicode = UNICODE_STRING {
        Length: bytes,
        MaximumLength: bytes,
        Buffer: name.as_mut_ptr(),
    };
    let attributes = OBJECT_ATTRIBUTES {
        Length: size_of::<OBJECT_ATTRIBUTES>() as u32,
        RootDirectory: parent.handle.as_raw_handle(),
        ObjectName: &unicode,
        Attributes: OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE,
        SecurityDescriptor: null(),
        SecurityQualityOfService: null(),
    };
    let mut io = initial_iosb();
    let mut raw = null_mut();
    let call = unsafe {
        nt::NtCreateFile(
            &mut raw,
            METADATA_RIGHTS,
            &attributes,
            &mut io,
            null(),
            0,
            FILE_SHARE_READ | FILE_SHARE_DELETE,
            nt::FILE_OPEN,
            nt::FILE_SYNCHRONOUS_IO_NONALERT | nt::FILE_OPEN_REPARSE_POINT,
            null(),
            0,
        )
    };
    let c = completion(call, &io);
    let valid = !raw.is_null() && raw != INVALID_HANDLE_VALUE;
    match classify(c, 1, valid) {
        // FILE_OPENED=1, never CREATED/OVERWRITTEN.
        CompletionClass::FatalPending => abort_pending("NtCreateFile", c),
        CompletionClass::Complete => Ok(unsafe { OwnedHandle::from_raw_handle(raw) }),
        CompletionClass::Reject => {
            let error = Err(failure(Failure::Completion("NtCreateFile", c)));
            if valid {
                finish(error, close(unsafe { OwnedHandle::from_raw_handle(raw) }))
            } else {
                error
            }
        }
    }
}
fn open_matching_child_metadata<'a>(
    parent: &ObservedDirectory<'_>,
    component: &InternalComponent,
    kind: ExpectedKind,
    expected: &'a HeldObjectExpectation,
) -> Result<HeldChildMetadata<'a>> {
    open_inner(parent, component, kind, expected, || Ok(()))
}
// Private deterministic precheck/native-call test hook; production uses a no-op.
fn open_inner<'a>(
    parent: &ObservedDirectory<'_>,
    component: &InternalComponent,
    kind: ExpectedKind,
    expected: &'a HeldObjectExpectation,
    after_precheck: impl FnOnce() -> Result<()>,
) -> Result<HeldChildMetadata<'a>> {
    parent.recheck()?;
    expected.recheck()?;
    after_precheck()?;
    let opened = native_open(parent, component);
    let mut retained = None;
    let observed = opened.and_then(|h| {
        retained = Some(h);
        let raw = retained.as_ref().unwrap().as_raw_handle();
        local_ntfs(raw)?;
        let f = facts(raw)?;
        validate(&f, kind, Some(parent.observed.original.volume))?;
        if f.identity() != expected.observed.original.identity() {
            return Err(failure(Failure::IdentityMismatch {
                expected: expected.observed.original.identity(),
                observed: f.identity(),
            }));
        }
        Ok(f)
    });
    let checked = finish(finish(observed, parent.recheck()), expected.recheck());
    match checked {
        Ok(original) => Ok(HeldChildMetadata {
            observed: Observation {
                handle: retained.unwrap(),
                original,
            },
            expectation: expected,
        }),
        Err(e) => {
            if let Some(h) = retained {
                finish(Err(e), close(h))
            } else {
                Err(e)
            }
        }
    }
}
// Separate observation-only sibling surface. It has no independently expected
// identity and cannot produce HeldChildMetadata or a protected root.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct OsPathComponent(Vec<u16>);
impl OsPathComponent {
    pub(super) fn new(units: &[u16]) -> Result<Self> {
        if units.is_empty() || units.len() > 255 {
            return Err(denial("OS component bounds"));
        }
        let text = String::from_utf16(units).map_err(|_| denial("OS component UTF16"))?;
        if text == "."
            || text == ".."
            || text.ends_with(['.', ' '])
            || text.chars().any(|c| c < ' ' || "\\/:*?\"<>|~".contains(c))
        {
            return Err(denial("OS component shape"));
        }
        let base = text.split('.').next().unwrap_or("").to_ascii_uppercase();
        let numbered = base
            .strip_prefix("COM")
            .or_else(|| base.strip_prefix("LPT"));
        if ["CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"].contains(&base.as_str())
            || numbered.is_some_and(|n| {
                matches!(
                    n,
                    "1" | "2"
                        | "3"
                        | "4"
                        | "5"
                        | "6"
                        | "7"
                        | "8"
                        | "9"
                        | "\u{b9}"
                        | "\u{b2}"
                        | "\u{b3}"
                )
            })
        {
            return Err(denial("OS DOS basename"));
        }
        unicode_bytes(units.len())?;
        Ok(Self(units.to_vec()))
    }
    pub(super) fn units(&self) -> &[u16] {
        &self.0
    }
}

pub(super) struct DirectoryObservation(Observation);
impl DirectoryObservation {
    pub(super) fn open_volume(root: &[u16]) -> Result<Self> {
        no_impersonation()?;
        let generated = volume_root(root, root.len().saturating_sub(1))?;
        if generated != root {
            return Err(denial("exact volume GUID root required"));
        }
        let raw = unsafe {
            CreateFileW(
                root.as_ptr(),
                METADATA_RIGHTS,
                FILE_SHARE_READ | FILE_SHARE_DELETE,
                null(),
                OPEN_EXISTING,
                FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
                null_mut(),
            )
        };
        if raw == INVALID_HANDLE_VALUE {
            return Err(last("CreateFileW volume root"));
        }
        Self::capture(unsafe { OwnedHandle::from_raw_handle(raw) })
    }
    fn capture(input: OwnedHandle) -> Result<Self> {
        Observation::capture(input, Some(ExpectedKind::Directory)).map(Self)
    }
    #[cfg(test)]
    pub(super) fn fixture_input(input: OwnedHandle) -> Result<Self> {
        Self::capture(input)
    }
    pub(super) fn child(&self, component: &OsPathComponent) -> Result<Self> {
        self.recheck()?;
        let mut retained = None;
        let result = native_open_units(&self.0, component.units()).and_then(|h| {
            let observed = Self::capture(h)?;
            retained = Some(observed);
            validate(
                &retained.as_ref().unwrap().0.original,
                ExpectedKind::Directory,
                Some(self.0.original.volume),
            )
        });
        let checked = finish(result, self.recheck());
        match checked {
            Ok(()) => Ok(retained.unwrap()),
            Err(e) => match retained {
                Some(v) => finish(Err(e), v.close()),
                None => Err(e),
            },
        }
    }
    pub(super) fn recheck(&self) -> Result<()> {
        self.0.recheck()
    }
    pub(super) fn close(self) -> Result<()> {
        self.0.close()
    }
    pub(super) fn security(
        &self,
    ) -> std::result::Result<
        crate::security_descriptor::OwnerDaclSnapshot,
        crate::security_descriptor::Error,
    > {
        crate::security_descriptor::observe_owner_dacl(&self.0.handle)
    }
    pub(super) fn normalized_path(&self) -> Result<Vec<u16>> {
        let mut buffer = vec![0; MAX_PATH_UNITS + 1];
        let length = unsafe {
            GetFinalPathNameByHandleW(
                self.0.handle.as_raw_handle(),
                buffer.as_mut_ptr(),
                buffer.len() as u32,
                VOLUME_NAME_GUID | FILE_NAME_NORMALIZED,
            )
        } as usize;
        if length == 0 {
            return Err(last("GetFinalPathNameByHandleW"));
        }
        volume_root(&buffer, length)?;
        buffer.truncate(length);
        Ok(buffer)
    }
    #[cfg(test)]
    pub(super) fn exact_rights_live(&self) -> Result<()> {
        let mut flags = 0;
        if unsafe { GetHandleInformation(self.0.handle.as_raw_handle(), &mut flags) } == 0 {
            return Err(last("GetHandleInformation"));
        }
        if flags & HANDLE_FLAG_INHERIT != 0
            || granted_access(self.0.handle.as_raw_handle())? != METADATA_RIGHTS
        {
            return Err(denial("observation rights or inheritance"));
        }
        self.recheck()
    }
}
#[cfg(test)]
pub(super) mod tests;
