//! Partial, private primary-token account diagnostics; never approval.

use super::{Error, Failure, OwnProcessObservation, Result, denied, finish, last, raw};
use std::mem::{align_of, size_of};
use std::os::windows::io::{FromRawHandle, IntoRawHandle, OwnedHandle};
use std::ptr::null_mut;
use windows_sys::Win32::Foundation::*;
use windows_sys::Win32::Security::*;
// Uppercase aliases keep native class values usable in Rust constant patterns.
use windows_sys::Win32::Security::{
    TokenUser as CLASS_USER, TokenType as CLASS_TYPE,
    TokenStatistics as CLASS_STATISTICS, TokenElevationType as CLASS_ELEVATION_TYPE,
    TokenElevation as CLASS_ELEVATION, TokenIsAppContainer as CLASS_IS_APP_CONTAINER,
    TokenImpersonationLevel as CLASS_IMPERSONATION_LEVEL,
};
use windows_sys::Win32::System::Threading::{GetCurrentThread, OpenProcessToken, OpenThreadToken};

const MAX_TOKEN_BYTES: usize = 65536;

// Both selected native records have at most eight-byte alignment. The
// allocation remains fixed while Windows writes pointers into TokenUser.
#[repr(C, align(8))]
#[derive(Clone)]
struct AlignedWord([u8; 8]);

struct AlignedBuffer {
    words: Vec<AlignedWord>,
    length: usize,
}

impl AlignedBuffer {
    fn new(length: usize) -> Result<Self> {
        if length == 0 || length > MAX_TOKEN_BYTES {
            return Err(denied("token buffer bound"));
        }
        Ok(Self {
            words: vec![AlignedWord([0; 8]); length.div_ceil(size_of::<AlignedWord>())],
            length,
        })
    }

    fn bytes_mut(&mut self) -> &mut [u8] {
        // SAFETY: the zeroed backing allocation contains at least length bytes.
        unsafe { std::slice::from_raw_parts_mut(self.words.as_mut_ptr().cast(), self.length) }
    }

    fn bytes(&self) -> &[u8] {
        // SAFETY: every byte is initialized and the allocation is at least length.
        unsafe { std::slice::from_raw_parts(self.words.as_ptr().cast(), self.length) }
    }
}

#[derive(Clone, PartialEq, Eq)]
struct UserFacts {
    sid: Vec<u8>,
    attributes: u32,
}

fn parse_user(buffer: &[u8]) -> Result<UserFacts> {
    let header_length = size_of::<TOKEN_USER>();
    let base = buffer.as_ptr() as usize;
    if buffer.len() < header_length
        || buffer.len() > MAX_TOKEN_BYTES
        || !base.is_multiple_of(align_of::<TOKEN_USER>())
    {
        return Err(denied("TokenUser header layout"));
    }
    // SAFETY: the complete, aligned header is inside the returned byte slice.
    // Copying its raw pointer value does not dereference that pointer.
    let header = unsafe { buffer.as_ptr().cast::<TOKEN_USER>().read() };
    let address = header.User.Sid as usize;
    let offset = address
        .checked_sub(base)
        .filter(|offset| *offset >= header_length)
        .ok_or_else(|| denied("TokenUser SID pointer"))?;
    if !address.is_multiple_of(align_of::<u32>()) {
        return Err(denied("TokenUser SID alignment"));
    }
    let sid_header_end = offset
        .checked_add(8)
        .filter(|end| *end <= buffer.len())
        .ok_or_else(|| denied("TokenUser SID header extent"))?;
    let sid_header = &buffer[offset..sid_header_end];
    if sid_header[0] != 1 || sid_header[1] > 15 {
        return Err(denied("TokenUser SID revision or count"));
    }
    let length = usize::from(sid_header[1])
        .checked_mul(4)
        .and_then(|count| count.checked_add(8))
        .filter(|length| *length <= 68)
        .ok_or_else(|| denied("TokenUser SID bound"))?;
    let end = offset
        .checked_add(length)
        .filter(|end| *end <= buffer.len())
        .ok_or_else(|| denied("TokenUser SID extent"))?;
    Ok(UserFacts {
        sid: buffer[offset..end].to_vec(),
        attributes: header.User.Attributes,
    })
}

