//! Task-owned native fixtures. Assertions follow explicit checked cleanup.
use super::*;
use std::collections::BTreeMap;
use std::panic::{AssertUnwindSafe, catch_unwind};
use std::path::{Path, PathBuf};
use std::sync::{
    Arc,
    atomic::{AtomicBool, AtomicUsize, Ordering},
    mpsc,
};
use std::time::{Duration, Instant};
use windows_sys::Win32::Security::Cryptography::*;
use windows_sys::Win32::System::IO::DeviceIoControl;
const MOUNT_TAG: u32 = 0xa0000003;
const SET_REPARSE: u32 = 0x000900a4;
const DELETE_REPARSE: u32 = 0x000900ac;
fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(Some(0)).collect()
}
fn require(ok: bool, reason: &'static str) -> Result<()> {
    if ok { Ok(()) } else { Err(denial(reason)) }
}
fn cleanup_identity_check(
    observed: Result<Facts>,
    original: Option<&Facts>,
    blocked: bool,
) -> Result<()> {
    let observed = observed?;
    let valid = original.is_some_and(|o| {
        observed.identity() == o.identity()
            && observed.kind == o.kind
            && observed.tag == 0
            && observed.attributes & FILE_ATTRIBUTE_REPARSE_POINT == 0
    }) && !blocked;
    require(valid, "fixture cleanup identity/tag/dependency refusal")
}
fn open_fixture(path: &Path, rights: u32) -> Result<OwnedHandle> {
    let h = unsafe {
        CreateFileW(
            wide(path.to_str().ok_or_else(|| denial("fixture UTF16"))?).as_ptr(),
            rights,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            null(),
            OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
            null_mut(),
        )
    };
    if h == INVALID_HANDLE_VALUE {
        Err(last("fixture open"))
    } else {
        Ok(unsafe { OwnedHandle::from_raw_handle(h) })
    }
}
fn hash(bytes: &[u8]) -> Result<[u8; 32]> {
    let mut alg = null_mut();
    let status =
        unsafe { BCryptOpenAlgorithmProvider(&mut alg, BCRYPT_SHA256_ALGORITHM, null(), 0) };
    if status != 0 {
        return Err(failure(Failure::Native(
            "fixture BCryptOpen",
            status as u32,
        )));
    }
    let mut digest = [0; 32];
    let status = unsafe {
        BCryptHash(
            alg,
            null(),
            0,
            bytes.as_ptr(),
            bytes.len() as u32,
            digest.as_mut_ptr(),
            32,
        )
    };
    let closed = unsafe { BCryptCloseAlgorithmProvider(alg, 0) };
    let result = if status == 0 {
        Ok(digest)
    } else {
        Err(failure(Failure::Native(
            "fixture BCryptHash",
            status as u32,
        )))
    };
    finish(
        result,
        if closed == 0 {
            Ok(())
        } else {
            Err(failure(Failure::Native(
                "fixture BCryptClose",
                closed as u32,
            )))
        },
    )
}
struct Entry {
    path: PathBuf,
    handle: Option<OwnedHandle>,
    original: Option<Facts>,
    control: Option<OwnedHandle>,
    reader: Option<OwnedHandle>,
    digest: Option<[u8; 32]>,
    content_len: usize,
}
pub(crate) struct Fixture {
    entries: Vec<Entry>,
    root: PathBuf,
    total: usize,
}
impl Fixture {
    fn new() -> Result<Self> {
        Self::new_at(
            "HUB_RELAY_RELATIVE_NTFS_FIXTURE_PARENT",
            "relative-fixtures",
        )
    }
    pub(crate) fn ancestor() -> Result<Self> {
        Self::new_at("HUB_RELAY_ANCESTOR_FIXTURE_PARENT", "ancestor-fixtures")
    }
    fn new_at(variable: &str, leaf: &str) -> Result<Self> {
        let parent = PathBuf::from(
            std::env::var_os(variable).ok_or_else(|| denial("fixture parent missing"))?,
        );
        // The guarded task location is derived from this delivery checkout;
        // no machine/user pathname is committed and there is no temp fallback.
        let work = Path::new(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(6)
            .ok_or_else(|| denial("fixture delivery layout"))?;
        let approved = work.join("20261027-hub-relay-relative-ntfs/relative-fixtures");
        require(
            (parent == approved && leaf == "relative-fixtures"
                || guarded_parent(&parent, work, leaf))
                && parent.is_absolute(),
            "exact approved fixture parent",
        )?;
        let canonical =
            std::fs::canonicalize(&parent).map_err(|_| denial("fixture parent resolution"))?;
        let extended = PathBuf::from(format!(
            r"\\?\{}",
            parent
                .to_str()
                .ok_or_else(|| denial("fixture path text"))?
                .replace('/', r"\")
        ));
        require(canonical == extended, "fixture parent reparse resolution")?;
        let h = open_fixture(&parent, METADATA_RIGHTS)?;
        let checked = local_ntfs(h.as_raw_handle())
            .and_then(|()| facts(h.as_raw_handle()))
            .and_then(|f| validate(&f, ExpectedKind::Directory, None));
        finish(checked, close(h))?;
        let mut random = [0u8; 16];
        let rng_status = unsafe {
            BCryptGenRandom(
                null_mut(),
                random.as_mut_ptr(),
                16,
                BCRYPT_USE_SYSTEM_PREFERRED_RNG,
            )
        };
        if rng_status != 0 {
            return Err(failure(Failure::Native(
                "fixture BCryptGenRandom",
                rng_status as u32,
            )));
        }
        let suffix: String = random.iter().map(|b| format!("{b:02x}")).collect();
        let root = canonical.join(format!("relative-{suffix}"));
        let mut f = Self {
            entries: vec![],
            root: root.clone(),
            total: 0,
        };
        match f.create(&root, ExpectedKind::Directory, &[]) {
            Ok(_) => Ok(f),
            Err(e) => finish(Err(e), f.cleanup()),
        }
    }
    fn push(&mut self, path: &Path, h: Option<OwnedHandle>) -> usize {
        self.entries.push(Entry {
            path: path.into(),
            handle: h,
            original: None,
            control: None,
            reader: None,
            digest: None,
            content_len: 0,
        });
        self.entries.len() - 1
    }
    fn create(&mut self, path: &Path, kind: ExpectedKind, content: &[u8]) -> Result<usize> {
        require(
            path.starts_with(&self.root)
                && path.components().count() <= self.root.components().count() + 3,
            "fixture child boundary",
        )?;
        if path != self.root {
            let parent = self
                .entries
                .iter()
                .find(|e| Some(e.path.as_path()) == path.parent())
                .ok_or_else(|| denial("fixture parent absent from creation journal"))?;
            let h = parent
                .handle
                .as_ref()
                .ok_or_else(|| denial("fixture parent handle missing"))?;
            let observed = facts(h.as_raw_handle())?;
            require(
                Some(observed.identity()) == parent.original.as_ref().map(Facts::identity),
                "fixture parent identity before create",
            )?;
            validate(&observed, ExpectedKind::Directory, None)?;
        }
        require(
            self.total + content.len() <= 1024 * 1024 && content.len() <= 64,
            "fixture content limit",
        )?;
        let index = if kind == ExpectedKind::Directory {
            if unsafe { CreateDirectoryW(wide(path.to_str().unwrap()).as_ptr(), null()) } == 0 {
                return Err(last("fixture CreateDirectoryW"));
            }
            let i = self.push(path, None); // Creation is journaled even if acquisition fails.
            self.entries[i].handle = Some(open_fixture(path, DELETE | FILE_READ_ATTRIBUTES)?);
            i
        } else {
            let raw = unsafe {
                CreateFileW(
                    wide(path.to_str().unwrap()).as_ptr(),
                    GENERIC_WRITE | DELETE | FILE_READ_ATTRIBUTES,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                    null(),
                    CREATE_NEW,
                    FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
                    null_mut(),
                )
            };
            if raw == INVALID_HANDLE_VALUE {
                return Err(last("fixture CREATE_NEW"));
            }
            self.push(path, Some(unsafe { OwnedHandle::from_raw_handle(raw) }))
        };
        let raw = self.raw(index);
        let original = facts(raw)?;
        validate(&original, kind, None)?;
        self.entries[index].original = Some(original);
        if kind == ExpectedKind::File {
            let written = (|| {
                if !content.is_empty() {
                    let mut count = 0;
                    if unsafe {
                        WriteFile(
                            raw,
                            content.as_ptr(),
                            content.len() as u32,
                            &mut count,
                            null_mut(),
                        )
                    } == 0
                    {
                        return Err(last("fixture WriteFile"));
                    }
                    require(count as usize == content.len(), "fixture short write")?;
                }
                if unsafe { FlushFileBuffers(raw) } == 0 {
                    return Err(last("fixture FlushFileBuffers"));
                }
                Ok(())
            })();
            let cleanup = open_fixture(path, DELETE | FILE_READ_ATTRIBUTES);
            match cleanup {
                Ok(h) => {
                    let matches = facts(h.as_raw_handle()).and_then(|v| {
                        require(
                            v.identity()
                                == self.entries[index].original.as_ref().unwrap().identity(),
                            "cleanup acquisition identity",
                        )
                    });
                    if let Err(e) = matches {
                        return finish(finish(Err(e), written), close(h));
                    }
                    let writer = self.entries[index].handle.replace(h).unwrap();
                    finish(written, close(writer))?;
                }
                Err(e) => return finish(Err(e), written),
            }
            self.total += content.len();
            if !content.is_empty() {
                self.entries[index].digest = Some(hash(content)?);
                self.entries[index].content_len = content.len();
                self.entries[index].reader =
                    Some(open_fixture(path, FILE_READ_DATA | FILE_READ_ATTRIBUTES)?);
                self.verify_sentinel(index)?;
            }
        }
        println!(
            "FIXTURE created path={} identity={:?} kind={kind:?} bytes={}",
            path.display(),
            self.entries[index].original.as_ref().unwrap().identity(),
            content.len()
        );
        Ok(index)
    }
    fn child(&mut self, parent: usize, name: &'static str, kind: ExpectedKind) -> Result<usize> {
        InternalComponent::new(name)?;
        self.create(&self.entries[parent].path.join(name), kind, &[])
    }
    pub(crate) fn sentinel(
        &mut self,
        parent: usize,
        name: &'static str,
        byte: u8,
    ) -> Result<usize> {
        InternalComponent::new(name)?;
        self.create(
            &self.entries[parent].path.join(name),
            ExpectedKind::File,
            &[byte; 32],
        )
    }
    pub(crate) fn os_child(&mut self, parent: usize, name: &str) -> Result<usize> {
        require(
            !name.is_empty() && !name.contains(['\\', '/', ':']) && name != "." && name != "..",
            "owned fixture component",
        )?;
        self.create(
            &self.entries[parent].path.join(name),
            ExpectedKind::Directory,
            &[],
        )
    }
    pub(crate) fn prepare_junction(&mut self, index: usize) -> Result<()> {
        self.control(index)
    }
    pub(crate) fn junction(&mut self, index: usize, target: usize) -> Result<()> {
        if self.entries[index].control.is_none() {
            self.control(index)?;
        }
        let bytes = junction_buffer(&self.entries[target].path)?;
        set_junction(
            self.entries[index]
                .control
                .as_ref()
                .unwrap()
                .as_raw_handle(),
            &bytes,
        )
    }
    pub(crate) fn set_dacl(&self, index: usize, sddl: &str) -> Result<()> {
        use windows_sys::Win32::Security::Authorization::*;
        use windows_sys::Win32::Security::*;
        let h = open_fixture(
            &self.entries[index].path,
            WRITE_DAC | READ_CONTROL | FILE_READ_ATTRIBUTES,
        )?;
        let result = (|| {
            let before = facts(h.as_raw_handle())?;
            require(
                Some(before.identity())
                    == self.entries[index].original.as_ref().map(Facts::identity),
                "DACL fixture identity",
            )?;
            validate(&before, ExpectedKind::Directory, None)?;
            let mut sd = null_mut();
            let converted = unsafe {
                ConvertStringSecurityDescriptorToSecurityDescriptorW(
                    wide(sddl).as_ptr(),
                    1,
                    &mut sd,
                    null_mut(),
                )
            };
            let applied = (|| {
                if converted == 0 {
                    return Err(last("fixture ConvertStringSD"));
                }
                if sd.is_null() {
                    return Err(denial("fixture descriptor output"));
                }
                let mut present = 0;
                let mut acl = null_mut();
                let mut defaulted = 0;
                if unsafe { GetSecurityDescriptorDacl(sd, &mut present, &mut acl, &mut defaulted) }
                    == 0
                {
                    return Err(last("fixture GetDacl"));
                }
                require(present != 0 && !acl.is_null(), "fixture explicit DACL")?;
                let status = unsafe {
                    SetSecurityInfo(
                        h.as_raw_handle(),
                        SE_FILE_OBJECT,
                        DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
                        null_mut(),
                        null_mut(),
                        acl,
                        null_mut(),
                    )
                };
                if status != 0 {
                    return Err(failure(Failure::Native("fixture SetSecurityInfo", status)));
                }
                require(
                    facts(h.as_raw_handle())?.identity() == before.identity(),
                    "DACL same identity",
                )
            })();
            let freed = if sd.is_null() || unsafe { LocalFree(sd) }.is_null() {
                Ok(())
            } else {
                Err(last("fixture LocalFree"))
            };
            finish(applied, freed)
        })();
        finish(result, close(h))
    }
    fn raw(&self, i: usize) -> HANDLE {
        self.entries[i].handle.as_ref().unwrap().as_raw_handle()
    }
    pub(crate) fn input(&self, i: usize) -> Result<OwnedHandle> {
        let h = open_fixture(&self.entries[i].path, METADATA_RIGHTS)?;
        match facts(h.as_raw_handle()).and_then(|f| {
            require(
                Some(f.identity()) == self.entries[i].original.as_ref().map(Facts::identity),
                "fixture input identity",
            )
        }) {
            Ok(()) => Ok(h),
            Err(e) => finish(Err(e), close(h)),
        }
    }
    fn rename_file(&mut self, i: usize, parent: usize, name: &'static str) -> Result<()> {
        require(
            self.entries[i].original.as_ref().unwrap().kind == ExpectedKind::File
                && self.entries[i].path.parent() == Some(self.entries[parent].path.as_path()),
            "owned file rename parent and kind",
        )?;
        set_owned_name(
            self.raw(i),
            self.entries[i].original.as_ref().unwrap(),
            self.raw(parent),
            self.entries[parent].original.as_ref().unwrap(),
            name,
            false,
        )?;
        let previous = self.entries[i].path.clone();
        self.entries[i].path = self.entries[parent].path.join(name);
        println!(
            "FIXTURE rename identity={:?} from={} to={}",
            self.entries[i].original.as_ref().unwrap().identity(),
            previous.display(),
            self.entries[i].path.display()
        );
        Ok(())
    }
    fn control(&mut self, i: usize) -> Result<()> {
        require(
            self.entries[i].control.is_none(),
            "duplicate fixture control",
        )?;
        let h = open_fixture(
            &self.entries[i].path,
            FILE_WRITE_ATTRIBUTES | FILE_READ_ATTRIBUTES,
        )?;
        let checked = facts(h.as_raw_handle()).and_then(|f| {
            require(
                Some(f.identity()) == self.entries[i].original.as_ref().map(Facts::identity)
                    && f.kind == ExpectedKind::Directory,
                "reparse control provenance",
            )
        });
        match checked {
            Ok(()) => {
                self.entries[i].control = Some(h);
                Ok(())
            }
            Err(e) => finish(Err(e), close(h)),
        }
    }
    pub(crate) fn verify_sentinel(&self, i: usize) -> Result<()> {
        let e = &self.entries[i];
        let h = e
            .reader
            .as_ref()
            .ok_or_else(|| denial("missing sentinel handle"))?
            .as_raw_handle();
        require(
            Some(facts(h)?.identity()) == e.original.as_ref().map(Facts::identity),
            "sentinel identity changed",
        )?;
        if unsafe { SetFilePointerEx(h, 0, null_mut(), FILE_BEGIN) } == 0 {
            return Err(last("sentinel seek"));
        }
        let mut bytes = [0u8; 65];
        let mut read = 0;
        if unsafe {
            ReadFile(
                h,
                bytes.as_mut_ptr(),
                bytes.len() as u32,
                &mut read,
                null_mut(),
            )
        } == 0
        {
            return Err(last("sentinel ReadFile"));
        }
        require(
            read as usize == e.content_len && Some(hash(&bytes[..read as usize])?) == e.digest,
            "sentinel hash changed",
        )?;
        println!(
            "SENTINEL identity={:?} sha256={:02x?} unchanged",
            e.original.as_ref().unwrap().identity(),
            e.digest.unwrap()
        );
        Ok(())
    }
    pub(crate) fn cleanup(&mut self) -> Result<()> {
        let mut result = Ok(());
        let mut blocked: Vec<PathBuf> = vec![];
        let mut deleted_paths = vec![];
        // All workers must have been joined before this function is entered.
        for e in &mut self.entries {
            if let Some(h) = e.control.take() {
                let removed = facts(h.as_raw_handle()).and_then(|f| {
                    require(
                        Some(f.identity()) == e.original.as_ref().map(Facts::identity),
                        "tag cleanup identity",
                    )?;
                    if f.tag == MOUNT_TAG {
                        clear_junction(h.as_raw_handle())?;
                    } else {
                        require(f.tag == 0, "unknown fixture tag")?;
                    }
                    let after = facts(h.as_raw_handle())?;
                    require(
                        after.tag == 0 && after.attributes & FILE_ATTRIBUTE_REPARSE_POINT == 0,
                        "tag cleanup verification",
                    )
                });
                if removed.is_err() {
                    blocked.push(e.path.clone());
                }
                let checked = finish(removed, close(h));
                println!(
                    "FIXTURE tag cleanup path={} outcome={checked:?}",
                    e.path.display()
                );
                result = finish(result, checked);
            }
            if let Some(h) = e.reader.take() {
                result = finish(result, close(h));
            }
        }
        for e in self.entries.iter_mut().rev() {
            let Some(h) = e.handle.take() else {
                blocked.push(e.path.clone());
                result = finish(result, Err(denial("created fixture lacks cleanup handle")));
                println!(
                    "UNRESOLVED created path={} lacks cleanup handle",
                    e.path.display()
                );
                continue;
            };
            let verified = cleanup_identity_check(
                facts(h.as_raw_handle()),
                e.original.as_ref(),
                blocked.iter().any(|p| p.starts_with(&e.path)),
            );
            let deleted = verified.and_then(|()| {
                let info = FILE_DISPOSITION_INFO { DeleteFile: true };
                if unsafe {
                    SetFileInformationByHandle(
                        h.as_raw_handle(),
                        FileDispositionInfo,
                        (&info as *const FILE_DISPOSITION_INFO).cast(),
                        size_of::<FILE_DISPOSITION_INFO>() as u32,
                    )
                } == 0
                {
                    Err(last("fixture delete"))
                } else {
                    Ok(())
                }
            });
            if deleted.is_err() {
                blocked.push(e.path.clone());
            }
            let checked = finish(deleted, close(h));
            if checked.is_ok() {
                deleted_paths.push(e.path.clone());
            }
            println!(
                "FIXTURE cleanup path={} identity={:?} outcome={checked:?}",
                e.path.display(),
                e.original.as_ref().map(Facts::identity)
            );
            result = finish(result, checked);
        }
        // A deliberately linked file can retain its pending unlink until every
        // owned handle closes; verify exact names only after all closes.
        for path in deleted_paths {
            let attr = unsafe { GetFileAttributesW(wide(path.to_str().unwrap()).as_ptr()) };
            let code = unsafe { GetLastError() };
            let absent = require(
                attr == INVALID_FILE_ATTRIBUTES
                    && [ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND].contains(&code),
                "fixture exact path still exists",
            );
            println!("FIXTURE absence path={} outcome={absent:?}", path.display());
            result = finish(result, absent);
        }
        result
    }
}
fn run_case(f: impl FnOnce(&mut Fixture) -> Result<()>) {
    let mut fixture = Fixture::new().expect("exclusive owned fixture");
    let outcome = catch_unwind(AssertUnwindSafe(|| f(&mut fixture)));
    let cleanup = fixture.cleanup();
    assert!(
        cleanup.is_ok(),
        "operation={outcome:?}; cleanup={cleanup:?}"
    );
    assert!(matches!(outcome, Ok(Ok(()))), "operation={outcome:?}");
}
fn with_pair(
    f: &mut Fixture,
    parent: usize,
    expected: usize,
    body: impl FnOnce(&mut Fixture, &ObservedDirectory<'_>, &HeldObjectExpectation) -> Result<()>,
) -> Result<()> {
    let parent = ObservedDirectory::capture(f.input(parent)?)?;
    let expected = f.input(expected).and_then(HeldObjectExpectation::capture);
    let outcome = match expected {
        Ok(expected) => {
            let result = body(f, &parent, &expected);
            finish(result, expected.close())
        }
        Err(e) => Err(e),
    };
    finish(outcome, parent.close())
}
fn opened(
    parent: &ObservedDirectory<'_>,
    name: &'static str,
    kind: ExpectedKind,
    expected: &HeldObjectExpectation,
) -> Result<()> {
    let c = open_matching_child_metadata(parent, &InternalComponent::new(name)?, kind, expected)?;
    finish(c.recheck(), c.close())
}
fn refused(result: Result<()>, predicate: impl FnOnce(&Failure) -> bool) -> Result<()> {
    println!("NATIVE refusal outcome={result:?}");
    match result {
        Err(e) if predicate(&e.primary) && e.cleanup.is_empty() => Ok(()),
        Err(e) => Err(e),
        Ok(()) => Err(denial("unexpected native acceptance")),
    }
}
fn native_or_reparse(f: &Failure) -> bool {
    matches!(
        f,
        Failure::Completion("NtCreateFile", _) | Failure::Denied("reparse metadata")
    )
}
fn junction_buffer(target: &Path) -> Result<Vec<u8>> {
    let target = target
        .to_str()
        .ok_or_else(|| denial("junction target text"))?;
    let dos = target
        .strip_prefix(r"\\?\")
        .ok_or_else(|| denial("junction target not owned canonical path"))?;
    let substitute = wide(&format!(r"\??\{dos}"));
    let print = wide(dos);
    let sub_bytes = (substitute.len() - 1) * 2;
    let print_bytes = (print.len() - 1) * 2;
    let data_len = 8 + (substitute.len() + print.len()) * 2;
    require(data_len <= 16 * 1024, "fixture junction bound")?;
    let mut b = vec![];
    b.extend(MOUNT_TAG.to_le_bytes());
    b.extend((data_len as u16).to_le_bytes());
    b.extend(0u16.to_le_bytes());
    for n in [0, sub_bytes, substitute.len() * 2, print_bytes] {
        b.extend((n as u16).to_le_bytes());
    }
    for c in substitute.into_iter().chain(print) {
        b.extend(c.to_le_bytes());
    }
    Ok(b)
}
fn control_call(h: HANDLE, code: u32, b: &[u8]) -> Result<()> {
    let mut returned = 0;
    if unsafe {
        DeviceIoControl(
            h,
            code,
            b.as_ptr().cast(),
            b.len() as u32,
            null_mut(),
            0,
            &mut returned,
            null_mut(),
        )
    } == 0
    {
        Err(last("fixture reparse control"))
    } else {
        require(returned == 0, "fixture reparse output length")
    }
}
fn set_junction(h: HANDLE, b: &[u8]) -> Result<()> {
    control_call(h, SET_REPARSE, b)
}
fn clear_junction(h: HANDLE) -> Result<()> {
    let mut b = [0u8; 8];
    b[..4].copy_from_slice(&MOUNT_TAG.to_le_bytes());
    control_call(h, DELETE_REPARSE, &b)
}

// Fixture-only namespace operations use the exact journaled DELETE handle.
// Both parent and source identities stay live; replacement is always disabled.
// Callers check the source's journaled current parent. Simple names stay in
// that same directory, so the documented RootDirectory field must be NULL.
fn set_owned_name(
    source: HANDLE,
    original: &Facts,
    parent: HANDLE,
    parent_original: &Facts,
    name: &'static str,
    link: bool,
) -> Result<()> {
    require(
        facts(source)?.identity() == original.identity(),
        "rename/link source provenance",
    )?;
    let parent_now = facts(parent)?;
    require(
        parent_now.identity() == parent_original.identity(),
        "rename/link parent provenance",
    )?;
    validate(&parent_now, ExpectedKind::Directory, None)?;
    let name = InternalComponent::new(name)?;
    let bytes = unicode_bytes(name.0.len())? as usize;
    let (offset, header) = if link {
        (
            std::mem::offset_of!(nt::FILE_LINK_INFORMATION, FileName),
            size_of::<nt::FILE_LINK_INFORMATION>(),
        )
    } else {
        (
            std::mem::offset_of!(nt::FILE_RENAME_INFORMATION, FileName),
            size_of::<nt::FILE_RENAME_INFORMATION>(),
        )
    };
    let length = offset + bytes;
    let mut storage = vec![0usize; length.max(header).div_ceil(size_of::<usize>())];
    unsafe {
        if link {
            let p = storage.as_mut_ptr().cast::<nt::FILE_LINK_INFORMATION>();
            p.write(nt::FILE_LINK_INFORMATION::default());
            (*p).RootDirectory = null_mut();
            (*p).FileNameLength = bytes as u32;
        } else {
            let p = storage.as_mut_ptr().cast::<nt::FILE_RENAME_INFORMATION>();
            p.write(nt::FILE_RENAME_INFORMATION::default());
            (*p).RootDirectory = null_mut();
            (*p).FileNameLength = bytes as u32;
        }
        std::ptr::copy_nonoverlapping(
            name.0.as_ptr().cast::<u8>(),
            storage.as_mut_ptr().cast::<u8>().add(offset),
            bytes,
        );
    }
    let mut io = initial_iosb();
    let call = unsafe {
        nt::NtSetInformationFile(
            source,
            &mut io,
            storage.as_ptr().cast(),
            length as u32,
            if link {
                nt::FileLinkInformation
            } else {
                nt::FileRenameInformation
            },
        )
    };
    let c = completion(call, &io);
    match classify(c, 0, true) {
        CompletionClass::Complete => Ok(()),
        CompletionClass::Reject => Err(failure(Failure::Completion(
            "fixture NtSetInformationFile",
            c,
        ))),
        CompletionClass::FatalPending => abort_pending("fixture NtSetInformationFile", c),
    }
}

#[test]
fn native_own_child_metadata() {
    run_case(|f| {
        let child = f.child(0, "child", ExpectedKind::File)?;
        with_pair(f, 0, child, |_, p, e| {
            opened(p, "child", ExpectedKind::File, e)
        })
    });
}

#[test]
fn native_directory_and_separately_stepped_child() {
    run_case(|f| {
        let dir = f.child(0, "directory", ExpectedKind::Directory)?;
        let child = f.child(dir, "child", ExpectedKind::File)?;
        with_pair(f, 0, dir, |f, p, e| {
            let c = open_matching_child_metadata(
                p,
                &InternalComponent::new("directory")?,
                ExpectedKind::Directory,
                e,
            )?;
            let step = c.into_directory()?;
            let expected = f.input(child).and_then(HeldObjectExpectation::capture);
            let outcome = match expected {
                Ok(expected) => {
                    let outcome = opened(&step, "child", ExpectedKind::File, &expected);
                    finish(outcome, expected.close())
                }
                Err(e) => Err(e),
            };
            finish(outcome, step.close())
        })
    });
}
#[test]
fn native_missing_leaf_preserves_status() {
    run_case(|f| {
        let child = f.child(0, "child", ExpectedKind::File)?;
        with_pair(f, 0, child, |_, p, e| {
            refused(
                opened(p, "absent", ExpectedKind::File, e),
                |f| matches!(f,Failure::Completion("NtCreateFile",c) if c.call==STATUS_OBJECT_NAME_NOT_FOUND),
            )
        })
    });
}
#[test]
fn native_wrong_expected_child_denies_identity() {
    run_case(|f| {
        let a = f.child(0, "a", ExpectedKind::File)?;
        let b = f.child(0, "b", ExpectedKind::File)?;
        let actual = f.entries[a].original.as_ref().unwrap().identity();
        let expected = f.entries[b].original.as_ref().unwrap().identity();
        with_pair(f, 0, b, |_, p, e| {
            refused(
                opened(p, "a", ExpectedKind::File, e),
                |v| matches!(v,Failure::IdentityMismatch{expected:x,observed:y} if *x==expected && *y==actual),
            )
        })
    });
}
#[test]
fn native_leaf_junction_is_not_followed() {
    run_case(|f| {
        let leaf = f.child(0, "leaf", ExpectedKind::Directory)?;
        let target = f.child(0, "target", ExpectedKind::Directory)?;
        f.control(leaf)?;
        let b = junction_buffer(&f.entries[target].path)?;
        set_junction(
            f.entries[leaf].control.as_ref().unwrap().as_raw_handle(),
            &b,
        )?;
        with_pair(f, 0, target, |_, p, e| {
            refused(
                opened(p, "leaf", ExpectedKind::Directory, e),
                native_or_reparse,
            )
        })
    });
}
#[test]
fn native_stepped_directory_rechecks_ancestor_tag() {
    run_case(|f| {
        let dir = f.child(0, "directory", ExpectedKind::Directory)?;
        let target = f.child(0, "target", ExpectedKind::Directory)?;
        let target_child = f.sentinel(target, "child", 9)?;
        f.control(dir)?;
        let b = junction_buffer(&f.entries[target].path)?;
        with_pair(f, 0, dir, |f, p, e| {
            let step = open_matching_child_metadata(
                p,
                &InternalComponent::new("directory")?,
                ExpectedKind::Directory,
                e,
            )?
            .into_directory()?;
            let expected = f
                .input(target_child)
                .and_then(HeldObjectExpectation::capture);
            let outcome = match expected {
                Ok(expected) => {
                    let set =
                        set_junction(f.entries[dir].control.as_ref().unwrap().as_raw_handle(), &b);
                    let outcome = set.and_then(|()| {
                        let denied = opened(&step, "child", ExpectedKind::File, &expected);
                        println!("STEPPED ancestor and independent expectation outcome={denied:?}");
                        match denied {
                            Err(e)
                                if e.primary == Failure::Denied("reparse metadata")
                                    && e.cleanup == [Failure::Denied("reparse metadata")] =>
                            {
                                Ok(())
                            }
                            Err(e) => Err(e),
                            Ok(()) => Err(denial("stepped reparse unexpectedly accepted")),
                        }
                    });
                    finish(outcome, expected.close())
                }
                Err(e) => Err(e),
            };
            let result = finish(outcome, step.close());
            finish(result, f.verify_sentinel(target_child))
        })
    });
}
#[test]
fn native_regular_hardlink_is_rejected() {
    run_case(|f| {
        let file = f.child(0, "file", ExpectedKind::File)?;
        let expected = f.child(0, "expected", ExpectedKind::File)?;
        let path = f.root.join("link");
        require(
            f.entries[file].path.parent() == Some(f.entries[0].path.as_path()),
            "hardlink same journaled parent",
        )?;
        set_owned_name(
            f.raw(file),
            f.entries[file].original.as_ref().unwrap(),
            f.raw(0),
            f.entries[0].original.as_ref().unwrap(),
            "link",
            true,
        )?;
        let index = f.push(&path, None);
        f.entries[index].handle = Some(open_fixture(&path, DELETE | FILE_READ_ATTRIBUTES)?);
        let linked = facts(f.raw(index))?;
        require(
            linked.identity() == f.entries[file].original.as_ref().unwrap().identity()
                && linked.links == 2,
            "hardlink provenance",
        )?;
        f.entries[index].original = Some(linked);
        with_pair(f, 0, expected, |_, p, e| {
            refused(opened(p, "link", ExpectedKind::File, e), |v| {
                matches!(v, Failure::Denied("regular file links"))
            })
        })
    });
}
#[test]
fn native_persistent_parent_conversion_same_id() {
    run_case(|f| {
        let parent = f.child(0, "parent", ExpectedKind::Directory)?;
        let target = f.child(0, "target", ExpectedKind::Directory)?;
        let expected = f.sentinel(target, "child", 13)?;
        f.control(parent)?;
        let b = junction_buffer(&f.entries[target].path)?;
        with_pair(f, parent, expected, |f, p, e| {
            set_junction(
                f.entries[parent].control.as_ref().unwrap().as_raw_handle(),
                &b,
            )?;
            let changed = facts(p.observed.handle.as_raw_handle())?;
            require(
                changed.identity() == p.observed.original.identity() && changed.tag == MOUNT_TAG,
                "same ID parent conversion",
            )?;
            let outcome = refused(opened(p, "child", ExpectedKind::File, e), |v| {
                matches!(v, Failure::Denied("reparse metadata"))
            });
            finish(outcome, f.verify_sentinel(expected))
        })
    });
}

fn race_outcome(
    result: Result<()>,
    original: &mut usize,
    mismatch: &mut usize,
    refused: &mut BTreeMap<String, usize>,
    expected: (u64, [u8; 16]),
    target: (u64, [u8; 16]),
    active_name_changes: bool,
) -> Result<Option<Error>> {
    match result {
        Ok(()) => *original += 1,
        Err(e) => {
            let path_refusal = |v: &Failure| {
                active_name_changes
                    && matches!(v, Failure::Native("GetFinalPathNameByHandleW", code)
                        if [ERROR_FILE_NOT_FOUND, ERROR_PATH_NOT_FOUND, ERROR_ACCESS_DENIED].contains(code))
            };
            let known_mismatch = matches!(&e.primary,
                Failure::IdentityMismatch { expected: actual, observed }
                    if *actual == expected && *observed == target);
            let primary_allowed = known_mismatch
                || path_refusal(&e.primary)
                || matches!(
                    &e.primary,
                    Failure::Completion("NtCreateFile", _)
                        | Failure::Denied("observed metadata changed")
                );
            // Inspect every failure before changing counters. Only documented
            // finite path refusals and metadata drift may be secondary here.
            if !primary_allowed
                || !e.cleanup.iter().all(|v| {
                    path_refusal(v) || matches!(v, Failure::Denied("observed metadata changed"))
                })
            {
                return Err(e);
            }
            let query_unavailable = path_refusal(&e.primary) || e.cleanup.iter().any(path_refusal);
            if known_mismatch && !query_unavailable {
                *mismatch += 1;
                if !e.cleanup.is_empty() {
                    // Return the complete bounded diagnostic for immediate logging,
                    // separately from the single counted mismatch outcome.
                    return Ok(Some(e));
                }
            } else {
                let identity = if known_mismatch {
                    "known-comparison"
                } else {
                    "unavailable"
                };
                *refused
                    .entry(format!("identity={identity} {e:?}"))
                    .or_default() += 1;
            }
        }
    }
    Ok(None)
}
fn log_mismatch_diagnostic(diagnostic: Option<Error>) {
    if let Some(error) = diagnostic {
        println!("KNOWN_MISMATCH diagnostic={error:?}");
    }
}
fn name_fixture(f: &mut Fixture) -> Result<(usize, usize, usize)> {
    let parent = f.child(0, "parent", ExpectedKind::Directory)?;
    let own = f.sentinel(parent, "child", 17)?;
    let comparison = f.sentinel(parent, "replacement", 23)?;
    Ok((parent, own, comparison))
}
fn restore_names(f: &mut Fixture, parent: usize, own: usize, comparison: usize) -> Result<()> {
    // Every successful change updates the creation journal immediately. The
    // rename helper never replaces an occupied name, including on restoration.
    let comparison_result = if f.entries[comparison].path.file_name().unwrap() != "replacement" {
        f.rename_file(comparison, parent, "replacement")
    } else {
        Ok(())
    };
    let own_result = if f.entries[own].path.file_name().unwrap() != "child" {
        f.rename_file(own, parent, "child")
    } else {
        Ok(())
    };
    finish(comparison_result, own_result)
}
fn checked_name_observation(result: Result<HeldChildMetadata<'_>>) -> Result<()> {
    result.and_then(|child| {
        let agreed = require(
            child.observed.original.identity() == child.expectation.observed.original.identity(),
            "name replacement accepted another object",
        );
        finish(finish(agreed, child.recheck()), child.close())
    })
}
#[test]
fn native_deterministic_precheck_open_name_replacement() {
    run_case(|f| {
        let (parent, own, comparison) = name_fixture(f)?;
        with_pair(f, parent, own, |f, p, e| {
            let comparison_held = HeldObjectExpectation::capture(f.input(comparison)?)?;
            let result = (|| {
                let name = InternalComponent::new("child")?;
                let outcome =
                    checked_name_observation(open_inner(p, &name, ExpectedKind::File, e, || {
                        f.rename_file(own, parent, "parked")?;
                        f.rename_file(comparison, parent, "child")
                    }));
                let mut original = 0;
                let mut mismatch = 0;
                let mut refusals = BTreeMap::new();
                let classified = race_outcome(
                    outcome,
                    &mut original,
                    &mut mismatch,
                    &mut refusals,
                    e.observed.original.identity(),
                    comparison_held.observed.original.identity(),
                    false,
                )
                .map(log_mismatch_diagnostic);
                println!(
                    "DETERMINISTIC_NAMES original={original} mismatch={mismatch} refusals={refusals:?}"
                );
                // Both changes complete before native_open. Only the held
                // comparison object is now named child; its identity must deny.
                finish(
                    classified,
                    require(
                        original == 0 && mismatch == 1 && refusals.is_empty(),
                        "deterministic replacement must observe and refuse comparison identity",
                    ),
                )
            })();
            let result = finish(result, restore_names(f, parent, own, comparison));
            let result = finish(result, comparison_held.recheck());
            let result = finish(result, comparison_held.close());
            finish(
                finish(result, f.verify_sentinel(own)),
                f.verify_sentinel(comparison),
            )
        })
    });
}
#[test]
fn native_bounded_concurrent_file_name_replacement() {
    run_case(|f| {
        let (parent, own, comparison) = name_fixture(f)?;
        with_pair(f, parent, own, |f, p, e| {
            let comparison_held = HeldObjectExpectation::capture(f.input(comparison)?)?;
            let result = (|| {
                let name = InternalComponent::new("child")?;
                checked_name_observation(open_matching_child_metadata(
                    p,
                    &name,
                    ExpectedKind::File,
                    e,
                ))?;
                println!("CONCURRENT_NAMES positive_before=agreement");
                let stop = Arc::new(AtomicBool::new(false));
                let worker_stop = stop.clone();
                // Odd phase means a cycle is in progress; a changed phase
                // brackets actual worker progress during an observation.
                let phase = Arc::new(AtomicUsize::new(0));
                let worker_phase = phase.clone();
                let (ready_tx, ready_rx) = mpsc::channel();
                let (done_tx, done_rx) = mpsc::channel();
                let fixture_path = f.root.clone();
                let start = Instant::now();
                let mut original = 0;
                let mut mismatch = 0;
                let mut refusals = BTreeMap::new();
                let mut attempts = 0;
                let mut overlapping = 0;
                let result = std::thread::scope(|scope| {
                    let worker_fixture = &mut *f;
                    let worker = scope.spawn(move || {
                        let mut cycles = 0;
                        let mut result = Ok(());
                        // Readiness means an actual comparison-name interval
                        // was established, not merely that a thread started.
                        while !worker_stop.load(Ordering::Acquire)
                            && start.elapsed() < Duration::from_secs(3)
                            && cycles < 32
                        {
                            worker_phase.fetch_add(1, Ordering::AcqRel);
                            result =
                                worker_fixture
                                    .rename_file(own, parent, "parked")
                                    .and_then(|()| {
                                        worker_fixture.rename_file(comparison, parent, "child")
                                    });
                            if cycles == 0 {
                                let _ = ready_tx.send(result.is_ok());
                            }
                            if result.is_err() {
                                break;
                            }
                            std::thread::yield_now();
                            result = restore_names(worker_fixture, parent, own, comparison);
                            if result.is_err() {
                                break;
                            }
                            cycles += 1;
                            worker_phase.fetch_add(1, Ordering::Release);
                        }
                        let _ = done_tx.send(());
                        (result, cycles)
                    });
                    let mut result = ready_rx
                        .recv_timeout(Duration::from_secs(2))
                        .map_err(|_| denial("name worker ready timeout"))
                        .and_then(|ready| require(ready, "name worker setup failed"));
                    while result.is_ok()
                        && start.elapsed() < Duration::from_secs(3)
                        && original + mismatch + refusals.values().sum::<usize>() < 128
                    {
                        let before = phase.load(Ordering::Acquire);
                        let outcome = checked_name_observation(open_matching_child_metadata(
                            p,
                            &name,
                            ExpectedKind::File,
                            e,
                        ));
                        let active = before % 2 == 1 || phase.load(Ordering::Acquire) != before;
                        attempts += 1;
                        overlapping += usize::from(active);
                        result = race_outcome(
                            outcome,
                            &mut original,
                            &mut mismatch,
                            &mut refusals,
                            e.observed.original.identity(),
                            comparison_held.observed.original.identity(),
                            active,
                        )
                        .map(log_mismatch_diagnostic);
                    }
                    stop.store(true, Ordering::Release);
                    if done_rx.recv_timeout(Duration::from_secs(3)).is_err() {
                        eprintln!(
                            "UNRESOLVED name worker; exact fixture {}",
                            fixture_path.display()
                        );
                        std::process::abort();
                    }
                    let joined = worker.join().map_err(|_| denial("name worker panic"))?;
                    println!(
                        "CONCURRENT_NAMES original={original} mismatch={mismatch} refusals={refusals:?} attempts={attempts} overlapping={overlapping} cycles={} wall_ms={}",
                        joined.1,
                        start.elapsed().as_millis()
                    );
                    let result = finish(result, joined.0);
                    finish(
                        result,
                        require(
                            joined.1 > 0
                                && overlapping > 0
                                && attempts > 0
                                && attempts <= 128
                                && original + mismatch + refusals.values().sum::<usize>()
                                    == attempts
                                && start.elapsed() < Duration::from_secs(10),
                            "name race bounded progress",
                        ),
                    )
                });
                let after = restore_names(f, parent, own, comparison).and_then(|()| {
                    checked_name_observation(open_matching_child_metadata(
                        p,
                        &name,
                        ExpectedKind::File,
                        e,
                    ))
                });
                println!("CONCURRENT_NAMES positive_after_restore={after:?}");
                finish(result, after)
            })();
            let result = finish(result, comparison_held.recheck());
            let result = finish(result, comparison_held.close());
            finish(
                finish(result, f.verify_sentinel(own)),
                f.verify_sentinel(comparison),
            )
        })
    });
}
#[test]
fn native_parent_rename_replacement_retains_original() {
    run_case(|f| {
        let parent = f.child(0, "parent", ExpectedKind::Directory)?;
        let p = ObservedDirectory::capture(f.input(parent)?)?;
        let result = (|| {
            // Keep the captured parent, but rename it before creating children.
            // No child expectation is claimed to survive a directory rename.
            let old = f.entries[parent].path.clone();
            let moved = f.root.join("moved");
            require(
                old.parent() == Some(f.entries[0].path.as_path()),
                "directory rename same journaled parent",
            )?;
            set_owned_name(
                f.raw(parent),
                f.entries[parent].original.as_ref().unwrap(),
                f.raw(0),
                f.entries[0].original.as_ref().unwrap(),
                "moved",
                false,
            )?;
            f.entries[parent].path = moved;
            println!(
                "FIXTURE empty parent rename identity={:?} from={} to={}",
                p.observed.original.identity(),
                old.display(),
                f.entries[parent].path.display()
            );
            require(
                facts(p.observed.handle.as_raw_handle())?.identity()
                    == f.entries[parent].original.as_ref().unwrap().identity(),
                "renamed live parent identity",
            )?;
            p.recheck()?;
            let original = f.child(parent, "child", ExpectedKind::File)?;
            let replacement = f.child(0, "parent", ExpectedKind::Directory)?;
            let replacement_child = f.child(replacement, "child", ExpectedKind::File)?;
            require(
                f.entries[replacement].original.as_ref().unwrap().identity()
                    != p.observed.original.identity()
                    && f.entries[replacement_child]
                        .original
                        .as_ref()
                        .unwrap()
                        .identity()
                        != f.entries[original].original.as_ref().unwrap().identity(),
                "replacement parent and child must differ",
            )?;
            let expected = HeldObjectExpectation::capture(f.input(original)?)?;
            let result = opened(&p, "child", ExpectedKind::File, &expected);
            finish(result, expected.close())
        })();
        finish(result, p.close())
    });
}
#[test]
fn native_noninheritability_and_exact_rights() {
    run_case(|f| {
        let child = f.child(0, "child", ExpectedKind::File)?;
        let input = f.input(0)?;
        if unsafe {
            SetHandleInformation(
                input.as_raw_handle(),
                HANDLE_FLAG_INHERIT,
                HANDLE_FLAG_INHERIT,
            )
        } == 0
        {
            return finish(Err(last("fixture set inherit")), close(input));
        }
        let parent = ObservedDirectory::capture(input)?;
        let expected = f.input(child).and_then(HeldObjectExpectation::capture);
        let outcome = match expected {
            Ok(expected) => {
                let result = (|| {
                    let c = open_matching_child_metadata(
                        &parent,
                        &InternalComponent::new("child")?,
                        ExpectedKind::File,
                        &expected,
                    )?;
                    let checked = (|| {
                        for h in [
                            parent.observed.handle.as_raw_handle(),
                            expected.observed.handle.as_raw_handle(),
                            c.observed.handle.as_raw_handle(),
                        ] {
                            let mut flags = 0;
                            if unsafe { GetHandleInformation(h, &mut flags) } == 0 {
                                return Err(last("GetHandleInformation test"));
                            }
                            require(
                                flags & HANDLE_FLAG_INHERIT == 0
                                    && granted_access(h)? == METADATA_RIGHTS,
                                "rights/noninheritability",
                            )?;
                        }
                        Ok(())
                    })();
                    finish(checked, c.close())
                })();
                finish(result, expected.close())
            }
            Err(e) => Err(e),
        };
        finish(outcome, parent.close())
    });
}
#[test]
fn native_input_cannot_upgrade_rights() {
    run_case(|f| {
        let input = open_fixture(&f.entries[0].path, FILE_READ_ATTRIBUTES)?;
        let result = ObservedDirectory::capture(input).and_then(|p| p.close());
        refused(result, |e| {
            matches!(e, Failure::Denied("input lacks metadata rights"))
        })
    });
}

#[test]
fn native_wrong_kind_denies_after_open() {
    run_case(|f| {
        let dir = f.child(0, "directory", ExpectedKind::Directory)?;
        with_pair(f, 0, dir, |_, p, e| {
            refused(opened(p, "directory", ExpectedKind::File, e), |v| {
                matches!(v, Failure::Denied("object type"))
            })
        })
    });
}
pub(crate) fn thread_token_id() -> Result<(u32, i32)> {
    use windows_sys::Win32::Security::{GetTokenInformation, TOKEN_STATISTICS, TokenStatistics};
    let mut raw = null_mut();
    if unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut raw) } == 0 {
        return Err(last("fixture thread token"));
    }
    let h = unsafe { OwnedHandle::from_raw_handle(raw) };
    let mut value = TOKEN_STATISTICS::default();
    let mut length = 0;
    let result = if unsafe {
        GetTokenInformation(
            raw,
            TokenStatistics,
            (&mut value as *mut TOKEN_STATISTICS).cast(),
            size_of::<TOKEN_STATISTICS>() as u32,
            &mut length,
        )
    } == 0
    {
        Err(last("fixture token statistics"))
    } else {
        require(
            length as usize == size_of::<TOKEN_STATISTICS>(),
            "fixture token statistics length",
        )
        .map(|()| (value.TokenId.LowPart, value.TokenId.HighPart))
    };
    finish(result, close(h))
}
#[test]
fn native_impersonation_denied_without_clearing() {
    run_case(|f| {
        let input = f.input(0)?;
        std::thread::spawn(move || {
            use windows_sys::Win32::Security::{
                ImpersonateSelf, RevertToSelf, SecurityIdentification,
            };
            if unsafe { ImpersonateSelf(SecurityIdentification) } == 0 {
                return finish(Err(last("fixture ImpersonateSelf")), close(input));
            }
            let before = thread_token_id();
            let outcome = ObservedDirectory::capture(input).and_then(|p| p.close());
            let after = thread_token_id();
            if unsafe { RevertToSelf() } == 0 {
                eprintln!("fatal owned fixture impersonation revert failure");
                std::process::abort();
            }
            let refused = refused(outcome, |v| {
                matches!(v, Failure::Denied("calling-thread impersonation"))
            });
            finish(
                refused,
                before.and_then(|before| {
                    after.and_then(|after| {
                        require(before == after, "impersonation token was changed")
                    })
                }),
            )
        })
        .join()
        .map_err(|_| denial("impersonation fixture thread panic"))?
    });
}

fn sample() -> Facts {
    Facts {
        volume: 1,
        id: [7; 16],
        kind: ExpectedKind::File,
        attributes: FILE_ATTRIBUTE_NORMAL,
        tag: 0,
        links: 1,
        pending: false,
        size: 0,
        allocated: 0,
    }
}
#[test]
fn names_accept_internal_bounds() {
    for s in [
        "a",
        "A0_-x.y",
        "com0",
        "com10",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    ] {
        assert!(InternalComponent::new(s).is_ok(), "{s}");
    }
}
#[test]
fn names_reject_dos_aliases() {
    for s in [
        "CON", "con.txt", "PRN", "aux.x", "NUL", "COM1", "com9.x", "LPT1", "lpt9.x", "CONIN$",
        "CONOUT$", "CLOCK$",
    ] {
        assert!(InternalComponent::new(s).is_err(), "{s}");
    }
}
#[test]
fn names_reject_malformed_and_unbounded() {
    for s in [
        "",
        ".",
        "..",
        ".a",
        "a.",
        "a..b",
        "a/b",
        r"a\b",
        "a:b",
        "a\0",
        "a b",
        "a~1",
        "a*",
        "a?",
        "é",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    ] {
        assert!(InternalComponent::new(s).is_err(), "{s}");
    }
}
#[test]
fn metadata_type_and_all_tags_deny() {
    let mut f = sample();
    assert!(validate(&f, ExpectedKind::Directory, None).is_err());
    for tag in [1, MOUNT_TAG, 0xa000000c] {
        f.tag = tag;
        assert!(validate(&f, ExpectedKind::File, None).is_err());
    }
    f.tag = 0;
    f.attributes |= FILE_ATTRIBUTE_REPARSE_POINT;
    assert!(validate(&f, ExpectedKind::File, None).is_err());
}
#[test]
fn metadata_links_volume_pending_and_sizes() {
    let mut f = sample();
    assert!(validate(&f, ExpectedKind::File, Some(2)).is_err());
    f.links = 2;
    assert!(validate(&f, ExpectedKind::File, None).is_err());
    f.kind = ExpectedKind::Directory;
    f.attributes = FILE_ATTRIBUTE_DIRECTORY;
    assert!(validate(&f, ExpectedKind::Directory, None).is_ok());
    f.pending = true;
    assert!(validate(&f, ExpectedKind::Directory, None).is_err());
    f.pending = false;
    f.size = -1;
    assert!(validate(&f, ExpectedKind::Directory, None).is_err());
}
#[test]
fn completion_only_exact_completed_open_passes() {
    let c = Completion {
        call: 0,
        io: 0,
        information: 1,
    };
    assert_eq!(classify(c, 1, true), CompletionClass::Complete);
    for altered in [
        Completion {
            call: STATUS_REPARSE,
            ..c
        },
        Completion {
            io: STATUS_REPARSE,
            ..c
        },
        Completion {
            information: 2,
            ..c
        },
    ] {
        assert_eq!(classify(altered, 1, true), CompletionClass::Reject);
    }
    assert_eq!(classify(c, 1, false), CompletionClass::Reject);
}
#[test]
fn completion_pending_and_contradictory_unwritten_are_fatal() {
    for c in [
        Completion {
            call: STATUS_PENDING,
            io: UNWRITTEN,
            information: UNWRITTEN_INFO,
        },
        Completion {
            call: 0,
            io: STATUS_PENDING,
            information: 1,
        },
        Completion {
            call: STATUS_ACCESS_DENIED,
            io: STATUS_PENDING,
            information: 0,
        },
        Completion {
            call: 0,
            io: UNWRITTEN,
            information: UNWRITTEN_INFO,
        },
    ] {
        assert_eq!(classify(c, 1, true), CompletionClass::FatalPending);
    }
}
#[test]
fn terminal_error_with_unwritten_iosb_is_not_pending() {
    let c = Completion {
        call: STATUS_ACCESS_DENIED,
        io: UNWRITTEN,
        information: UNWRITTEN_INFO,
    };
    assert_eq!(classify(c, 1, false), CompletionClass::Reject);
    assert_ne!(c.call, c.io);
}
#[test]
fn native_buffer_bounds() {
    assert_eq!(unicode_bytes(64), Ok(128));
    assert!(unicode_bytes(32768).is_err());
    assert!(unicode_bytes(usize::MAX).is_err());
    let good = wide(r"\\?\Volume{12345678-1234-1234-1234-123456789abc}\file");
    assert!(volume_root(&good, good.len() - 1).is_ok());
    for length in [0, good.len(), MAX_PATH_UNITS + 1] {
        assert!(volume_root(&good, length).is_err());
    }
    assert!(volume_root(&wide(r"\\server\share\file"), 19).is_err());
}
#[test]
fn all_secondary_failures_are_preserved() {
    let e: Result<()> = Err(denial("primary"));
    let c = finish(Err(denial("first close")), Err(denial("second close")));
    let result = finish(e, c).unwrap_err();
    assert_eq!(result.primary, Failure::Denied("primary"));
    assert_eq!(
        result.cleanup,
        [
            Failure::Denied("first close"),
            Failure::Denied("second close")
        ]
    );
}

#[test]
fn known_mismatch_retains_secondary_drift_diagnostic_once() {
    let expected = (7, [11; 16]);
    let comparison = (7, [22; 16]);
    let error = || Error {
        primary: Failure::IdentityMismatch {
            expected,
            observed: comparison,
        },
        cleanup: vec![
            Failure::Denied("observed metadata changed"),
            Failure::Denied("observed metadata changed"),
            Failure::Denied("observed metadata changed"),
        ],
    };
    let mut original = 0;
    let mut mismatch = 0;
    let mut refusals = BTreeMap::new();
    for count in 1..=2 {
        let diagnostic = race_outcome(
            Err(error()),
            &mut original,
            &mut mismatch,
            &mut refusals,
            expected,
            comparison,
            false,
        )
        .unwrap();
        assert_eq!((original, mismatch, refusals.len()), (0, count, 0));
        assert_eq!(
            original + mismatch + refusals.values().sum::<usize>(),
            count
        );
        assert_eq!(diagnostic, Some(error()));
    }
}

#[test]
fn fixture_cleanup_preserves_query_then_close_failures() {
    let query = || Error {
        primary: Failure::Native("GetFileInformationByHandleEx", 5),
        cleanup: vec![
            Failure::Denied("query secondary first"),
            Failure::Denied("query secondary second"),
        ],
    };
    let original = sample();
    let mut deletion_called = false;
    let deleted = cleanup_identity_check(Err(query()), Some(&original), false).map(|()| {
        deletion_called = true;
    });
    assert!(!deletion_called);
    assert!(deleted.is_err()); // The fixture harness blocks dependencies on this result.
    let checked = finish(
        deleted,
        Err(Error {
            primary: Failure::Native("CloseHandle", 6),
            cleanup: vec![Failure::Denied("close secondary")],
        }),
    )
    .unwrap_err();
    assert_eq!(checked.primary, query().primary);
    assert_eq!(
        checked.cleanup,
        vec![
            Failure::Denied("query secondary first"),
            Failure::Denied("query secondary second"),
            Failure::Native("CloseHandle", 6),
            Failure::Denied("close secondary"),
        ]
    );
    // A successful query retains the distinct identity/tag/dependency refusal.
    assert!(cleanup_identity_check(Ok(original.clone()), Some(&original), false).is_ok());
    for (observed, blocked) in [
        (original.clone(), true),
        (
            Facts {
                id: [99; 16],
                ..original.clone()
            },
            false,
        ),
        (
            Facts {
                tag: MOUNT_TAG,
                ..original.clone()
            },
            false,
        ),
    ] {
        assert_eq!(
            cleanup_identity_check(Ok(observed), Some(&original), blocked).unwrap_err(),
            denial("fixture cleanup identity/tag/dependency refusal")
        );
    }
}

#[test]
fn name_race_refusal_preserves_unknown_identities_and_cleanup_failures() {
    let expected = (1, [1; 16]);
    let comparison = (1, [2; 16]);
    let unknown = (1, [3; 16]);
    let query = |code| Failure::Native("GetFinalPathNameByHandleW", code);
    let error = |primary, cleanup| Error { primary, cleanup };
    let identity = |expected, observed| Failure::IdentityMismatch { expected, observed };
    let mut original = 0;
    let mut mismatch = 0;
    let mut refusals = BTreeMap::new();
    let mut accepted_refusals = 0;
    // Codes2/5 were observed;3 is prospective finite-family coverage only.
    for code in [
        ERROR_FILE_NOT_FOUND,
        ERROR_PATH_NOT_FOUND,
        ERROR_ACCESS_DENIED,
    ] {
        for input in [
            error(query(code), vec![]),
            error(identity(expected, comparison), vec![query(code)]),
            error(
                query(code),
                vec![
                    query(2),
                    query(3),
                    query(5),
                    Failure::Denied("observed metadata changed"),
                ],
            ),
            error(
                Failure::Completion(
                    "NtCreateFile",
                    Completion {
                        call: STATUS_OBJECT_NAME_NOT_FOUND,
                        io: UNWRITTEN,
                        information: UNWRITTEN_INFO,
                    },
                ),
                vec![query(code)],
            ),
            error(
                Failure::Denied("observed metadata changed"),
                vec![query(code)],
            ),
        ] {
            let complete_error = format!("{input:?}");
            let has_identity = matches!(&input.primary, Failure::IdentityMismatch { .. });
            race_outcome(
                Err(input),
                &mut original,
                &mut mismatch,
                &mut refusals,
                expected,
                comparison,
                true,
            )
            .unwrap();
            accepted_refusals += 1;
            assert_eq!(
                (original, mismatch, refusals.values().sum::<usize>()),
                (0, 0, accepted_refusals)
            );
            let label = if has_identity {
                "known-comparison"
            } else {
                "unavailable"
            };
            assert!(refusals.contains_key(&format!("identity={label} {complete_error}")));
        }
    }
    let mut rejected = vec![
        (false, error(query(2), vec![])),
        (false, error(identity(expected, comparison), vec![query(5)])),
        (true, error(identity(expected, unknown), vec![query(2)])),
        (true, error(identity(unknown, comparison), vec![query(5)])),
        (true, error(query(2), vec![identity(expected, unknown)])),
        (
            true,
            error(Failure::Native("UnknownOperation", 2), vec![query(2)]),
        ),
        (
            true,
            error(query(2), vec![Failure::Native("UnknownOperation", 5)]),
        ),
        (
            true,
            error(Failure::Native("CloseHandle", 6), vec![query(2)]),
        ),
        (
            true,
            error(query(2), vec![Failure::Native("CloseHandle", 6)]),
        ),
        (
            true,
            error(
                identity(expected, comparison),
                vec![query(5), Failure::Native("CloseHandle", 6)],
            ),
        ),
        (
            true,
            error(Failure::Denied("unknown reason"), vec![query(2)]),
        ),
        (
            true,
            error(query(2), vec![Failure::Denied("unknown reason")]),
        ),
    ];
    for code in [6, 87, 8] {
        rejected.push((true, error(query(code), vec![])));
        rejected.push((
            true,
            error(identity(expected, comparison), vec![query(code)]),
        ));
        rejected.push((true, error(query(2), vec![query(code)])));
    }
    for (active, input) in rejected {
        let expected_debug = format!("{input:?}");
        let actual = race_outcome(
            Err(input),
            &mut original,
            &mut mismatch,
            &mut refusals,
            expected,
            comparison,
            active,
        )
        .unwrap_err();
        assert_eq!(format!("{actual:?}"), expected_debug);
        assert_eq!(
            (original, mismatch, refusals.values().sum::<usize>()),
            (0, 0, accepted_refusals)
        );
    }
    race_outcome(
        Ok(()),
        &mut original,
        &mut mismatch,
        &mut refusals,
        expected,
        comparison,
        false,
    )
    .unwrap();
    race_outcome(
        Err(error(identity(expected, comparison), vec![])),
        &mut original,
        &mut mismatch,
        &mut refusals,
        expected,
        comparison,
        false,
    )
    .unwrap();
    assert_eq!(
        (original, mismatch, refusals.values().sum::<usize>()),
        (1, 1, accepted_refusals)
    );
}

// Test-only allowlist: exact task, one versioned run directory and one fixture leaf.
pub(crate) fn guarded_parent(parent: &Path, work: &Path, leaf: &str) -> bool {
    let runs = work.join("20261027-hub-relay-ancestor-chain/runs");
    let Ok(tail) = parent.strip_prefix(runs) else {
        return false;
    };
    let pieces: Vec<_> = tail.iter().collect();
    if pieces.len() != 2 || pieces[1] != leaf {
        return false;
    }
    let Some(label) = pieces[0].to_str() else {
        return false;
    };
    let Some((name, version)) = label.rsplit_once("-v") else {
        return false;
    };
    !name.is_empty()
        && name.as_bytes()[0].is_ascii_lowercase()
        && name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
        && version.len() >= 3
        && version.bytes().all(|b| b.is_ascii_digit())
}

pub(crate) fn expected_refusal(error: &Error, wanted: &str) -> bool {
    if error.has_cleanup_failure() {
        return false;
    }
    match (wanted, &error.primary) {
        ("missing", Failure::Completion("NtCreateFile", c)) => c.call as u32 == 0xc0000034,
        ("access", Failure::Completion("NtCreateFile", c)) => c.call as u32 == 0xc0000022,
        ("reparse", Failure::Completion("NtCreateFile", c)) => c.call as u32 == 0xc000050b,
        ("reparse", Failure::Denied("reparse metadata")) => true,
        ("impersonation", Failure::Denied("calling-thread impersonation")) => true,
        _ => false,
    }
}

#[test]
fn primary_close_failure_is_cleanup_failure() {
    let primary = failure(Failure::Native("CloseHandle", 6));
    assert!(primary.has_cleanup_failure());
    assert!(!expected_refusal(&primary, "missing"));
    let ordinary = failure(Failure::Native("GetFinalPathNameByHandleW", 5));
    assert!(!ordinary.has_cleanup_failure());
    let secondary = finish::<()>(Err(denial("original")), Err(primary)).unwrap_err();
    assert!(secondary.has_cleanup_failure());
    assert_eq!(secondary.primary, Failure::Denied("original"));
}
