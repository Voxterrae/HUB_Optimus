//! Dormant, private, one-shot bootstrap exchange. This is not key provenance,
//! protected storage, enrollment, admission, or release authority.
//!
//! Wire format (exactly 96 bytes, one message): 0..8 = `HUBBSP01`, byte 8 = 1,
//! byte 9 = role (hello=1, challenge=2, finish=3, terminal=4), 10..16 = zero,
//! 16..32 = independently conveyed random ceremony ID, 32..64 = server nonce,
//! 64..96 = client nonce. Hello alone has a zero server nonce. Other nonces are
//! fresh 32-byte system RNG output and must be nonzero. Terminal has no payload.
//! Consuming endpoints, one instance and one connection prevent a second run.

use std::os::windows::io::{AsRawHandle, FromRawHandle, IntoRawHandle, OwnedHandle};
use std::ptr::{null, null_mut};
use std::time::Instant;
use windows_sys::Win32::Foundation::*;
use windows_sys::Win32::Security::Authorization::*;
use windows_sys::Win32::Security::Cryptography::{
    BCRYPT_USE_SYSTEM_PREFERRED_RNG, BCryptGenRandom,
};
use windows_sys::Win32::Security::*;
use windows_sys::Win32::Storage::FileSystem::*;
use windows_sys::Win32::System::IO::*;
use windows_sys::Win32::System::Pipes::*;
use windows_sys::Win32::System::Threading::*;

const HELLO: u8 = 1;
const CHALLENGE: u8 = 2;
const FINISH: u8 = 3;
const TERMINAL: u8 = 4;
const FRAME_LEN: usize = 96;
// Individual client rights: data read/write, attributes read/write, synchronize,
// read-control. In particular bit 0x4 (FILE_CREATE_PIPE_INSTANCE) is absent.
const CLIENT_ACCESS: u32 = 0x0012_0183;
const MAX_EXCHANGE_MS: u128 = 10_000;
// WinNT.h SE_GROUP_LOGON_ID; avoid importing the broad SystemServices feature.
const LOGON_ID: u32 = 0xc000_0000;

