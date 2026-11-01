//! Bounded own-process observations. These records convey no authority.
//!
//! The acquisition adapter copies every declared field before reusing native
//! storage. Equality uses index views over those copies, never live pointers.
use crate::arena::Arena;
use crate::model::{Domain, Error, Luid, Operation, Phase, Privilege, Process, Reason, Result,
    SidAttributes, ThreadContext, Token};
use crate::token_buffer::{self, DecodeError, Layout, TokenInformation};
use std::cmp::Ordering;

const MAX_BUFFER: usize = 65_536;
const MAX_GROUPS: usize = 2_048;
const MAX_PRIVILEGES: usize = 256;
const MAX_PRIVILEGE_NAME: usize = 256;

pub struct State<'a> {
    pub process: Option<Process<'a>>,
    pub primary: Option<Token<'a>>,
    pub thread: Option<Token<'a>>,
    pub thread_context: ThreadContext,
    process_slot: Option<usize>,
    primary_slot: Option<usize>,
    thread_slot: Option<usize>,
}

impl<'a> State<'a> {
    pub const fn new() -> Self {
        Self { process: None, primary: None, thread: None, thread_context: ThreadContext::Unknown,
            process_slot: None, primary_slot: None, thread_slot: None }
    }
}
impl Default for State<'_> { fn default() -> Self { Self::new() } }

fn malformed(phase: Phase) -> Error {
    Error::internal(phase, Operation::GetTokenInformation, Reason::Malformed)
}
fn in_phase(mut error: Error, phase: Phase) -> Error { error.phase = phase; error }
fn decode_error(error: DecodeError, phase: Phase) -> Error {
    let reason = match error {
        DecodeError::UnsupportedClass | DecodeError::UnsupportedLayout => Reason::Unsupported,
        DecodeError::BufferTooLarge | DecodeError::CountLimit => Reason::Bound,
        _ => Reason::Malformed,
    };
    Error::internal(phase, Operation::GetTokenInformation, reason)
}

/// Pure acquisition seam for synthetic fixtures; no implementation chooses a PID
/// or changes a token. Production supplies only the retained own-token handle.
pub trait TokenSource {
    fn size(&mut self, class: u32) -> Result<usize>;
    fn retrieve(&mut self, class: u32, bytes: &mut [u8]) -> Result<usize>;
    fn privilege_name(&mut self, luid: Luid, name: &mut [u16]) -> Result<usize>;
}

pub fn validate_token_size(size: usize, phase: Phase) -> Result<usize> {
    if size == 0 { return Err(malformed(phase)); }
    if size > MAX_BUFFER {
        return Err(Error::internal(phase, Operation::GetTokenInformation, Reason::Bound));
    }
    Ok(size)
}

pub fn validate_retrieval(expected: usize, returned: usize, phase: Phase) -> Result<()> {
    validate_token_size(expected, phase)?;
    if expected != returned { return Err(malformed(phase)); }
    Ok(())
}

/// Candidate-only class-21 compatibility interpretation. The pinned historical
/// decoder remains byte-for-byte unchanged and requires a four-byte DWORD.
/// Microsoft Learn still describes DWORD; Jevan Saks's 2026-09-15 clarification
/// in microsoft/win32metadata discussion 2308 describes a BOOLEAN at a DWORD-
/// aligned address and confirms capacity four / ReturnLength one. The union of
/// returned lengths one and four here is this candidate's interpretation, pending
/// independent review and exact native evidence, not an adopted universal ABI.
/// Only the returned extent is consumed; no bool normalization or trailing read.
pub fn decode_scalar(class: u32, bytes: &[u8], base: u64, phase: Phase) -> Result<u32> {
    if class == 21 {
        if base % 4 != 0 || base.checked_add(bytes.len() as u64).is_none() {
            return Err(malformed(phase));
        }
        return match bytes {
            [value] => Ok(u32::from(*value)),
            [a, b, c, d] => Ok(u32::from_le_bytes([*a, *b, *c, *d])),
            _ => Err(malformed(phase)),
        };
    }
    match token_buffer::decode(Layout::WindowsX64, class, bytes, base)
        .map_err(|error| decode_error(error, phase))? {
        TokenInformation::Dword(value) => Ok(value),
        _ => Err(malformed(phase)),
    }
}

pub fn classify_thread_failure(code: u32, phase: Phase) -> Result<ThreadContext> {
    // No access-denied/anonymous/unsupported error establishes nonimpersonation.
    if code == 1008 { return Ok(ThreadContext::NoToken); } // ERROR_NO_TOKEN
    Err(Error::native(phase, Operation::OpenThreadToken, Domain::Win32, code))
}

