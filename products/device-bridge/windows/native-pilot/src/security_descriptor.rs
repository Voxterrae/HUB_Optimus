//! Private file-security metadata observations; no root or identity authority.
//!
//! Supported input is a revision-1 self-relative SD (20-byte header), revision
//! 2/4 ACL (8-byte header), and standard allow ACEs (4-byte header, u32 mask,
//! revision-1 SID with 0..15 u32 subauthorities). Sizes, offsets, masks and SID
//! subauthorities are little-endian; the six authority bytes retain their
//! big-endian SID encoding. Offsets and ACE sizes are DWORD-aligned. Regions cannot
//! overlap. Unknown ACE layouts fail; every ACE flag denies policy matching.
//! Copy/parser limit: 64 KiB, applied AFTER GetSecurityInfo's OS allocation.
//!
//! Root-shape metadata: SYSTEM owner/full access 0x001f01ff; expected distinct
//! service SID gets 0x001200ab (READ_CONTROL, SYNCHRONIZE, LIST_DIRECTORY,
//! ADD_FILE, READ_EA, TRAVERSE, READ_ATTRIBUTES). No ADD_SUBDIRECTORY,
//! DELETE/DELETE_CHILD, WRITE_DAC/WRITE_OWNER or WRITE_ATTRIBUTES grant.
//! ADD_FILE shares the FILE_WRITE_DATA bit accepted by reparse mutation APIs;
//! this grant is not a no-reparse guarantee. SID bytes and a match do not
//! authenticate a service or protect an ancestor.

use std::os::windows::io::{AsRawHandle, OwnedHandle};
use std::ptr::null_mut;
use windows_sys::Win32::Foundation::{GetLastError, LocalFree};
use windows_sys::Win32::Security::Authorization::{GetSecurityInfo, SE_FILE_OBJECT};
use windows_sys::Win32::Security::{
    DACL_SECURITY_INFORMATION, GetSecurityDescriptorLength, OWNER_SECURITY_INFORMATION,
    PSECURITY_DESCRIPTOR,
};

mod os_ancestor;

const MAX_SNAPSHOT: usize = 65_536;
const SYSTEM_SID: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0];

#[derive(Debug, Clone, PartialEq, Eq)]
enum Denial {
    Bounds,
    Layout,
    Sid,
    UnsupportedAce,
    Owner,
    AbsentDacl,
    NullDacl,
    UnprotectedDacl,
    AceFlags,
    DuplicateGrant,
    Grants,
    PolicyInput,
}
#[derive(Debug, Clone, PartialEq, Eq)]
enum Failure {
    Native {
        operation: &'static str,
        status: u32,
    },
    Policy(Denial),
}
#[derive(Debug)]
pub(super) struct Error {
    primary: Failure,
    cleanup: Vec<Failure>,
}
type Result<T> = std::result::Result<T, Error>;
impl Error {
    pub(super) fn has_cleanup_failure(&self) -> bool {
        !self.cleanup.is_empty()
            || matches!(
                self.primary,
                Failure::Native {
                    operation: "LocalFree",
                    ..
                }
            )
    }
    fn new(primary: Failure) -> Self {
        Self {
            primary,
            cleanup: Vec::new(),
        }
    }
}
fn deny<T>(reason: Denial) -> Result<T> {
    Err(Error::new(Failure::Policy(reason)))
}
fn finish<T>(result: Result<T>, cleanup: Result<()>) -> Result<T> {
    match (result, cleanup) {
        (result, Ok(())) => result,
        (Ok(_), Err(error)) => Err(error),
        (Err(mut primary), Err(cleanup)) => {
            primary.cleanup.push(cleanup.primary);
            primary.cleanup.extend(cleanup.cleanup);
            Err(primary)
        }
    }
}

struct NativeAllocation(PSECURITY_DESCRIPTOR);
impl NativeAllocation {
    fn release(mut self) -> Result<()> {
        let raw = std::mem::replace(&mut self.0, null_mut());
        if raw.is_null() || unsafe { LocalFree(raw) }.is_null() {
            Ok(())
        } else {
            Err(Error::new(Failure::Native {
                operation: "LocalFree",
                status: unsafe { GetLastError() },
            }))
        }
    }
}
impl Drop for NativeAllocation {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe {
                LocalFree(self.0);
            }
        }
    }
}

/// Borrow a live handle; never open a path, change the object, or retain its
/// identity. The returned snapshot can be stale immediately after this call.
fn inspect(handle: &OwnedHandle) -> Result<DescriptorFacts> {
    capture_transform(handle, parse_snapshot)
}

/// Ordered opaque bytes returned by the OS. No policy, grants or effective access.
#[derive(Clone, PartialEq, Eq)]
pub(super) struct OwnerDaclSnapshot(Vec<u8>);
impl OwnerDaclSnapshot {
    /// Private diagnostic only; no effective-access or retained-chain authority.
    pub(super) fn matches_os_ancestor_policy(&self) -> Result<()> {
        os_ancestor::compare(&self.0)
    }