#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) enum Error {
    Native(&'static str, u32),
    TokenInfo {
        class: i32,
        status: u32,
        length: u32,
    },
    TokenLayout {
        class: i32,
        length: u32,
    },
    Crypto(i32),
    Denied(&'static str),
    // Native completion status after deadline cancellation and bounded drain.
    Deadline(u32),
    Cleanup(Option<Box<Error>>, Vec<u32>),
}

type Result<T> = std::result::Result<T, Error>;

fn last(operation: &'static str) -> Error {
    Error::Native(operation, unsafe { GetLastError() })
}
fn raw(handle: &OwnedHandle) -> HANDLE {
    handle.as_raw_handle()
}

fn owned(handle: HANDLE) -> Result<OwnedHandle> {
    if handle.is_null() || handle == INVALID_HANDLE_VALUE {
        return Err(last("acquire handle"));
    }
    // SAFETY: caller transfers a newly acquired Win32 handle, exactly once.
    Ok(unsafe { OwnedHandle::from_raw_handle(handle) })
}

fn close_checked(handle: OwnedHandle) -> Result<()> {
    if unsafe { CloseHandle(handle.into_raw_handle()) } == 0 {
        Err(last("CloseHandle"))
    } else {
        Ok(())
    }
}

fn duplicate(process: HANDLE, inherit: bool) -> Result<OwnedHandle> {
    let mut handle = null_mut();
    if unsafe {
        DuplicateHandle(
            GetCurrentProcess(),
            process,
            GetCurrentProcess(),
            &mut handle,
            PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
            i32::from(inherit),
            0,
        )
    } == 0
    {
        return Err(last("DuplicateHandle limited process"));
    }
    owned(handle)
}

fn random(bytes: &mut [u8]) -> Result<()> {
    let status = unsafe {
        BCryptGenRandom(
            null_mut(),
            bytes.as_mut_ptr(),
            bytes.len() as u32,
            BCRYPT_USE_SYSTEM_PREFERRED_RNG,
        )
    };
    if status < 0 {
        return Err(Error::Crypto(status));
    }
    if bytes.iter().all(|byte| *byte == 0) {
        return Err(Error::Denied("zero random"));
    }
    Ok(())
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}
fn utf16(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(Some(0)).collect()
}

// Aligned token data; pointers embedded by GetTokenInformation remain valid
// while this owning buffer lives. Token information is bounded to 64 KiB.
struct TokenData(Vec<usize>);
impl TokenData {
    fn pointer<T>(&self) -> *const T {
        self.0.as_ptr().cast()
    }
    fn query(token: HANDLE, class: TOKEN_INFORMATION_CLASS) -> Result<Self> {
        let mut length = 0;
        unsafe { GetTokenInformation(token, class, null_mut(), 0, &mut length) };
        let status = unsafe { GetLastError() };
        // The API documents ReturnLength for sizing, not one universal error
        // code for every information class (fixed-size classes can report
        // ERROR_BAD_LENGTH). The real bounded query must still succeed.
        if length == 0 || length > 65536 {
            return Err(Error::TokenInfo {
                class,
                status,
                length,
            });
        }
        let mut data = Self(vec![
            0;
            (length as usize).div_ceil(std::mem::size_of::<usize>())
        ]);
        if unsafe {
            GetTokenInformation(
                token,
                class,
                data.0.as_mut_ptr().cast(),
                length,
                &mut length,
            )
        } == 0
        {
            return Err(Error::TokenInfo {
                class,
                status: unsafe { GetLastError() },
                length,
            });
        }
        Ok(data)
    }
    fn word(token: HANDLE, class: TOKEN_INFORMATION_CLASS) -> Result<u32> {
        let mut value = 0u32;
        let mut length = 0;
        if unsafe {
            GetTokenInformation(
                token,
                class,
                (&mut value as *mut u32).cast(),
                std::mem::size_of::<u32>() as u32,
                &mut length,
            )
        } == 0
        {
            return Err(Error::TokenInfo {
                class,
                status: unsafe { GetLastError() },
                length,
            });
        }
        // Microsoft documents HasRestrictions as a DWORD history flag (ever
        // filtered). Native Windows 10 19045 returns length 1 and writes only
        // its low byte. Storage is zero-initialized; allow that exact observed
        // layout plus the documented DWORD, and normalize the boolean. This is
        // not IsTokenRestricted and must not reject an expected UAC token.
        let valid = if class == TokenHasRestrictions {
            matches!(length, 1 | 4)
        } else if [
            TokenType,
            TokenImpersonationLevel,
            TokenSessionId,
            TokenIsAppContainer,
            TokenElevationType,
            TokenElevation,
            TokenMandatoryPolicy,
        ]
        .contains(&class)
        {
            length == 4
        } else {
            return Err(Error::Denied("unsupported token scalar"));
        };
        if !valid {
            return Err(Error::TokenLayout { class, length });
        }
        Ok(if class == TokenHasRestrictions {
            u32::from(value != 0)
        } else {
            value
        })
    }
}

fn sid_bytes(sid: PSID) -> Result<Vec<u8>> {
    if unsafe { IsValidSid(sid) } == 0 {
        return Err(Error::Denied("invalid native SID"));
    }
    let length = unsafe { GetLengthSid(sid) } as usize;
    if length > 68 {
        return Err(Error::Denied("SID bound"));
    }
    Ok(unsafe { std::slice::from_raw_parts(sid.cast::<u8>(), length) }.to_vec())
}

fn groups(token: HANDLE, class: TOKEN_INFORMATION_CLASS) -> Result<Vec<(Vec<u8>, u32)>> {
    let data = TokenData::query(token, class)?;
    let pointer = data.pointer::<TOKEN_GROUPS>();
    let count = unsafe { (*pointer).GroupCount } as usize;
    let offset = std::mem::offset_of!(TOKEN_GROUPS, Groups);
    if offset + count * std::mem::size_of::<SID_AND_ATTRIBUTES>()
        > std::mem::size_of_val(data.0.as_slice())
    {
        return Err(Error::Denied("native groups bound"));
    }
    // Do not form a reference to the generated one-element placeholder when
    // the kernel returns a zero-element flexible array.
    let first = unsafe { std::ptr::addr_of!((*pointer).Groups).cast::<SID_AND_ATTRIBUTES>() };
    let entries = unsafe { std::slice::from_raw_parts(first, count) };
    let mut result = Vec::new();
    for entry in entries {
        result.push((sid_bytes(entry.Sid)?, entry.Attributes));
    }
    result.sort();
    Ok(result)
}

#[derive(Debug, PartialEq, Eq)]
struct TokenContext {
    user: Vec<u8>,
    groups: Vec<(Vec<u8>, u32)>,
    restricted: Vec<(Vec<u8>, u32)>,
    privileges: Vec<(u32, i32, u32)>,
    integrity: Vec<u8>,
    authentication: (u32, i32),
    scalar: [u32; 6],
}

impl TokenContext {
    fn capture(token: HANDLE) -> Result<Self> {
        let user = TokenData::query(token, TokenUser)?;
        let user = sid_bytes(unsafe { (*user.pointer::<TOKEN_USER>()).User.Sid })?;
        let label = TokenData::query(token, TokenIntegrityLevel)?;
        let integrity =
            sid_bytes(unsafe { (*label.pointer::<TOKEN_MANDATORY_LABEL>()).Label.Sid })?;
        let stats = TokenData::query(token, TokenStatistics)?;
        let authentication = unsafe { (*stats.pointer::<TOKEN_STATISTICS>()).AuthenticationId };
        let data = TokenData::query(token, TokenPrivileges)?;
        let pointer = data.pointer::<TOKEN_PRIVILEGES>();
        let count = unsafe { (*pointer).PrivilegeCount } as usize;
        if std::mem::offset_of!(TOKEN_PRIVILEGES, Privileges)
            + count * std::mem::size_of::<LUID_AND_ATTRIBUTES>()
            > std::mem::size_of_val(data.0.as_slice())
        {
            return Err(Error::Denied("native privileges bound"));
        }
        let first =
            unsafe { std::ptr::addr_of!((*pointer).Privileges).cast::<LUID_AND_ATTRIBUTES>() };
        let entries = unsafe { std::slice::from_raw_parts(first, count) };
        let mut privileges: Vec<_> = entries
            .iter()
            .map(|item| (item.Luid.LowPart, item.Luid.HighPart, item.Attributes))
            .collect();
        privileges.sort();
        let scalar = [
            TokenSessionId,
            TokenHasRestrictions,
            TokenIsAppContainer,
            TokenElevationType,
            TokenElevation,
            TokenMandatoryPolicy,
        ]
        .map(|class| TokenData::word(token, class))
        .into_iter()
        .collect::<Result<Vec<_>>>()?
        .try_into()
        .unwrap();
        let context = Self {
            user,
            groups: groups(token, TokenGroups)?,
            restricted: groups(token, TokenRestrictedSids)?,
            privileges,
            integrity,
            authentication: (authentication.LowPart, authentication.HighPart),
            scalar,
        };
        if !context
            .groups
            .iter()
            .any(|(_, attributes)| attributes & LOGON_ID == LOGON_ID)
        {
            return Err(Error::Denied("missing logon SID"));
        }
        Ok(context)
    }

    fn logon_sddl(&self) -> Result<String> {
        let sid = &self
            .groups
            .iter()
            .find(|(_, attributes)| attributes & LOGON_ID == LOGON_ID)
            .ok_or(Error::Denied("missing logon SID"))?
            .0;
        // SID binary layout: revision, subauthority count, big-endian authority,
        // followed by little-endian 32-bit subauthorities. No raw SID pointers escape.
        let authority = sid[2..8]
            .iter()
            .fold(0u64, |acc, byte| (acc << 8) | u64::from(*byte));
        let mut result = format!("S-{}-{authority}", sid[0]);
        for value in sid[8..].as_chunks::<4>().0 {
            result.push_str(&format!("-{}", u32::from_le_bytes(*value)));
        }
        Ok(result)
    }
}

pub(super) struct ExpectedPeer {
    process: OwnedHandle,
    token: OwnedHandle,
    pid: u32,
    creation: u64,
    token_id: (u32, i32),
    context: TokenContext,
}

fn process_token(process: HANDLE) -> Result<OwnedHandle> {
    let mut token = null_mut();
    if unsafe { OpenProcessToken(process, TOKEN_QUERY, &mut token) } == 0 {
        return Err(last("OpenProcessToken"));
    }
    owned(token)
}

fn creation(process: HANDLE) -> Result<u64> {
    let mut values: [FILETIME; 4] = unsafe { std::mem::zeroed() };
    let [a, b, c, d] = &mut values;
    if unsafe { GetProcessTimes(process, a, b, c, d) } == 0 {
        return Err(last("GetProcessTimes"));
    }
    Ok(u64::from(a.dwLowDateTime) | (u64::from(a.dwHighDateTime) << 32))
}

fn token_id(token: HANDLE) -> Result<(u32, i32)> {
    let stats = TokenData::query(token, TokenStatistics)?;
    let id = unsafe { (*stats.pointer::<TOKEN_STATISTICS>()).TokenId };
    Ok((id.LowPart, id.HighPart))
}

impl ExpectedPeer {
    pub(super) fn process_handle(&self) -> HANDLE {
        raw(&self.process)
    }
    pub(super) fn user(&self) -> &[u8] {
        &self.context.user
    }
    pub(super) fn stamp(&self) -> (u32, u64, (u32, i32)) {
        (self.pid, self.creation, self.token_id)
    }
    pub(super) fn session(&self) -> u32 {
        self.context.scalar[0]
    }
    pub(super) fn unsupported_restrictions(&self) -> bool {
        self.context.scalar[1] != 0
            || self.context.scalar[2] != 0
            || !self.context.restricted.is_empty()
    }
    pub(super) fn privileges(&self) -> &[(u32, i32, u32)] {
        &self.context.privileges
    }

    // Trusted launcher supplies an already owned handle, never a pipe PID/name.
    // Always duplicate DOWN to the minimum query+synchronize rights and clear inheritance.
    pub(super) fn from_owned(input: OwnedHandle) -> Result<Self> {
        let process = combine(duplicate(raw(&input), false), [input])?;
        let token = match process_token(raw(&process)) {
            Ok(token) => token,
            Err(error) => return combine(Err(error), [process]),
        };
        let metadata = (|| {
            let pid = unsafe { GetProcessId(raw(&process)) };
            if pid == 0 {
                return Err(last("GetProcessId"));
            }
            if TokenData::word(raw(&token), TokenType)? != TokenPrimary as u32 {
                return Err(Error::Denied("primary token"));
            }
            Ok((
                pid,
                creation(raw(&process))?,
                token_id(raw(&token))?,
                TokenContext::capture(raw(&token))?,
            ))
        })();
        let (pid, creation, token_id, context) = match metadata {
            Ok(metadata) => metadata,
            Err(error) => return combine(Err(error), [token, process]),
        };
        let peer = Self {
            creation,
            token_id,
            process,
            token,
            pid,
            context,
        };
        if let Err(error) = peer.recheck() {
            return finish_peer(Err(error), peer);
        }
        Ok(peer)
    }

    pub(super) fn recheck(&self) -> Result<()> {
        for handle in [&self.process, &self.token] {
            let mut flags = 0;
            if unsafe { GetHandleInformation(raw(handle), &mut flags) } == 0 {
                return Err(last("GetHandleInformation retained peer"));
            }
            if flags & HANDLE_FLAG_INHERIT != 0 {
                return Err(Error::Denied("inheritable retained peer handle"));
            }
        }
        match unsafe { WaitForSingleObject(raw(&self.process), 0) } {
            WAIT_TIMEOUT => (),
            WAIT_OBJECT_0 => return Err(Error::Denied("process exited")),
            _ => return Err(last("WaitForSingleObject process")),
        }
        if unsafe { GetProcessId(raw(&self.process)) } != self.pid
            || creation(raw(&self.process))? != self.creation
        {
            return Err(Error::Denied("process identity"));
        }
        let current = process_token(raw(&self.process))?;
        let result = (|| {
            if token_id(raw(&current))? != self.token_id
                || TokenContext::capture(raw(&current))? != self.context
                || TokenContext::capture(raw(&self.token))? != self.context
            {
                return Err(Error::Denied("primary context changed"));
            }
            Ok(())
        })();
        combine(result, [current])
    }

    fn bind_pipe(&self, pipe: &OwnedHandle, server_side: bool) -> Result<()> {
        self.recheck()?;
        let mut pid = 0;
        let success = unsafe {
            if server_side {
                GetNamedPipeClientProcessId(raw(pipe), &mut pid)
            } else {
                GetNamedPipeServerProcessId(raw(pipe), &mut pid)
            }
        };
        if success == 0 {
            return Err(last("GetNamedPipe peer PID"));
        }
        if pid != self.pid {
            return Err(Error::Denied("pipe process"));
        }
        self.recheck()
    }

    pub(super) fn close(self) -> Result<()> {
        combine(Ok(()), [self.token, self.process])
    }
}

// Never clear a token owned by someone else. Any non-NO_TOKEN error also denies.
pub(super) fn no_impersonation() -> Result<()> {
    let mut token = null_mut();
    if unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut token) } != 0 {
        return combine(
            Err(Error::Denied("preexisting impersonation")),
            [owned(token)?],
        );
    }
    let code = unsafe { GetLastError() };
    if code == ERROR_NO_TOKEN {
        Ok(())
    } else {
        Err(Error::Native("OpenThreadToken precheck", code))
    }
}

