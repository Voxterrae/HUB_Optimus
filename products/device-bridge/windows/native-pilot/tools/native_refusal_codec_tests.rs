//! Synthetic standalone conformance tests; no host or Windows observations.
//! Compile with rustc --edition=2021 --test native_refusal_codec_tests.rs.

#[path = "native_refusal_codec.rs"]
mod codec;

use codec::{
    Cleanup, CodecError, Collector, Completion, Domain, ErrorKind, ErrorRecord,
    MinimumRefusal, Operation, Phase, Reason, Recheck, ThreadContext,
};

const GOLDEN: &str = concat!(
    r#"{"activation":"blocked","ancestors":null,"anchor":null,"cleanup":"complete","collector":{"policy_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","source_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","target":"x86_64-pc-windows-msvc"},"elapsed_ms":"10001","errors":[{"ancestor_index":null,"code":null,"completion":null,"domain":"internal","kind":"primary","operation":"validate","phase":"initial","reason":"unsupported"}],"finished_utc":"10","loaded_image_provenance":"not_established","mode":"diagnostic_only","outcome":"refused","primary_token":null,"process":null,"product_collision":"not_observed","recheck":"not_completed","schema":"hub_relay.bootstrap_inventory.v0.1","service_collision":"not_observed","service_sid_binding":"external_evidence_required","started_utc":"20","thread_context":"unknown","thread_token":null}"#,
);

fn primary() -> ErrorRecord {
    ErrorRecord {
        kind: ErrorKind::Primary,
        phase: Phase::Initial,
        operation: Operation::Validate,
        domain: Domain::Internal,
        code: None,
        reason: Some(Reason::Unsupported),
        ancestor_index: None,
        completion: None,
    }
}

fn cleanup() -> ErrorRecord {
    ErrorRecord {
        kind: ErrorKind::Cleanup,
        phase: Phase::Cleanup,
        operation: Operation::CloseHandle,
        domain: Domain::Win32,
        code: Some(6),
        reason: None,
        ancestor_index: None,
        completion: None,
    }
}

fn receipt_bound() -> ErrorRecord {
    ErrorRecord {
        kind: ErrorKind::Receipt,
        phase: Phase::Serialize,
        operation: Operation::Serialize,
        domain: Domain::Internal,
        code: None,
        reason: Some(Reason::ReceiptBound),
        ancestor_index: None,
        completion: None,
    }
}

fn nt_error(call: u32, io_status: u32, information: u64) -> ErrorRecord {
    ErrorRecord {
        operation: Operation::NtCreateFile,
        domain: Domain::Ntstatus,
        code: Some(call),
        reason: None,
        completion: Some(Completion { call, io_status, information }),
        ..primary()
    }
}

fn record(errors: &[ErrorRecord]) -> MinimumRefusal<'_> {
    MinimumRefusal {
        collector: Collector {
            source_commit: [0xaa; 20],
            policy_sha256: [0xbb; 32],
            target: "x86_64-pc-windows-msvc",
        },
        started_utc: 20,
        finished_utc: 10,
        elapsed_ms: 10001,
        thread_context: ThreadContext::Unknown,
        recheck: Recheck::NotCompleted,
        errors,
        cleanup: Cleanup::Complete,
    }
}

fn encoded(value: &MinimumRefusal<'_>) -> String {
    String::from_utf8(codec::serialize(value).expect("synthetic record must encode"))
        .expect("serializer must emit UTF-8")
}

fn reject(value: &MinimumRefusal<'_>) {
    assert!(matches!(codec::validate(value), Err(CodecError)));
    assert!(matches!(codec::serialize(value), Err(CodecError)));
}

#[test]
fn canonical_json_matches_independent_python_reference_bytes() {
    let errors = [primary()];
    assert_eq!(encoded(&record(&errors)), GOLDEN);
}

