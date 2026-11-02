//! Dormant, allocation-free Windows x64 GetTokenInformation buffer decoder.
//!
//! The supplied base address and embedded pointers are numeric values only.
//! Successful decoding validates bytes, not acquisition, identity, or authority.
#![forbid(unsafe_code)]

use std::fmt;
use std::iter::FusedIterator;
use std::slice::ChunksExact;

const MAX_BUFFER: usize = 65_536;
const MAX_GROUPS: usize = 2_048;
const MAX_PRIVILEGES: usize = 256;

/// An explicit byte-layout selection, independent of the machine running this code.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Layout {
    WindowsX64,
    Unsupported,
}

/// Closed diagnostics contain no addresses, identifiers, bytes, or caller text.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DecodeError {
    UnsupportedLayout,
    UnsupportedClass,
    BufferTooLarge,
    AddressOverflow,
    MisalignedBuffer,
    Truncated,
    InvalidLength,
    CountLimit,
    ArithmeticOverflow,
    NullSid,
    MisalignedSid,
    PointerOutsideBuffer,
    SidOverlapsHeader,
    InvalidSid,
    InvalidEnum,
}

impl fmt::Display for DecodeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::UnsupportedLayout => "unsupported token buffer layout",
            Self::UnsupportedClass => "unsupported token information class",
            Self::BufferTooLarge => "token buffer exceeds bound",
            Self::AddressOverflow => "token buffer address overflow",
            Self::MisalignedBuffer => "token buffer header misaligned",
            Self::Truncated => "token buffer truncated",
            Self::InvalidLength => "token buffer length invalid",
            Self::CountLimit => "token entry count exceeds bound",
            Self::ArithmeticOverflow => "token buffer arithmetic overflow",
            Self::NullSid => "token SID pointer null",
            Self::MisalignedSid => "token SID pointer misaligned",
            Self::PointerOutsideBuffer => "token SID pointer outside buffer",
            Self::SidOverlapsHeader => "token SID overlaps header",
            Self::InvalidSid => "token SID invalid",
            Self::InvalidEnum => "token enum unsupported",
        })
    }
}

impl std::error::Error for DecodeError {}

/// Data-bearing views intentionally have no Debug implementation.
pub enum TokenInformation<'a> {
    SidAndAttributes(SidAndAttributes<'a>),
    Sid(Sid<'a>),
    Groups(Groups<'a>),
    Privileges(Privileges<'a>),
    Statistics(Statistics),
    Dword(u32),
}

#[derive(Clone, Copy)]
pub struct Sid<'a> {
    bytes: &'a [u8],
}

impl<'a> Sid<'a> {
    pub fn as_bytes(self) -> &'a [u8] {
        self.bytes
    }

    /// SID_IDENTIFIER_AUTHORITY is six bytes in most-significant-byte order.
    pub fn identifier_authority(self) -> u64 {
        self.bytes[2..8]
            .iter()
            .fold(0, |authority, byte| (authority << 8) | u64::from(*byte))
    }

    pub fn sub_authorities(self) -> SubAuthorities<'a> {
        SubAuthorities {
            entries: self.bytes[8..].chunks_exact(4),
        }
    }
}

#[derive(Clone)]
pub struct SubAuthorities<'a> {
    entries: ChunksExact<'a, u8>,
}

impl Iterator for SubAuthorities<'_> {
    type Item = u32;

    fn next(&mut self) -> Option<Self::Item> {
        self.entries.next().map(|entry| u32_at(entry, 0))
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.entries.size_hint()
    }
}

impl ExactSizeIterator for SubAuthorities<'_> {}
impl FusedIterator for SubAuthorities<'_> {}

#[derive(Clone, Copy)]
pub struct SidAndAttributes<'a> {
    sid: Sid<'a>,
    attributes: u32,
}

impl<'a> SidAndAttributes<'a> {
    pub fn sid(self) -> Sid<'a> {
        self.sid
    }

    pub fn attributes(self) -> u32 {
        self.attributes
    }
}

#[derive(Clone, Copy)]
pub struct Groups<'a> {
    buffer: &'a [u8],
    base: u64,
    header_end: usize,
    count: usize,
}

impl<'a> Groups<'a> {
    pub fn len(self) -> usize {
        self.count
    }

    pub fn is_empty(self) -> bool {
        self.count == 0
    }

    pub fn iter(self) -> GroupsIter<'a> {
        GroupsIter {
            buffer: self.buffer,
            base: self.base,
            entries: self.buffer[8..self.header_end].chunks_exact(16),
        }
    }
}

#[derive(Clone)]
pub struct GroupsIter<'a> {
    buffer: &'a [u8],
    base: u64,
    entries: ChunksExact<'a, u8>,
}

impl<'a> Iterator for GroupsIter<'a> {
    type Item = SidAndAttributes<'a>;