struct Revert;
impl Drop for Revert {
    fn drop(&mut self) {
        // Continuing in an unexpected token is forbidden. Fail-fast the entire
        // hosting process; there is no privilege-bearing recovery or next request.
        if unsafe { RevertToSelf() } == 0 {
            std::process::abort();
        }
    }
}

fn authenticate_message(pipe: &OwnedHandle, expected: &ExpectedPeer) -> Result<()> {
    no_impersonation()?;
    if unsafe { ImpersonateNamedPipeClient(raw(pipe)) } == 0 {
        return Err(last("ImpersonateNamedPipeClient"));
    }
    let revert = Revert;
    let result = (|| {
        let mut token = null_mut();
        if unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut token) } == 0 {
            return Err(last("OpenThreadToken"));
        }
        let token = owned(token)?;
        let result = (|| {
            if TokenData::word(raw(&token), TokenType)? != TokenImpersonation as u32
                || TokenData::word(raw(&token), TokenImpersonationLevel)?
                    != SecurityIdentification as u32
            {
                return Err(Error::Denied("identification level"));
            }
            if TokenContext::capture(raw(&token))? != expected.context {
                return Err(Error::Denied("message token context"));
            }
            Ok(())
        })();
        combine(result, [token])
    })();
    drop(revert);
    no_impersonation()?;
    result
}

