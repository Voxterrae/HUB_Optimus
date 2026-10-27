//! Native descriptor fixtures and separately labeled deterministic parser cases.
use super::*;
use std::os::windows::io::{AsRawHandle, FromRawHandle, IntoRawHandle, OwnedHandle};
use std::panic::{AssertUnwindSafe, catch_unwind, resume_unwind};
use std::path::PathBuf;
use std::ptr::{null, null_mut};
use windows_sys::Win32::Foundation::*;
use windows_sys::Win32::Security::Authorization::*;
use windows_sys::Win32::Security::Cryptography::{
    BCRYPT_USE_SYSTEM_PREFERRED_RNG, BCryptGenRandom,
};
use windows_sys::Win32::Security::*;
use windows_sys::Win32::Storage::FileSystem::*;
use windows_sys::Win32::System::Threading::*;

const FIXTURE_RIGHTS: u32 = 0x0013_0080; // SYNCHRONIZE, DELETE, READ_CONTROL, READ_ATTRIBUTES; owner supplies WRITE_DAC.
const SYSTEM: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0];

fn wide(text: &str) -> Vec<u16> {
    text.encode_utf16().chain(Some(0)).collect()
}
fn check(ok: i32, operation: &str) -> std::result::Result<(), String> {
    if ok != 0 {
        Ok(())
    } else {
        Err(format!("{operation}: {}", unsafe { GetLastError() }))
    }
}
fn close(handle: OwnedHandle) -> std::result::Result<(), String> {
    check(
        unsafe { CloseHandle(handle.into_raw_handle()) },
        "CloseHandle",
    )
}

struct LocalDescriptor(PSECURITY_DESCRIPTOR);
impl LocalDescriptor {
    fn new(sddl: &str) -> Self {
        let mut raw = null_mut();
        check(
            unsafe {
                ConvertStringSecurityDescriptorToSecurityDescriptorW(
                    wide(sddl).as_ptr(),
                    1,
                    &mut raw,
                    null_mut(),
                )
            },
            "ConvertStringSD",
        )
        .unwrap();
        Self(raw)
    }
    fn release(mut self) -> std::result::Result<(), String> {
        let raw = std::mem::replace(&mut self.0, null_mut());
        if unsafe { LocalFree(raw) }.is_null() {
            Ok(())
        } else {
            Err("LocalFree descriptor failed".into())
        }
    }
}
impl Drop for LocalDescriptor {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe {
                LocalFree(self.0);
            }
        }
    }
}

fn current_user() -> (Vec<u8>, String) {
    let mut raw = null_mut();
    check(
        unsafe { OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &mut raw) },
        "OpenProcessToken",
    )
    .unwrap();
    let token = unsafe { OwnedHandle::from_raw_handle(raw) };
    let result = catch_unwind(AssertUnwindSafe(|| {
        let mut length = 0;
        let first = unsafe { GetTokenInformation(raw, TokenUser, null_mut(), 0, &mut length) };
        assert_eq!(first, 0);
        assert_eq!(unsafe { GetLastError() }, ERROR_INSUFFICIENT_BUFFER);
        assert!(length as usize >= std::mem::size_of::<TOKEN_USER>() && length < 4096);
        let mut storage = vec![0usize; (length as usize).div_ceil(std::mem::size_of::<usize>())];
        check(
            unsafe {
                GetTokenInformation(
                    raw,
                    TokenUser,
                    storage.as_mut_ptr().cast(),
                    length,
                    &mut length,
                )
            },
            "TokenUser",
        )
        .unwrap();
        assert!(
            length as usize >= std::mem::size_of::<TOKEN_USER>()
                && length as usize <= storage.len() * std::mem::size_of::<usize>()
        );
        let user = unsafe { &*storage.as_ptr().cast::<TOKEN_USER>() };
        let start = storage.as_ptr() as usize;
        let sid_start = user.User.Sid as usize;
        assert!(sid_start >= start && sid_start + 8 <= start + length as usize);
        let sid_length = unsafe { GetLengthSid(user.User.Sid) } as usize;
        assert!(sid_length <= 68 && sid_start + sid_length <= start + length as usize);
        let sid =
            unsafe { std::slice::from_raw_parts(user.User.Sid.cast::<u8>(), sid_length) }.to_vec();
        let mut text = null_mut();
        check(
            unsafe { ConvertSidToStringSidW(user.User.Sid, &mut text) },
            "ConvertSid",
        )
        .unwrap();
        let mut count = 0;
        while count < 192 && unsafe { *text.add(count) } != 0 {
            count += 1;
        }
        let rendered = String::from_utf16(unsafe { std::slice::from_raw_parts(text, count) });
        let freed = unsafe { LocalFree(text.cast()) }.is_null();
        assert!(freed, "SID string cleanup; conversion {rendered:?}");
        assert!(count < 192);
        let rendered = rendered.unwrap();
        (sid, rendered)
    }));
    let closed = close(token);
    assert!(
        closed.is_ok(),
        "token query {result:?}; token cleanup {closed:?}"
    );
    match result {
        Ok(user) => user,
        Err(panic) => resume_unwind(panic),
    }
}

