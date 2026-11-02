//! Synthetic conformance only: this test executable never queries host tokens.
#![forbid(unsafe_code)]

#[path = "native_token_buffer.rs"]
mod native_token_buffer;

use native_token_buffer::{decode, DecodeError, Layout, TokenInformation};

const BASE: u64 = 0x0000_1234_0000_0000;
const SID: [u8; 12] = [1, 1, 0, 0, 0, 0, 0, 5, 32, 0, 0, 0];

fn put32(b: &mut [u8], at: usize, value: u32) {
    b[at..at + 4].copy_from_slice(&value.to_le_bytes());
}

fn put64(b: &mut [u8], at: usize, value: u64) {
    b[at..at + 8].copy_from_slice(&value.to_le_bytes());
}

fn single_sid(class: u32, attributes: u32) -> Vec<u8> {
    let header = if class == 4 || class == 5 { 8 } else { 16 };
    let mut b = vec![0; header + SID.len()];
    put64(&mut b, 0, BASE + header as u64);
    if header == 16 {
        put32(&mut b, 8, attributes);
    }
    b[header..].copy_from_slice(&SID);
    b
}

fn groups(count: usize, same_pointer: bool) -> Vec<u8> {
    let header = 8 + count * 16;
    let mut b = vec![0; header + if count == 0 { 0 } else { SID.len() * count }];
    put32(&mut b, 0, count as u32);
    for i in 0..count {
        let offset = header + if same_pointer { 0 } else { SID.len() * i };
        put64(&mut b, 8 + i * 16, BASE + offset as u64);
        put32(&mut b, 16 + i * 16, [0, 0x10, 0xffff_ffff][i % 3]);
        b[offset..offset + SID.len()].copy_from_slice(&SID);
    }
    b
}

fn privileges(count: usize) -> Vec<u8> {
    let mut b = vec![0; 4 + count * 12];
    put32(&mut b, 0, count as u32);
    for i in 0..count {
        put32(&mut b, 4 + i * 12, 0x89ab_cdef);
        put32(&mut b, 8 + i * 12, 0xffff_fffe);
        put32(&mut b, 12 + i * 12, [0, 0x8000_0000, 0xffff_ffff][i % 3]);
    }
    b
}

fn statistics() -> [u8; 56] {
    let mut b = [0; 56];
    // Deliberately distinct halves: truncating/reordering any LUID is observable.
    put32(&mut b, 0, 0x1122_3344);
    put32(&mut b, 4, 0xffff_fffe);
    put32(&mut b, 8, 0x5566_7788);
    put32(&mut b, 12, 0x8000_0000);
    put64(&mut b, 16, 0x7fff_ffff_ffff_ffff);
    put32(&mut b, 24, 2);
    put32(&mut b, 28, 3);
    put32(&mut b, 32, 0x0002_0000); // Internal memory is not the returned-buffer cap.
    put32(&mut b, 36, 0x0001_0000);
    put32(&mut b, 40, 7);
    put32(&mut b, 44, 9);
    put32(&mut b, 48, 0x99aa_bbcc);
    put32(&mut b, 52, 0x7fff_ffff);
    b
}

fn error(class: u32, b: &[u8]) -> DecodeError {
    match decode(Layout::WindowsX64, class, b, BASE) {
        Err(e) => e,
        Ok(_) => panic!("malformed synthetic fixture was accepted"),
    }
}

#[test]
fn user_and_integrity_borrow_exact_sid_and_preserve_all_attributes() {
    for class in [1, 25] {
        let b = single_sid(class, 0xfedc_ba98);
        let TokenInformation::SidAndAttributes(v) =
            decode(Layout::WindowsX64, class, &b, BASE).unwrap()
        else { panic!("wrong information shape") };
        assert_eq!(v.attributes(), 0xfedc_ba98);
        assert_eq!(v.sid().as_bytes(), SID);
        assert_eq!(v.sid().as_bytes().as_ptr(), b[16..].as_ptr());
        assert_eq!(v.sid().identifier_authority(), 5);
        assert_eq!(v.sid().sub_authorities().collect::<Vec<_>>(), [32]);
    }
}