fn combine<T, const N: usize>(result: Result<T>, handles: [OwnedHandle; N]) -> Result<T> {
    let errors: Vec<_> = handles
        .into_iter()
        .filter_map(|handle| match close_checked(handle) {
            Err(Error::Native(_, status)) => Some(status),
            _ => None,
        })
        .collect();
    if errors.is_empty() {
        result
    } else {
        Err(Error::Cleanup(result.err().map(Box::new), errors))
    }
}

fn finish_peer<T>(result: Result<T>, peer: ExpectedPeer) -> Result<T> {
    combine(result, [peer.token, peer.process])
}

fn valid_deadline(deadline: Instant) -> Result<()> {
    let remaining = deadline
        .saturating_duration_since(Instant::now())
        .as_millis();
    if remaining == 0 {
        return Err(Error::Deadline(0));
    }
    if remaining > MAX_EXCHANGE_MS {
        return Err(Error::Denied("deadline bound"));
    }
    Ok(())
}

fn completion(
    pipe: &OwnedHandle,
    overlapped: &mut OVERLAPPED,
    deadline: Instant,
    operation: &'static str,
) -> Result<u32> {
    let remaining = deadline
        .saturating_duration_since(Instant::now())
        .as_millis()
        .min(MAX_EXCHANGE_MS) as u32;
    let wait = unsafe { WaitForSingleObject(overlapped.hEvent, remaining) };
    if wait != WAIT_OBJECT_0 {
        // Cancellation is not completion. Keep both OVERLAPPED and the borrowed
        // buffer alive until the event and GetOverlappedResult prove completion.
        let canceled = unsafe { CancelIoEx(raw(pipe), overlapped) };
        let cancel_error = if canceled == 0 {
            unsafe { GetLastError() }
        } else {
            0
        };
        if unsafe { WaitForSingleObject(overlapped.hEvent, 1000) } != WAIT_OBJECT_0 {
            // A broken driver cannot turn the finite exchange into a dangling
            // stack pointer or an unbounded wait. Fail-fast with buffers alive.
            std::process::abort();
        }
        let mut transferred = 0;
        let finished = unsafe { GetOverlappedResult(raw(pipe), overlapped, &mut transferred, 0) };
        let status = if finished == 0 {
            unsafe { GetLastError() }
        } else {
            0
        };
        if cancel_error != 0 && cancel_error != ERROR_NOT_FOUND {
            return Err(Error::Native("CancelIoEx", cancel_error));
        }
        if wait == WAIT_TIMEOUT {
            return Err(Error::Deadline(status));
        }
        return Err(Error::Denied("I/O wait failed; drained"));
    }
    let mut transferred = 0;
    if unsafe { GetOverlappedResult(raw(pipe), overlapped, &mut transferred, 0) } == 0 {
        return Err(last(operation));
    }
    Ok(transferred)
}

