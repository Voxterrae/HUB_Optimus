//! Dormant observations of two fixed Windows known-folder ancestor chains.
//! Ordered owner/DACL bytes, namespace and metadata equality confer no authority.
//! Equality is not atomic, trusted initial acquisition, effective access or ABA exclusion.
use crate::relative_ntfs::{self, DirectoryObservation, OsPathComponent};
use crate::security_descriptor::{self, OwnerDaclSnapshot};
use std::ptr::{null, null_mut};
use windows_sys::Win32::Foundation::{GetLastError, HANDLE};
use windows_sys::Win32::Storage::FileSystem::GetVolumeNameForVolumeMountPointW;
use windows_sys::core::{BOOL, GUID, HRESULT, PCWSTR, PWSTR};

// Exact private ABI/DLLs/constants from cached windows-sys 0.61.2:
// Win32/UI/Shell (SHGetKnownFolderPath, known-folder IDs), System/Com and
// Globalization. Link attributes mirror windows-link 0.2.1, including x86
// decoration only for compilation; known_folder still refuses non-64-bit use.
#[cfg_attr(
    target_arch = "x86",
    link(
        name = "shell32.dll",
        kind = "raw-dylib",
        modifiers = "+verbatim",
        import_name_type = "undecorated"
    )
)]
#[cfg_attr(
    not(target_arch = "x86"),
    link(name = "shell32.dll", kind = "raw-dylib", modifiers = "+verbatim")
)]
unsafe extern "system" {
    fn SHGetKnownFolderPath(
        rfid: *const GUID,
        dwflags: u32,
        htoken: HANDLE,
        ppszpath: *mut PWSTR,
    ) -> HRESULT;
}
#[cfg_attr(
    target_arch = "x86",
    link(
        name = "ole32.dll",
        kind = "raw-dylib",
        modifiers = "+verbatim",
        import_name_type = "undecorated"
    )
)]
#[cfg_attr(
    not(target_arch = "x86"),
    link(name = "ole32.dll", kind = "raw-dylib", modifiers = "+verbatim")
)]
unsafe extern "system" {
    fn CoInitializeEx(pvreserved: *const core::ffi::c_void, dwcoinit: u32) -> HRESULT;
    fn CoUninitialize();
}
#[cfg_attr(
    target_arch = "x86",
    link(
        name = "combase.dll",
        kind = "raw-dylib",
        modifiers = "+verbatim",
        import_name_type = "undecorated"
    )
)]
#[cfg_attr(
    not(target_arch = "x86"),
    link(name = "combase.dll", kind = "raw-dylib", modifiers = "+verbatim")
)]
unsafe extern "system" {
    fn CoTaskMemFree(pv: *const core::ffi::c_void);
}
#[cfg_attr(
    target_arch = "x86",
    link(
        name = "kernel32.dll",
        kind = "raw-dylib",
        modifiers = "+verbatim",
        import_name_type = "undecorated"
    )
)]
#[cfg_attr(
    not(target_arch = "x86"),
    link(name = "kernel32.dll", kind = "raw-dylib", modifiers = "+verbatim")
)]
unsafe extern "system" {
    fn CompareStringOrdinal(
        lpstring1: PCWSTR,
        cchcount1: i32,
        lpstring2: PCWSTR,
        cchcount2: i32,
        bignorecase: BOOL,
    ) -> i32;
}
const COINIT_MULTITHREADED: i32 = 0;
const CSTR_EQUAL: i32 = 2;
const FOLDERID_PROGRAM_DATA: GUID = GUID::from_u128(0x62ab5d82_fdc1_4dc3_a9dd_070d1d495d97);
const FOLDERID_PROGRAM_FILES: GUID = GUID::from_u128(0x905e63b6_c1bf_494e_b29c_65b732d3d21a);