#[repr(C, align(8))]
struct TokenBuffer([u8; MAX_BUFFER]);

fn query<'b>(source: &mut impl TokenSource, buffer: &'b mut TokenBuffer,
    class: u32, phase: Phase) -> Result<TokenInformation<'b>> {
    let capacity = match class {
        1 | 2 | 3 | 4 | 5 | 11 | 25 | 30 => {
            let size = source.size(class).map_err(|error| in_phase(error, phase))?;
            validate_token_size(size, phase)?
        }
        10 => 56,
        _ => 4,
    };
    buffer.0[..capacity].fill(0);
    let returned = source.retrieve(class, &mut buffer.0[..capacity])
        .map_err(|error| in_phase(error, phase))?;
    // No growth retry, truncation tolerance, or capacity-as-length substitution.
    if class != 21 { validate_retrieval(capacity, returned, phase)?; }
    else if returned != 1 && returned != 4 { return Err(malformed(phase)); }
    let bytes = &buffer.0[..returned];
    let base = buffer.0.as_ptr() as u64;
    if class == 21 {
        return Ok(TokenInformation::Dword(decode_scalar(class, bytes, base, phase)?));
    }
    token_buffer::decode(Layout::WindowsX64, class, bytes, base)
        .map_err(|error| decode_error(error, phase))
}

fn statistics(source: &mut impl TokenSource, buffer: &mut TokenBuffer,
    phase: Phase) -> Result<token_buffer::Statistics> {
    match query(source, buffer, 10, phase)? {
        TokenInformation::Statistics(value) => Ok(value), _ => Err(malformed(phase)),
    }
}
fn scalar(source: &mut impl TokenSource, buffer: &mut TokenBuffer,
    class: u32, phase: Phase) -> Result<u32> {
    match query(source, buffer, class, phase)? {
        TokenInformation::Dword(value) => Ok(value), _ => Err(malformed(phase)),
    }
}
fn sid<'a>(arena: &'a Arena, source: &mut impl TokenSource, buffer: &mut TokenBuffer,
    class: u32, phase: Phase) -> Result<&'a [u8]> {
    let bytes = match query(source, buffer, class, phase)? {
        TokenInformation::Sid(value) => value.as_bytes(),
        TokenInformation::SidAndAttributes(value) => value.sid().as_bytes(),
        _ => return Err(malformed(phase)),
    };
    arena.bytes(bytes).map_err(|error| in_phase(error, phase))
}
fn sid_attributes<'a>(arena: &'a Arena, source: &mut impl TokenSource,
    buffer: &mut TokenBuffer, class: u32, phase: Phase) -> Result<SidAttributes<'a>> {
    match query(source, buffer, class, phase)? {
        TokenInformation::SidAndAttributes(value) => Ok(SidAttributes {
            sid: arena.bytes(value.sid().as_bytes()).map_err(|error| in_phase(error, phase))?,
            attributes: value.attributes(),
        }),
        _ => Err(malformed(phase)),
    }
}
fn groups<'a>(arena: &'a Arena, source: &mut impl TokenSource, buffer: &mut TokenBuffer,
    class: u32, phase: Phase) -> Result<&'a [SidAttributes<'a>]> {
    let values = match query(source, buffer, class, phase)? {
        TokenInformation::Groups(values) => values, _ => return Err(malformed(phase)),
    };
    let mut copied = [SidAttributes { sid: &[], attributes: 0 }; MAX_GROUPS];
    for (target, value) in copied.iter_mut().zip(values.iter()) {
        *target = SidAttributes {
            sid: arena.bytes(value.sid().as_bytes()).map_err(|error| in_phase(error, phase))?,
            attributes: value.attributes(),
        };
    }
    arena.slice(&copied[..values.len()]).map_err(|error| in_phase(error, phase))
}
fn luid(value: token_buffer::Luid) -> Luid { Luid { low: value.low, high: value.high } }
fn privileges<'a>(arena: &'a Arena, source: &mut impl TokenSource,
    buffer: &mut TokenBuffer, phase: Phase) -> Result<&'a [Privilege<'a>]> {
    let values = match query(source, buffer, 3, phase)? {
        TokenInformation::Privileges(values) => values, _ => return Err(malformed(phase)),
    };
    let mut copied = [Privilege { luid: Luid { low: 0, high: 0 }, name: "", attributes: 0 }; MAX_PRIVILEGES];
    for (target, value) in copied.iter_mut().zip(values.iter()) {
        // The API receives room for the maximum name plus its terminator, once.
        let mut name = [0_u16; MAX_PRIVILEGE_NAME + 1];
        let id = luid(value.luid());
        let length = source.privilege_name(id, &mut name).map_err(|error| in_phase(error, phase))?;
        if length == 0 { return Err(Error::internal(phase, Operation::LookupPrivilegeNameW, Reason::Malformed)); }
        if length > MAX_PRIVILEGE_NAME {
            return Err(Error::internal(phase, Operation::LookupPrivilegeNameW, Reason::Bound));
        }
        *target = Privilege { luid: id,
            name: arena.text(&name[..length], MAX_PRIVILEGE_NAME).map_err(|error| in_phase(error, phase))?,
            attributes: value.attributes(),
        };
    }
    arena.slice(&copied[..values.len()]).map_err(|error| in_phase(error, phase))
}