#[derive(Clone, PartialEq, Eq)]
struct StatisticsFacts {
    token_id: (u32, i32),
    authentication_id: (u32, i32),
    expiration: i64,
    token_type: TOKEN_TYPE,
    impersonation_level: SECURITY_IMPERSONATION_LEVEL,
    dynamic_charged: u32,
    dynamic_available: u32,
    group_count: u32,
    privilege_count: u32,
    modified_id: (u32, i32),
}

impl From<TOKEN_STATISTICS> for StatisticsFacts {
    fn from(value: TOKEN_STATISTICS) -> Self {
        Self {
            token_id: (value.TokenId.LowPart, value.TokenId.HighPart),
            authentication_id: (
                value.AuthenticationId.LowPart,
                value.AuthenticationId.HighPart,
            ),
            expiration: value.ExpirationTime,
            token_type: value.TokenType,
            impersonation_level: value.ImpersonationLevel,
            dynamic_charged: value.DynamicCharged,
            dynamic_available: value.DynamicAvailable,
            group_count: value.GroupCount,
            privilege_count: value.PrivilegeCount,
            modified_id: (value.ModifiedId.LowPart, value.ModifiedId.HighPart),
        }
    }
}

#[derive(Clone, PartialEq, Eq)]
struct TokenFacts {
    user: UserFacts,
    token_type: u32,
    statistics: StatisticsFacts,
    elevation_type: u32,
    elevated: bool,
    app_container: bool,
}

struct QueryReply {
    success: bool,
    length: u32,
    code: u32,
}

// This seam owns only acquisition/query/check/cleanup behavior. Native handles
// and synthetic test IDs are separate associated types with consuming cleanup.
trait TokenApi {
    type Handle;

    fn process_recheck(&mut self) -> Result<()>;
    fn open_primary(&mut self) -> Result<Self::Handle>;
    fn open_thread(&mut self) -> Result<Option<Self::Handle>>;
    fn noninheritable(&mut self, handle: &Self::Handle) -> Result<()>;
    fn close(&mut self, handle: Self::Handle) -> Result<()>;
    fn query(
        &mut self,
        handle: &Self::Handle,
        class: TOKEN_INFORMATION_CLASS,
        buffer: Option<&mut [u8]>,
    ) -> QueryReply;
}

fn native_error(operation: &'static str, code: u32) -> Error {
    Error {
        primary: Failure::Native(operation, code),
        cleanup: vec![],
    }
}

fn operation(class: TOKEN_INFORMATION_CLASS) -> &'static str {
    match class {
        CLASS_USER => "GetTokenInformation TokenUser",
        CLASS_TYPE => "GetTokenInformation TokenType",
        CLASS_STATISTICS => "GetTokenInformation TokenStatistics",
        CLASS_ELEVATION_TYPE => "GetTokenInformation TokenElevationType",
        CLASS_ELEVATION => "GetTokenInformation TokenElevation",
        CLASS_IS_APP_CONTAINER => "GetTokenInformation TokenIsAppContainer",
        CLASS_IMPERSONATION_LEVEL => "GetTokenInformation TokenImpersonationLevel",
        _ => "GetTokenInformation selected class",
    }
}

fn fixed<A: TokenApi>(
    api: &mut A,
    handle: &A::Handle,
    class: TOKEN_INFORMATION_CLASS,
    length: usize,
) -> Result<AlignedBuffer> {
    let mut buffer = AlignedBuffer::new(length)?;
    let reply = api.query(handle, class, Some(buffer.bytes_mut()));
    if !reply.success {
        return Err(native_error(operation(class), reply.code));
    }
    if reply.length as usize != length {
        return Err(denied("fixed token information size"));
    }
    Ok(buffer)
}

fn scalar<A: TokenApi>(
    api: &mut A,
    handle: &A::Handle,
    class: TOKEN_INFORMATION_CLASS,
) -> Result<u32> {
    // The pinned bindings use one 32-bit integer for each selected scalar,
    // including TOKEN_ELEVATION's sole TokenIsElevated member.
    let buffer = fixed(api, handle, class, size_of::<u32>())?;
    // SAFETY: exact initialized u32 size, aligned backing allocation, all bits valid.
    Ok(unsafe { buffer.bytes().as_ptr().cast::<u32>().read() })
}