const MAX_PATH_UNITS: usize = 32767;
const MAX_STEPS: usize = 128;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum PersonalAnchor {
    ProgramData,
    ProgramFiles,
}
#[derive(Debug)]
enum Failure {
    Denied(&'static str),
    Native(&'static str, u32),
    Relative(relative_ntfs::Error),
    Security(security_descriptor::Error),
}
#[derive(Debug)]
struct Error {
    step: Option<usize>,
    primary: Failure,
    cleanup: Vec<Failure>,
}
impl Error {
    fn at_step(mut self, index: usize) -> Self {
        self.step = Some(index);
        self
    }
    fn has_cleanup_failure(&self) -> bool {
        !self.cleanup.is_empty()
            || match &self.primary {
                Failure::Relative(e) => e.has_cleanup_failure(),
                Failure::Security(e) => e.has_cleanup_failure(),
                _ => false,
            }
    }
}
type Result<T> = std::result::Result<T, Error>;
fn error(primary: Failure) -> Error {
    Error {
        step: None,
        primary,
        cleanup: vec![],
    }
}
fn denied(reason: &'static str) -> Error {
    error(Failure::Denied(reason))
}
fn last(op: &'static str) -> Error {
    error(Failure::Native(op, unsafe { GetLastError() }))
}
impl From<relative_ntfs::Error> for Error {
    fn from(e: relative_ntfs::Error) -> Self {
        error(Failure::Relative(e))
    }
}
impl From<security_descriptor::Error> for Error {
    fn from(e: security_descriptor::Error) -> Self {
        error(Failure::Security(e))
    }
}
// Successful values passed here own no native resource requiring checked close.
fn finish<T>(result: Result<T>, cleanup: Result<()>) -> Result<T> {
    match (result, cleanup) {
        (r, Ok(())) => r,
        (Ok(_), Err(e)) => Err(e),
        (Err(mut e), Err(c)) => {
            e.cleanup.push(c.primary);
            e.cleanup.extend(c.cleanup);
            Err(e)
        }
    }
}
struct Release<F: FnOnce()>(Option<F>);
impl<F: FnOnce()> Drop for Release<F> {
    fn drop(&mut self) {
        if let Some(f) = self.0.take() {
            f();
        }
    }
}
fn initialized_com<T>(
    status: i32,
    body: impl FnOnce() -> Result<T>,
    uninitialize: impl FnOnce(),
) -> Result<T> {
    if status != 0 && status != 1 {
        return Err(error(Failure::Native("CoInitializeEx", status as u32)));
    }
    let _guard = Release(Some(uninitialize));
    body()
}
fn allocated_path<T>(
    status: i32,
    copy: impl FnOnce() -> Result<T>,
    free: impl FnOnce(),
) -> Result<T> {
    let _allocation = Release(Some(free));
    if status != 0 {
        return Err(error(Failure::Native(
            "SHGetKnownFolderPath",
            status as u32,
        )));
    }
    copy()
}
fn known_folder(anchor: PersonalAnchor) -> Result<Vec<u16>> {
    relative_ntfs::no_impersonation()?;
    if usize::BITS != 64 {
        return Err(denied("64-bit known-folder interpretation required"));
    }
    initialized_com(
        unsafe { CoInitializeEx(null(), COINIT_MULTITHREADED as u32) },
        || {
            let id = match anchor {
                PersonalAnchor::ProgramData => &FOLDERID_PROGRAM_DATA,
                PersonalAnchor::ProgramFiles => &FOLDERID_PROGRAM_FILES,
            };
            let mut raw = null_mut();
            let status = unsafe { SHGetKnownFolderPath(id, 0, null_mut(), &mut raw) };
            allocated_path(
                status,
                || {
                    if raw.is_null() {
                        return Err(denied("known-folder null output"));
                    }
                    let mut copied = Vec::new();
                    // Only OS-returned, NUL-terminated allocation reaches pointer reads.
                    // Pure malformed cases pass slices to parsing, never native getters.
                    for i in 0..=MAX_PATH_UNITS {
                        let unit = unsafe { *raw.add(i) };
                        if unit == 0 {
                            return Ok(copied);
                        }
                        if i == MAX_PATH_UNITS {
                            break;
                        }
                        copied.push(unit);
                    }
                    Err(denied("known-folder path bounds"))
                },
                || unsafe { CoTaskMemFree(raw.cast()) },
            )
        },
        || unsafe { CoUninitialize() },
    )
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct DrivePath {
    original: Vec<u16>,
    drive: Vec<u16>,
    components: Vec<OsPathComponent>,
}
fn parse_drive_path(units: &[u16]) -> Result<DrivePath> {
    if units.len() < 3
        || units.len() > MAX_PATH_UNITS
        || units[0] > 127
        || !(units[0] as u8).is_ascii_alphabetic()
        || units[1..3] != [58, 92]
    {
        return Err(denied("known-folder drive-root form"));
    }
    String::from_utf16(units).map_err(|_| denied("known-folder UTF16"))?;
    let components = components(&units[3..])?;
    Ok(DrivePath {
        original: units.to_vec(),
        drive: units[..3].iter().copied().chain(Some(0)).collect(),
        components,
    })
}
fn components(units: &[u16]) -> Result<Vec<OsPathComponent>> {
    if units.is_empty() {
        return Ok(vec![]);
    }
    let mut result = vec![];
    for part in units.split(|&c| c == 92) {
        if result.len() + 1 >= MAX_STEPS {
            return Err(denied("ancestor step bound"));
        }
        result.push(OsPathComponent::new(part)?);
    }
    Ok(result)
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct GuidPath {
    root: Vec<u16>,
    components: Vec<OsPathComponent>,
}
impl GuidPath {
    fn parse(units: &[u16]) -> Result<Self> {
        if !(49..=MAX_PATH_UNITS).contains(&units.len()) {
            return Err(denied("normalized GUID path bounds"));
        }
        let text = String::from_utf16(units).map_err(|_| denied("normalized GUID path UTF16"))?;
        if !text.starts_with(r"\\?\Volume{")
            || units[47..49] != [125, 92]
            || !units[11..47].iter().enumerate().all(|(i, &u)| {
                if [8, 13, 18, 23].contains(&i) {
                    u == 45
                } else {
                    u <= 127 && (u as u8).is_ascii_hexdigit()
                }
            })
        {
            return Err(denied("normalized volume GUID shape"));
        }
        Ok(Self {
            root: units[..49].to_vec(),
            components: components(&units[49..])?,
        })
    }
    fn append(&self, component: &OsPathComponent) -> Result<Self> {
        if self.components.len() + 1 >= MAX_STEPS {
            return Err(denied("ancestor step bound"));
        }
        let mut next = self.clone();
        next.components.push(component.clone());
        let length = next.root.len()
            + next
                .components
                .iter()
                .map(|c| c.units().len())
                .sum::<usize>()
            + next.components.len().saturating_sub(1);
        if length > MAX_PATH_UNITS {
            return Err(denied("normalized path bound"));
        }
        Ok(next)
    }
    fn agrees(&self, other: &Self) -> Result<()> {
        self.agrees_using(other, ordinal_equal)
    }
    fn agrees_using(
        &self,
        other: &Self,
        mut compare: impl FnMut(&[u16], &[u16]) -> Result<bool>,
    ) -> Result<()> {
        if self.components.len() != other.components.len() || !compare(&self.root, &other.root)? {
            return Err(denied("normalized path sequence mismatch"));
        }
        for (a, b) in self.components.iter().zip(&other.components) {
            if !compare(a.units(), b.units())? {
                return Err(denied("normalized path sequence mismatch"));
            }
        }
        Ok(())
    }
}
fn ordinal_equal(a: &[u16], b: &[u16]) -> Result<bool> {
    if a.is_empty() || b.is_empty() || a.len() > MAX_PATH_UNITS || b.len() > MAX_PATH_UNITS {
        return Err(denied("ordinal comparison bounds"));
    }
    let result =
        unsafe { CompareStringOrdinal(a.as_ptr(), a.len() as i32, b.as_ptr(), b.len() as i32, 1) };
    if result == 0 {
        return Err(last("CompareStringOrdinal"));
    }
    Ok(result == CSTR_EQUAL)
}
fn volume_mapping(drive: &[u16]) -> Result<GuidPath> {
    let mut mapped = [0u16; 50];
    if unsafe {
        GetVolumeNameForVolumeMountPointW(drive.as_ptr(), mapped.as_mut_ptr(), mapped.len() as u32)
    } == 0
    {
        return Err(last("GetVolumeNameForVolumeMountPointW"));
    }
    let end = mapped
        .iter()
        .position(|&u| u == 0)
        .ok_or_else(|| denied("mapped root termination"))?;
    let root = GuidPath::parse(&mapped[..end])?;
    if !root.components.is_empty() {
        return Err(denied("mapping is not a volume root"));
    }
    Ok(root)
}
#[derive(Clone)]
struct ResolvedAnchor {
    anchor: PersonalAnchor,
    path: DrivePath,
    volume: GuidPath,
}
impl ResolvedAnchor {
    fn resolve(anchor: PersonalAnchor) -> Result<Self> {
        let path = parse_drive_path(&known_folder(anchor)?)?;
        let volume = volume_mapping(&path.drive)?;
        Ok(Self {
            anchor,
            path,
            volume,
        })
    }
    fn recheck(&self) -> Result<()> {
        let now = Self::resolve(self.anchor)?;
        if self.path != now.path {
            return Err(denied("known-folder resolution changed"));
        }
        self.volume.agrees(&now.volume)
    }
}
struct RetainedStep {
    directory: DirectoryObservation,
    path: GuidPath,
    security: OwnerDaclSnapshot,
}
impl RetainedStep {
    fn capture(directory: DirectoryObservation, path: GuidPath) -> Result<Self> {
        let result = (|| {
            directory.recheck()?;
            path.agrees(&GuidPath::parse(&directory.normalized_path()?)?)?;
            let security = directory.security()?;
            directory.recheck()?;
            Ok(security)
        })();
        match result {
            Ok(security) => Ok(Self {
                directory,
                path,
                security,
            }),
            Err(e) => finish(Err(e), directory.close().map_err(Error::from)),
        }
    }
    fn recheck(&self) -> Result<()> {
        self.directory.recheck()?;
        self.path
            .agrees(&GuidPath::parse(&self.directory.normalized_path()?)?)?;
        if self.security != self.directory.security()? {
            return Err(denied("owner/DACL bytes changed"));
        }
        Ok(())
    }
}
struct ObservedAncestorChain {
    steps: Vec<RetainedStep>,
    source: Option<ResolvedAnchor>,
}
impl ObservedAncestorChain {
    fn observe(anchor: PersonalAnchor) -> Result<Self> {
        let source = ResolvedAnchor::resolve(anchor)?;
        let root: Vec<_> = source.volume.root.iter().copied().chain(Some(0)).collect();
        let directory =
            DirectoryObservation::open_volume(&root).map_err(|e| Error::from(e).at_step(0))?;
        Self::walk(
            directory,
            source.volume.clone(),
            &source.path.components.clone(),
            Some(source),
        )
    }
    fn walk(
        directory: DirectoryObservation,
        root: GuidPath,
        components: &[OsPathComponent],
        source: Option<ResolvedAnchor>,
    ) -> Result<Self> {
        let mut chain = Self {
            steps: vec![RetainedStep::capture(directory, root).map_err(|e| e.at_step(0))?],
            source,
        };
        let result = (|| {
            for component in components {
                chain.recheck_steps()?;
                let parent = chain.steps.last().unwrap();
                let expected = parent.path.append(component)?;
                let index = chain.steps.len();
                let child = parent
                    .directory
                    .child(component)
                    .map_err(|e| Error::from(e).at_step(index))?;
                chain
                    .steps
                    .push(RetainedStep::capture(child, expected).map_err(|e| e.at_step(index))?);
                chain.recheck_steps()?;
            }
            chain.recheck()
        })();
        match result {
            Ok(()) => Ok(chain),
            Err(e) => finish(Err(e), chain.close()),
        }
    }
    fn recheck_steps(&self) -> Result<()> {
        relative_ntfs::no_impersonation()?;
        for (index, step) in self.steps.iter().enumerate() {
            step.recheck().map_err(|e| e.at_step(index))?;
        }
        Ok(())
    }
    fn recheck(&self) -> Result<()> {
        self.recheck_steps()?;
        if let Some(source) = &self.source {
            source.recheck()?;
        }
        self.recheck_steps()
    }
    fn close(mut self) -> Result<()> {
        let mut result = Ok(());
        while let Some(step) = self.steps.pop() {
            result = finish(result, step.directory.close().map_err(Error::from));
        }
        result
    }
    #[cfg(test)]
    fn fixture(input: std::os::windows::io::OwnedHandle, names: &[&str]) -> Result<Self> {
        let directory = DirectoryObservation::fixture_input(input)?;
        let parsed = (|| {
            let root = GuidPath::parse(&directory.normalized_path()?)?;
            let components = names
                .iter()
                .map(|s| {
                    OsPathComponent::new(&s.encode_utf16().collect::<Vec<_>>()).map_err(Error::from)
                })
                .collect::<Result<Vec<_>>>()?;
            Ok((root, components))
        })();
        match parsed {
            Ok((root, components)) => Self::walk(directory, root, &components, None),
            Err(e) => finish(Err(e), directory.close().map_err(Error::from)),
        }
    }
}
impl Drop for ObservedAncestorChain {
    fn drop(&mut self) {
        // Best-effort fallback only. Explicit close is required for checked evidence.
        while let Some(step) = self.steps.pop() {
            let _ = step.directory.close();
        }
    }
}
#[cfg(test)]
mod tests;