/// Complete declared token capture. A returned record contains no borrowed native
/// storage; failure returns no partial record. Fixed classes receive one retrieval;
/// each variable class receives exactly one size query and one bounded retrieval.
pub fn capture_token<'a>(arena: &'a Arena, source: &mut impl TokenSource, phase: Phase) -> Result<Token<'a>> {
    let mut buffer = TokenBuffer([0; MAX_BUFFER]);
    let before = statistics(source, &mut buffer, phase)?;
    let token_type = scalar(source, &mut buffer, 8, phase)?;
    let impersonation_level = if token_type == 2 { Some(scalar(source, &mut buffer, 9, phase)?) } else { None };
    let user = sid(arena, source, &mut buffer, 1, phase)?;
    let owner = sid(arena, source, &mut buffer, 4, phase)?;
    let primary_group = sid(arena, source, &mut buffer, 5, phase)?;
    let integrity = sid_attributes(arena, source, &mut buffer, 25, phase)?;
    let groups = groups(arena, source, &mut buffer, 2, phase)?;
    let restricted_sids = self::groups(arena, source, &mut buffer, 11, phase)?;
    let capabilities = self::groups(arena, source, &mut buffer, 30, phase)?;
    let privileges = privileges(arena, source, &mut buffer, phase)?;
    let session_id = scalar(source, &mut buffer, 12, phase)?;
    let elevation_type = scalar(source, &mut buffer, 18, phase)?;
    let elevation = scalar(source, &mut buffer, 20, phase)?;
    let has_restrictions = scalar(source, &mut buffer, 21, phase)?;
    let is_app_container = scalar(source, &mut buffer, 29, phase)?;
    let mandatory_policy = scalar(source, &mut buffer, 27, phase)?;
    let ui_access = scalar(source, &mut buffer, 26, phase)?;
    let virtualization_allowed = scalar(source, &mut buffer, 23, phase)?;
    let virtualization_enabled = scalar(source, &mut buffer, 24, phase)?;
    let after = statistics(source, &mut buffer, phase)?;
    if before.token_id != after.token_id || before.modified_id != after.modified_id
        || before.authentication_id != after.authentication_id || before.token_type != token_type
        || after.token_type != token_type || before.group_count as usize != groups.len()
        || after.group_count != before.group_count || before.privilege_count as usize != privileges.len()
        || after.privilege_count != before.privilege_count
        || impersonation_level.is_some_and(|level| level != before.impersonation_level || level != after.impersonation_level) {
        return Err(Error::internal(phase, Operation::GetTokenInformation, Reason::TokenChanged));
    }
    Ok(Token { token_type, impersonation_level, user, owner, primary_group, integrity, groups,
        restricted_sids, capabilities, privileges, token_id: luid(before.token_id),
        authentication_id: luid(before.authentication_id), modified_id: luid(before.modified_id),
        session_id, elevation_type, elevation, has_restrictions, is_app_container, mandatory_policy,
        ui_access, virtualization_allowed, virtualization_enabled })
}

