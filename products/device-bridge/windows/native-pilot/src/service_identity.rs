//! Dormant SCM/process observation, never authority.
const SERVICE: &str = "HUBRelayBrokerPersonal";
const ACCOUNT: &str = r"NT SERVICE\HUBRelayBrokerPersonal";
const IMAGE: &str = r"C:\Program Files\HUB_Relay\Personal\personal_broker_service.exe";
#[derive(Clone)]
struct ServicePolicyCandidate {
    command: String,
    image: String,
    privilege: (u32, i32, u32),
}
impl ServicePolicyCandidate {
    fn with_resolved_privilege(luid: (u32, i32)) -> Self {
        Self {
            command: format!("\"{IMAGE}\""),
            image: IMAGE.into(),
            privilege: (luid.0, luid.1, 3),
        }
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct Config {
    kind: u32,
    start: u32,
    account: String,
    command: String,
    required: Vec<String>,
    other: (u32, u32, String, Vec<String>, String),
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct ProcessFacts {
    pid: u32,
    creation: u64,
    token_id: (u32, i32),
    user: Vec<u8>,
    session: u32,
    restricted: bool,
    privileges: Vec<(u32, i32, u32)>,
    image: String,
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct Observation {
    config: Config,
    state: u32,
    pid: u32,
    process: ProcessFacts,
}
fn policy(
    candidate: &ServicePolicyCandidate,
    sid: &[u8],
    transport: &[u8],
    facts: &Observation,
    previous: Option<&Observation>,
) -> std::result::Result<(), &'static str> {
    if facts.config.kind != SERVICE_WIN32_OWN_PROCESS
        || facts.config.start != SERVICE_DEMAND_START
        || facts.config.account != ACCOUNT
        || facts.config.command != candidate.command
        || !facts.config.required.is_empty()
    {
        return Err("service configuration");
    }
    if facts.state != SERVICE_RUNNING || facts.pid == 0 || facts.pid != facts.process.pid {
        return Err("service process status");
    }
    let p = &facts.process;
    if p.user != sid
        || p.user == transport
        || p.session != 0
        || p.restricted
        || p.image != candidate.image
    {
        return Err("service primary principal");
    }
    // USED_FOR_ACCESS is deliberately NOT masked: this unmeasured strict policy
    // rejects every attribute drift, including use history, and disabled extras.
    if p.privileges != [candidate.privilege] {
        return Err("service privilege inventory");
    }
    if previous.is_some_and(|previous| previous != facts) {
        return Err("captured observation changed");
    }
    Ok(())
}

use crate::bootstrap_peer::{self, ExpectedPeer};
use std::os::windows::io::{FromRawHandle, OwnedHandle};
use std::ptr::{null, null_mut};
use windows_sys::Win32::Foundation::*;
use windows_sys::Win32::Security::*;
use windows_sys::Win32::Storage::FileSystem::SYNCHRONIZE;
use windows_sys::Win32::System::Services::*;
use windows_sys::Win32::System::Threading::*;
const MAX_CONFIG: usize = 8192;
#[derive(Debug, PartialEq, Eq)]
enum Failure {
    Native(&'static str, u32),
    Denied(&'static str),
    Peer(bootstrap_peer::Error),
}
#[derive(Debug, PartialEq, Eq)]
struct Error {
    primary: Failure,
    cleanup: Vec<Failure>,
}
type Result<T> = std::result::Result<T, Error>;
impl From<bootstrap_peer::Error> for Error {
    fn from(e: bootstrap_peer::Error) -> Self {
        Self {
            primary: Failure::Peer(e),
            cleanup: vec![],
        }
    }
}
fn denial(reason: &'static str) -> Error {
    Error {
        primary: Failure::Denied(reason),
        cleanup: vec![],
    }
}
fn last(operation: &'static str) -> Error {
    Error {
        primary: Failure::Native(operation, unsafe { GetLastError() }),
        cleanup: vec![],
    }
}
fn finish<T>(result: Result<T>, cleanup: Result<()>) -> Result<T> {
    match (result, cleanup) {
        (r, Ok(())) => r,
        (Ok(_), Err(e)) => Err(e),
        (Err(mut e), Err(c)) => {
            e.cleanup.push(c.primary);
            e.cleanup.extend(c.cleanup);
            Err(e)
        }
    }
}
fn wide(s: &str) -> Vec<u16> {
    s.encode_utf16().chain(Some(0)).collect()
}
struct ScHandle(SC_HANDLE);
impl ScHandle {
    fn manager() -> Result<Self> {
        let h = unsafe { OpenSCManagerW(null(), null(), SC_MANAGER_CONNECT) };
        if h.is_null() {
            Err(last("OpenSCManagerW"))
        } else {
            Ok(Self(h))
        }
    }
    fn personal(&self) -> Result<Self> {
        let h = unsafe {
            OpenServiceW(
                self.0,
                wide(SERVICE).as_ptr(),
                SERVICE_QUERY_CONFIG | SERVICE_QUERY_STATUS,
            )
        };
        if h.is_null() {
            Err(last("OpenServiceW personal"))
        } else {
            Ok(Self(h))
        }
    }
    fn close(mut self) -> Result<()> {
        if unsafe { CloseServiceHandle(self.0) } == 0 {
            Err(last("CloseServiceHandle"))
        } else {
            self.0 = null_mut();
            Ok(())
        }
    }
}
impl Drop for ScHandle {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe {
                CloseServiceHandle(self.0);
            }
        }
    }
}

// Bounded aligned allocation. Only `length` bytes were supplied to Windows;
// rounded backing-storage padding is never considered returned data.
struct ConfigBuffer {
    data: Vec<usize>,
    length: usize,
}
impl ConfigBuffer {
    fn allocate(length: usize, minimum: usize) -> Result<Self> {
        if length < minimum || length > MAX_CONFIG {
            return Err(denial("config allocation bound"));
        }
        Ok(Self {
            data: vec![usize::MAX; length.div_ceil(size_of::<usize>())],
            length,
        })
    }
    fn bytes(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.data.as_ptr().cast(), self.length) }
    }
    fn query(service: &ScHandle, privileges: bool) -> Result<Self> {
        let minimum = if privileges {
            size_of::<SERVICE_REQUIRED_PRIVILEGES_INFOW>()
        } else {
            size_of::<QUERY_SERVICE_CONFIGW>()
        };
        let mut needed = 0;
        let call = |pointer: *mut u8, length: u32, needed: *mut u32| unsafe {
            if privileges {
                QueryServiceConfig2W(
                    service.0,
                    SERVICE_CONFIG_REQUIRED_PRIVILEGES_INFO,
                    pointer,
                    length,
                    needed,
                )
            } else {
                QueryServiceConfigW(service.0, pointer.cast(), length, needed)
            }
        };
        if call(null_mut(), 0, &mut needed) != 0 {
            return Err(denial("unexpected config sizing success"));
        }
        if unsafe { GetLastError() } != ERROR_INSUFFICIENT_BUFFER {
            return Err(last("QueryServiceConfig sizing"));
        }
        let mut buffer = Self::allocate(needed as usize, minimum)?;
        // pcbBytesNeeded is defined only on insufficient-buffer failure, not a
        // successful-query byte count. The exact supplied allocation bounds parsing.
        if call(
            buffer.data.as_mut_ptr().cast(),
            buffer.length as u32,
            &mut needed,
        ) == 0
        {
            return Err(last("QueryServiceConfig data"));
        }
        Ok(buffer)
    }
    fn text(
        &self,
        pointer: *const u16,
        minimum: usize,
        multi: bool,
        optional: bool,
    ) -> Result<Vec<String>> {
        parse_strings(
            self.bytes(),
            self.data.as_ptr() as usize,
            pointer as usize,
            minimum,
            multi,
            optional,
        )
    }
}
fn parse_strings(
    bytes: &[u8],
    base: usize,
    pointer: usize,
    minimum: usize,
    multi: bool,
    optional: bool,
) -> Result<Vec<String>> {
    if bytes.len() > MAX_CONFIG || minimum > bytes.len() {
        return Err(denial("string allocation bound"));
    }
    if pointer == 0 {
        return if optional {
            Ok(vec![])
        } else {
            Err(denial("null config string"))
        };
    }
    let offset = pointer
        .checked_sub(base)
        .ok_or_else(|| denial("config pointer before buffer"))?;
    if !pointer.is_multiple_of(2) || offset < minimum || offset >= bytes.len() {
        return Err(denial("config pointer bound/alignment"));
    }
    let mut cursor = offset;
    let mut strings = vec![];
    loop {
        let mut words = vec![];
        loop {
            let pair = bytes
                .get(
                    cursor
                        ..cursor
                            .checked_add(2)
                            .ok_or_else(|| denial("string overflow"))?,
                )
                .ok_or_else(|| denial("unterminated config string"))?;
            cursor += 2;
            let word = u16::from_le_bytes([pair[0], pair[1]]);
            if word == 0 {
                break;
            }
            words.push(word);
        }
        if multi && words.is_empty() {
            // Empty MULTI_SZ has two NULs, too. Nonempty lists consumed the
            // previous string terminator on their previous iteration.
            if strings.is_empty() && bytes.get(cursor..cursor + 2) != Some(&[0, 0]) {
                return Err(denial("empty MULTI_SZ terminator"));
            }
            return Ok(strings);
        }
        strings.push(String::from_utf16(&words).map_err(|_| denial("invalid config UTF16"))?);
        if !multi {
            return Ok(strings);
        }
    }
}
fn config(service: &ScHandle) -> Result<Config> {
    let b = ConfigBuffer::query(service, false)?;
    let q = unsafe { &*b.data.as_ptr().cast::<QUERY_SERVICE_CONFIGW>() };
    let n = size_of::<QUERY_SERVICE_CONFIGW>();
    let text = |p, optional| -> Result<String> {
        Ok(b.text(p, n, false, optional)?
            .into_iter()
            .next()
            .unwrap_or_default())
    };
    let mut facts = Config {
        kind: q.dwServiceType,
        start: q.dwStartType,
        account: text(q.lpServiceStartName, false)?,
        command: text(q.lpBinaryPathName, false)?,
        required: vec![],
        other: (
            q.dwErrorControl,
            q.dwTagId,
            text(q.lpLoadOrderGroup, true)?,
            b.text(q.lpDependencies, n, true, true)?,
            text(q.lpDisplayName, false)?,
        ),
    };
    let b = ConfigBuffer::query(service, true)?;
    let q = unsafe { &*b.data.as_ptr().cast::<SERVICE_REQUIRED_PRIVILEGES_INFOW>() };
    // A null pointer is conservatively unsupported here; no query failure or
    // absent data is converted to an empty configured inventory.
    facts.required = b.text(
        q.pmszRequiredPrivileges,
        size_of::<SERVICE_REQUIRED_PRIVILEGES_INFOW>(),
        true,
        false,
    )?;
    Ok(facts)
}
fn status(service: &ScHandle) -> Result<SERVICE_STATUS_PROCESS> {
    let mut value: SERVICE_STATUS_PROCESS = unsafe { std::mem::zeroed() };
    let mut length = 0;
    if unsafe {
        QueryServiceStatusEx(
            service.0,
            SC_STATUS_PROCESS_INFO,
            (&mut value as *mut SERVICE_STATUS_PROCESS).cast(),
            size_of::<SERVICE_STATUS_PROCESS>() as u32,
            &mut length,
        )
    } == 0
    {
        return Err(last("QueryServiceStatusEx"));
    }
    // Successful fixed-size query owns the entire supplied status structure;
    // pcbBytesNeeded is only specified for insufficient-buffer failures.
    if value.dwServiceType != SERVICE_WIN32_OWN_PROCESS
        || value.dwCurrentState != SERVICE_RUNNING
        || value.dwProcessId == 0
    {
        return Err(denial("service status"));
    }
    Ok(value)
}
fn intended_sid() -> Result<Vec<u8>> {
    let mut size = 0;
    let mut domain_size = 0;
    let mut kind = 0;
    let account = wide(ACCOUNT);
    if unsafe {
        LookupAccountNameW(
            null(),
            account.as_ptr(),
            null_mut(),
            &mut size,
            null_mut(),
            &mut domain_size,
            &mut kind,
        )
    } != 0
    {
        return Err(denial("unexpected SID sizing success"));
    }
    if unsafe { GetLastError() } != ERROR_INSUFFICIENT_BUFFER {
        return Err(last("LookupAccountNameW sizing"));
    }
    if !(8..=68).contains(&size) || domain_size > 256 {
        return Err(denial("account allocation bound"));
    }
    let capacity = size;
    let mut sid = vec![0u32; (size as usize).div_ceil(4)];
    let mut domain = vec![0u16; domain_size as usize];
    if unsafe {
        LookupAccountNameW(
            null(),
            account.as_ptr(),
            sid.as_mut_ptr().cast(),
            &mut size,
            domain.as_mut_ptr(),
            &mut domain_size,
            &mut kind,
        )
    } == 0
    {
        return Err(last("LookupAccountNameW personal"));
    }
    if size > capacity || size != 32 {
        return Err(denial("resolved SID length"));
    }
    let bytes = unsafe { std::slice::from_raw_parts(sid.as_ptr().cast::<u8>(), size as usize) };
    // Check the complete structural extent before giving a SID to Windows.
    if bytes[..8] != [1, 6, 0, 0, 0, 0, 0, 5] || bytes[8..12] != 80u32.to_le_bytes() {
        return Err(denial("resolved service SID shape"));
    }
    if unsafe { IsValidSid(sid.as_ptr().cast_mut().cast()) } == 0
        || unsafe { GetLengthSid(sid.as_ptr().cast_mut().cast()) } != size
    {
        return Err(denial("resolved SID layout"));
    }
    Ok(bytes.to_vec())
}
impl ServicePolicyCandidate {
    fn personal() -> Result<Self> {
        let mut luid = LUID {
            LowPart: 0,
            HighPart: 0,
        };
        if unsafe {
            LookupPrivilegeValueW(null(), wide("SeChangeNotifyPrivilege").as_ptr(), &mut luid)
        } == 0
        {
            return Err(last("LookupPrivilegeValueW"));
        }
        Ok(Self::with_resolved_privilege((luid.LowPart, luid.HighPart)))
    }
}
fn process_facts(peer: &ExpectedPeer) -> Result<ProcessFacts> {
    peer.recheck()?;
    let mut image = vec![0u16; 32768];
    let mut length = image.len() as u32;
    if unsafe {
        QueryFullProcessImageNameW(peer.process_handle(), 0, image.as_mut_ptr(), &mut length)
    } == 0
    {
        return Err(last("QueryFullProcessImageNameW"));
    }
    if length == 0 || length as usize >= image.len() {
        return Err(denial("process image length"));
    }
    let (pid, creation, token_id) = peer.stamp();
    Ok(ProcessFacts {
        pid,
        creation,
        token_id,
        user: peer.user().to_vec(),
        session: peer.session(),
        restricted: peer.unsupported_restrictions(),
        privileges: peer.privileges().to_vec(),
        image: String::from_utf16(&image[..length as usize])
            .map_err(|_| denial("process image UTF16"))?,
    })
}
struct HeldScmProcessBinding {
    manager: ScHandle,
    service: ScHandle,
    peer: ExpectedPeer,
    intended: Vec<u8>,
    candidate: ServicePolicyCandidate,
    captured: Observation,
}
impl HeldScmProcessBinding {
    fn capture(candidate: ServicePolicyCandidate, transport: &ExpectedPeer) -> Result<Self> {
        bootstrap_peer::no_impersonation()?;
        transport.recheck()?;
        let manager = ScHandle::manager()?;
        let service = match manager.personal() {
            Ok(s) => s,
            Err(e) => return finish(Err(e), manager.close()),
        };
        let result = (|| {
            let intended = intended_sid()?;
            let config = config(&service)?;
            let status = status(&service)?;
            let handle = unsafe {
                OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
                    0,
                    status.dwProcessId,
                )
            };
            if handle.is_null() {
                return Err(last("OpenProcess SCM PID"));
            }
            let peer = ExpectedPeer::from_owned(unsafe { OwnedHandle::from_raw_handle(handle) })?;
            let observation = (|| {
                let process = process_facts(&peer)?;
                let facts = Observation {
                    config,
                    state: status.dwCurrentState,
                    pid: status.dwProcessId,
                    process,
                };
                policy(&candidate, &intended, transport.user(), &facts, None).map_err(denial)?;
                Ok(facts)
            })();
            match observation {
                Ok(facts) => Ok((intended, peer, facts)),
                Err(e) => finish(Err(e), peer.close().map_err(Into::into)),
            }
        })();
        let (intended, peer, captured) = match result {
            Ok(v) => v,
            Err(e) => return finish(finish(Err(e), service.close()), manager.close()),
        };
        let binding = Self {
            manager,
            service,
            peer,
            intended,
            candidate,
            captured,
        };
        if let Err(e) = binding.revalidate(transport) {
            return binding.finish(Err(e));
        }
        Ok(binding)
    }
    fn revalidate(&self, transport: &ExpectedPeer) -> Result<()> {
        bootstrap_peer::no_impersonation()?;
        transport.recheck()?;
        self.peer.recheck()?;
        if intended_sid()? != self.intended {
            return Err(denial("resolved principal changed"));
        }
        let observed_config = config(&self.service)?;
        let before = status(&self.service)?;
        let process = process_facts(&self.peer)?;
        let facts = Observation {
            config: observed_config,
            state: before.dwCurrentState,
            pid: before.dwProcessId,
            process,
        };
        policy(
            &self.candidate,
            &self.intended,
            transport.user(),
            &facts,
            Some(&self.captured),
        )
        .map_err(denial)?;
        // Bracket process observation with a second status/config capture. This is
        // a conservative snapshot check, not atomic SCM locking or future authority.
        let after = status(&self.service)?;
        if after.dwProcessId != facts.pid || config(&self.service)? != facts.config {
            return Err(denial("SCM changed during recheck"));
        }
        self.peer.recheck()?;
        transport.recheck()?;
        bootstrap_peer::no_impersonation()?;
        Ok(())
    }
    fn finish<T>(self, result: Result<T>) -> Result<T> {
        finish(
            finish(
                finish(result, self.peer.close().map_err(Into::into)),
                self.service.close(),
            ),
            self.manager.close(),
        )
    }
    fn close(self) -> Result<()> {
        self.finish(Ok(()))
    }
}
#[cfg(test)]
mod tests;