    fn copy(bytes: &[u8]) -> Result<Self> {
        if !(20..=MAX_SNAPSHOT).contains(&bytes.len()) {
            return deny(Denial::Bounds);
        }
        Ok(Self(bytes.to_vec()))
    }
}
pub(super) fn observe_owner_dacl(handle: &OwnedHandle) -> Result<OwnerDaclSnapshot> {
    capture_transform(handle, OwnerDaclSnapshot::copy)
}

// Transform BEFORE checked release: preserve strict parser error precedence and
// aggregate release failure even when parsing fails. Never parse arbitrary bytes via FFI.
fn capture_transform<T>(
    handle: &OwnedHandle,
    transform: impl FnOnce(&[u8]) -> Result<T>,
) -> Result<T> {
    let mut raw = null_mut();
    let status = unsafe {
        GetSecurityInfo(
            handle.as_raw_handle(),
            SE_FILE_OBJECT,
            OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
            null_mut(),
            null_mut(),
            null_mut(),
            null_mut(),
            &mut raw,
        )
    };
    let allocation = NativeAllocation(raw);
    let result = (|| {
        if status != 0 {
            return Err(Error::new(Failure::Native {
                operation: "GetSecurityInfo",
                status,
            }));
        }
        if raw.is_null() {
            return deny(Denial::Layout);
        }
        // Only the valid OS-returned allocation reaches this Windows getter.
        // Arbitrary/malformed byte tests use the safe parser below, never FFI.
        let length = unsafe { GetSecurityDescriptorLength(raw) } as usize;
        if !(20..=MAX_SNAPSHOT).contains(&length) {
            return deny(Denial::Bounds);
        }
        let snapshot = unsafe { std::slice::from_raw_parts(raw.cast::<u8>(), length) }.to_vec();
        transform(&snapshot)
    })();
    finish(result, allocation.release())
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct Grant {
    sid: Vec<u8>,
    mask: u32,
}
#[derive(Debug)]
struct Ace {
    grant: Grant,
    flags: u8,
}
#[derive(Debug)]
struct DescriptorFacts {
    owner: Vec<u8>,
    dacl_present: bool,
    dacl_protected: bool,
    dacl: Option<Vec<Ace>>,
}
#[derive(Debug)]
struct DescriptorPolicy {
    owner: Vec<u8>,
    grants: Vec<Grant>,
}

impl DescriptorPolicy {
    /// An expectation only. A supplied SID is not measured/authenticated identity.
    fn root_shape(service: Vec<u8>) -> Result<Self> {
        // NT SERVICE shape S-1-5-80 plus five DWORDs. No account/name lookup or
        // authentication: another fabricated service-shaped SID also fits.
        if service.len() != 32 || !service.starts_with(&[1, 6, 0, 0, 0, 0, 0, 5, 80, 0, 0, 0]) {
            return deny(Denial::PolicyInput);
        }
        Ok(Self {
            owner: SYSTEM_SID.to_vec(),
            grants: vec![
                Grant {
                    sid: SYSTEM_SID.to_vec(),
                    mask: 0x001f_01ff,
                },
                Grant {
                    sid: service,
                    mask: 0x0012_00ab,
                },
            ],
        })
    }
    fn compare(&self, facts: &DescriptorFacts) -> Result<()> {
        if sid_size(&self.owner).ok() != Some(self.owner.len())
            || self.grants.is_empty()
            || self.grants.iter().any(|grant| {
                sid_size(&grant.sid).ok() != Some(grant.sid.len())
                    || grant.mask == 0
                    || grant.mask & !0x001f_01ff != 0
            })
        {
            return deny(Denial::PolicyInput);
        }
        let mut expected = self.grants.clone();
        expected.sort();
        if expected.windows(2).any(|pair| pair[0].sid == pair[1].sid) {
            return deny(Denial::PolicyInput);
        }
        if facts.owner != self.owner {
            return deny(Denial::Owner);
        }
        if !facts.dacl_present {
            return deny(Denial::AbsentDacl);
        }
        let Some(aces) = &facts.dacl else {
            return deny(Denial::NullDacl);
        };
        if !facts.dacl_protected {
            return deny(Denial::UnprotectedDacl);
        }
        if aces.iter().any(|ace| ace.flags != 0) {
            return deny(Denial::AceFlags);
        }
        let mut observed: Vec<_> = aces.iter().map(|ace| ace.grant.clone()).collect();
        observed.sort();
        // Deliberately require one exact grant per SID, not aggregation of
        // duplicate/split grants; allowed ACE ordering alone is immaterial.
        if observed.windows(2).any(|pair| pair[0].sid == pair[1].sid) {
            return deny(Denial::DuplicateGrant);
        }
        if observed != expected {
            return deny(Denial::Grants);
        }
        Ok(())
    }
}

fn region(bytes: &[u8], start: usize, length: usize) -> Result<&[u8]> {
    let end = start
        .checked_add(length)
        .ok_or_else(|| Error::new(Failure::Policy(Denial::Bounds)))?;
    bytes
        .get(start..end)
        .ok_or_else(|| Error::new(Failure::Policy(Denial::Bounds)))
}
fn u16_at(bytes: &[u8], start: usize) -> Result<u16> {
    let value = region(bytes, start, 2)?;
    Ok(u16::from_le_bytes([value[0], value[1]]))
}
fn u32_at(bytes: &[u8], start: usize) -> Result<u32> {
    let value = region(bytes, start, 4)?;
    Ok(u32::from_le_bytes([value[0], value[1], value[2], value[3]]))
}
fn sid_size(bytes: &[u8]) -> Result<usize> {
    let header = region(bytes, 0, 8)?;
    if header[0] != 1 || header[1] > 15 {
        return deny(Denial::Sid);
    }
    let length = 8 + header[1] as usize * 4;
    region(bytes, 0, length)?;
    Ok(length)
}
fn offset(bytes: &[u8], field: usize) -> Result<usize> {
    let offset = u32_at(bytes, field)? as usize;
    if offset != 0 && (offset < 20 || !offset.is_multiple_of(4) || offset >= bytes.len()) {
        return deny(Denial::Layout);
    }
    Ok(offset)
}
fn add_region(regions: &mut Vec<(usize, usize)>, start: usize, length: usize) -> Result<()> {
    let end = start
        .checked_add(length)
        .ok_or_else(|| Error::new(Failure::Policy(Denial::Bounds)))?;
    if regions
        .iter()
        .any(|&(other_start, other_end)| start < other_end && other_start < end)
    {
        return deny(Denial::Layout);
    }
    regions.push((start, end));
    Ok(())
}
fn parse_snapshot(bytes: &[u8]) -> Result<DescriptorFacts> {
    if !(20..=MAX_SNAPSHOT).contains(&bytes.len()) {
        return deny(Denial::Bounds);
    }
    let control = u16_at(bytes, 2)?;
    if bytes[0] != 1 || bytes[1] != 0 || control & 0x8000 == 0 {
        return deny(Denial::Layout);
    }
    let mut regions = Vec::new();
    let owner_offset = offset(bytes, 4)?;
    if owner_offset == 0 {
        return deny(Denial::Sid);
    }
    let owner_length = sid_size(&bytes[owner_offset..])?;
    add_region(&mut regions, owner_offset, owner_length)?;
    let owner = region(bytes, owner_offset, owner_length)?.to_vec();
    // A group is not queried/compared, but validate its layout if the OS includes it.
    let group_offset = offset(bytes, 8)?;
    if group_offset != 0 {
        let group_length = sid_size(&bytes[group_offset..])?;
        add_region(&mut regions, group_offset, group_length)?;
    }
    // This owner+DACL inspector does not request or interpret SACLs.
    if u32_at(bytes, 12)? != 0 {
        return deny(Denial::Layout);
    }
    let dacl_offset = offset(bytes, 16)?;
    let dacl_present = control & 4 != 0;
    if !dacl_present && dacl_offset != 0 {
        return deny(Denial::Layout);
    }
    let mut facts = DescriptorFacts {
        owner,
        dacl_present,
        dacl_protected: control & 0x1000 != 0,
        dacl: None,
    };
    if dacl_offset == 0 {
        return Ok(facts);
    }
    let header = region(bytes, dacl_offset, 8)?;
    let length = u16_at(header, 2)? as usize;
    if ![2, 4].contains(&header[0])
        || header[1] != 0
        || u16_at(header, 6)? != 0
        || length < 8
        || !length.is_multiple_of(4)
    {
        return deny(Denial::Layout);
    }
    let acl = region(bytes, dacl_offset, length)?;
    add_region(&mut regions, dacl_offset, length)?;
    let count = u16_at(header, 4)? as usize;
    if count > (length - 8) / 16 {
        return deny(Denial::Bounds);
    }
    let mut aces = Vec::with_capacity(count);
    let mut cursor = 8;
    for _ in 0..count {
        let header = region(acl, cursor, 4)?;
        let ace_length = u16_at(header, 2)? as usize;
        if ace_length < 16 || !ace_length.is_multiple_of(4) {
            return deny(Denial::Layout);
        }
        let ace = region(acl, cursor, ace_length)?;
        if ace[0] != 0 {
            return deny(Denial::UnsupportedAce);
        }
        let sid_length = sid_size(&ace[8..])?;
        if sid_length != ace_length - 8 {
            return deny(Denial::Layout);
        }
        aces.push(Ace {
            grant: Grant {
                sid: ace[8..].to_vec(),
                mask: u32_at(ace, 4)?,
            },
            flags: ace[1],
        });
        cursor += ace_length; // bounded by region(acl, ...) above
    }
    // ACL slack is not a grant. Accept only zero-filled alignment/free space.
    if acl[cursor..].iter().any(|&byte| byte != 0) {
        return deny(Denial::Layout);
    }
    facts.dacl = Some(aces);
    Ok(facts)
}

#[cfg(test)]
mod tests;
