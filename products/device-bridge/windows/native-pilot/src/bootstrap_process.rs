//! Dormant observations of this process, retained by a limited real handle.
//! The image names are metadata observations; trusted launch remains separate.

use std::os::windows::io::{AsRawHandle, FromRawHandle, IntoRawHandle, OwnedHandle};
use std::ptr::null_mut;
use windows_sys::Win32::Foundation::*;
use windows_sys::Win32::System::Threading::*;
use windows_sys::core::BOOL;

// Exact ABI from cached windows-sys 0.61.2:
// Windows/Win32/System/Threading/mod.rs, gated there on SystemInformation.
// Keep the existing dependency features unchanged, as in ancestor_chain.rs.
#[cfg_attr(
    target_arch = "x86",
    link(
        name = "kernel32.dll",
        kind = "raw-dylib",
        modifiers = "+verbatim",
        import_name_type = "undecorated"
    )
)]
#[cfg_attr(
    not(target_arch = "x86"),
    link(name = "kernel32.dll", kind = "raw-dylib", modifiers = "+verbatim")
)]
unsafe extern "system" {
    fn IsWow64Process2(
        process: HANDLE,
        process_machine: *mut u16,
        native_machine: *mut u16,
    ) -> BOOL;
}

const IMAGE_FILE_MACHINE_UNKNOWN: u16 = 0;
const IMAGE_FILE_MACHINE_AMD64: u16 = 0x8664;
const PROCESS_NAME_NATIVE: u32 = 1;
const MAX_IMAGE_UNITS: usize = 32768;