    fn next(&mut self) -> Option<Self::Item> {
        let entry = self.entries.next()?;
        // The constructor validated every pointer/extent. The immutable borrow
        // preserves those invariants for the complete lifetime of this iterator.
        let offset = (u64_at(entry, 0) - self.base) as usize;
        let sid_len = 8 + usize::from(self.buffer[offset + 1]) * 4;
        Some(SidAndAttributes {
            sid: Sid { bytes: &self.buffer[offset..offset + sid_len] },
            attributes: u32_at(entry, 8),
        })
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.entries.size_hint()
    }
}

impl ExactSizeIterator for GroupsIter<'_> {}
impl FusedIterator for GroupsIter<'_> {}

#[derive(Clone, Copy, PartialEq, Eq)]
pub struct Luid {
    pub low: u32,
    pub high: i32,
}

#[derive(Clone, Copy)]
pub struct Privilege {
    luid: Luid,
    attributes: u32,
}

impl Privilege {
    pub fn luid(self) -> Luid {
        self.luid
    }

    pub fn attributes(self) -> u32 {
        self.attributes
    }
}

#[derive(Clone, Copy)]
pub struct Privileges<'a> {
    entries: &'a [u8],
}

impl<'a> Privileges<'a> {
    pub fn len(self) -> usize {
        self.entries.len() / 12
    }

    pub fn is_empty(self) -> bool {
        self.entries.is_empty()
    }

    pub fn iter(self) -> PrivilegesIter<'a> {
        PrivilegesIter { entries: self.entries.chunks_exact(12) }
    }
}

#[derive(Clone)]
pub struct PrivilegesIter<'a> {
    entries: ChunksExact<'a, u8>,
}

impl Iterator for PrivilegesIter<'_> {
    type Item = Privilege;

    fn next(&mut self) -> Option<Self::Item> {
        self.entries.next().map(|entry| Privilege {
            luid: luid_at(entry, 0),
            attributes: u32_at(entry, 8),
        })
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        self.entries.size_hint()
    }
}

impl ExactSizeIterator for PrivilegesIter<'_> {}
impl FusedIterator for PrivilegesIter<'_> {}

#[derive(Clone, Copy)]
pub struct Statistics {
    pub token_id: Luid,
    pub authentication_id: Luid,
    pub expiration_time: i64,
    pub token_type: u32,
    /// Only meaningful for token_type 2; otherwise retained without interpretation.
    pub impersonation_level: u32,
    pub dynamic_charged: u32,
    pub dynamic_available: u32,
    pub group_count: u32,
    pub privilege_count: u32,
    pub modified_id: Luid,
}

/// Decode one supported returned buffer without reading through native pointers.
///
/// `bytes` must have the successful API retrieval's exact returned length and
/// `base_address` must identify its original byte zero. Those are caller claims,
/// not facts this pure decoder can establish. All returned references borrow
/// only the supplied slice. Validation finishes before any view is returned.
pub fn decode(
    layout: Layout,
    information_class: u32,
    bytes: &[u8],
    base_address: u64,
) -> Result<TokenInformation<'_>, DecodeError> {
    if layout != Layout::WindowsX64 {
        return Err(DecodeError::UnsupportedLayout);
    }
    let alignment = match information_class {
        1 | 2 | 4 | 5 | 10 | 11 | 25 | 30 => 8,
        3 | 8 | 9 | 12 | 18 | 20 | 21 | 23 | 24 | 26 | 27 | 29 => 4,
        _ => return Err(DecodeError::UnsupportedClass),
    };
    if bytes.len() > MAX_BUFFER {
        return Err(DecodeError::BufferTooLarge);
    }
    // Reject even a wrapping exclusive upper bound, before interpreting a field.
    base_address.checked_add(bytes.len() as u64).ok_or(DecodeError::AddressOverflow)?;
    if base_address % alignment != 0 {
        return Err(DecodeError::MisalignedBuffer);
    }

    match information_class {
        1 | 25 => {
            at_least(bytes, 16)?;
            let sid = validate_sid(bytes, base_address, u64_at(bytes, 0), 16)?;
            Ok(TokenInformation::SidAndAttributes(SidAndAttributes {
                sid,
                attributes: u32_at(bytes, 8),
            }))
        }
        4 | 5 => {
            at_least(bytes, 8)?;
            Ok(TokenInformation::Sid(validate_sid(bytes, base_address, u64_at(bytes, 0), 8)?))
        }
        2 | 11 | 30 => {
            at_least(bytes, 8)?;
            let count = u32_at(bytes, 0) as usize;
            let header_end = array_end(count, MAX_GROUPS, 8, 16)?;
            at_least(bytes, header_end)?;
            for entry in bytes[8..header_end].chunks_exact(16) {
                validate_sid(bytes, base_address, u64_at(entry, 0), header_end)?;
            }
            Ok(TokenInformation::Groups(Groups { buffer: bytes, base: base_address, header_end, count }))
        }
        3 => {
            at_least(bytes, 4)?;
            let length = array_end(u32_at(bytes, 0) as usize, MAX_PRIVILEGES, 4, 12)?;
            exact_length(bytes, length)?;
            Ok(TokenInformation::Privileges(Privileges { entries: &bytes[4..] }))
        }
        10 => {
            exact_length(bytes, 56)?;
            let token_type = u32_at(bytes, 24);
            let impersonation_level = u32_at(bytes, 28);
            valid_enum(token_type, 1, 2)?;
            if token_type == 2 {
                valid_enum(impersonation_level, 0, 3)?;
            }
            Ok(TokenInformation::Statistics(Statistics {
                token_id: luid_at(bytes, 0),
                authentication_id: luid_at(bytes, 8),
                expiration_time: u64_at(bytes, 16) as i64,
                token_type,
                impersonation_level,
                dynamic_charged: u32_at(bytes, 32),
                dynamic_available: u32_at(bytes, 36),
                group_count: u32_at(bytes, 40),
                privilege_count: u32_at(bytes, 44),
                modified_id: luid_at(bytes, 48),
            }))
        }
        _ => {
            exact_length(bytes, 4)?;
            let value = u32_at(bytes, 0);
            match information_class {
                8 => valid_enum(value, 1, 2)?,
                9 => valid_enum(value, 0, 3)?,
                18 => valid_enum(value, 1, 3)?,
                _ => (),
            }
            Ok(TokenInformation::Dword(value))
        }
    }
}