#[test]
fn owner_and_primary_group_have_pointer_only_headers() {
    for class in [4, 5] {
        let b = single_sid(class, 0);
        let TokenInformation::Sid(v) =
            decode(Layout::WindowsX64, class, &b, BASE).unwrap()
        else { panic!("wrong information shape") };
        assert_eq!(v.as_bytes(), SID);
        assert_eq!(v.as_bytes().as_ptr(), b[8..].as_ptr());
    }
}

#[test]
fn groups_restricted_sids_and_capabilities_preserve_order_duplicates_and_bits() {
    for class in [2, 11, 30] {
        // Three records alias one SID. Entries must not be deduplicated or filtered.
        let b = groups(3, true);
        let TokenInformation::Groups(v) =
            decode(Layout::WindowsX64, class, &b, BASE).unwrap()
        else { panic!("wrong information shape") };
        assert_eq!(v.len(), 3);
        let mut it = v.iter();
        assert_eq!(it.len(), 3);
        for expected in [0, 0x10, 0xffff_ffff] {
            let group = it.next().unwrap();
            assert_eq!(group.attributes(), expected);
            assert_eq!(group.sid().as_bytes(), SID);
        }
        assert!(it.next().is_none());
        assert_eq!(it.len(), 0);
    }
}

#[test]
fn complete_group_validation_precedes_returning_any_view() {
    let mut b = groups(2, false);
    let late_pointer = BASE + b.len() as u64 - 4;
    put64(&mut b, 24, late_pointer);
    assert_eq!(error(2, &b), DecodeError::Truncated);
}

#[test]
fn empty_arrays_and_exact_group_limit_are_supported() {
    for count in [0, 2048] {
        let b = groups(count, true);
        let TokenInformation::Groups(v) = decode(Layout::WindowsX64, 2, &b, BASE).unwrap()
        else { panic!("wrong information shape") };
        assert_eq!(v.len(), count);
        assert_eq!(v.is_empty(), count == 0);
        assert_eq!(v.iter().count(), count);
    }
    let b = groups(2049, true);
    assert_eq!(error(2, &b), DecodeError::CountLimit);
}

#[test]
fn malicious_group_counts_and_truncated_entry_arrays_are_rejected() {
    let mut b = [0; 8];
    put32(&mut b, 0, u32::MAX);
    assert_eq!(error(2, &b), DecodeError::CountLimit);
    put32(&mut b, 0, 1);
    assert_eq!(error(2, &b), DecodeError::Truncated);
    assert_eq!(error(2, &[0; 7]), DecodeError::Truncated);
}

#[test]
fn sid_pointers_must_be_nonnull_aligned_contained_and_outside_the_header() {
    let mut b = single_sid(1, 0);
    for (pointer, expected) in [
        (0, DecodeError::NullSid),
        (BASE - 4, DecodeError::PointerOutsideBuffer),
        (BASE + 28, DecodeError::PointerOutsideBuffer),
        (BASE + 17, DecodeError::MisalignedSid),
        (BASE + 4, DecodeError::SidOverlapsHeader),
    ] {
        put64(&mut b, 0, pointer);
        assert_eq!(error(1, &b), expected);
    }
    let mut b = groups(2, true);
    put64(&mut b, 8, BASE + 24); // Another array entry is not a SID payload.
    assert_eq!(error(2, &b), DecodeError::SidOverlapsHeader);
}