enum Transfer<'a> {
    Read(&'a mut [u8]),
    Write(&'a [u8]),
}

fn event() -> Result<OwnedHandle> {
    owned(unsafe { CreateEventW(null(), 1, 0, null()) })
}

fn transfer(pipe: &OwnedHandle, transfer: Transfer<'_>, deadline: Instant) -> Result<u32> {
    valid_deadline(deadline)?;
    let event = event()?;
    let mut overlapped: OVERLAPPED = unsafe { std::mem::zeroed() };
    overlapped.hEvent = raw(&event);
    let (success, operation) = match transfer {
        Transfer::Read(buffer) => (
            unsafe {
                ReadFile(
                    raw(pipe),
                    buffer.as_mut_ptr(),
                    buffer.len() as u32,
                    null_mut(),
                    &mut overlapped,
                )
            },
            "ReadFile",
        ),
        Transfer::Write(buffer) => (
            unsafe {
                WriteFile(
                    raw(pipe),
                    buffer.as_ptr(),
                    buffer.len() as u32,
                    null_mut(),
                    &mut overlapped,
                )
            },
            "WriteFile",
        ),
    };
    let code = if success == 0 {
        unsafe { GetLastError() }
    } else {
        0
    };
    let result = if code != 0 && code != ERROR_IO_PENDING {
        Err(Error::Native(operation, code))
    } else {
        completion(pipe, &mut overlapped, deadline, operation)
    };
    combine(result, [event])
}

fn connect_pipe(pipe: &OwnedHandle, deadline: Instant) -> Result<()> {
    valid_deadline(deadline)?;
    let event = event()?;
    let mut overlapped: OVERLAPPED = unsafe { std::mem::zeroed() };
    overlapped.hEvent = raw(&event);
    let connected = unsafe { ConnectNamedPipe(raw(pipe), &mut overlapped) };
    let code = if connected == 0 {
        unsafe { GetLastError() }
    } else {
        0
    };
    let result = match code {
        ERROR_PIPE_CONNECTED => Ok(()),
        0 | ERROR_IO_PENDING => {
            completion(pipe, &mut overlapped, deadline, "ConnectNamedPipe").map(|_| ())
        }
        _ => Err(Error::Native("ConnectNamedPipe", code)),
    };
    combine(result, [event])
}

fn open_pipe(name: &str, deadline: Instant, sqos: u32) -> Result<OwnedHandle> {
    // Caller cannot direct this primitive to a remote or arbitrary filesystem path.
    const PREFIX: &str = "\\\\.\\pipe\\HUB_Relay.NativePilot.Bootstrap.";
    if !name.starts_with(PREFIX)
        || name.len() != PREFIX.len() + 64
        || !name[PREFIX.len()..]
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit())
    {
        return Err(Error::Denied("pipe name"));
    }
    let name = utf16(name);
    loop {
        valid_deadline(deadline)?;
        let handle = unsafe {
            CreateFileW(
                name.as_ptr(),
                CLIENT_ACCESS,
                0,
                null(),
                OPEN_EXISTING,
                FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | sqos,
                null_mut(),
            )
        };
        if handle != INVALID_HANDLE_VALUE {
            let handle = owned(handle)?;
            let mode = PIPE_READMODE_MESSAGE;
            if unsafe { SetNamedPipeHandleState(raw(&handle), &mode, null(), null()) } == 0 {
                return combine(Err(last("SetNamedPipeHandleState")), [handle]);
            }
            return Ok(handle);
        }
        let code = unsafe { GetLastError() };
        if code != ERROR_PIPE_BUSY && code != ERROR_FILE_NOT_FOUND {
            return Err(Error::Native("CreateFileW pipe", code));
        }
        std::thread::sleep(std::time::Duration::from_millis(2));
    }
}

