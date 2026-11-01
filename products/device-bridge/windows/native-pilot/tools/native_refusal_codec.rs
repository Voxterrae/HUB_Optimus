//! Private proposal-stage minimum-refusal validator and serializer.
//!
//! This standalone tool is not imported by the native crate. It never parses,
//! collects observations, calls Windows, writes output or creates authority.
//! Build metadata remains an unverified claim. Only refused records with null
//! observations and blocked activation can be emitted.
//!
//! Input records are borrowed immutably. Validation and the first counting pass
//! allocate nothing; the second pass reserves its complete bounded output with
//! fallible reservation. The 128 KiB wire cap bounds logical output bytes, not
//! allocator overhead, input ownership, native acquisition or process memory.
#![forbid(unsafe_code)]

const MAX_RECEIPT_BYTES: usize = 128 * 1024;

/// Fixed, data-free failure; neither formatting path retains input details.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct CodecError;

impl std::fmt::Display for CodecError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("Invalid minimum refusal receipt")
    }
}

impl std::error::Error for CodecError {}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum ThreadContext {
    NoToken,
    Present,
    Unknown,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Recheck {
    Equal,
    Changed,
    NotCompleted,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Cleanup {
    Complete,
    Failed,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum ErrorKind {
    Primary,
    Cleanup,
    Receipt,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Phase {
    Initial,
    Capture,
    Recheck,
    Cleanup,
    Serialize,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Operation {
    DuplicateHandle,
    GetHandleInformation,
    GetProcessId,
    GetProcessTimes,
    QueryFullProcessImageNameW,
    IsWow64Process2,
    OpenProcessToken,
    OpenThreadToken,
    GetTokenInformation,
    CoInitializeEx,
    SHGetKnownFolderPath,
    CreateFileW,
    NtCreateFile,
    NtQueryInformationFile,
    GetFileInformationByHandleEx,
    GetFileType,
    GetVolumeInformationByHandleW,
    GetFinalPathNameByHandleW,
    GetVolumeNameForVolumeMountPointW,
    GetDriveTypeW,
    GetSecurityInfo,
    LookupPrivilegeNameW,
    CompareStringOrdinal,
    CloseHandle,
    LocalFree,
    Validate,
    Serialize,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Domain {
    Win32,
    Hresult,
    Ntstatus,
    Internal,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Reason {
    Unsupported,
    Malformed,
    Bound,
    Policy,
    Impersonation,
    AppContainer,
    TokenChanged,
    Drift,
    Budget,
    ReceiptBound,
}

#[derive(Clone, Copy)]
pub(crate) struct Collector<'a> {
    pub(crate) source_commit: [u8; 20],
    pub(crate) policy_sha256: [u8; 32],
    pub(crate) target: &'a str,
}

#[derive(Clone, Copy)]
pub(crate) struct Completion {
    pub(crate) call: u32,
    pub(crate) io_status: u32,
    pub(crate) information: u64,
}

#[derive(Clone, Copy)]
pub(crate) struct ErrorRecord {
    pub(crate) kind: ErrorKind,
    pub(crate) phase: Phase,
    pub(crate) operation: Operation,
    pub(crate) domain: Domain,
    pub(crate) code: Option<u32>,
    pub(crate) reason: Option<Reason>,
    pub(crate) ancestor_index: Option<u8>,
    pub(crate) completion: Option<Completion>,
}

#[derive(Clone, Copy)]
pub(crate) struct MinimumRefusal<'a> {
    pub(crate) collector: Collector<'a>,
    pub(crate) started_utc: u64,
    pub(crate) finished_utc: u64,
    pub(crate) elapsed_ms: u64,
    pub(crate) thread_context: ThreadContext,
    pub(crate) recheck: Recheck,
    pub(crate) errors: &'a [ErrorRecord],
    pub(crate) cleanup: Cleanup,
}

fn cleanup_operation(operation: Operation) -> bool {
    matches!(operation, Operation::CloseHandle | Operation::LocalFree)
}

fn validate_error(error: &ErrorRecord) -> Result<(), CodecError> {
    if matches!(error.ancestor_index, Some(index) if index > 127) {
        return Err(CodecError);
    }
    match error.domain {
        Domain::Internal if error.code.is_none() && error.reason.is_some() => {}
        Domain::Win32 | Domain::Hresult | Domain::Ntstatus
            if error.code.is_some() && error.reason.is_none() => {}
        _ => return Err(CodecError),
    }

    match error.completion {
        Some(completion) => {
            // These raw bits mirror the existing 64-bit terminal classifier.
            // Pending native storage must never become a valid receipt.
            if completion.call == 0x103
                || completion.io_status == 0x103
                || (completion.call < 0x8000_0000
                    && completion.io_status == 0xc000_0001
                    && completion.information == u64::MAX)
                || !matches!(
                    error.operation,
                    Operation::NtCreateFile | Operation::NtQueryInformationFile
                )
            {
                return Err(CodecError);
            }
            match error.domain {
                Domain::Ntstatus
                    if error.code == Some(completion.call)
                        && (completion.call != 0 || completion.io_status != 0) => {}
                Domain::Internal
                    if error.reason == Some(Reason::Malformed)
                        && completion.call == 0
                        && completion.io_status == 0 => {}
                _ => return Err(CodecError),
            }
        }
        None if error.domain == Domain::Ntstatus => return Err(CodecError),
        None => {}
    }

    match error.kind {
        ErrorKind::Receipt => {
            if error.phase != Phase::Serialize
                || error.operation != Operation::Serialize
                || error.domain != Domain::Internal
                || error.code.is_some()
                || error.reason != Some(Reason::ReceiptBound)
                || error.ancestor_index.is_some()
                || error.completion.is_some()
            {
                return Err(CodecError);
            }
        }
        ErrorKind::Cleanup => {
            if error.phase != Phase::Cleanup || !cleanup_operation(error.operation) {
                return Err(CodecError);
            }
        }
        ErrorKind::Primary => {
            if error.phase == Phase::Serialize
                || error.operation == Operation::Serialize
                || ((error.phase == Phase::Cleanup) != cleanup_operation(error.operation))
            {
                return Err(CodecError);
            }
        }
    }
    Ok(())
}

/// Check the complete typed minimum subset without repairing or copying it.
pub(crate) fn validate(record: &MinimumRefusal<'_>) -> Result<(), CodecError> {
    if record.collector.target.len() > 128
        || !record.collector.target.is_ascii()
        || record.errors.is_empty()
        || record.errors.len() > 256
    {
        return Err(CodecError);
    }
    let mut primary_seen = false;
    let mut receipt_seen = false;
    let mut cleanup_failed = false;
    for (index, error) in record.errors.iter().enumerate() {
        validate_error(error)?;
        match error.kind {
            ErrorKind::Primary => {
                if primary_seen || index != 0 {
                    return Err(CodecError);
                }
                primary_seen = true;
                cleanup_failed = cleanup_operation(error.operation);
            }
            ErrorKind::Cleanup => {
                if receipt_seen {
                    return Err(CodecError);
                }
                cleanup_failed = true;
            }
            ErrorKind::Receipt => {
                if receipt_seen || index != record.errors.len() - 1 {
                    return Err(CodecError);
                }
                receipt_seen = true;
            }
        }
    }
    if (record.errors.len() == 256 && !receipt_seen)
        || ((record.cleanup == Cleanup::Failed) != cleanup_failed)
    {
        return Err(CodecError);
    }
    Ok(())
}

trait Sink {
    fn append(&mut self, bytes: &[u8]) -> Result<(), CodecError>;
}

struct Counter {
    length: usize,
    limit: usize,
}

impl Sink for Counter {
    fn append(&mut self, bytes: &[u8]) -> Result<(), CodecError> {
        let length = self.length.checked_add(bytes.len()).ok_or(CodecError)?;
        if length > self.limit {
            return Err(CodecError);
        }
        self.length = length;
        Ok(())
    }
}

struct Output {
    bytes: Vec<u8>,
    limit: usize,
}

impl Sink for Output {
    fn append(&mut self, bytes: &[u8]) -> Result<(), CodecError> {
        let length = self.bytes.len().checked_add(bytes.len()).ok_or(CodecError)?;
        if length > self.limit || length > self.bytes.capacity() {
            return Err(CodecError);
        }
        // The complete pass was reserved already; this cannot grow capacity.
        self.bytes.extend_from_slice(bytes);
        Ok(())
    }
}

fn decimal(sink: &mut impl Sink, mut number: u64) -> Result<(), CodecError> {
    let mut buffer = [0u8; 20];
    let mut start = buffer.len();
    loop {
        start -= 1;
        buffer[start] = b'0' + (number % 10) as u8;
        number /= 10;
        if number == 0 {
            break;
        }
    }
    sink.append(&buffer[start..])
}

fn quoted_decimal(sink: &mut impl Sink, number: u64) -> Result<(), CodecError> {
    sink.append(b"\"")?;
    decimal(sink, number)?;
    sink.append(b"\"")
}

fn hex(sink: &mut impl Sink, bytes: &[u8]) -> Result<(), CodecError> {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    sink.append(b"\"")?;
    for &byte in bytes {
        sink.append(&[DIGITS[(byte >> 4) as usize], DIGITS[(byte & 15) as usize]])?;
    }
    sink.append(b"\"")
}

fn string(sink: &mut impl Sink, text: &str) -> Result<(), CodecError> {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    sink.append(b"\"")?;
    for byte in text.bytes() {
        match byte {
            b'"' => sink.append(b"\\\"")?,
            b'\\' => sink.append(b"\\\\")?,
            8 => sink.append(b"\\b")?,
            9 => sink.append(b"\\t")?,
            10 => sink.append(b"\\n")?,
            12 => sink.append(b"\\f")?,
            13 => sink.append(b"\\r")?,
            0..=31 | 127 => {
                sink.append(b"\\u00")?;
                sink.append(&[DIGITS[(byte >> 4) as usize], DIGITS[(byte & 15) as usize]])?;
            }
            32..=126 => sink.append(&[byte])?,
            _ => return Err(CodecError),
        }
    }
    sink.append(b"\"")
}

fn operation_text(operation: Operation) -> &'static str {
    match operation {
        Operation::DuplicateHandle => "DuplicateHandle",
        Operation::GetHandleInformation => "GetHandleInformation",
        Operation::GetProcessId => "GetProcessId",
        Operation::GetProcessTimes => "GetProcessTimes",
        Operation::QueryFullProcessImageNameW => "QueryFullProcessImageNameW",
        Operation::IsWow64Process2 => "IsWow64Process2",
        Operation::OpenProcessToken => "OpenProcessToken",
        Operation::OpenThreadToken => "OpenThreadToken",
        Operation::GetTokenInformation => "GetTokenInformation",
        Operation::CoInitializeEx => "CoInitializeEx",
        Operation::SHGetKnownFolderPath => "SHGetKnownFolderPath",
        Operation::CreateFileW => "CreateFileW",
        Operation::NtCreateFile => "NtCreateFile",
        Operation::NtQueryInformationFile => "NtQueryInformationFile",
        Operation::GetFileInformationByHandleEx => "GetFileInformationByHandleEx",
        Operation::GetFileType => "GetFileType",
        Operation::GetVolumeInformationByHandleW => "GetVolumeInformationByHandleW",
        Operation::GetFinalPathNameByHandleW => "GetFinalPathNameByHandleW",
        Operation::GetVolumeNameForVolumeMountPointW => "GetVolumeNameForVolumeMountPointW",
        Operation::GetDriveTypeW => "GetDriveTypeW",
        Operation::GetSecurityInfo => "GetSecurityInfo",
        Operation::LookupPrivilegeNameW => "LookupPrivilegeNameW",
        Operation::CompareStringOrdinal => "CompareStringOrdinal",
        Operation::CloseHandle => "CloseHandle",
        Operation::LocalFree => "LocalFree",
        Operation::Validate => "validate",
        Operation::Serialize => "serialize",
    }
}

fn reason_text(reason: Reason) -> &'static str {
    match reason {
        Reason::Unsupported => "unsupported",
        Reason::Malformed => "malformed",
        Reason::Bound => "bound",
        Reason::Policy => "policy",
        Reason::Impersonation => "impersonation",
        Reason::AppContainer => "app_container",
        Reason::TokenChanged => "token_changed",
        Reason::Drift => "drift",
        Reason::Budget => "budget",
        Reason::ReceiptBound => "receipt_bound",
    }
}

fn emit_error(sink: &mut impl Sink, error: &ErrorRecord) -> Result<(), CodecError> {
    sink.append(b"{\"ancestor_index\":")?;
    match error.ancestor_index {
        Some(index) => decimal(sink, index as u64)?,
        None => sink.append(b"null")?,
    }
    sink.append(b",\"code\":")?;
    match error.code {
        Some(code) => decimal(sink, code as u64)?,
        None => sink.append(b"null")?,
    }
    sink.append(b",\"completion\":")?;
    match error.completion {
        Some(completion) => {
            sink.append(b"{\"call\":")?;
            decimal(sink, completion.call as u64)?;
            sink.append(b",\"information\":")?;
            quoted_decimal(sink, completion.information)?;
            sink.append(b",\"io_status\":")?;
            decimal(sink, completion.io_status as u64)?;
            sink.append(b"}")?;
        }
        None => sink.append(b"null")?,
    }
    sink.append(b",\"domain\":")?;
    string(sink, match error.domain {
        Domain::Win32 => "win32",
        Domain::Hresult => "hresult",
        Domain::Ntstatus => "ntstatus",
        Domain::Internal => "internal",
    })?;
    sink.append(b",\"kind\":")?;
    string(sink, match error.kind {
        ErrorKind::Primary => "primary",
        ErrorKind::Cleanup => "cleanup",
        ErrorKind::Receipt => "receipt",
    })?;
    sink.append(b",\"operation\":")?;
    string(sink, operation_text(error.operation))?;
    sink.append(b",\"phase\":")?;
    string(sink, match error.phase {
        Phase::Initial => "initial",
        Phase::Capture => "capture",
        Phase::Recheck => "recheck",
        Phase::Cleanup => "cleanup",
        Phase::Serialize => "serialize",
    })?;
    sink.append(b",\"reason\":")?;
    match error.reason {
        Some(reason) => string(sink, reason_text(reason))?,
        None => sink.append(b"null")?,
    }
    sink.append(b"}")
}

// Property order and ASCII escaping match the existing Python reference.
// Both passes call this exact emitter over the same immutably borrowed values.
fn emit(sink: &mut impl Sink, record: &MinimumRefusal<'_>) -> Result<(), CodecError> {
    sink.append(b"{\"activation\":\"blocked\",\"ancestors\":null,\"anchor\":null,\"cleanup\":")?;
    string(sink, match record.cleanup {
        Cleanup::Complete => "complete",
        Cleanup::Failed => "failed",
    })?;
    sink.append(b",\"collector\":{\"policy_sha256\":")?;
    hex(sink, &record.collector.policy_sha256)?;
    sink.append(b",\"source_commit\":")?;
    hex(sink, &record.collector.source_commit)?;
    sink.append(b",\"target\":")?;
    string(sink, record.collector.target)?;
    sink.append(b"},\"elapsed_ms\":")?;
    quoted_decimal(sink, record.elapsed_ms)?;
    sink.append(b",\"errors\":[")?;
    for (index, error) in record.errors.iter().enumerate() {
        if index != 0 {
            sink.append(b",")?;
        }
        emit_error(sink, error)?;
    }
    sink.append(b"],\"finished_utc\":")?;
    quoted_decimal(sink, record.finished_utc)?;
    sink.append(b",\"loaded_image_provenance\":\"not_established\",\"mode\":\"diagnostic_only\",\"outcome\":\"refused\",\"primary_token\":null,\"process\":null,\"product_collision\":\"not_observed\",\"recheck\":")?;
    string(sink, match record.recheck {
        Recheck::Equal => "equal",
        Recheck::Changed => "changed",
        Recheck::NotCompleted => "not_completed",
    })?;
    sink.append(b",\"schema\":\"hub_relay.bootstrap_inventory.v0.1\",\"service_collision\":\"not_observed\",\"service_sid_binding\":\"external_evidence_required\",\"started_utc\":")?;
    quoted_decimal(sink, record.started_utc)?;
    sink.append(b",\"thread_context\":")?;
    string(sink, match record.thread_context {
        ThreadContext::NoToken => "no_token",
        ThreadContext::Present => "present",
        ThreadContext::Unknown => "unknown",
    })?;
    sink.append(b",\"thread_token\":null}")
}

fn serialize_limited(record: &MinimumRefusal<'_>, limit: usize) -> Result<Vec<u8>, CodecError> {
    validate(record)?;
    let mut counter = Counter { length: 0, limit: limit.min(MAX_RECEIPT_BYTES) };
    emit(&mut counter, record)?;
    let mut output = Output { bytes: Vec::new(), limit: counter.length };
    output.bytes.try_reserve_exact(counter.length).map_err(|_| CodecError)?;
    emit(&mut output, record)?;
    if output.bytes.len() != counter.length {
        return Err(CodecError);
    }
    Ok(output.bytes)
}

/// Return one complete bounded JSON value, or a fixed error and no partial bytes.
pub(crate) fn serialize(record: &MinimumRefusal<'_>) -> Result<Vec<u8>, CodecError> {
    serialize_limited(record, MAX_RECEIPT_BYTES)
}

#[cfg(test)]
pub(crate) fn serialize_with_limit_for_test(
    record: &MinimumRefusal<'_>,
    limit: usize,
) -> Result<Vec<u8>, CodecError> {
    serialize_limited(record, limit)
}