#[test]
fn sid_extents_revision_and_subauthority_bound_are_checked() {
    let mut b = single_sid(1, 0);
    b[16] = 2;
    assert_eq!(error(1, &b), DecodeError::InvalidSid);
    b[16] = 1;
    b[17] = 16;
    assert_eq!(error(1, &b), DecodeError::InvalidSid);
    b[17] = 2;
    assert_eq!(error(1, &b), DecodeError::Truncated);
    b[17] = 1;
    b.truncate(23);
    assert_eq!(error(1, &b), DecodeError::Truncated);
}

#[test]
fn zero_and_fifteen_subauthorities_preserve_authority_and_full_u32_values() {
    for count in [0, 15] {
        let mut b = vec![0; 16 + 8 + count * 4];
        put64(&mut b, 0, BASE + 16);
        b[16] = 1;
        b[17] = count as u8;
        b[18..24].copy_from_slice(&[0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc]);
        for i in 0..count { put32(&mut b, 24 + i * 4, u32::MAX - i as u32); }
        let TokenInformation::SidAndAttributes(v) =
            decode(Layout::WindowsX64, 1, &b, BASE).unwrap()
        else { panic!("wrong information shape") };
        assert_eq!(v.sid().as_bytes().len(), 8 + count * 4);
        assert_eq!(v.sid().identifier_authority(), 0x1234_5678_9abc);
        assert_eq!(v.sid().sub_authorities().len(), count);
        assert_eq!(v.sid().sub_authorities().collect::<Vec<_>>(),
                   (0..count).map(|i| u32::MAX - i as u32).collect::<Vec<_>>());
    }
}

#[test]
fn privileges_preserve_duplicate_luids_signed_high_halves_and_raw_attributes() {
    let b = privileges(3);
    let TokenInformation::Privileges(v) = decode(Layout::WindowsX64, 3, &b, BASE).unwrap()
    else { panic!("wrong information shape") };
    assert_eq!(v.len(), 3);
    for (p, expected) in v.iter().zip([0, 0x8000_0000, 0xffff_ffff]) {
        assert_eq!(p.luid().low, 0x89ab_cdef);
        assert_eq!(p.luid().high, -2);
        assert_eq!(p.attributes(), expected);
    }
    assert_eq!(v.iter().len(), 3);
}

#[test]
fn privilege_array_exact_length_and_limit_are_enforced() {
    for count in [0, 256] {
        let b = privileges(count);
        let TokenInformation::Privileges(v) = decode(Layout::WindowsX64, 3, &b, BASE).unwrap()
        else { panic!("wrong information shape") };
        assert_eq!(v.len(), count);
        assert_eq!(v.is_empty(), count == 0);
        assert_eq!(v.iter().count(), count);
    }
    assert_eq!(error(3, &privileges(257)), DecodeError::CountLimit);
    let mut b = privileges(1);
    b.pop();
    assert_eq!(error(3, &b), DecodeError::Truncated);
    b.extend_from_slice(&[0, 0]);
    assert_eq!(error(3, &b), DecodeError::InvalidLength);
    assert_eq!(error(3, &[0xff; 4]), DecodeError::CountLimit);
}

#[test]
fn statistics_uses_x64_offsets_without_conflating_luids_or_memory_sizes() {
    let b = statistics();
    let TokenInformation::Statistics(v) = decode(Layout::WindowsX64, 10, &b, BASE).unwrap()
    else { panic!("wrong information shape") };
    assert_eq!(v.token_id.low, 0x1122_3344);
    assert_eq!(v.token_id.high, -2);
    assert_eq!(v.authentication_id.low, 0x5566_7788);
    assert_eq!(v.authentication_id.high, i32::MIN);
    assert_eq!(v.modified_id.low, 0x99aa_bbcc);
    assert_eq!(v.modified_id.high, i32::MAX);
    assert_eq!(v.expiration_time, i64::MAX);
    assert_eq!(v.token_type, 2);
    assert_eq!(v.impersonation_level, 3);
    assert_eq!(v.dynamic_charged, 131072);
    assert_eq!(v.dynamic_available, 65536);
    assert_eq!(v.group_count, 7);
    assert_eq!(v.privilege_count, 9);
}