fn validate_sid(
    bytes: &[u8],
    base: u64,
    pointer: u64,
    header_end: usize,
) -> Result<Sid<'_>, DecodeError> {
    if pointer == 0 {
        return Err(DecodeError::NullSid);
    }
    if pointer % 4 != 0 {
        return Err(DecodeError::MisalignedSid);
    }
    let offset = pointer.checked_sub(base).ok_or(DecodeError::PointerOutsideBuffer)?;
    if offset >= bytes.len() as u64 {
        return Err(DecodeError::PointerOutsideBuffer);
    }
    // offset is now less than the bounded slice length and fits usize.
    let offset = offset as usize;
    if offset < header_end {
        return Err(DecodeError::SidOverlapsHeader);
    }
    let header_extent = offset.checked_add(8).ok_or(DecodeError::ArithmeticOverflow)?;
    at_least(bytes, header_extent)?;
    if bytes[offset] != 1 || bytes[offset + 1] > 15 {
        return Err(DecodeError::InvalidSid);
    }
    let length = array_end(usize::from(bytes[offset + 1]), 15, 8, 4)?;
    let end = offset.checked_add(length).ok_or(DecodeError::ArithmeticOverflow)?;
    pointer.checked_add(length as u64).ok_or(DecodeError::AddressOverflow)?;
    at_least(bytes, end)?;
    Ok(Sid { bytes: &bytes[offset..end] })
}

fn at_least(bytes: &[u8], length: usize) -> Result<(), DecodeError> {
    if bytes.len() < length { Err(DecodeError::Truncated) } else { Ok(()) }
}

fn exact_length(bytes: &[u8], length: usize) -> Result<(), DecodeError> {
    at_least(bytes, length)?;
    if bytes.len() == length { Ok(()) } else { Err(DecodeError::InvalidLength) }
}

fn array_end(count: usize, maximum: usize, offset: usize, stride: usize) -> Result<usize, DecodeError> {
    if count > maximum {
        return Err(DecodeError::CountLimit);
    }
    count.checked_mul(stride).and_then(|size| offset.checked_add(size))
        .ok_or(DecodeError::ArithmeticOverflow)
}

fn valid_enum(value: u32, low: u32, high: u32) -> Result<(), DecodeError> {
    if (low..=high).contains(&value) { Ok(()) } else { Err(DecodeError::InvalidEnum) }
}

// These readers operate only on fixed headers or entries whose complete length
// was checked by the constructor; no cast, alignment-dependent read, or pointer
// dereference occurs. Array literals avoid fallible conversions or allocations.
fn u32_at(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes([bytes[offset], bytes[offset + 1], bytes[offset + 2], bytes[offset + 3]])
}

fn u64_at(bytes: &[u8], offset: usize) -> u64 {
    u64::from_le_bytes([
        bytes[offset], bytes[offset + 1], bytes[offset + 2], bytes[offset + 3],
        bytes[offset + 4], bytes[offset + 5], bytes[offset + 6], bytes[offset + 7],
    ])
}

fn luid_at(bytes: &[u8], offset: usize) -> Luid {
    Luid { low: u32_at(bytes, offset), high: u32_at(bytes, offset + 4) as i32 }
}