#[test]
fn fixed_literals_keep_every_observation_null_and_activation_blocked() {
    let errors = [receipt_bound()];
    let output = encoded(&record(&errors));
    for literal in [
        r#""activation":"blocked""#,
        r#""outcome":"refused""#,
        r#""loaded_image_provenance":"not_established""#,
        r#""mode":"diagnostic_only""#,
        r#""process":null"#,
        r#""primary_token":null"#,
        r#""thread_token":null"#,
        r#""anchor":null"#,
        r#""ancestors":null"#,
    ] {
        assert_eq!(output.matches(literal).count(), 1);
    }
}

#[test]
fn binary_build_metadata_uses_lowercase_hex_without_losing_zero_bytes() {
    let errors = [primary()];
    let mut value = record(&errors);
    value.collector.source_commit = [0; 20];
    value.collector.source_commit[19] = 0xff;
    value.collector.policy_sha256 = [0x0f; 32];
    let output = encoded(&value);
    assert!(output.contains(r#""source_commit":"00000000000000000000000000000000000000ff""#));
    assert!(output.contains(concat!(
        r#""policy_sha256":""#,
        "0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f",
        r#"""#,
    )));
}

#[test]
fn timings_encode_zero_and_u64_maximum_as_canonical_decimal_strings() {
    let errors = [primary()];
    let mut value = record(&errors);
    value.started_utc = 0;
    value.finished_utc = u64::MAX;
    value.elapsed_ms = u64::MAX;
    let output = encoded(&value);
    assert!(output.contains(r#""started_utc":"0""#));
    assert!(output.contains(r#""finished_utc":"18446744073709551615""#));
    assert!(output.contains(r#""elapsed_ms":"18446744073709551615""#));
}

#[test]
fn wall_clock_reversal_and_elapsed_over_budget_remain_representable_refusals() {
    let errors = [primary()];
    assert!(codec::validate(&record(&errors)).is_ok());
    assert!(encoded(&record(&errors)).contains(r#""elapsed_ms":"10001""#));
}

#[test]
fn every_thread_and_recheck_outcome_is_retained_without_promotion() {
    let errors = [primary()];
    for (context, context_text) in [
        (ThreadContext::NoToken, "no_token"),
        (ThreadContext::Present, "present"),
        (ThreadContext::Unknown, "unknown"),
    ] {
        for (recheck, recheck_text) in [
            (Recheck::Equal, "equal"),
            (Recheck::Changed, "changed"),
            (Recheck::NotCompleted, "not_completed"),
        ] {
            let mut value = record(&errors);
            value.thread_context = context;
            value.recheck = recheck;
            let output = encoded(&value);
            assert!(output.contains(&format!(r#""thread_context":"{context_text}""#)));
            assert!(output.contains(&format!(r#""recheck":"{recheck_text}""#)));
            assert!(output.contains(r#""outcome":"refused""#));
        }
    }
}

#[test]
fn empty_ascii_build_target_is_representable() {
    let errors = [primary()];
    let mut value = record(&errors);
    value.collector.target = "";
    assert!(encoded(&value).contains(r#""target":"""#));
}

#[test]
fn target_at_128_ascii_bytes_is_accepted() {
    let errors = [primary()];
    let target = "x".repeat(128);
    let mut value = record(&errors);
    value.collector.target = &target;
    assert!(codec::validate(&value).is_ok());
    assert!(encoded(&value).contains(&format!(r#""target":"{target}""#)));
}

#[test]
fn target_above_128_ascii_bytes_is_rejected() {
    let errors = [primary()];
    let target = "x".repeat(129);
    let mut value = record(&errors);
    value.collector.target = &target;
    reject(&value);
}

#[test]
fn non_ascii_target_is_rejected_even_when_its_utf8_bytes_fit() {
    let errors = [primary()];
    for target in ["é", "\u{0080}", "🦀"] {
        let mut value = record(&errors);
        value.collector.target = target;
        reject(&value);
    }
}

#[test]
fn all_128_ascii_values_match_python_json_escaping_including_del() {
    let errors = [primary()];
    let target: String = (0u8..=127).map(char::from).collect();
    let mut value = record(&errors);
    value.collector.target = &target;
    let expected = concat!(
        r##""target":"\u0000\u0001\u0002\u0003\u0004\u0005\u0006\u0007\b\t\n\u000b\f\r\u000e\u000f\u0010\u0011\u0012\u0013\u0014\u0015\u0016\u0017\u0018\u0019\u001a\u001b\u001c\u001d\u001e\u001f !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~\u007f""##,
    );
    let output = encoded(&value);
    assert!(output.contains(expected));
    assert!(output.bytes().all(|byte| (32..=126).contains(&byte)));
}

#[test]
fn all_noncleanup_operations_and_capture_phases_keep_their_exact_spelling() {
    for (operation, text) in [
        (Operation::DuplicateHandle, "DuplicateHandle"),
        (Operation::GetHandleInformation, "GetHandleInformation"),
        (Operation::GetProcessId, "GetProcessId"),
        (Operation::GetProcessTimes, "GetProcessTimes"),
        (Operation::QueryFullProcessImageNameW, "QueryFullProcessImageNameW"),
        (Operation::IsWow64Process2, "IsWow64Process2"),
        (Operation::OpenProcessToken, "OpenProcessToken"),
        (Operation::OpenThreadToken, "OpenThreadToken"),
        (Operation::GetTokenInformation, "GetTokenInformation"),
        (Operation::CoInitializeEx, "CoInitializeEx"),
        (Operation::SHGetKnownFolderPath, "SHGetKnownFolderPath"),
        (Operation::CreateFileW, "CreateFileW"),
        (Operation::NtCreateFile, "NtCreateFile"),
        (Operation::NtQueryInformationFile, "NtQueryInformationFile"),
        (Operation::GetFileInformationByHandleEx, "GetFileInformationByHandleEx"),
        (Operation::GetFileType, "GetFileType"),
        (Operation::GetVolumeInformationByHandleW, "GetVolumeInformationByHandleW"),
        (Operation::GetFinalPathNameByHandleW, "GetFinalPathNameByHandleW"),
        (Operation::GetVolumeNameForVolumeMountPointW, "GetVolumeNameForVolumeMountPointW"),
        (Operation::GetDriveTypeW, "GetDriveTypeW"),
        (Operation::GetSecurityInfo, "GetSecurityInfo"),
        (Operation::LookupPrivilegeNameW, "LookupPrivilegeNameW"),
        (Operation::CompareStringOrdinal, "CompareStringOrdinal"),
        (Operation::Validate, "validate"),
    ] {
        for (phase, phase_text) in [
            (Phase::Initial, "initial"),
            (Phase::Capture, "capture"),
            (Phase::Recheck, "recheck"),
        ] {
            let errors = [ErrorRecord { operation, phase, ..primary() }];
            let output = encoded(&record(&errors));
            assert!(output.contains(&format!(r#""operation":"{text}""#)));
            assert!(output.contains(&format!(r#""phase":"{phase_text}""#)));
        }
    }
}

#[test]
fn internal_reasons_are_retained_as_closed_literal_values() {
    for (reason, text) in [
        (Reason::Unsupported, "unsupported"),
        (Reason::Malformed, "malformed"),
        (Reason::Bound, "bound"),
        (Reason::Policy, "policy"),
        (Reason::Impersonation, "impersonation"),
        (Reason::AppContainer, "app_container"),
        (Reason::TokenChanged, "token_changed"),
        (Reason::Drift, "drift"),
        (Reason::Budget, "budget"),
        (Reason::ReceiptBound, "receipt_bound"),
    ] {
        let errors = [ErrorRecord { reason: Some(reason), ..primary() }];
        assert!(encoded(&record(&errors)).contains(&format!(r#""reason":"{text}""#)));
    }
}

#[test]
fn win32_and_hresult_preserve_every_u32_status_bit() {
    for (domain, text) in [(Domain::Win32, "win32"), (Domain::Hresult, "hresult")] {
        for code in [0, u32::MAX] {
            let errors = [ErrorRecord { domain, code: Some(code), reason: None, ..primary() }];
            let output = encoded(&record(&errors));
            assert!(output.contains(&format!(r#""domain":"{text}""#)));
            assert!(output.contains(&format!(r#""code":{code},"#)));
            assert!(output.contains(r#""reason":null"#));
        }
    }
}

#[test]
fn internal_domain_rejects_a_native_code_or_missing_reason() {
    for invalid in [
        ErrorRecord { code: Some(0), ..primary() },
        ErrorRecord { reason: None, ..primary() },
    ] {
        reject(&record(&[invalid]));
    }
}

#[test]
fn native_domains_reject_missing_code_or_internal_reason() {
    for domain in [Domain::Win32, Domain::Hresult, Domain::Ntstatus] {
        let base = match domain {
            Domain::Ntstatus => nt_error(0, 0xc0000022, 1),
            _ => ErrorRecord { domain, code: Some(5), reason: None, ..primary() },
        };
        for invalid in [
            ErrorRecord { code: None, ..base },
            ErrorRecord { reason: Some(Reason::Unsupported), ..base },
        ] {
            reject(&record(&[invalid]));
        }
    }
}

#[test]
fn ancestor_index_accepts_127_and_rejects_128_without_wrapping() {
    let accepted = [ErrorRecord { ancestor_index: Some(127), ..primary() }];
    assert!(encoded(&record(&accepted)).contains(r#""ancestor_index":127,"#));
    let rejected = [ErrorRecord { ancestor_index: Some(128), ..primary() }];
    reject(&record(&rejected));
}

#[test]
fn nt_call_iosb_and_information_remain_independent_raw_values() {
    for (call, io_status, information) in [
        (0, 0xc0000022, 7),
        (0xc0000001, 0, u64::MAX),
        (1, 0, 17),
        (0xffffffff, 0xfffffffe, u64::MAX),
    ] {
        let errors = [nt_error(call, io_status, information)];
        let output = encoded(&record(&errors));
        assert!(output.contains(&format!(
            r#""completion":{{"call":{call},"information":"{information}","io_status":{io_status}}}"#
        )));
        assert!(output.contains(&format!(r#""code":{call},"#)));
    }
}

#[test]
fn both_nt_operations_can_report_terminal_completion_rejection() {
    for operation in [Operation::NtCreateFile, Operation::NtQueryInformationFile] {
        let errors = [ErrorRecord { operation, ..nt_error(0, 0xc0000022, 2) }];
        assert!(codec::validate(&record(&errors)).is_ok());
        assert!(codec::serialize(&record(&errors)).is_ok());
    }
}

#[test]
fn ntstatus_requires_completion_and_matching_raw_call_code() {
    for invalid in [
        ErrorRecord { completion: None, ..nt_error(0, 0xc0000022, 1) },
        ErrorRecord { code: Some(5), ..nt_error(0, 0xc0000022, 1) },
        nt_error(0, 0, 1),
    ] {
        reject(&record(&[invalid]));
    }
}

#[test]
fn completion_is_rejected_for_non_nt_operations_or_unrelated_domains() {
    for invalid in [
        ErrorRecord { operation: Operation::CreateFileW, ..nt_error(0, 0xc0000022, 1) },
        ErrorRecord { domain: Domain::Win32, ..nt_error(0, 0xc0000022, 1) },
        ErrorRecord { domain: Domain::Hresult, ..nt_error(0, 0xc0000022, 1) },
    ] {
        reject(&record(&[invalid]));
    }
}

#[test]
fn successful_statuses_with_invalid_shape_keep_internal_malformed_completion() {
    let errors = [ErrorRecord {
        domain: Domain::Internal,
        code: None,
        reason: Some(Reason::Malformed),
        ..nt_error(0, 0, 17)
    }];
    let output = encoded(&record(&errors));
    assert!(output.contains(r#""completion":{"call":0,"information":"17","io_status":0}"#));
    assert!(output.contains(r#""reason":"malformed""#));
}

#[test]
fn internal_completion_rejects_nonmalformed_reason_or_unsuccessful_status() {
    for (reason, call, io_status) in [
        (Reason::Policy, 0, 0),
        (Reason::Malformed, 1, 0),
        (Reason::Malformed, 0, 1),
    ] {
        let errors = [ErrorRecord {
            domain: Domain::Internal, code: None, reason: Some(reason),
            ..nt_error(call, io_status, 1)
        }];
        reject(&record(&errors));
    }
}

#[test]
fn pending_call_or_iosb_cannot_be_serialized_as_terminal_failure() {
    for (call, io_status) in [(0x103, 0), (0, 0x103), (0xc0000001, 0x103)] {
        reject(&record(&[nt_error(call, io_status, 0)]));
    }
}

#[test]
fn unwritten_64_bit_iosb_sentinel_refuses_only_its_nonterminal_shape() {
    for call in [0, 1, 0x7fffffff] {
        reject(&record(&[nt_error(call, 0xc0000001, u64::MAX)]));
    }
    let terminal = [nt_error(0x80000000, 0xc0000001, u64::MAX)];
    assert!(codec::validate(&record(&terminal)).is_ok());
    let different_information = [nt_error(0, 0xc0000001, u32::MAX as u64)];
    assert!(codec::validate(&record(&different_information)).is_ok());
}

#[test]
fn empty_error_list_is_rejected_without_inventing_an_error() {
    reject(&record(&[]));
}

#[test]
fn duplicate_or_nonfirst_primary_errors_are_rejected() {
    reject(&record(&[primary(), primary()]));
    let errors = [cleanup(), primary()];
    let mut value = record(&errors);
    value.cleanup = Cleanup::Failed;
    reject(&value);
}

#[test]
fn cleanup_duplicates_and_occurrence_order_are_retained() {
    let errors = [
        primary(),
        cleanup(),
        ErrorRecord { operation: Operation::LocalFree, code: Some(8), ..cleanup() },
        cleanup(),
    ];
    let mut value = record(&errors);
    value.cleanup = Cleanup::Failed;
    let output = encoded(&value);
    assert_eq!(output.matches(r#""operation":"CloseHandle""#).count(), 2);
    let first = output.find(r#""operation":"CloseHandle""#).unwrap();
    let middle = output.find(r#""operation":"LocalFree""#).unwrap();
    let last = output.rfind(r#""operation":"CloseHandle""#).unwrap();
    assert!(first < middle && middle < last);
    assert!(output.contains(r#""cleanup":"failed""#));
}

#[test]
fn cleanup_failure_without_primary_is_representable() {
    let errors = [cleanup()];
    let mut value = record(&errors);
    value.cleanup = Cleanup::Failed;
    assert!(codec::validate(&value).is_ok());
    assert!(encoded(&value).contains(r#""kind":"cleanup""#));
}

#[test]
fn first_close_failure_can_be_primary_and_requires_failed_cleanup() {
    for operation in [Operation::CloseHandle, Operation::LocalFree] {
        let errors = [ErrorRecord { kind: ErrorKind::Primary, operation, ..cleanup() }];
        let mut value = record(&errors);
        reject(&value);
        value.cleanup = Cleanup::Failed;
        assert!(codec::validate(&value).is_ok());
        assert!(codec::serialize(&value).is_ok());
    }
}

#[test]
fn cleanup_state_must_equal_presence_of_cleanup_failure() {
    let errors = [primary()];
    let mut value = record(&errors);
    value.cleanup = Cleanup::Failed;
    reject(&value);
    reject(&record(&[cleanup()]));
}

#[test]
fn cleanup_kind_and_primary_cleanup_phase_require_only_close_operations() {
    for (invalid, cleanup_state) in [
        (ErrorRecord { phase: Phase::Capture, ..cleanup() }, Cleanup::Failed),
        (ErrorRecord { operation: Operation::Validate, ..cleanup() }, Cleanup::Failed),
        (ErrorRecord { phase: Phase::Cleanup, ..primary() }, Cleanup::Complete),
        (ErrorRecord { operation: Operation::CloseHandle, ..primary() }, Cleanup::Failed),
        (ErrorRecord { phase: Phase::Serialize, ..primary() }, Cleanup::Complete),
        (ErrorRecord { operation: Operation::Serialize, ..primary() }, Cleanup::Complete),
    ] {
        let errors = [invalid];
        let mut value = record(&errors);
        value.cleanup = cleanup_state;
        reject(&value);
    }
}

#[test]
fn acquisition_cleanup_255_errors_fit_without_receipt_slot() {
    let errors = vec![cleanup(); 255];
    let mut value = record(&errors);
    value.cleanup = Cleanup::Failed;
    let output = encoded(&value);
    assert_eq!(output.matches(r#""kind":"cleanup""#).count(), 255);
}

#[test]
fn reserved_256th_slot_preserves_primary_and_every_cleanup() {
    let mut errors = vec![primary()];
    errors.extend(std::iter::repeat(cleanup()).take(254));
    errors.push(receipt_bound());
    let mut value = record(&errors);
    value.cleanup = Cleanup::Failed;
    let output = encoded(&value);
    assert_eq!(output.matches(r#""kind":"primary""#).count(), 1);
    assert_eq!(output.matches(r#""kind":"cleanup""#).count(), 254);
    assert_eq!(output.matches(r#""kind":"receipt""#).count(), 1);
    assert!(output.find(r#""kind":"primary""#) < output.find(r#""kind":"cleanup""#));
    assert!(output.rfind(r#""kind":"cleanup""#) < output.find(r#""kind":"receipt""#));
}

#[test]
fn nonreceipt_256_errors_and_any_257th_error_are_rejected() {
    for count in [256, 257] {
        let errors = vec![cleanup(); count];
        let mut value = record(&errors);
        value.cleanup = Cleanup::Failed;
        reject(&value);
    }
    let mut errors = vec![cleanup(); 256];
    errors.push(receipt_bound());
    let mut value = record(&errors);
    value.cleanup = Cleanup::Failed;
    reject(&value);
}

#[test]
fn receipt_error_must_be_unique_last_and_exact() {
    for (errors, cleanup_state) in [
        (vec![receipt_bound(), receipt_bound()], Cleanup::Complete),
        (vec![receipt_bound(), primary()], Cleanup::Complete),
        (vec![receipt_bound(), cleanup()], Cleanup::Failed),
    ] {
        let mut value = record(&errors);
        value.cleanup = cleanup_state;
        reject(&value);
    }
    for invalid in [
        ErrorRecord { phase: Phase::Initial, ..receipt_bound() },
        ErrorRecord { operation: Operation::Validate, ..receipt_bound() },
        ErrorRecord { domain: Domain::Win32, code: Some(5), reason: None, ..receipt_bound() },
        ErrorRecord { reason: Some(Reason::Bound), ..receipt_bound() },
        ErrorRecord { ancestor_index: Some(0), ..receipt_bound() },
        ErrorRecord { completion: Some(Completion { call: 0, io_status: 0, information: 0 }), ..receipt_bound() },
    ] {
        reject(&record(&[invalid]));
    }
}

#[test]
fn counted_byte_limit_includes_json_escaping_and_has_no_partial_success() {
    let errors = [primary()];
    let target = "\0".repeat(128);
    let mut value = record(&errors);
    value.collector.target = &target;
    let output = codec::serialize(&value).unwrap();
    let exact = codec::serialize_with_limit_for_test(&value, output.len()).unwrap();
    assert_eq!(exact, output);
    assert!(matches!(
        codec::serialize_with_limit_for_test(&value, output.len() - 1),
        Err(CodecError)
    ));
    assert!(matches!(codec::serialize_with_limit_for_test(&value, 0), Err(CodecError)));
}

#[test]
fn repeated_serialization_borrows_input_without_reordering_or_repair() {
    let errors = [primary(), cleanup(), cleanup(), receipt_bound()];
    let target = String::from("synthetic-target");
    let mut value = record(&errors);
    value.collector.target = &target;
    value.cleanup = Cleanup::Failed;
    let first = codec::serialize(&value).unwrap();
    let second = codec::serialize(&value).unwrap();
    assert_eq!(first, second);
    assert!(matches!(errors[0].kind, ErrorKind::Primary));
    assert!(matches!(errors[1].kind, ErrorKind::Cleanup));
    assert!(matches!(errors[2].kind, ErrorKind::Cleanup));
    assert!(matches!(errors[3].kind, ErrorKind::Receipt));
    assert_eq!(target, "synthetic-target");
}