#[derive(Debug, Clone, Copy)]
struct Frame([u8; FRAME_LEN]);
impl Frame {
    fn new(role: u8, ceremony: [u8; 16], server: [u8; 32], client: [u8; 32]) -> Self {
        let mut bytes = [0; FRAME_LEN];
        bytes[..8].copy_from_slice(b"HUBBSP01");
        bytes[8] = 1;
        bytes[9] = role;
        bytes[16..32].copy_from_slice(&ceremony);
        bytes[32..64].copy_from_slice(&server);
        bytes[64..96].copy_from_slice(&client);
        Self(bytes)
    }
    fn server(&self) -> [u8; 32] {
        self.0[32..64].try_into().unwrap()
    }
    fn client(&self) -> [u8; 32] {
        self.0[64..96].try_into().unwrap()
    }
    fn check(
        &self,
        role: u8,
        ceremony: &[u8; 16],
        server: Option<&[u8; 32]>,
        client: Option<&[u8; 32]>,
    ) -> Result<()> {
        if self.0[..8] != *b"HUBBSP01"
            || self.0[8] != 1
            || self.0[9] != role
            || self.0[10..16] != [0; 6]
            || self.0[16..32] != *ceremony
            || self.client() == [0; 32]
            || (role == HELLO && self.server() != [0; 32])
            || (role != HELLO && self.server() == [0; 32])
            || server.is_some_and(|value| self.server() != *value)
            || client.is_some_and(|value| self.client() != *value)
        {
            Err(Error::Denied("frame"))
        } else {
            Ok(())
        }
    }
}