#[derive(Debug, PartialEq, Eq)]
enum Failure {
    Native(&'static str, u32),
    Denied(&'static str),
}

#[derive(Debug, PartialEq, Eq)]
pub(super) struct Error {
    primary: Failure,
    cleanup: Vec<Failure>,
}
type Result<T> = std::result::Result<T, Error>;

fn last(operation: &'static str) -> Error {
    Error {
        primary: Failure::Native(operation, unsafe { GetLastError() }),
        cleanup: vec![],
    }
}

fn denied(reason: &'static str) -> Error {
    Error {
        primary: Failure::Denied(reason),
        cleanup: vec![],
    }
}

fn finish<T>(result: Result<T>, cleanup: Result<()>) -> Result<T> {
    match (result, cleanup) {
        (result, Ok(())) => result,
        (Ok(_), Err(error)) => Err(error),
        (Err(mut error), Err(cleanup)) => {
            error.cleanup.push(cleanup.primary);
            error.cleanup.extend(cleanup.cleanup);
            Err(error)
        }
    }
}

fn raw(handle: &OwnedHandle) -> HANDLE {
    handle.as_raw_handle()
}

fn close_checked(handle: OwnedHandle) -> Result<()> {
    // Consume ownership before the single close attempt. No Drop retry after
    // a failed or uncertain native close, matching the crate's ownership rule.
    if unsafe { CloseHandle(handle.into_raw_handle()) } == 0 {
        Err(last("CloseHandle own process"))
    } else {
        Ok(())
    }
}

fn duplicate_current() -> Result<OwnedHandle> {
    let mut handle = null_mut();
    if unsafe {
        DuplicateHandle(
            GetCurrentProcess(),
            GetCurrentProcess(),
            GetCurrentProcess(),
            &mut handle,
            PROCESS_QUERY_LIMITED_INFORMATION,
            0,
            0,
        )
    } == 0
    {
        return Err(last("DuplicateHandle own process"));
    }
    if handle.is_null() || handle == INVALID_HANDLE_VALUE {
        return Err(denied("invalid duplicated process handle"));
    }
    // SAFETY: successful DuplicateHandle transfers one noninheritable real
    // handle with only PROCESS_QUERY_LIMITED_INFORMATION to this owner.
    Ok(unsafe { OwnedHandle::from_raw_handle(handle) })
}

fn noninheritable(handle: HANDLE) -> Result<()> {
    let mut flags = 0;
    if unsafe { GetHandleInformation(handle, &mut flags) } == 0 {
        return Err(last("GetHandleInformation own process"));
    }
    if flags & HANDLE_FLAG_INHERIT != 0 {
        return Err(denied("inheritable own process handle"));
    }
    Ok(())
}

fn bounded_image(buffer: &[u16], count: usize) -> Result<Vec<u16>> {
    // This diagnostic profile admits 1..=32766 code units plus a terminator.
    if count == 0
        || count >= MAX_IMAGE_UNITS - 1
        || count >= buffer.len()
        || buffer[count] != 0
        || buffer[..count].contains(&0)
    {
        return Err(denied("invalid image-name extent"));
    }
    // Preserve original UTF-16 code units, including unpaired surrogates.
    Ok(buffer[..count].to_vec())
}

fn image_name(handle: HANDLE, flags: u32) -> Result<Vec<u16>> {
    // A nonzero sentinel makes the terminator check inspect API output.
    let mut buffer = vec![u16::MAX; MAX_IMAGE_UNITS];
    let mut count = MAX_IMAGE_UNITS as u32;
    if unsafe { QueryFullProcessImageNameW(handle, flags, buffer.as_mut_ptr(), &mut count) } == 0 {
        return Err(last("QueryFullProcessImageNameW own process"));
    }
    bounded_image(&buffer, count as usize)
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct ProcessFacts {
    pid: u32,
    creation: u64,
    process_machine: u16,
    native_machine: u16,
    win32_image: Vec<u16>,
    native_image: Vec<u16>,
}

fn observe(handle: HANDLE) -> Result<ProcessFacts> {
    noninheritable(handle)?;
    let pid = unsafe { GetProcessId(handle) };
    if pid == 0 {
        return Err(last("GetProcessId own process"));
    }
    let mut times: [FILETIME; 4] = unsafe { std::mem::zeroed() };
    let [creation, exit, kernel, user] = &mut times;
    if unsafe { GetProcessTimes(handle, creation, exit, kernel, user) } == 0 {
        return Err(last("GetProcessTimes own process"));
    }
    let creation = u64::from(creation.dwLowDateTime) | (u64::from(creation.dwHighDateTime) << 32);
    let (mut process_machine, mut native_machine) = (0, 0);
    if unsafe { IsWow64Process2(handle, &mut process_machine, &mut native_machine) } == 0 {
        return Err(last("IsWow64Process2 own process"));
    }
    if process_machine != IMAGE_FILE_MACHINE_UNKNOWN || native_machine != IMAGE_FILE_MACHINE_AMD64 {
        return Err(denied("unsupported process architecture"));
    }
    let facts = ProcessFacts {
        pid,
        creation,
        process_machine,
        native_machine,
        win32_image: image_name(handle, 0)?,
        native_image: image_name(handle, PROCESS_NAME_NATIVE)?,
    };
    noninheritable(handle)?;
    Ok(facts)
}

pub(super) struct OwnProcessObservation {
    process: OwnedHandle,
    facts: ProcessFacts,
}

impl OwnProcessObservation {
    pub(super) fn capture_current() -> Result<Self> {
        if !cfg!(target_arch = "x86_64") {
            return Err(denied("unsupported process architecture"));
        }
        let process = duplicate_current()?;
        let facts = match observe(raw(&process)) {
            Ok(facts) => facts,
            Err(error) => return finish(Err(error), close_checked(process)),
        };
        let observation = Self { process, facts };
        if let Err(error) = observation.recheck() {
            return finish(Err(error), observation.close());
        }
        Ok(observation)
    }

    pub(super) fn recheck(&self) -> Result<()> {
        if observe(raw(&self.process))? != self.facts {
            return Err(denied("own process observation changed"));
        }
        Ok(())
    }

    pub(super) fn close(self) -> Result<()> {
        close_checked(self.process)
    }
}

#[cfg(test)]
mod tests;