#[test]
fn statistics_rejects_truncation_extensions_and_unknown_token_type() {
    let mut b = statistics().to_vec();
    assert_eq!(error(10, &b[..55]), DecodeError::Truncated);
    b.push(0);
    assert_eq!(error(10, &b), DecodeError::InvalidLength);
    b.pop();
    put32(&mut b, 24, 0);
    assert_eq!(error(10, &b), DecodeError::InvalidEnum);
    put32(&mut b, 24, 3);
    assert_eq!(error(10, &b), DecodeError::InvalidEnum);
}

#[test]
fn statistics_checks_impersonation_enum_only_when_semantically_applicable() {
    let mut b = statistics();
    put32(&mut b, 28, 4);
    assert_eq!(error(10, &b), DecodeError::InvalidEnum);
    put32(&mut b, 24, 1);
    let TokenInformation::Statistics(v) = decode(Layout::WindowsX64, 10, &b, BASE).unwrap()
    else { panic!("wrong information shape") };
    assert_eq!(v.impersonation_level, 4); // Unspecified primary-token field stays raw.
}

#[test]
fn scalar_classes_require_exact_dwords_and_preserve_nonzero_raw_values() {
    for class in [12, 20, 21, 23, 24, 26, 27, 29] {
        let b = 0xfedc_ba98_u32.to_le_bytes();
        let TokenInformation::Dword(v) = decode(Layout::WindowsX64, class, &b, BASE).unwrap()
        else { panic!("wrong information shape") };
        assert_eq!(v, 0xfedc_ba98);
        assert_eq!(error(class, &b[..1]), DecodeError::Truncated);
        assert_eq!(error(class, &[0; 5]), DecodeError::InvalidLength);
    }
    assert_eq!(error(21, &[1]), DecodeError::Truncated); // No historical one-byte exception.
}

#[test]
fn known_scalar_enums_accept_documented_values_and_refuse_unknown_values() {
    for (class, good, bad) in [(8_u32, 1_u32, 0_u32), (8, 2, 3), (9, 0, 4), (9, 3, u32::MAX),
                               (18, 1, 0), (18, 3, 4)] {
        assert!(decode(Layout::WindowsX64, class, &good.to_le_bytes(), BASE).is_ok());
        assert_eq!(error(class, &bad.to_le_bytes()), DecodeError::InvalidEnum);
    }
}

#[test]
fn unsupported_layout_and_information_class_have_no_partial_success() {
    assert!(matches!(decode(Layout::Unsupported, 12, &[0; 4], BASE),
                     Err(DecodeError::UnsupportedLayout)));
    for class in [0, 6, 7, 13, 19, 22, 28, u32::MAX] {
        assert_eq!(error(class, &[0; 64]), DecodeError::UnsupportedClass);
    }
}

#[test]
fn buffer_cap_address_overflow_and_native_header_alignment_are_enforced() {
    let mut b = single_sid(1, 0);
    b.resize(65536, 0); // Uninterpreted native padding does not enlarge the borrowed SID.
    assert!(decode(Layout::WindowsX64, 1, &b, BASE).is_ok());
    b.push(0);
    assert_eq!(error(1, &b), DecodeError::BufferTooLarge);
    assert!(matches!(decode(Layout::WindowsX64, 12, &[0; 4], u64::MAX - 3),
                     Err(DecodeError::AddressOverflow)));
    assert!(matches!(decode(Layout::WindowsX64, 1, &single_sid(1, 0), BASE + 4),
                     Err(DecodeError::MisalignedBuffer)));
    assert!(matches!(decode(Layout::WindowsX64, 12, &[0; 4], BASE + 2),
                     Err(DecodeError::MisalignedBuffer)));
    // Privilege/scalar ABI alignment is four, not pointer alignment eight.
    assert!(decode(Layout::WindowsX64, 3, &privileges(1), BASE + 4).is_ok());
    assert!(decode(Layout::WindowsX64, 12, &[0; 4], BASE + 4).is_ok());
}