fn read_frame(pipe: &OwnedHandle, deadline: Instant) -> Result<Frame> {
    let mut frame = Frame([0; FRAME_LEN]);
    if transfer(pipe, Transfer::Read(&mut frame.0), deadline)? != FRAME_LEN as u32 {
        return Err(Error::Denied("frame length"));
    }
    Ok(frame)
}
fn write_frame(pipe: &OwnedHandle, frame: Frame, deadline: Instant) -> Result<()> {
    if transfer(pipe, Transfer::Write(&frame.0), deadline)? != FRAME_LEN as u32 {
        return Err(Error::Denied("short write"));
    }
    Ok(())
}

#[derive(Debug)]
struct TerminalTranscript {
    ceremony: [u8; 16],
    server: [u8; 32],
    client: [u8; 32],
}

struct Server {
    pipe: OwnedHandle,
    name: String,
    ceremony: [u8; 16],
}
impl Server {
    fn create(expected: &ExpectedPeer) -> Result<Self> {
        no_impersonation()?;
        expected.recheck()?;
        let mut suffix = [0; 32];
        random(&mut suffix)?;
        let name = format!(
            "\\\\.\\pipe\\HUB_Relay.NativePilot.Bootstrap.{}",
            hex(&suffix)
        );
        // Logon SID restricts sessions; process/token comparison restricts the peer.
        // This ACL is explicitly NOT same-user protected storage.
        let sddl = utf16(&format!(
            "D:P(A;;0x{CLIENT_ACCESS:08x};;;{})",
            expected.context.logon_sddl()?
        ));
        let mut descriptor = null_mut();
        if unsafe {
            ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl.as_ptr(),
                SDDL_REVISION_1,
                &mut descriptor,
                null_mut(),
            )
        } == 0
        {
            return Err(last("ConvertStringSecurityDescriptor"));
        }
        let attributes = SECURITY_ATTRIBUTES {
            nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
            lpSecurityDescriptor: descriptor,
            bInheritHandle: 0,
        };
        let pipe = unsafe {
            CreateNamedPipeW(
                utf16(&name).as_ptr(),
                PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE | FILE_FLAG_OVERLAPPED,
                PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_REJECT_REMOTE_CLIENTS,
                1,
                FRAME_LEN as u32,
                FRAME_LEN as u32,
                0,
                &attributes,
            )
        };
        let result = owned(pipe);
        if !unsafe { LocalFree(descriptor) }.is_null() {
            let error = last("LocalFree security descriptor");
            return match result {
                Ok(pipe) => combine(Err(error), [pipe]),
                Err(_) => Err(error),
            };
        }
        let pipe = result?;
        let mut ceremony = [0; 16];
        if let Err(error) = random(&mut ceremony) {
            return combine(Err(error), [pipe]);
        }
        Ok(Self {
            pipe,
            name,
            ceremony,
        })
    }

    fn exchange(self, expected: ExpectedPeer, deadline: Instant) -> Result<TerminalTranscript> {
        // The same fresh dedicated thread performs all message reads, token checks
        // and reverts. No pool reuse, detach, or context transfer across threads.
        // Scope keeps resource ownership on the caller even if spawning fails.
        let result = std::thread::scope(|scope| {
            std::thread::Builder::new()
                .name("bootstrap-peer".into())
                .spawn_scoped(scope, || self.on_thread(&expected, deadline))
                .map_err(|_| Error::Denied("dedicated thread spawn"))?
                .join()
                .map_err(|_| Error::Denied("dedicated thread panic"))?
        });
        finish_peer(combine(result, [self.pipe]), expected)
    }

    fn on_thread(&self, expected: &ExpectedPeer, deadline: Instant) -> Result<TerminalTranscript> {
        let result = (|| {
            no_impersonation()?;
            valid_deadline(deadline)?;
            expected.recheck()?;
            connect_pipe(&self.pipe, deadline)?;
            expected.bind_pipe(&self.pipe, true)?;
            let hello = read_frame(&self.pipe, deadline)?;
            hello.check(HELLO, &self.ceremony, None, None)?;
            authenticate_message(&self.pipe, expected)?;
            let client = hello.client();
            let mut server = [0; 32];
            random(&mut server)?;
            write_frame(
                &self.pipe,
                Frame::new(CHALLENGE, self.ceremony, server, client),
                deadline,
            )?;
            let finish = read_frame(&self.pipe, deadline)?;
            finish.check(FINISH, &self.ceremony, Some(&server), Some(&client))?;
            authenticate_message(&self.pipe, expected)?;
            expected.bind_pipe(&self.pipe, true)?;
            valid_deadline(deadline)?;
            write_frame(
                &self.pipe,
                Frame::new(TERMINAL, self.ceremony, server, client),
                deadline,
            )?;
            Ok(TerminalTranscript {
                ceremony: self.ceremony,
                server,
                client,
            })
        })();
        // This query runs on the dedicated thread on every success/error path.
        no_impersonation()?;
        result
    }
}