struct Fixture {
    handle: Option<OwnedHandle>,
    path: PathBuf,
    identity: (u32, u32, u32),
    sid: Vec<u8>,
    sid_text: String,
}
fn file_identity(handle: HANDLE) -> std::result::Result<(u32, u32, u32), String> {
    let mut info = unsafe { std::mem::zeroed::<BY_HANDLE_FILE_INFORMATION>() };
    check(
        unsafe { GetFileInformationByHandle(handle, &mut info) },
        "FileIdentity",
    )?;
    if info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) != 0
        || info.nNumberOfLinks != 1
    {
        return Err("fixture is not a single-link regular file".into());
    }
    Ok((
        info.dwVolumeSerialNumber,
        info.nFileIndexHigh,
        info.nFileIndexLow,
    ))
}
impl Fixture {
    fn new() -> Self {
        let (sid, sid_text) = current_user();
        assert_ne!(
            sid, SYSTEM,
            "same-user fixture requires a non-SYSTEM test owner"
        );
        let parent = std::env::var_os("HUB_RELAY_NTFS_FIXTURE_PARENT")
            .map(PathBuf::from)
            .expect("explicit guarded descriptor fixture parent");
        let work = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .ancestors()
            .nth(6)
            .unwrap();
        let previous = work.join("20261027-hub-relay-relative-ntfs/ntfs-fixtures");
        assert!(
            parent == previous
                || crate::relative_ntfs::tests::guarded_parent(&parent, work, "ntfs-fixtures")
        );
        let canonical = std::fs::canonicalize(&parent).expect("fixture parent resolution");
        let extended = PathBuf::from(format!(
            r"\\?\{}",
            parent.to_str().unwrap().replace('/', r"\")
        ));
        assert_eq!(canonical, extended, "descriptor parent reparse escape");
        let parent_text = parent.to_str().unwrap();
        assert!(parent.is_absolute() && !parent_text.starts_with("\\\\"));
        let mut volume_path = [0u16; 1024];
        check(
            unsafe {
                GetVolumePathNameW(
                    wide(parent_text).as_ptr(),
                    volume_path.as_mut_ptr(),
                    volume_path.len() as u32,
                )
            },
            "GetVolumePathName",
        )
        .unwrap();
        assert_eq!(
            unsafe { GetDriveTypeW(volume_path.as_ptr()) },
            3,
            "fixture volume must be local fixed storage"
        );
        let mut fs = [0u16; 64];
        check(
            unsafe {
                GetVolumeInformationW(
                    volume_path.as_ptr(),
                    null_mut(),
                    0,
                    null_mut(),
                    null_mut(),
                    null_mut(),
                    fs.as_mut_ptr(),
                    fs.len() as u32,
                )
            },
            "GetVolumeInformation",
        )
        .unwrap();
        assert_eq!(String::from_utf16(&fs[..4]).unwrap(), "NTFS");
        let mut random = [0u8; 16];
        assert_eq!(
            unsafe {
                BCryptGenRandom(
                    null_mut(),
                    random.as_mut_ptr(),
                    16,
                    BCRYPT_USE_SYSTEM_PREFERRED_RNG,
                )
            },
            0
        );
        let suffix: String = random.iter().map(|byte| format!("{byte:02x}")).collect();
        let path = parent.join(format!("descriptor-{suffix}.fixture"));
        let sd = LocalDescriptor::new(&format!(
            "O:{sid_text}D:P(A;;0x130080;;;{sid_text})(A;;FA;;;SY)"
        ));
        let attributes = SECURITY_ATTRIBUTES {
            nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
            lpSecurityDescriptor: sd.0,
            bInheritHandle: 0,
        };
        let raw = unsafe {
            CreateFileW(
                wide(path.to_str().unwrap()).as_ptr(),
                FIXTURE_RIGHTS | WRITE_DAC,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                &attributes,
                CREATE_NEW,
                FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
                null_mut(),
            )
        };
        let create_error = unsafe { GetLastError() };
        let release = sd.release();
        assert_ne!(
            raw, INVALID_HANDLE_VALUE,
            "CreateFile fixture {create_error}; descriptor cleanup {release:?}"
        );
        let handle = unsafe { OwnedHandle::from_raw_handle(raw) };
        let identity = file_identity(raw);
        let mut fixture = Self {
            handle: Some(handle),
            path,
            identity: (0, 0, 0),
            sid,
            sid_text,
        };
        match (identity, release) {
            (Ok(id), Ok(())) => fixture.identity = id,
            (id, freed) => {
                let cleanup = fixture.cleanup(false);
                panic!("fixture acquisition {id:?} {freed:?}; cleanup {cleanup:?}");
            }
        }
        let mut flags = 0;
        let validation = check(
            unsafe { GetHandleInformation(fixture.raw(), &mut flags) },
            "GetHandleInformation",
        )
        .and_then(|()| {
            if flags & HANDLE_FLAG_INHERIT == 0 {
                Ok(())
            } else {
                Err("fixture handle inherited".into())
            }
        });
        if let Err(primary) = validation {
            let cleanup = fixture.cleanup(true);
            panic!("fixture handle validation {primary}; cleanup {cleanup:?}");
        }
        fixture
    }
    fn raw(&self) -> HANDLE {
        self.handle.as_ref().unwrap().as_raw_handle()
    }
    fn policy(&self) -> DescriptorPolicy {
        DescriptorPolicy {
            owner: self.sid.clone(),
            grants: vec![
                Grant {
                    sid: self.sid.clone(),
                    mask: FIXTURE_RIGHTS,
                },
                Grant {
                    sid: SYSTEM.to_vec(),
                    mask: 0x001f_01ff,
                },
            ],
        }
    }
    fn set_acl(&self, dacl: &str, protected: bool) {
        self.set_acl_on(self.raw(), dacl, protected);
    }
    fn set_acl_on(&self, handle: HANDLE, dacl: &str, protected: bool) {
        let sd = LocalDescriptor::new(&format!("D:{dacl}"));
        let mut present = 0;
        let mut acl = null_mut();
        let mut defaulted = 0;
        check(
            unsafe { GetSecurityDescriptorDacl(sd.0, &mut present, &mut acl, &mut defaulted) },
            "GetDacl test",
        )
        .unwrap();
        assert_ne!(present, 0);
        let protection = if protected {
            PROTECTED_DACL_SECURITY_INFORMATION
        } else {
            UNPROTECTED_DACL_SECURITY_INFORMATION
        };
        let status = unsafe {
            SetSecurityInfo(
                handle,
                SE_FILE_OBJECT,
                DACL_SECURITY_INFORMATION | protection,
                null_mut(),
                null_mut(),
                acl,
                null_mut(),
            )
        };
        let freed = sd.release();
        assert_eq!(status, 0, "SetSecurityInfo; cleanup {freed:?}");
        freed.unwrap();
    }
    fn null_acl(&self) {
        assert_eq!(
            unsafe {
                SetSecurityInfo(
                    self.raw(),
                    SE_FILE_OBJECT,
                    DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
                    null_mut(),
                    null_mut(),
                    null_mut(),
                    null_mut(),
                )
            },
            0
        );
    }
    fn cleanup(&mut self, verify_identity: bool) -> std::result::Result<(), Vec<String>> {
        let mut errors = Vec::new();
        if let Some(handle) = self.handle.take() {
            let identity = file_identity(handle.as_raw_handle());
            let matches = !verify_identity || identity.as_ref() == Ok(&self.identity);
            if !matches {
                errors.push(format!("cleanup identity mismatch: {identity:?}"));
            }
            if matches {
                let disposition = FILE_DISPOSITION_INFO { DeleteFile: true };
                if let Err(error) = check(
                    unsafe {
                        SetFileInformationByHandle(
                            handle.as_raw_handle(),
                            FileDispositionInfo,
                            (&disposition as *const FILE_DISPOSITION_INFO).cast(),
                            std::mem::size_of_val(&disposition) as u32,
                        )
                    },
                    "Delete own fixture",
                ) {
                    errors.push(error);
                }
            }
            if let Err(error) = close(handle) {
                errors.push(error);
            }
            let found = unsafe { GetFileAttributesW(wide(self.path.to_str().unwrap()).as_ptr()) };
            let error = unsafe { GetLastError() };
            if found != INVALID_FILE_ATTRIBUTES || error != ERROR_FILE_NOT_FOUND {
                errors.push(format!("owned path not absent: {found}/{error}"));
            }
        }
        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = self.cleanup(true);
    }
}
fn fixture(test: impl FnOnce(&Fixture)) {
    let mut owned = Fixture::new();
    let primary = catch_unwind(AssertUnwindSafe(|| test(&owned)));
    let cleanup = owned.cleanup(true);
    assert!(cleanup.is_ok(), "primary {primary:?}; cleanup {cleanup:?}");
    eprintln!("descriptor fixture: exact live identity deleted, handle closed, path absent");
    if let Err(panic) = primary {
        resume_unwind(panic);
    }
}
fn policy_denial(facts: &DescriptorFacts, policy: &DescriptorPolicy, want: Denial) {
    assert_eq!(
        policy.compare(facts).unwrap_err().primary,
        Failure::Policy(want)
    );
}

#[test]
fn native_snapshot_matches_explicit_fixture_policy() {
    fixture(|f| {
        let facts = inspect(f.handle.as_ref().unwrap()).unwrap();
        assert_eq!(facts.owner, f.sid);
        assert!(facts.dacl_protected);
        f.policy().compare(&facts).unwrap();
    });
}
#[test]
fn native_allow_ace_order_is_semantic() {
    fixture(|f| {
        f.set_acl(
            &format!("P(A;;FA;;;SY)(A;;0x130080;;;{})", f.sid_text),
            true,
        );
        f.policy()
            .compare(&inspect(f.handle.as_ref().unwrap()).unwrap())
            .unwrap();
    });
}
#[test]
fn native_user_owner_fails_system_rule() {
    fixture(|f| {
        policy_denial(
            &inspect(f.handle.as_ref().unwrap()).unwrap(),
            &DescriptorPolicy::root_shape(service_sid()).unwrap(),
            Denial::Owner,
        );
    });
}
#[test]
fn native_null_dacl_denied() {
    fixture(|f| {
        f.null_acl();
        policy_denial(
            &inspect(f.handle.as_ref().unwrap()).unwrap(),
            &f.policy(),
            Denial::NullDacl,
        );
    });
}
#[test]
fn native_unprotected_dacl_denied() {
    fixture(|f| {
        f.set_acl(
            &format!("(A;;0x130080;;;{})(A;;FA;;;SY)", f.sid_text),
            false,
        );
        policy_denial(
            &inspect(f.handle.as_ref().unwrap()).unwrap(),
            &f.policy(),
            Denial::UnprotectedDacl,
        );
    });
}
#[test]
fn native_extra_rights_and_broad_grant_denied() {
    fixture(|f| {
        f.set_acl(
            &format!("P(A;;0x130180;;;{})(A;;FA;;;SY)", f.sid_text),
            true,
        );
        policy_denial(
            &inspect(f.handle.as_ref().unwrap()).unwrap(),
            &f.policy(),
            Denial::Grants,
        );
        f.set_acl(
            &format!("P(A;;0x130080;;;{})(A;;FA;;;SY)(A;;FR;;;WD)", f.sid_text),
            true,
        );
        policy_denial(
            &inspect(f.handle.as_ref().unwrap()).unwrap(),
            &f.policy(),
            Denial::Grants,
        );
    });
}
#[test]
fn native_inheritance_normalization_and_unsupported_ace() {
    fixture(|f| {
        f.set_acl(
            &format!("P(A;;0x130080;;;{})(A;OI;FA;;;SY)", f.sid_text),
            true,
        );
        let facts = inspect(f.handle.as_ref().unwrap()).unwrap();
        let flags: Vec<_> = facts
            .dacl
            .as_ref()
            .unwrap()
            .iter()
            .map(|ace| ace.flags)
            .collect();
        eprintln!("native inheritance input: observed ACE flags {flags:?}");
        if flags.iter().all(|&flag| flag == 0) {
            f.policy().compare(&facts).unwrap(); // OS removed irrelevant file inheritance.
        } else {
            policy_denial(&facts, &f.policy(), Denial::AceFlags);
        }
        f.set_acl(
            &format!("P(D;;0x100;;;WD)(A;;0x130080;;;{})(A;;FA;;;SY)", f.sid_text),
            true,
        );
        assert_eq!(
            inspect(f.handle.as_ref().unwrap()).unwrap_err().primary,
            Failure::Policy(Denial::UnsupportedAce)
        );
    });
}
#[test]
fn native_duplicate_input_is_checked_after_os_normalization() {
    fixture(|f| {
        f.set_acl(
            &format!("P(A;;0x130080;;;{})(A;;FA;;;SY)(A;;FA;;;SY)", f.sid_text),
            true,
        );
        let facts = inspect(f.handle.as_ref().unwrap()).unwrap();
        let count = facts.dacl.as_ref().unwrap().len();
        eprintln!("native duplicate input: observed ACE count {count}");
        match count {
            2 => f.policy().compare(&facts).unwrap(), // NTFS normalized duplicate grants.
            3 => policy_denial(&facts, &f.policy(), Denial::DuplicateGrant),
            _ => panic!("unexpected normalized ACL size {count}"),
        }
    });
}
#[test]
fn native_attribute_write_denied_but_owner_can_change_dacl() {
    fixture(|f| {
        let raw = unsafe {
            CreateFileW(
                wide(f.path.to_str().unwrap()).as_ptr(),
                FILE_WRITE_ATTRIBUTES,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                null(),
                OPEN_EXISTING,
                FILE_FLAG_OPEN_REPARSE_POINT,
                null_mut(),
            )
        };
        let error = unsafe { GetLastError() };
        if raw != INVALID_HANDLE_VALUE {
            close(unsafe { OwnedHandle::from_raw_handle(raw) }).unwrap();
        }
        assert_eq!(
            raw, INVALID_HANDLE_VALUE,
            "attribute write unexpectedly allowed"
        );
        assert_eq!(error, ERROR_ACCESS_DENIED);
        // WRITE_DAC is absent from the measured ACL. A new owner handle can
        // still obtain it; use that specific handle for the actual ACL change.
        let owner_raw = unsafe {
            CreateFileW(
                wide(f.path.to_str().unwrap()).as_ptr(),
                WRITE_DAC | READ_CONTROL,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                null(),
                OPEN_EXISTING,
                FILE_FLAG_OPEN_REPARSE_POINT,
                null_mut(),
            )
        };
        assert_ne!(owner_raw, INVALID_HANDLE_VALUE, "owner implicit WRITE_DAC");
        let owner = unsafe { OwnedHandle::from_raw_handle(owner_raw) };
        let changed = catch_unwind(AssertUnwindSafe(|| {
            f.set_acl_on(
                owner_raw,
                &format!("P(A;;0x130180;;;{})(A;;FA;;;SY)", f.sid_text),
                true,
            )
        }));
        let closed = close(owner);
        assert!(
            closed.is_ok(),
            "primary {changed:?}; owner close {closed:?}"
        );
        if let Err(panic) = changed {
            resume_unwind(panic);
        }
        policy_denial(
            &inspect(f.handle.as_ref().unwrap()).unwrap(),
            &f.policy(),
            Denial::Grants,
        );
        let raw = unsafe {
            CreateFileW(
                wide(f.path.to_str().unwrap()).as_ptr(),
                FILE_WRITE_ATTRIBUTES,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                null(),
                OPEN_EXISTING,
                FILE_FLAG_OPEN_REPARSE_POINT,
                null_mut(),
            )
        };
        assert_ne!(
            raw, INVALID_HANDLE_VALUE,
            "owner DACL change did not grant attribute write"
        );
        close(unsafe { OwnedHandle::from_raw_handle(raw) }).unwrap();
    });
}
#[test]
fn native_query_without_read_control_denied() {
    fixture(|f| {
        let raw = unsafe {
            CreateFileW(
                wide(f.path.to_str().unwrap()).as_ptr(),
                FILE_READ_ATTRIBUTES,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                null(),
                OPEN_EXISTING,
                FILE_FLAG_OPEN_REPARSE_POINT,
                null_mut(),
            )
        };
        assert_ne!(raw, INVALID_HANDLE_VALUE);
        let narrow = unsafe { OwnedHandle::from_raw_handle(raw) };
        let result = inspect(&narrow);
        close(narrow).unwrap();
        assert_eq!(
            result.unwrap_err().primary,
            Failure::Native {
                operation: "GetSecurityInfo",
                status: ERROR_ACCESS_DENIED
            }
        );
    });
}

// Hand-built bytes: SD20 + owner SYSTEM12 + ACL8 + standard allow ACE20.
fn image() -> Vec<u8> {
    let mut bytes = vec![
        1, 0, 4, 0x90, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0,
    ];
    bytes.extend_from_slice(SYSTEM);
    bytes.extend_from_slice(&[2, 0, 28, 0, 1, 0, 0, 0, 0, 0, 20, 0, 0xff, 1, 0x1f, 0]);
    bytes.extend_from_slice(SYSTEM);
    bytes
}
#[test]
fn parser_bounds_layouts_and_sid_fail_closed() {
    let good = image();
    assert_eq!(parse_snapshot(&good).unwrap().owner, SYSTEM);
    for length in 0..good.len() {
        assert!(
            parse_snapshot(&good[..length]).is_err(),
            "truncation {length}"
        );
    }
    for (offset, value) in [
        (0, 2),
        (3, 0x10),
        (4, 0xff),
        (16, 33),
        (32, 3),
        (34, 0xff),
        (36, 2),
        (42, 3),
        (48, 2),
        (49, 16),
    ] {
        let mut bad = good.clone();
        bad[offset] = value;
        assert!(parse_snapshot(&bad).is_err(), "malformed offset {offset}");
    }
    let mut unknown = good.clone();
    unknown[40] = 0xff;
    assert_eq!(
        parse_snapshot(&unknown).unwrap_err().primary,
        Failure::Policy(Denial::UnsupportedAce)
    );
    assert!(parse_snapshot(&vec![0; 65_537]).is_err());
}
#[test]
fn parser_absent_dacl_is_distinct_from_null() {
    let mut absent = image();
    absent[2] = 0;
    absent[16..20].fill(0);
    let policy = DescriptorPolicy {
        owner: SYSTEM.to_vec(),
        grants: vec![Grant {
            sid: SYSTEM.to_vec(),
            mask: 0x001f_01ff,
        }],
    };
    policy_denial(
        &parse_snapshot(&absent).unwrap(),
        &policy,
        Denial::AbsentDacl,
    );
    let mut null = image();
    null[16..20].fill(0);
    policy_denial(&parse_snapshot(&null).unwrap(), &policy, Denial::NullDacl);
}
fn service_sid() -> Vec<u8> {
    // Structurally shaped test SID only: no service is resolved or authenticated.
    vec![
        1, 6, 0, 0, 0, 0, 0, 5, 80, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 4, 0, 0, 0, 5, 0,
        0, 0,
    ]
}
#[test]
fn root_policy_rejects_nonservice_inputs_and_changed_grants() {
    for sid in [
        SYSTEM.to_vec(),
        vec![1, 0],
        vec![1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
        vec![1, 2, 0, 0, 0, 0, 0, 5, 80, 0, 0, 0, 0, 0, 0, 0],
    ] {
        assert_eq!(
            DescriptorPolicy::root_shape(sid).unwrap_err().primary,
            Failure::Policy(Denial::PolicyInput)
        );
    }
    let service = service_sid();
    let policy = DescriptorPolicy::root_shape(service.clone()).unwrap();
    // Literal data independent of the policy builder; a wrong grant must fail.
    let mut facts = DescriptorFacts {
        owner: SYSTEM.to_vec(),
        dacl_present: true,
        dacl_protected: true,
        dacl: Some(vec![
            Ace {
                grant: Grant {
                    sid: service,
                    mask: 0x0012_00ab,
                },
                flags: 0,
            },
            Ace {
                grant: Grant {
                    sid: SYSTEM.to_vec(),
                    mask: 0x001f_01ff,
                },
                flags: 0,
            },
        ]),
    };
    policy.compare(&facts).unwrap();
    facts.dacl.as_mut().unwrap()[0].grant.mask |= 0x100;
    policy_denial(&facts, &policy, Denial::Grants);
    facts.dacl.as_mut().unwrap()[0].grant.mask = 0x0012_00ab;
    facts.dacl.as_mut().unwrap()[0].grant.sid[12] = 9;
    policy_denial(&facts, &policy, Denial::Grants);
}
#[test]
fn native_add_file_mask_is_also_file_write_data() {
    fixture(|f| {
        // Regular empty file positive control for the shared numeric bit; no
        // directory, junction mutation, content write or root authority claim.
        f.set_acl(
            &format!("P(A;;0x1200ab;;;{})(A;;FA;;;SY)", f.sid_text),
            true,
        );
        let facts = inspect(f.handle.as_ref().unwrap()).unwrap();
        DescriptorPolicy {
            owner: f.sid.clone(),
            grants: vec![
                Grant {
                    sid: f.sid.clone(),
                    mask: 0x0012_00ab,
                },
                Grant {
                    sid: SYSTEM.to_vec(),
                    mask: 0x001f_01ff,
                },
            ],
        }
        .compare(&facts)
        .unwrap();
        let raw = unsafe {
            CreateFileW(
                wide(f.path.to_str().unwrap()).as_ptr(),
                FILE_WRITE_DATA,
                FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                null(),
                OPEN_EXISTING,
                FILE_FLAG_OPEN_REPARSE_POINT,
                null_mut(),
            )
        };
        assert_ne!(raw, INVALID_HANDLE_VALUE, "0x2 data-write control denied");
        close(unsafe { OwnedHandle::from_raw_handle(raw) }).unwrap();
    });
}
#[test]
fn error_aggregation_retains_primary_and_cleanup() {
    let primary = Error::new(Failure::Policy(Denial::Owner));
    let cleanup = Failure::Native {
        operation: "synthetic cleanup accounting",
        status: 123,
    };
    let result: Result<()> = finish(Err(primary), Err(Error::new(cleanup.clone())));
    let error = result.unwrap_err();
    assert_eq!(error.primary, Failure::Policy(Denial::Owner));
    assert_eq!(error.cleanup, vec![cleanup]);
}

#[test]
fn parser_duplicate_and_inherited_grants_are_denied() {
    let policy = DescriptorPolicy {
        owner: SYSTEM.to_vec(),
        grants: vec![Grant {
            sid: SYSTEM.to_vec(),
            mask: 0x001f_01ff,
        }],
    };
    let mut duplicate = image();
    duplicate.extend_from_slice(&image()[40..]);
    duplicate[34..36].copy_from_slice(&48u16.to_le_bytes());
    duplicate[36] = 2;
    policy_denial(
        &parse_snapshot(&duplicate).unwrap(),
        &policy,
        Denial::DuplicateGrant,
    );
    for flag in [1, 2, 4, 8, 16, 32, 64, 128] {
        let mut inherited = image();
        inherited[41] = flag;
        policy_denial(
            &parse_snapshot(&inherited).unwrap(),
            &policy,
            Denial::AceFlags,
        );
    }
}

impl OwnerDaclSnapshot {
    pub(crate) fn fixture_ace_headers(&self) -> Vec<(u8, u8)> {
        assert!(self.0.len() >= 20);
        let dacl = u32::from_le_bytes(self.0[16..20].try_into().unwrap()) as usize;
        assert!(dacl >= 20 && dacl <= self.0.len() - 8);
        let size = u16::from_le_bytes(self.0[dacl + 2..dacl + 4].try_into().unwrap()) as usize;
        assert!(size >= 8 && size <= self.0.len() - dacl);
        let end = dacl + size;
        let count = u16::from_le_bytes(self.0[dacl + 4..dacl + 6].try_into().unwrap());
        let mut at = dacl + 8;
        let mut headers = vec![];
        for _ in 0..count {
            assert!(at + 4 <= end);
            let size = u16::from_le_bytes(self.0[at + 2..at + 4].try_into().unwrap()) as usize;
            assert!(size >= 4 && size <= end - at);
            headers.push((self.0[at], self.0[at + 1]));
            at += size;
        }
        headers
    }
}
#[test]
fn opaque_native_ordered_deny_and_inherited_bytes_preserve_strict_refusal() {
    let mut owned = crate::relative_ntfs::tests::Fixture::ancestor().unwrap();
    let mut sentinel = None;
    let outcome = catch_unwind(AssertUnwindSafe(|| {
        sentinel = Some(owned.sentinel(0, "outside", 0x63).unwrap());
        let parent = owned.os_child(0, "Inheritance parent").unwrap();
        owned
            .set_dacl(
                parent,
                "D:P(D;OICI;0x2;;;WD)(A;OICI;FA;;;WD)(A;OICI;FA;;;SY)",
            )
            .unwrap();
        // The OS inherits the parent's ACEs during creation; no synthetic ID flag.
        let child = owned.os_child(parent, "Inherited child").unwrap();
        let handle = owned.input(child).unwrap();
        let checked = catch_unwind(AssertUnwindSafe(|| {
            let observed = observe_owner_dacl(&handle).unwrap();
            let again = observe_owner_dacl(&handle).unwrap();
            assert!(observed == again);
            let headers = observed.fixture_ace_headers();
            println!("OPAQUE_NATIVE ordered ACE headers={headers:?}");
            assert_eq!(
                headers.iter().map(|&(kind, _)| kind).collect::<Vec<_>>(),
                vec![1, 0, 0],
                "native deny then allow order"
            );
            assert!(
                headers.iter().all(|&(_, flags)| flags & 0x10 != 0),
                "native inherited precondition"
            );
            let refusal = inspect(&handle).unwrap_err();
            assert!(!refusal.has_cleanup_failure(), "strict cleanup={refusal:?}");
            assert_eq!(refusal.primary, Failure::Policy(Denial::UnsupportedAce));
        }));
        let closed = close(handle);
        assert!(
            closed.is_ok(),
            "operation={checked:?}; observation close={closed:?}"
        );
        if let Err(panic) = checked {
            resume_unwind(panic);
        }
    }));
    let unchanged = sentinel.map(|index| owned.verify_sentinel(index));
    let cleanup = owned.cleanup();
    assert!(
        cleanup.is_ok(),
        "operation={outcome:?}; sentinel={unchanged:?}; cleanup={cleanup:?}"
    );
    assert!(matches!(unchanged, Some(Ok(()))), "sentinel={unchanged:?}");
    if let Err(panic) = outcome {
        resume_unwind(panic);
    }
}
#[test]
fn opaque_copy_keeps_every_byte_without_interpreting_unsupported_aces() {
    let mut first = image();
    first[40] = 1;
    first[41] = 0x10;
    let snapshot = OwnerDaclSnapshot::copy(&first).unwrap();
    assert_eq!(snapshot.0, first);
    assert_eq!(
        parse_snapshot(&snapshot.0).unwrap_err().primary,
        Failure::Policy(Denial::UnsupportedAce)
    );
    let mut changed = first.clone();
    changed[44] ^= 1;
    assert!(snapshot != OwnerDaclSnapshot::copy(&changed).unwrap());
    assert!(OwnerDaclSnapshot::copy(&[0; 19]).is_err());
    assert!(OwnerDaclSnapshot::copy(&vec![0; 65536]).is_ok());
    assert!(OwnerDaclSnapshot::copy(&vec![0; 65537]).is_err());
}
#[test]
fn strict_parse_error_precedes_and_retains_release_failure() {
    let mut unsupported = image();
    unsupported[40] = 1;
    let result = finish(
        parse_snapshot(&unsupported),
        Err(Error::new(Failure::Native {
            operation: "LocalFree",
            status: 5,
        })),
    );
    let error = result.unwrap_err();
    assert_eq!(error.primary, Failure::Policy(Denial::UnsupportedAce));
    assert_eq!(
        error.cleanup,
        vec![Failure::Native {
            operation: "LocalFree",
            status: 5
        }]
    );
}

#[test]
fn primary_release_failure_is_cleanup_failure() {
    let primary = Error::new(Failure::Native {
        operation: "LocalFree",
        status: 5,
    });
    assert!(primary.has_cleanup_failure());
    let ordinary = Error::new(Failure::Native {
        operation: "GetSecurityInfo",
        status: 5,
    });
    assert!(!ordinary.has_cleanup_failure());
    let secondary = finish::<()>(deny(Denial::UnsupportedAce), Err(primary)).unwrap_err();
    assert!(secondary.has_cleanup_failure());
    assert_eq!(secondary.primary, Failure::Policy(Denial::UnsupportedAce));
}