#[test]
fn all_fixed_headers_reject_every_truncated_prefix() {
    for (class, b, header) in [(1, single_sid(1, 0), 16), (25, single_sid(25, 0), 16),
                              (4, single_sid(4, 0), 8), (5, single_sid(5, 0), 8),
                              (2, groups(1, true), 8), (3, privileges(1), 4),
                              (10, statistics().to_vec(), 56)] {
        for end in 0..header { assert_eq!(error(class, &b[..end]), DecodeError::Truncated); }
    }
}

#[test]
fn rejection_debug_and_display_are_fixed_diagnostics() {
    let b = single_sid(1, 0);
    let e = error(1, &b[..17]);
    assert_eq!(format!("{e:?}"), "Truncated");
    assert_eq!(format!("{e}"), "token buffer truncated");
}

// Independent ABI assertions: transcribed Microsoft winnt.h field order, not
// decoder constants. repr(C) uses the compiler's actual Windows x64 ABI.
#[cfg(all(target_os = "windows", target_arch = "x86_64"))]
#[test]
fn windows_x64_compiler_confirms_documented_c_layouts() {
    use std::ffi::c_void;
    use std::mem::{align_of, offset_of, size_of};
    #[repr(C)] struct Luid { low: u32, high: i32 }
    #[repr(C)] struct SidAndAttributes { sid: *mut c_void, attributes: u32 }
    #[repr(C)] struct TokenGroups { count: u32, groups: [SidAndAttributes; 1] }
    #[repr(C)] struct LuidAndAttributes { luid: Luid, attributes: u32 }
    #[repr(C)] struct TokenPrivileges { count: u32, privileges: [LuidAndAttributes; 1] }
    #[repr(C)] struct TokenStatistics {
        token_id: Luid, authentication_id: Luid, expiration_time: i64,
        token_type: i32, impersonation_level: i32, dynamic_charged: u32,
        dynamic_available: u32, group_count: u32, privilege_count: u32, modified_id: Luid,
    }
    #[repr(C)] struct Sid15 { revision: u8, count: u8, authority: [u8; 6], sub: [u32; 15] }
    assert_eq!(size_of::<*mut c_void>(), 8);
    assert_eq!(size_of::<SidAndAttributes>(), 16);
    assert_eq!(align_of::<SidAndAttributes>(), 8);
    assert_eq!(offset_of!(SidAndAttributes, attributes), 8);
    assert_eq!(offset_of!(TokenGroups, groups), 8);
    assert_eq!(size_of::<LuidAndAttributes>(), 12);
    assert_eq!(align_of::<LuidAndAttributes>(), 4);
    assert_eq!(offset_of!(TokenPrivileges, privileges), 4);
    assert_eq!(size_of::<TokenStatistics>(), 56);
    assert_eq!(align_of::<TokenStatistics>(), 8);
    assert_eq!(offset_of!(TokenStatistics, authentication_id), 8);
    assert_eq!(offset_of!(TokenStatistics, expiration_time), 16);
    assert_eq!(offset_of!(TokenStatistics, token_type), 24);
    assert_eq!(offset_of!(TokenStatistics, impersonation_level), 28);
    assert_eq!(offset_of!(TokenStatistics, dynamic_charged), 32);
    assert_eq!(offset_of!(TokenStatistics, dynamic_available), 36);
    assert_eq!(offset_of!(TokenStatistics, group_count), 40);
    assert_eq!(offset_of!(TokenStatistics, privilege_count), 44);
    assert_eq!(offset_of!(TokenStatistics, modified_id), 48);
    assert_eq!(align_of::<Sid15>(), 4);
    assert_eq!(offset_of!(Sid15, sub), 8);
    assert_eq!(size_of::<Sid15>(), 68);
}