fn statistics<A: TokenApi>(api: &mut A, handle: &A::Handle) -> Result<StatisticsFacts> {
    let buffer = fixed(api, handle, TokenStatistics, size_of::<TOKEN_STATISTICS>())?;
    // SAFETY: exact initialized native record size and eight-byte alignment;
    // the pinned record contains only integer fields and integer enum aliases.
    Ok(unsafe { buffer.bytes().as_ptr().cast::<TOKEN_STATISTICS>().read() }.into())
}

fn user<A: TokenApi>(api: &mut A, handle: &A::Handle) -> Result<UserFacts> {
    let sizing = api.query(handle, TokenUser, None);
    if sizing.success {
        return Err(denied("unexpected TokenUser sizing success"));
    }
    if sizing.code != ERROR_INSUFFICIENT_BUFFER {
        return Err(native_error(operation(TokenUser), sizing.code));
    }
    let mut buffer = AlignedBuffer::new(sizing.length as usize)?;
    let reply = api.query(handle, TokenUser, Some(buffer.bytes_mut()));
    if !reply.success {
        return Err(native_error(operation(TokenUser), reply.code));
    }
    if reply.length != sizing.length {
        return Err(denied("TokenUser retrieval size"));
    }
    // Parse only the actual returned extent, exactly equal to this allocation's
    // requested extent. No retry or larger allocation follows growth/truncation.
    parse_user(buffer.bytes())
}

fn boolean(value: u32) -> Result<bool> {
    match value {
        0 => Ok(false),
        1 => Ok(true),
        _ => Err(denied("unknown token boolean")),
    }
}

fn capture_token<A: TokenApi>(api: &mut A, handle: &A::Handle) -> Result<TokenFacts> {
    api.noninheritable(handle)?;
    let before = statistics(api, handle)?;
    let user = user(api, handle)?;
    let token_type = scalar(api, handle, TokenType)?;
    if token_type != TokenPrimary as u32 || before.token_type != TokenPrimary {
        return Err(denied("primary token required"));
    }
    let elevation_type = scalar(api, handle, TokenElevationType)?;
    if ![
        TokenElevationTypeDefault as u32,
        TokenElevationTypeFull as u32,
        TokenElevationTypeLimited as u32,
    ]
    .contains(&elevation_type)
    {
        return Err(denied("unknown token elevation type"));
    }
    let elevated = boolean(scalar(api, handle, TokenElevation)?)?;
    let app_container = boolean(scalar(api, handle, TokenIsAppContainer)?)?;
    if app_container {
        return Err(denied("app-container token refused"));
    }
    let after = statistics(api, handle)?;
    if before.token_id != after.token_id || before.modified_id != after.modified_id {
        return Err(denied("token changed during capture"));
    }
    if after.token_type != TokenPrimary {
        return Err(denied("primary token required"));
    }
    api.noninheritable(handle)?;
    Ok(TokenFacts {
        user,
        token_type,
        statistics: before,
        elevation_type,
        elevated,
        app_container,
    })
}

fn no_thread_token<A: TokenApi>(api: &mut A) -> Result<()> {
    let Some(token) = api.open_thread()? else {
        return Ok(());
    };
    let result = (|| {
        api.noninheritable(&token)?;
        let token_type = scalar(api, &token, TokenType)?;
        if token_type == TokenImpersonation as u32 {
            let level = scalar(api, &token, TokenImpersonationLevel)?;
            if level > SecurityDelegation as u32 {
                return Err(denied("unknown thread impersonation level"));
            }
        } else if token_type != TokenPrimary as u32 {
            return Err(denied("unknown thread token type"));
        }
        Err(denied("calling thread has a token"))
    })();
    finish(result, api.close(token))
}

fn recheck_with<A: TokenApi>(api: &mut A, token: &A::Handle, facts: &TokenFacts) -> Result<()> {
    api.process_recheck()?;
    no_thread_token(api)?;
    if capture_token(api, token)? != *facts {
        return Err(denied("retained primary token changed"));
    }
    let current = api.open_primary()?;
    let result = (|| {
        if capture_token(api, &current)? != *facts {
            return Err(denied("current primary token changed"));
        }
        Ok(())
    })();
    finish(result, api.close(current))?;
    api.process_recheck()?;
    no_thread_token(api)
}