fn sid_cmp(left: &SidAttributes<'_>, right: &SidAttributes<'_>) -> Ordering {
    left.sid.cmp(right.sid).then_with(|| left.attributes.cmp(&right.attributes))
}
fn privilege_cmp(left: &Privilege<'_>, right: &Privilege<'_>) -> Ordering {
    left.luid.low.cmp(&right.luid.low).then_with(|| left.luid.high.cmp(&right.luid.high))
        .then_with(|| left.name.cmp(right.name)).then_with(|| left.attributes.cmp(&right.attributes))
}
fn multiset<T, const N: usize>(left: &[T], right: &[T], compare: impl Fn(&T, &T) -> Ordering,
    phase: Phase) -> Result<bool> {
    if left.len() > N || right.len() > N {
        return Err(Error::internal(phase, Operation::GetTokenInformation, Reason::Bound));
    }
    if left.len() != right.len() { return Ok(false); }
    // Allocation-free canonical index views leave every captured entry unchanged.
    let mut left_index = [0_usize; N];
    let mut right_index = [0_usize; N];
    for (index, target) in left_index[..left.len()].iter_mut().enumerate() { *target = index; }
    for (index, target) in right_index[..right.len()].iter_mut().enumerate() { *target = index; }
    left_index[..left.len()].sort_unstable_by(|a, b| compare(&left[*a], &left[*b]));
    right_index[..right.len()].sort_unstable_by(|a, b| compare(&right[*a], &right[*b]));
    Ok(left_index[..left.len()].iter().zip(&right_index[..right.len()])
        .all(|(a, b)| compare(&left[*a], &right[*b]) == Ordering::Equal))
}

pub fn tokens_equal(left: &Token<'_>, right: &Token<'_>, phase: Phase) -> Result<bool> {
    let groups = multiset::<_, MAX_GROUPS>(left.groups, right.groups, sid_cmp, phase)?;
    let restricted = multiset::<_, MAX_GROUPS>(left.restricted_sids, right.restricted_sids, sid_cmp, phase)?;
    let capabilities = multiset::<_, MAX_GROUPS>(left.capabilities, right.capabilities, sid_cmp, phase)?;
    let privileges = multiset::<_, MAX_PRIVILEGES>(left.privileges, right.privileges, privilege_cmp, phase)?;
    // Derived equality covers every remaining declared field, including raw bits.
    let mut a = *left;
    let mut b = *right;
    a.groups = &[]; a.restricted_sids = &[]; a.capabilities = &[]; a.privileges = &[];
    b.groups = &[]; b.restricted_sids = &[]; b.capabilities = &[]; b.privileges = &[];
    Ok(a == b && groups && restricted && capabilities && privileges)
}

#[cfg(windows)]
pub use native::{capture, recheck};

#[cfg(windows)]
mod native {
    use super::*;
    use crate::model::Path;
    use crate::windows::{Context, ResourceKind};
    use windows_sys::Win32::Foundation::{DuplicateHandle, FILETIME, GetLastError, HANDLE, LUID};
    use windows_sys::Win32::Security::{GetTokenInformation, LookupPrivilegeNameW};
    use windows_sys::Win32::System::Threading::{GetCurrentProcess, GetCurrentThread, GetProcessId,
        GetProcessTimes, IsWow64Process2, OpenProcessToken, OpenThreadToken, QueryFullProcessImageNameW};

