use bootstrap_inventory::arena::Arena;
use bootstrap_inventory::model::{Luid, Phase, Privilege, Reason, SidAttributes, Token};
use bootstrap_inventory::process::{self, TokenSource};

const SID: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0];

#[derive(Default)]
struct Source {
    sizes: Vec<u32>,
    reads: Vec<u32>,
    statistics_reads: usize,
    grow_class: Option<u32>,
    fail_class: Option<u32>,
    change_modified_id: bool,
    change_token_id: bool,
    token_id: u32,
    app_container: u32,
    has_restrictions_byte: bool,
    reported_name_length: Option<usize>,
    invalid_name: bool,
    invalid_sid_pointer: bool,
    oversized_size: bool,
}

fn put32(bytes: &mut [u8], offset: usize, value: u32) {
    bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}
fn put64(bytes: &mut [u8], offset: usize, value: u64) {
    bytes[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}

impl TokenSource for Source {
    fn size(&mut self, class: u32) -> bootstrap_inventory::model::Result<usize> {
        self.sizes.push(class);
        if self.oversized_size { return Ok(65_537); }
        Ok(match class {
            1 | 25 => 16 + SID.len(),
            4 | 5 => 8 + SID.len(),
            // Two identical entries deliberately retain multiplicity and raw bits.
            2 | 11 | 30 => 40 + SID.len(),
            3 => 28,
            _ => panic!("fixed information class must not receive size query"),
        })
    }

    fn retrieve(&mut self, class: u32, bytes: &mut [u8]) -> bootstrap_inventory::model::Result<usize> {
        self.reads.push(class);
        if self.fail_class == Some(class) {
            return Err(bootstrap_inventory::model::Error::internal(
                Phase::Capture, bootstrap_inventory::model::Operation::GetTokenInformation, Reason::Unsupported));
        }
        let base = bytes.as_ptr() as u64;
        bytes.fill(0);
        match class {
            1 | 25 => {
                put64(bytes, 0, base + 16);
                put32(bytes, 8, 0x8000_0010);
                bytes[16..16 + SID.len()].copy_from_slice(SID);
                if self.invalid_sid_pointer { put64(bytes, 0, base); }
            }
            4 | 5 => {
                put64(bytes, 0, base + 8);
                bytes[8..8 + SID.len()].copy_from_slice(SID);
            }
            2 | 11 | 30 => {
                put32(bytes, 0, 2);
                for offset in [8, 24] {
                    put64(bytes, offset, base + 40);
                    put32(bytes, offset + 8, 0x8000_0010);
                }
                bytes[40..40 + SID.len()].copy_from_slice(SID);
            }
            3 => {
                put32(bytes, 0, 2);
                for offset in [4, 16] {
                    put32(bytes, offset, 23);
                    put32(bytes, offset + 4, u32::MAX);
                    put32(bytes, offset + 8, 0x8000_0000);
                }
            }
            10 => {
                self.statistics_reads += 1;
                put32(bytes, 0, self.token_id + u32::from(self.change_token_id && self.statistics_reads > 1));
                put32(bytes, 8, 42);
                put32(bytes, 24, 1);
                put32(bytes, 32, 256);
                put32(bytes, 40, 2);
                put32(bytes, 44, 2);
                put32(bytes, 48, if self.change_modified_id && self.statistics_reads > 1 { 9 } else { 7 });
            }
            8 | 18 => put32(bytes, 0, 1),
            29 => put32(bytes, 0, self.app_container),
            21 if self.has_restrictions_byte => { bytes[0] = 0x80; return Ok(1); }
            _ => put32(bytes, 0, 0x8000_0000),
        }
        Ok(bytes.len() + usize::from(self.grow_class == Some(class)))
    }

    fn privilege_name(&mut self, _: Luid, name: &mut [u16]) -> bootstrap_inventory::model::Result<usize> {
        if let Some(length) = self.reported_name_length { return Ok(length); }
        if self.invalid_name { name[0] = 0xd800; return Ok(1); }
        let units: Vec<u16> = "SeChangeNotifyPrivilege".encode_utf16().collect();
        name[..units.len()].copy_from_slice(&units);
        Ok(units.len())
    }
}

#[test]
fn captures_all_classes_once_and_copies_before_buffer_reuse() {
    let arena = Arena::new(2 * 1024 * 1024).unwrap();
    let mut source = Source::default();
    let token = process::capture_token(&arena, &mut source, Phase::Capture).unwrap();
    assert_eq!(source.sizes, [1, 4, 5, 25, 2, 11, 30, 3]);
    assert_eq!(source.reads, [10, 8, 1, 4, 5, 25, 2, 11, 30, 3, 12, 18, 20, 21, 29, 27, 26, 23, 24, 10]);
    assert_eq!(token.user, SID);
    assert_eq!(token.owner, SID);
    assert_eq!(token.primary_group, SID);
    assert_eq!(token.groups.len(), 2);
    assert!(token.groups.iter().all(|entry| entry.sid == SID && entry.attributes == 0x8000_0010));
    assert!(token.restricted_sids == token.groups);
    assert!(token.capabilities == token.groups);
    assert_eq!(token.privileges.len(), 2);
    assert!(token.privileges.iter().all(|entry| entry.luid.high == -1 && entry.attributes == 0x8000_0000));
    assert_eq!(token.impersonation_level, None);
}

#[test]
fn variable_length_growth_and_capture_modification_refuse_without_retry() {
    let arena = Arena::new(2 * 1024 * 1024).unwrap();
    let mut growth = Source { grow_class: Some(1), ..Source::default() };
    let error = process::capture_token(&arena, &mut growth, Phase::Capture).err().unwrap();
    assert_eq!(error.reason, Some(Reason::Malformed));
    assert_eq!(growth.sizes, [1]);
    assert_eq!(growth.reads, [10, 8, 1]);
    let mut drift = Source { change_modified_id: true, ..Source::default() };
    let error = process::capture_token(&arena, &mut drift, Phase::Recheck).err().unwrap();
    assert_eq!(error.reason, Some(Reason::TokenChanged));
    assert_eq!(error.phase, Phase::Recheck);
    let mut drift = Source { change_token_id: true, ..Source::default() };
    assert_eq!(process::capture_token(&arena, &mut drift, Phase::Capture).err().unwrap().reason, Some(Reason::TokenChanged));
}

#[test]
fn oversized_query_and_sid_header_overlap_refuse_before_copying_a_record() {
    let arena = Arena::new(2 * 1024 * 1024).unwrap();
    let mut source = Source { oversized_size: true, ..Source::default() };
    assert_eq!(process::capture_token(&arena, &mut source, Phase::Capture).err().unwrap().reason, Some(Reason::Bound));
    assert_eq!(source.reads, [10, 8]);
    let mut source = Source { invalid_sid_pointer: true, ..Source::default() };
    assert_eq!(process::capture_token(&arena, &mut source, Phase::Capture).err().unwrap().reason, Some(Reason::Malformed));
    assert_eq!(source.reads, [10, 8, 1]);
}

#[test]
fn unsupported_class_stops_complete_capture() {
    let arena = Arena::new(2 * 1024 * 1024).unwrap();
    let mut source = Source { fail_class: Some(29), ..Source::default() };
    assert!(process::capture_token(&arena, &mut source, Phase::Capture).is_err());
    assert_eq!(source.reads.last(), Some(&29));
    assert_eq!(source.statistics_reads, 1);
}

#[test]
fn class21_candidate_exception_is_exclusive_aligned_and_preserves_raw_bits() {
    for (bytes, value) in [(&[0x80][..], 0x80), (&[0xff][..], 0xff), (&[0, 0, 0, 0x80][..], 0x8000_0000)] {
        assert_eq!(process::decode_scalar(21, bytes, 0x1000, Phase::Capture).unwrap(), value);
    }
    for size in [0, 2, 3, 5] {
        assert!(process::decode_scalar(21, &[0; 5][..size], 0x1000, Phase::Capture).is_err());
    }
    assert!(process::decode_scalar(21, &[1], 0x1001, Phase::Capture).is_err());
    for class in [8, 9, 12, 18, 20, 23, 24, 26, 27, 29] {
        assert!(process::decode_scalar(class, &[1], 0x1000, Phase::Capture).is_err());
    }
    let arena = Arena::new(2 * 1024 * 1024).unwrap();
    let mut source = Source { has_restrictions_byte: true, ..Source::default() };
    assert_eq!(process::capture_token(&arena, &mut source, Phase::Capture).unwrap().has_restrictions, 0x80);
}

#[test]
fn bounded_lengths_accept_exact_maximum_and_reject_zero_growth_and_plus_one() {
    assert_eq!(process::validate_token_size(65_536, Phase::Capture).unwrap(), 65_536);
    assert!(process::validate_token_size(0, Phase::Capture).is_err());
    assert!(process::validate_token_size(65_537, Phase::Capture).is_err());
    assert!(process::validate_retrieval(20, 19, Phase::Capture).is_err());
    assert!(process::validate_retrieval(20, 21, Phase::Capture).is_err());
    assert!(process::validate_retrieval(20, 20, Phase::Capture).is_ok());
}

#[test]
fn only_error_no_token_establishes_nonimpersonation() {
    assert_eq!(process::classify_thread_failure(1008, Phase::Capture).unwrap(), bootstrap_inventory::model::ThreadContext::NoToken);
    for code in [0, 5, 122, 1347, u32::MAX] {
        let error = process::classify_thread_failure(code, Phase::Recheck).err().unwrap();
        assert_eq!(error.code, Some(code));
        assert_eq!(error.phase, Phase::Recheck);
        assert_eq!(error.operation, bootstrap_inventory::model::Operation::OpenThreadToken);
    }
}

#[test]
fn privilege_name_extent_and_utf16_fail_before_complete_token() {
    let arena = Arena::new(2 * 1024 * 1024).unwrap();
    for length in [0, 257, usize::MAX] {
        let mut source = Source { reported_name_length: Some(length), ..Source::default() };
        assert!(process::capture_token(&arena, &mut source, Phase::Capture).is_err());
        assert_eq!(source.statistics_reads, 1);
    }
    let mut source = Source { invalid_name: true, ..Source::default() };
    assert!(process::capture_token(&arena, &mut source, Phase::Recheck).is_err());
    assert_eq!(source.statistics_reads, 1);
}

fn token<'a>(groups: &'a [SidAttributes<'a>], privileges: &'a [Privilege<'a>]) -> Token<'a> {
    Token {
        token_type: 1, impersonation_level: None, user: SID, owner: SID, primary_group: SID,
        integrity: SidAttributes { sid: SID, attributes: 0x20 }, groups, restricted_sids: groups,
        capabilities: groups, privileges, token_id: Luid { low: 1, high: -1 },
        authentication_id: Luid { low: 2, high: -2 }, modified_id: Luid { low: 3, high: -3 },
        session_id: 7, elevation_type: 1, elevation: 0x80, has_restrictions: 0xff,
        is_app_container: 0, mandatory_policy: 0x80, ui_access: 0x100,
        virtualization_allowed: 0x200, virtualization_enabled: 0x400,
    }
}

#[test]
fn canonical_multisets_preserve_multiplicity_attributes_and_every_scalar() {
    let a = SidAttributes { sid: SID, attributes: 0x8000_0010 };
    let b = SidAttributes { sid: SID, attributes: 0 };
    let p = Privilege { luid: Luid { low: 9, high: -1 }, name: "SeA", attributes: 0x8000_0000 };
    let q = Privilege { luid: Luid { low: 8, high: 1 }, name: "SeB", attributes: 0 };
    let left_groups = [a, a, b];
    let right_groups = [b, a, a];
    let left_privileges = [p, p, q];
    let right_privileges = [q, p, p];
    let left = token(&left_groups, &left_privileges);
    let right = token(&right_groups, &right_privileges);
    assert!(process::tokens_equal(&left, &right, Phase::Recheck).unwrap());
    let fewer = [b, a, b];
    assert!(!process::tokens_equal(&left, &token(&fewer, &right_privileges), Phase::Recheck).unwrap());
    let mut changed = right;
    changed.modified_id.low += 1;
    assert!(!process::tokens_equal(&left, &changed, Phase::Recheck).unwrap());
    changed = right;
    changed.token_id.low += 1;
    assert!(!process::tokens_equal(&left, &changed, Phase::Recheck).unwrap());
    changed = right;
    changed.virtualization_enabled ^= 0x8000_0000;
    assert!(!process::tokens_equal(&left, &changed, Phase::Recheck).unwrap());
    let excess = [a; 2_049];
    assert!(process::tokens_equal(&token(&excess, &[]), &token(&excess, &[]), Phase::Recheck).is_err());
    let excess = [p; 257];
    assert!(process::tokens_equal(&token(&[], &excess), &token(&[], &excess), Phase::Recheck).is_err());
    let exact_groups = [a; 2_048];
    let exact_privileges = [p; 256];
    let exact = token(&exact_groups, &exact_privileges);
    assert!(process::tokens_equal(&exact, &exact, Phase::Recheck).unwrap());
}

#[test]
fn reopening_replacement_is_detected_while_original_snapshot_stays_stable() {
    let arena = Arena::new(2 * 1024 * 1024).unwrap();
    let original = process::capture_token(&arena, &mut Source { token_id: 4, ..Source::default() }, Phase::Capture).unwrap();
    let replacement = process::capture_token(&arena, &mut Source { token_id: 5, ..Source::default() }, Phase::Recheck).unwrap();
    assert_eq!(original.token_id.low, 4);
    assert!(!process::tokens_equal(&original, &replacement, Phase::Recheck).unwrap());
}

#[cfg(windows)]
#[test]
fn native_own_process_context_captures_rechecks_and_closes_without_token_output() {
    let arena = Arena::new(8 * 1024 * 1024).unwrap();
    let mut context = bootstrap_inventory::windows::Context::new(&arena);
    let mut state = process::State::new();
    let captured = process::capture(&mut context, &mut state);
    let checked = if captured.is_ok() { process::recheck(&mut context, &mut state) } else { captured };
    context.finish_cleanup();
    assert!(checked.is_ok(), "own native AMD64 context did not complete");
    assert!(!context.errors.cleanup_failed());
    assert!(state.process.is_some() && state.primary.is_some() && state.thread.is_none());
    assert_eq!(state.thread_context, bootstrap_inventory::model::ThreadContext::NoToken);
}

#[cfg(windows)]
#[test]
fn native_class21_only_consumes_successful_returned_extent() {
    use bootstrap_inventory::model::{Domain, Error, Operation};
    use bootstrap_inventory::windows::{Context, ResourceKind};
    use windows_sys::Win32::Foundation::GetLastError;
    use windows_sys::Win32::Security::GetTokenInformation;
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, OpenProcessToken};
    let arena = Arena::new(1024 * 1024).unwrap();
    let mut context = Context::new(&arena);
    let result = (|| -> bootstrap_inventory::model::Result<()> {
        let mut raw = std::ptr::null_mut();
        context.check(Operation::OpenProcessToken, Phase::Capture)?;
        if unsafe { OpenProcessToken(GetCurrentProcess(), 0x0008, &mut raw) } == 0 {
            return Err(Error::native(Phase::Capture, Operation::OpenProcessToken, Domain::Win32, unsafe { GetLastError() }));
        }
        let slot = context.acquire(raw, ResourceKind::ProcessToken)?;
        // Four-byte capacity/alignment; only ReturnLength bytes reach the decoder.
        let mut storage = [0xa5a5_a5a5_u32];
        let mut returned = 0_u32;
        context.check(Operation::GetTokenInformation, Phase::Capture)?;
        if unsafe { GetTokenInformation(context.raw(slot), 21, storage.as_mut_ptr().cast(), 4, &mut returned) } == 0 {
            return Err(Error::native(Phase::Capture, Operation::GetTokenInformation, Domain::Win32, unsafe { GetLastError() }));
        }
        if !matches!(returned, 1 | 4) {
            return Err(Error::internal(Phase::Capture, Operation::GetTokenInformation, Reason::Malformed));
        }
        let bytes = storage[0].to_ne_bytes();
        process::decode_scalar(21, &bytes[..returned as usize], storage.as_ptr() as u64, Phase::Capture)?;
        Ok(())
    })();
    context.finish_cleanup();
    assert!(result.is_ok(), "class21 shape was rejected");
    assert!(!context.errors.cleanup_failed());
}