fn capture_with<A: TokenApi>(api: &mut A) -> Result<(A::Handle, TokenFacts)> {
    api.process_recheck()?;
    no_thread_token(api)?;
    let token = api.open_primary()?;
    let result = (|| {
        let facts = capture_token(api, &token)?;
        recheck_with(api, &token, &facts)?;
        Ok(facts)
    })();
    match result {
        Ok(facts) => Ok((token, facts)),
        Err(error) => finish(Err(error), api.close(token)),
    }
}

struct NativeApi<'a> {
    process: &'a OwnProcessObservation,
}

fn owned_token(handle: HANDLE) -> Result<OwnedHandle> {
    if handle.is_null() || handle == INVALID_HANDLE_VALUE {
        return Err(denied("invalid opened token handle"));
    }
    // SAFETY: called only after successful OpenProcessToken/OpenThreadToken,
    // which transfers one new real handle to this sole owner.
    Ok(unsafe { OwnedHandle::from_raw_handle(handle) })
}

impl TokenApi for NativeApi<'_> {
    type Handle = OwnedHandle;

    fn process_recheck(&mut self) -> Result<()> {
        self.process.recheck()
    }

    fn open_primary(&mut self) -> Result<OwnedHandle> {
        let mut token = null_mut();
        if unsafe { OpenProcessToken(raw(&self.process.process), TOKEN_QUERY, &mut token) } == 0 {
            return Err(last("OpenProcessToken bootstrap"));
        }
        owned_token(token)
    }

    fn open_thread(&mut self) -> Result<Option<OwnedHandle>> {
        let mut token = null_mut();
        if unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut token) } != 0 {
            return owned_token(token).map(Some);
        }
        let code = unsafe { GetLastError() };
        if code == ERROR_NO_TOKEN {
            Ok(None)
        } else {
            Err(native_error("OpenThreadToken bootstrap", code))
        }
    }

    fn noninheritable(&mut self, handle: &OwnedHandle) -> Result<()> {
        let mut flags = 0;
        if unsafe { GetHandleInformation(raw(handle), &mut flags) } == 0 {
            return Err(last("GetHandleInformation bootstrap token"));
        }
        if flags & HANDLE_FLAG_INHERIT != 0 {
            return Err(denied("inheritable token handle"));
        }
        Ok(())
    }

    fn close(&mut self, handle: OwnedHandle) -> Result<()> {
        // Consume before exactly one checked close: no destructor retry if its
        // success is uncertain. Token owners are closed before the borrowed process.
        if unsafe { CloseHandle(handle.into_raw_handle()) } == 0 {
            Err(last("CloseHandle bootstrap token"))
        } else {
            Ok(())
        }
    }

    fn query(
        &mut self,
        handle: &OwnedHandle,
        class: TOKEN_INFORMATION_CLASS,
        buffer: Option<&mut [u8]>,
    ) -> QueryReply {
        let (pointer, capacity) = match buffer {
            Some(buffer) => (buffer.as_mut_ptr().cast(), buffer.len() as u32),
            None => (null_mut(), 0),
        };
        let mut length = 0;
        let success =
            unsafe { GetTokenInformation(raw(handle), class, pointer, capacity, &mut length) } != 0;
        let code = if success {
            0
        } else {
            unsafe { GetLastError() }
        };
        QueryReply {
            success,
            length,
            code,
        }
    }
}

pub(super) struct PrimaryAccountObservation<'a> {
    process: &'a OwnProcessObservation,
    token: OwnedHandle,
    facts: TokenFacts,
}

impl OwnProcessObservation {
    pub(super) fn capture_primary_account(&self) -> Result<PrimaryAccountObservation<'_>> {
        let mut api = NativeApi { process: self };
        let (token, facts) = capture_with(&mut api)?;
        Ok(PrimaryAccountObservation {
            process: self,
            token,
            facts,
        })
    }
}

impl PrimaryAccountObservation<'_> {
    pub(super) fn recheck(&self) -> Result<()> {
        let mut api = NativeApi {
            process: self.process,
        };
        recheck_with(&mut api, &self.token, &self.facts)
    }

    pub(super) fn close(self) -> Result<()> {
        let mut api = NativeApi {
            process: self.process,
        };
        api.close(self.token)
    }
}

#[cfg(test)]
mod tests;