    fn last_error(phase: Phase, operation: Operation) -> Error {
        Error::native(phase, operation, Domain::Win32, unsafe { GetLastError() })
    }
    fn internal(phase: Phase, operation: Operation, reason: Reason) -> Error {
        Error::internal(phase, operation, reason)
    }
    struct NativeTokenSource<'c, 'a> { ctx: &'c mut Context<'a>, handle: HANDLE, phase: Phase }
    impl TokenSource for NativeTokenSource<'_, '_> {
        fn size(&mut self, class: u32) -> Result<usize> {
            let mut returned = 0;
            self.ctx.check(Operation::GetTokenInformation, self.phase)?;
            if unsafe { GetTokenInformation(self.handle, class as i32, std::ptr::null_mut(), 0, &mut returned) } != 0 {
                return Err(malformed(self.phase));
            }
            let code = unsafe { GetLastError() };
            if code != 122 { // ERROR_INSUFFICIENT_BUFFER is the only sizing response.
                return Err(Error::native(self.phase, Operation::GetTokenInformation, Domain::Win32, code));
            }
            Ok(returned as usize)
        }
        fn retrieve(&mut self, class: u32, bytes: &mut [u8]) -> Result<usize> {
            let mut returned = 0;
            self.ctx.check(Operation::GetTokenInformation, self.phase)?;
            if unsafe { GetTokenInformation(self.handle, class as i32, bytes.as_mut_ptr().cast(), bytes.len() as u32, &mut returned) } == 0 {
                return Err(last_error(self.phase, Operation::GetTokenInformation));
            }
            Ok(returned as usize)
        }
        fn privilege_name(&mut self, luid: Luid, name: &mut [u16]) -> Result<usize> {
            let id = LUID { LowPart: luid.low, HighPart: luid.high };
            let mut length = name.len() as u32;
            self.ctx.check(Operation::LookupPrivilegeNameW, self.phase)?;
            if unsafe { LookupPrivilegeNameW(std::ptr::null(), &id, name.as_mut_ptr(), &mut length) } == 0 {
                return Err(last_error(self.phase, Operation::LookupPrivilegeNameW));
            }
            Ok(length as usize)
        }
    }
    fn token<'a>(ctx: &mut Context<'a>, slot: usize, phase: Phase) -> Result<Token<'a>> {
        let arena = ctx.arena;
        let handle = ctx.raw(slot);
        capture_token(arena, &mut NativeTokenSource { ctx, handle, phase }, phase)
    }
    fn image<'a>(ctx: &mut Context<'a>, handle: HANDLE, flags: u32, phase: Phase) -> Result<Path<'a>> {
        let mut buffer = [0_u16; 32_768];
        let mut length = buffer.len() as u32;
        ctx.check(Operation::QueryFullProcessImageNameW, phase)?;
        if unsafe { QueryFullProcessImageNameW(handle, flags, buffer.as_mut_ptr(), &mut length) } == 0 {
            return Err(last_error(phase, Operation::QueryFullProcessImageNameW));
        }
        if length == 0 || length > 32_767 {
            return Err(internal(phase, Operation::QueryFullProcessImageNameW, Reason::Bound));
        }
        ctx.arena.path(&buffer[..length as usize]).map_err(|error| in_phase(error, phase))
    }
    fn process<'a>(ctx: &mut Context<'a>, slot: usize, phase: Phase) -> Result<Process<'a>> {
        let handle = ctx.raw(slot);
        ctx.check(Operation::GetProcessId, phase)?;
        let pid = unsafe { GetProcessId(handle) };
        if pid == 0 { return Err(last_error(phase, Operation::GetProcessId)); }
        let mut creation = FILETIME { dwLowDateTime: 0, dwHighDateTime: 0 };
        let mut exit = creation;
        let mut kernel = creation;
        let mut user = creation;
        ctx.check(Operation::GetProcessTimes, phase)?;
        if unsafe { GetProcessTimes(handle, &mut creation, &mut exit, &mut kernel, &mut user) } == 0 {
            return Err(last_error(phase, Operation::GetProcessTimes));
        }
        let mut process_machine = u16::MAX;
        let mut native_machine = u16::MAX;
        ctx.check(Operation::IsWow64Process2, phase)?;
        if unsafe { IsWow64Process2(handle, &mut process_machine, &mut native_machine) } == 0 {
            return Err(last_error(phase, Operation::IsWow64Process2));
        }
        if !cfg!(target_arch = "x86_64") || process_machine != 0 || native_machine != 0x8664 {
            return Err(internal(phase, Operation::IsWow64Process2, Reason::Unsupported));
        }
        let image_win32 = image(ctx, handle, 0, phase)?;
        let image_native = image(ctx, handle, 1, phase)?; // PROCESS_NAME_NATIVE
        Ok(Process { pid, creation_utc: (u64::from(creation.dwHighDateTime) << 32) | u64::from(creation.dwLowDateTime),
            process_machine, native_machine, image_win32, image_native })
    }
    fn open_primary(ctx: &mut Context<'_>, process_slot: usize, phase: Phase) -> Result<usize> {
        let mut handle = std::ptr::null_mut();
        ctx.check(Operation::OpenProcessToken, phase)?;
        ctx.before_acquire(ResourceKind::ProcessToken)?;
        if unsafe { OpenProcessToken(ctx.raw(process_slot), 0x0008, &mut handle) } == 0 {
            return Err(last_error(phase, Operation::OpenProcessToken));
        }
        // Context owns the returned handle even when inheritance validation fails.
        ctx.acquire(handle, ResourceKind::ProcessToken).map_err(|error| in_phase(error, phase))
    }
    fn thread<'a>(ctx: &mut Context<'a>, state: &mut State<'a>, phase: Phase) -> Result<()> {
        let mut handle = std::ptr::null_mut();
        ctx.check(Operation::OpenThreadToken, phase)?;
        ctx.before_acquire(ResourceKind::ProcessToken)?;
        if unsafe { OpenThreadToken(GetCurrentThread(), 0x0008, 1, &mut handle) } == 0 {
            let code = unsafe { GetLastError() };
            state.thread_context = ThreadContext::Unknown;
            state.thread_context = classify_thread_failure(code, phase)?;
            return Ok(());
        }
        state.thread_context = ThreadContext::Present;
        let slot = ctx.acquire(handle, ResourceKind::ProcessToken).map_err(|error| in_phase(error, phase))?;
        state.thread_slot = Some(slot);
        // Present context remains present on any incomplete capture; only a full
        // record is installed. No impersonation-clearing or identity fallback.
        state.thread = Some(token(ctx, slot, phase)?);
        Err(internal(phase, Operation::OpenThreadToken, Reason::Impersonation))
    }

    pub fn capture<'a>(ctx: &mut Context<'a>, state: &mut State<'a>) -> Result<()> {
        if state.process_slot.is_some() || state.primary_slot.is_some() || state.thread_slot.is_some()
            || state.process.is_some() || state.primary.is_some() || state.thread.is_some() {
            return Err(internal(Phase::Capture, Operation::Validate, Reason::Malformed));
        }
        if !cfg!(target_arch = "x86_64") {
            return Err(internal(Phase::Capture, Operation::IsWow64Process2, Reason::Unsupported));
        }
        let mut handle = std::ptr::null_mut();
        ctx.check(Operation::DuplicateHandle, Phase::Capture)?;
        ctx.before_acquire(ResourceKind::ProcessToken)?;
        if unsafe { DuplicateHandle(GetCurrentProcess(), GetCurrentProcess(), GetCurrentProcess(),
            &mut handle, 0x1000, 0, 0) } == 0 { // QUERY_LIMITED_INFORMATION; no SYNCHRONIZE/options.
            return Err(last_error(Phase::Capture, Operation::DuplicateHandle));
        }
        let process_slot = ctx.acquire(handle, ResourceKind::ProcessToken)?;
        state.process_slot = Some(process_slot);
        state.process = Some(process(ctx, process_slot, Phase::Capture)?);
        let primary_slot = open_primary(ctx, process_slot, Phase::Capture)?;
        state.primary_slot = Some(primary_slot);
        let primary = token(ctx, primary_slot, Phase::Capture)?;
        state.primary = Some(primary);
        if primary.token_type != 1 {
            return Err(internal(Phase::Capture, Operation::GetTokenInformation, Reason::Impersonation));
        }
        if primary.is_app_container != 0 {
            return Err(internal(Phase::Capture, Operation::GetTokenInformation, Reason::AppContainer));
        }
        thread(ctx, state, Phase::Capture)
    }

    pub fn recheck<'a>(ctx: &mut Context<'a>, state: &mut State<'a>) -> Result<()> {
        if state.thread_context != ThreadContext::NoToken {
            return Err(internal(Phase::Recheck, Operation::OpenThreadToken, Reason::Impersonation));
        }
        let process_slot = state.process_slot.ok_or_else(|| internal(Phase::Recheck, Operation::Validate, Reason::Malformed))?;
        let original_process = state.process.ok_or_else(|| internal(Phase::Recheck, Operation::Validate, Reason::Malformed))?;
        let original_token = state.primary.ok_or_else(|| internal(Phase::Recheck, Operation::Validate, Reason::Malformed))?;
        if state.primary_slot.is_none() { return Err(internal(Phase::Recheck, Operation::Validate, Reason::Malformed)); }
        if process(ctx, process_slot, Phase::Recheck)? != original_process {
            return Err(internal(Phase::Recheck, Operation::Validate, Reason::Drift));
        }
        // Reopen the primary currently associated with the real process handle.
        // Stability of the old token handle alone cannot detect replacement.
        let current = open_primary(ctx, process_slot, Phase::Recheck)?;
        let compared = token(ctx, current, Phase::Recheck).and_then(|observed| {
            if tokens_equal(&original_token, &observed, Phase::Recheck)? { Ok(()) }
            else { Err(internal(Phase::Recheck, Operation::GetTokenInformation, Reason::TokenChanged)) }
        });
        if let Err(error) = compared { ctx.errors.primary(error); }
        let closed = ctx.close(current);
        if let Err(primary) = compared {
            if let Err(cleanup) = closed { ctx.errors.cleanup(cleanup); }
            return Err(primary);
        }
        // A first close failure remains the primary error, with Cleanup phase.
        closed?;
        thread(ctx, state, Phase::Recheck)
    }
}