struct Client {
    pipe: OwnedHandle,
    expected: ExpectedPeer,
    ceremony: [u8; 16],
    deadline: Instant,
}
impl Client {
    fn connect(
        name: &str,
        ceremony: [u8; 16],
        expected: ExpectedPeer,
        deadline: Instant,
    ) -> Result<Self> {
        let acquired = (|| {
            no_impersonation()?;
            valid_deadline(deadline)?;
            expected.recheck()?;
            let pipe = open_pipe(name, deadline, SECURITY_IDENTIFICATION)?;
            if let Err(error) = expected.bind_pipe(&pipe, false) {
                return combine(Err(error), [pipe]);
            }
            Ok(pipe)
        })();
        match acquired {
            Ok(pipe) => Ok(Self {
                pipe,
                expected,
                ceremony,
                deadline,
            }),
            Err(error) => finish_peer(Err(error), expected),
        }
    }

    fn exchange(self, deadline: Instant) -> Result<TerminalTranscript> {
        let deadline = deadline.min(self.deadline);
        let result = (|| {
            no_impersonation()?;
            valid_deadline(deadline)?;
            // Repeat server binding immediately before the first byte.
            self.expected.bind_pipe(&self.pipe, false)?;
            let mut client = [0; 32];
            random(&mut client)?;
            write_frame(
                &self.pipe,
                Frame::new(HELLO, self.ceremony, [0; 32], client),
                deadline,
            )?;
            let challenge = read_frame(&self.pipe, deadline)?;
            challenge.check(CHALLENGE, &self.ceremony, None, Some(&client))?;
            let server = challenge.server();
            write_frame(
                &self.pipe,
                Frame::new(FINISH, self.ceremony, server, client),
                deadline,
            )?;
            let terminal = read_frame(&self.pipe, deadline)?;
            terminal.check(TERMINAL, &self.ceremony, Some(&server), Some(&client))?;
            self.expected.bind_pipe(&self.pipe, false)?;
            valid_deadline(deadline)?;
            Ok(TerminalTranscript {
                ceremony: self.ceremony,
                server,
                client,
            })
        })();
        finish_peer(combine(result, [self.pipe]), self.expected)
    }
}

#[cfg(test)]
mod tests;
