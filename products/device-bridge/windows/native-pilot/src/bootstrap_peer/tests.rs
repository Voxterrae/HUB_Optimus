use super::*;
use std::ffi::OsStr;
use std::os::windows::ffi::OsStrExt;
use std::time::Duration;

const LIMIT: Duration = Duration::from_secs(4);

fn wide(value: impl AsRef<OsStr>) -> Vec<u16> {
    value.as_ref().encode_wide().chain(Some(0)).collect()
}

fn current() -> ExpectedPeer {
    ExpectedPeer::from_owned(duplicate(unsafe { GetCurrentProcess() }, false).unwrap()).unwrap()
}

struct Child {
    process: Option<OwnedHandle>,
    thread: Option<OwnedHandle>,
    peer: Option<ExpectedPeer>,
    sentinel: Option<OwnedHandle>,
}

impl Child {
    fn launch(mode: &str, server: &Server) -> Self {
        // Only this limited parent process handle is inheritable and allow-listed.
        let parent = duplicate(unsafe { GetCurrentProcess() }, true).unwrap();
        let attributes = SECURITY_ATTRIBUTES {
            nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
            lpSecurityDescriptor: std::ptr::null_mut(),
            bInheritHandle: 1,
        };
        // A real inheritable event is deliberately omitted from the allow-list.
        let sentinel = owned(unsafe { CreateEventW(&attributes, 1, 0, std::ptr::null()) }).unwrap();
        let mut bytes = 0;
        unsafe { InitializeProcThreadAttributeList(std::ptr::null_mut(), 1, 0, &mut bytes) };
        let mut storage = vec![0usize; bytes.div_ceil(std::mem::size_of::<usize>())];
        let list = storage.as_mut_ptr().cast();
        assert_ne!(
            unsafe { InitializeProcThreadAttributeList(list, 1, 0, &mut bytes) },
            0
        );
        let mut inherited = [raw(&parent)];
        assert_ne!(
            unsafe {
                UpdateProcThreadAttribute(
                    list,
                    0,
                    PROC_THREAD_ATTRIBUTE_HANDLE_LIST as usize,
                    inherited.as_mut_ptr().cast(),
                    std::mem::size_of_val(&inherited),
                    std::ptr::null_mut(),
                    std::ptr::null(),
                )
            },
            0
        );
        let mut startup: STARTUPINFOEXW = unsafe { std::mem::zeroed() };
        startup.StartupInfo.cb = std::mem::size_of::<STARTUPINFOEXW>() as u32;
        startup.lpAttributeList = list;
        let exe = std::env::current_exe().unwrap();
        let mut command = wide(format!(
            "\"{}\" --ignored --exact bootstrap_peer::tests::native_child_entry --nocapture --test-threads=1",
            exe.display()
        ));
        let mut vars: Vec<(String, String)> = std::env::vars()
            .filter(|(key, _)| !key.starts_with("HUB_RELAY_PEER_"))
            .collect();
        vars.extend([
            ("HUB_RELAY_PEER_MODE".into(), mode.into()),
            (
                "HUB_RELAY_PEER_PARENT".into(),
                (raw(&parent) as usize).to_string(),
            ),
            ("HUB_RELAY_PEER_PIPE".into(), server.name.clone()),
            ("HUB_RELAY_PEER_CORRELATION".into(), hex(&server.ceremony)),
            (
                "HUB_RELAY_PEER_SENTINEL".into(),
                (raw(&sentinel) as usize).to_string(),
            ),
        ]);
        vars.sort_by_key(|(key, _)| key.to_uppercase());
        let mut environment = Vec::<u16>::new();
        for (key, value) in vars {
            environment.extend(wide(format!("{key}={value}")));
        }
        environment.push(0);
        let mut info: PROCESS_INFORMATION = unsafe { std::mem::zeroed() };
        let success = unsafe {
            CreateProcessW(
                wide(&exe).as_ptr(),
                command.as_mut_ptr(),
                std::ptr::null(),
                std::ptr::null(),
                1,
                CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT | EXTENDED_STARTUPINFO_PRESENT,
                environment.as_ptr().cast(),
                std::ptr::null(),
                &startup.StartupInfo,
                &mut info,
            )
        };
        let error = unsafe { GetLastError() };
        unsafe { DeleteProcThreadAttributeList(list) };
        close_checked(parent).unwrap();
        assert_ne!(success, 0, "CreateProcessW {error}");
        let process = owned(info.hProcess).unwrap();
        let thread = owned(info.hThread).unwrap();
        let peer = ExpectedPeer::from_owned(duplicate(raw(&process), false).unwrap()).unwrap();
        Self {
            process: Some(process),
            thread: Some(thread),
            peer: Some(peer),
            sentinel: Some(sentinel),
        }
    }

    fn expected(&mut self) -> ExpectedPeer {
        self.peer.take().unwrap()
    }

    fn finish(mut self) {
        let process = self.process.as_ref().unwrap();
        assert_eq!(
            unsafe { WaitForSingleObject(raw(process), 6000) },
            WAIT_OBJECT_0,
            "child deadline"
        );
        let mut code = 0;
        assert_ne!(unsafe { GetExitCodeProcess(raw(process), &mut code) }, 0);
        if let Some(peer) = self.peer.take() {
            peer.close().unwrap();
        }
        close_checked(self.thread.take().unwrap()).unwrap();
        close_checked(self.process.take().unwrap()).unwrap();
        let sentinel = self.sentinel.take().unwrap();
        assert_eq!(
            unsafe { WaitForSingleObject(raw(&sentinel), 0) },
            WAIT_TIMEOUT,
            "omitted event must remain unsignaled"
        );
        close_checked(sentinel).unwrap();
        assert_eq!(code, 0, "child fixture failed");
    }
}

impl Drop for Child {
    fn drop(&mut self) {
        if let Some(peer) = self.peer.take() {
            peer.close().unwrap();
        }
        if let Some(process) = self.process.take() {
            if unsafe { WaitForSingleObject(raw(&process), 0) } == WAIT_TIMEOUT {
                assert_ne!(unsafe { TerminateProcess(raw(&process), 99) }, 0);
                assert_eq!(
                    unsafe { WaitForSingleObject(raw(&process), 2000) },
                    WAIT_OBJECT_0
                );
            }
            close_checked(process).unwrap();
        }
        if let Some(thread) = self.thread.take() {
            close_checked(thread).unwrap();
        }
        if let Some(sentinel) = self.sentinel.take() {
            close_checked(sentinel).unwrap();
        }
    }
}

fn server() -> Server {
    let peer = current();
    let server = Server::create(&peer).unwrap();
    peer.close().unwrap();
    server
}

#[test]
#[ignore = "subprocess fixture entry; exercised by native parent tests"]
fn native_child_entry() {
    let mode = std::env::var("HUB_RELAY_PEER_MODE").unwrap();
    let inherited: usize = std::env::var("HUB_RELAY_PEER_PARENT")
        .unwrap()
        .parse()
        .unwrap();
    let parent = ExpectedPeer::from_owned(owned(inherited as HANDLE).unwrap()).unwrap();
    assert_ne!(unsafe { GetCurrentProcessId() }, parent.pid);
    let name = std::env::var("HUB_RELAY_PEER_PIPE").unwrap();
    let ceremony: [u8; 16] = unhex(&std::env::var("HUB_RELAY_PEER_CORRELATION").unwrap())
        .try_into()
        .unwrap();
    let deadline = Instant::now() + LIMIT;
    if mode == "idle" {
        std::thread::sleep(Duration::from_millis(450));
        parent.close().unwrap();
        return;
    }
    let expected_challenge_error = match mode.as_str() {
        "bad-challenge-frame" => Some(Error::Denied("frame")),
        "bad-challenge-oversize" => Some(Error::Native("ReadFile", ERROR_MORE_DATA)),
        "bad-challenge-truncated" => Some(Error::Denied("frame length")),
        _ => None,
    };
    if mode == "honest"
        || mode == "wrong-server"
        || mode == "wrong-client"
        || expected_challenge_error.is_some()
    {
        let retry_peer = if mode == "honest" {
            Some(ExpectedPeer::from_owned(duplicate(raw(&parent.process), false).unwrap()).unwrap())
        } else {
            None
        };
        let result = Client::connect(&name, ceremony, parent, deadline)
            .and_then(|client| client.exchange(deadline));
        if let Some(expected) = expected_challenge_error {
            assert_eq!(result.unwrap_err(), expected, "exact challenge rejection");
        } else if mode == "honest" {
            assert!(result.is_ok(), "{result:?}");
        } else {
            assert!(result.is_err(), "unexpected peer accepted");
        }
        if let Some(peer) = retry_peer {
            assert!(
                Client::connect(
                    &name,
                    ceremony,
                    peer,
                    Instant::now() + Duration::from_millis(80)
                )
                .is_err(),
                "second exchange accepted"
            );
        }
        no_impersonation().unwrap();
        return;
    }
    if mode == "inheritance" {
        let mut flags = 0;
        assert_ne!(
            unsafe { GetHandleInformation(raw(&parent.process), &mut flags) },
            0
        );
        assert_eq!(
            flags & HANDLE_FLAG_INHERIT,
            0,
            "ExpectedPeer narrows inherited handle again"
        );
        let mut duplicate_handle = std::ptr::null_mut();
        assert_eq!(
            unsafe {
                DuplicateHandle(
                    raw(&parent.process),
                    GetCurrentProcess(),
                    GetCurrentProcess(),
                    &mut duplicate_handle,
                    0,
                    0,
                    DUPLICATE_SAME_ACCESS,
                )
            },
            0,
            "limited parent handle must not grant PROCESS_DUP_HANDLE"
        );
        let sentinel: usize = std::env::var("HUB_RELAY_PEER_SENTINEL")
            .unwrap()
            .parse()
            .unwrap();
        assert_eq!(
            unsafe { SetEvent(sentinel as HANDLE) },
            0,
            "omitted inheritable sentinel must not be usable"
        );
        parent.close().unwrap();
        return;
    }
    if mode == "restricted" || mode == "filtered" {
        let mut source = std::ptr::null_mut();
        assert_ne!(
            unsafe {
                OpenProcessToken(
                    GetCurrentProcess(),
                    TOKEN_QUERY | TOKEN_DUPLICATE,
                    &mut source,
                )
            },
            0
        );
        let source = owned(source).unwrap();
        let original_context = TokenContext::capture(raw(&source)).unwrap();
        let logon_data = TokenData::query(raw(&source), TokenLogonSid).unwrap();
        let logon = logon_data.pointer::<TOKEN_GROUPS>();
        assert_eq!(unsafe { (*logon).GroupCount }, 1);
        let restricting_sid = SID_AND_ATTRIBUTES {
            Sid: unsafe { (*logon).Groups[0].Sid },
            Attributes: 0,
        };
        let restrict_count = u32::from(mode == "restricted");
        let mut restricted = std::ptr::null_mut();
        assert_ne!(
            unsafe {
                CreateRestrictedToken(
                    raw(&source),
                    DISABLE_MAX_PRIVILEGE,
                    0,
                    std::ptr::null(),
                    0,
                    std::ptr::null(),
                    restrict_count,
                    &restricting_sid,
                    &mut restricted,
                )
            },
            0
        );
        let restricted = owned(restricted).unwrap();
        let altered_context = TokenContext::capture(raw(&restricted)).unwrap();
        assert_ne!(
            altered_context.privileges, original_context.privileges,
            "actual privilege filtering"
        );
        if mode == "restricted" {
            assert_ne!(unsafe { IsTokenRestricted(raw(&restricted)) }, 0);
            assert_ne!(altered_context.restricted, original_context.restricted);
            assert_eq!(altered_context.restricted.len(), 1);
            assert_eq!(
                altered_context.restricted[0].0,
                sid_bytes(restricting_sid.Sid).unwrap()
            );
        } else {
            assert_eq!(
                altered_context.restricted, original_context.restricted,
                "privilege-only filter adds no restricting SID"
            );
        }
        let mut impersonation = std::ptr::null_mut();
        assert_ne!(
            unsafe {
                DuplicateTokenEx(
                    raw(&restricted),
                    TOKEN_QUERY | TOKEN_IMPERSONATE,
                    std::ptr::null(),
                    SecurityImpersonation,
                    TokenImpersonation,
                    &mut impersonation,
                )
            },
            0
        );
        let impersonation = owned(impersonation).unwrap();
        assert_ne!(
            unsafe { SetThreadToken(std::ptr::null(), raw(&impersonation)) },
            0
        );
        close_checked(impersonation).unwrap();
        close_checked(restricted).unwrap();
        close_checked(source).unwrap();
    }
    let sqos = if mode == "anonymous" {
        SECURITY_ANONYMOUS
    } else {
        SECURITY_IDENTIFICATION
    };
    let pipe = open_pipe(&name, deadline, sqos).unwrap();
    if mode == "restricted" || mode == "filtered" {
        assert_ne!(unsafe { RevertToSelf() }, 0);
    }
    if mode == "disconnect" {
        close_checked(pipe).unwrap();
        std::thread::sleep(Duration::from_millis(450));
        parent.close().unwrap();
        return;
    }
    if mode == "stall" {
        std::thread::sleep(Duration::from_millis(450));
        close_checked(pipe).unwrap();
        parent.close().unwrap();
        return;
    }
    let mut client_nonce = [0; 32];
    random(&mut client_nonce).unwrap();
    let hello = Frame::new(HELLO, ceremony, [0; 32], client_nonce);
    let mut bytes = hello.0.to_vec();
    match mode.as_str() {
        "version" => bytes[8] ^= 1,
        "role" => bytes[9] = FINISH,
        "reserved" => bytes[10] = 1,
        "correlation" => bytes[16] ^= 1,
        "hello-challenge" => bytes[32] = 1,
        "zero-nonce" => bytes[64..96].fill(0),
        "oversize" => bytes.push(0),
        "truncated" => {
            bytes.pop();
        }
        _ => (),
    }
    transfer(&pipe, Transfer::Write(&bytes), deadline).unwrap();
    if matches!(
        mode.as_str(),
        "anonymous"
            | "filtered"
            | "restricted"
            | "version"
            | "role"
            | "reserved"
            | "correlation"
            | "hello-challenge"
            | "zero-nonce"
            | "oversize"
            | "truncated"
    ) {
        assert!(read_frame(&pipe, deadline).is_err());
        close_checked(pipe).unwrap();
        parent.close().unwrap();
        return;
    }
    let challenge = read_frame(&pipe, deadline).unwrap();
    if mode == "exit-after-challenge" {
        close_checked(pipe).unwrap();
        parent.close().unwrap();
        std::process::exit(0);
    }
    let mut finish = Frame::new(FINISH, ceremony, challenge.server(), client_nonce);
    match mode.as_str() {
        "finish-server" => finish.0[32] ^= 1,
        "finish-client" => finish.0[64] ^= 1,
        "finish-correlation" => finish.0[16] ^= 1,
        "replay" => finish = hello,
        _ => panic!("unknown fixture"),
    }
    transfer(&pipe, Transfer::Write(&finish.0), deadline).unwrap();
    assert!(read_frame(&pipe, deadline).is_err());
    close_checked(pipe).unwrap();
    parent.close().unwrap();
    no_impersonation().unwrap();
}

#[test]
fn honest_held_parent_child_exchange() {
    let server = server();
    let mut child = Child::launch("honest", &server);
    let result = server.exchange(child.expected(), Instant::now() + LIMIT);
    assert!(result.is_ok(), "{result:?}");
    child.finish();
    no_impersonation().unwrap();
}

#[test]
fn actual_same_sid_wrong_client_is_denied() {
    let server = server();
    let child = Child::launch("wrong-client", &server);
    let error = server
        .exchange(current(), Instant::now() + LIMIT)
        .unwrap_err();
    assert_eq!(error, Error::Denied("pipe process"));
    child.finish();
}

#[test]
fn actual_substituted_server_is_denied_before_hello() {
    let server = server();
    let mut child = Child::launch("idle", &server);
    // The held child is expected; the actual server is the parent, same SID.
    let expected = child.expected();
    let pipe = Client::connect(
        &server.name,
        server.ceremony,
        expected,
        Instant::now() + LIMIT,
    );
    assert!(matches!(pipe, Err(Error::Denied("pipe process"))));
    let deadline = Instant::now() + LIMIT;
    let error = connect_pipe(&server.pipe, deadline)
        .and_then(|_| read_frame(&server.pipe, deadline))
        .unwrap_err();
    assert!(
        matches!(
            error,
            Error::Native("ReadFile", ERROR_BROKEN_PIPE | ERROR_PIPE_NOT_CONNECTED)
                | Error::Native("ConnectNamedPipe", ERROR_NO_DATA)
        ),
        "no hello bytes: {error:?}"
    );
    close_checked(server.pipe).unwrap();
    child.finish();
}

#[test]
fn dead_expected_peer_live_replacement_denied() {
    let server = server();
    let mut dead = Child::launch("idle", &server);
    let expected = dead.expected();
    dead.finish();
    let replacement = Child::launch("wrong-client", &server);
    assert_eq!(
        server
            .exchange(expected, Instant::now() + LIMIT)
            .unwrap_err(),
        Error::Denied("process exited")
    );
    replacement.finish();
}

#[test]
fn native_exact_hello_negatives() {
    for mode in [
        "version",
        "role",
        "reserved",
        "correlation",
        "hello-challenge",
        "zero-nonce",
    ] {
        let server = server();
        let mut child = Child::launch(mode, &server);
        assert_eq!(
            server
                .exchange(child.expected(), Instant::now() + LIMIT)
                .unwrap_err(),
            Error::Denied("frame"),
            "{mode}"
        );
        child.finish();
        no_impersonation().unwrap();
    }
}

#[test]
fn native_exact_final_challenge_and_replay_negatives() {
    for mode in [
        "finish-server",
        "finish-client",
        "finish-correlation",
        "replay",
    ] {
        let server = server();
        let mut child = Child::launch(mode, &server);
        assert_eq!(
            server
                .exchange(child.expected(), Instant::now() + LIMIT)
                .unwrap_err(),
            Error::Denied("frame"),
            "{mode}"
        );
        child.finish();
        no_impersonation().unwrap();
    }
}

#[test]
fn native_oversize_and_truncated_frames() {
    for mode in ["oversize", "truncated"] {
        let server = server();
        let mut child = Child::launch(mode, &server);
        let error = server
            .exchange(child.expected(), Instant::now() + LIMIT)
            .unwrap_err();
        println!("{mode}: {error:?}");
        if mode == "oversize" {
            assert_eq!(error, Error::Native("ReadFile", ERROR_MORE_DATA));
        } else {
            assert_eq!(error, Error::Denied("frame length"));
        }
        child.finish();
        no_impersonation().unwrap();
    }
}

#[test]
fn native_anonymous_last_message_is_denied() {
    for mode in ["anonymous", "filtered", "restricted"] {
        let server = server();
        let mut child = Child::launch(mode, &server);
        let error = server
            .exchange(child.expected(), Instant::now() + LIMIT)
            .unwrap_err();
        println!("{mode} native denial: {error:?}");
        if mode == "anonymous" {
            assert!(matches!(
                error,
                Error::Native("OpenThreadToken", ERROR_CANT_OPEN_ANONYMOUS)
                    | Error::Denied("identification level")
            ));
        } else {
            assert_eq!(error, Error::Denied("message token context"));
        }
        child.finish();
        no_impersonation().unwrap();
    }
}

#[test]
fn native_stall_cancels_and_disconnect_denies() {
    let unconnected = server();
    let started = Instant::now();
    let error = unconnected
        .exchange(current(), started + Duration::from_millis(80))
        .unwrap_err();
    assert_eq!(error, Error::Deadline(ERROR_OPERATION_ABORTED));
    assert!(started.elapsed() < Duration::from_secs(2));
    println!("unconnected native cancellation: {error:?}");
    for mode in ["stall", "disconnect", "exit-after-challenge"] {
        let server = server();
        let mut child = Child::launch(mode, &server);
        if mode == "stall" {
            connect_pipe(&server.pipe, Instant::now() + LIMIT).unwrap();
        }
        let started = Instant::now();
        let limit = if mode == "stall" {
            Duration::from_millis(250)
        } else {
            LIMIT
        };
        let error = server
            .exchange(child.expected(), started + limit)
            .unwrap_err();
        println!("{mode}: {error:?}");
        assert!(started.elapsed() < LIMIT);
        if mode == "stall" {
            assert_eq!(error, Error::Deadline(ERROR_OPERATION_ABORTED));
        } else {
            assert!(matches!(
                error,
                Error::Native("ReadFile", ERROR_BROKEN_PIPE | ERROR_PIPE_NOT_CONNECTED)
                    | Error::Native("ConnectNamedPipe", ERROR_NO_DATA)
                    | Error::Native("GetNamedPipe peer PID", ERROR_PIPE_NOT_CONNECTED)
                    | Error::Denied("process exited")
            ));
        }
        child.finish();
        no_impersonation().unwrap();
    }
}

#[test]
fn native_second_instance_and_handle_noninheritance() {
    let server = server();
    let mut flags = 0;
    assert_ne!(
        unsafe { GetHandleInformation(raw(&server.pipe), &mut flags) },
        0
    );
    assert_eq!(flags & HANDLE_FLAG_INHERIT, 0);
    let handle = unsafe {
        CreateNamedPipeW(
            wide(&server.name).as_ptr(),
            PIPE_ACCESS_DUPLEX | FILE_FLAG_FIRST_PIPE_INSTANCE | FILE_FLAG_OVERLAPPED,
            PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_REJECT_REMOTE_CLIENTS,
            1,
            96,
            96,
            0,
            std::ptr::null(),
        )
    };
    assert_eq!(handle, INVALID_HANDLE_VALUE);
    let status = unsafe { GetLastError() };
    assert_eq!(status, ERROR_ACCESS_DENIED);
    println!("second server instance native denial: {status}");
    close_checked(server.pipe).unwrap();
}

#[test]
fn native_preexisting_impersonation_is_preserved() {
    std::thread::spawn(|| {
        let server = server();
        let peer = current();
        assert_ne!(unsafe { ImpersonateSelf(SecurityImpersonation) }, 0);
        let mut before = std::ptr::null_mut();
        assert_ne!(
            unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut before) },
            0
        );
        let before = owned(before).unwrap();
        let before_id = token_id(raw(&before)).unwrap();
        let before_context = TokenContext::capture(raw(&before)).unwrap();
        assert_eq!(
            no_impersonation(),
            Err(Error::Denied("preexisting impersonation"))
        );
        assert!(matches!(
            Server::create(&peer),
            Err(Error::Denied("preexisting impersonation"))
        ));
        assert!(matches!(
            Client::connect(&server.name, server.ceremony, peer, Instant::now() + LIMIT),
            Err(Error::Denied("preexisting impersonation"))
        ));
        let mut token = std::ptr::null_mut();
        assert_ne!(
            unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut token) },
            0
        );
        let token = owned(token).unwrap();
        assert_eq!(token_id(raw(&token)).unwrap(), before_id);
        assert_eq!(TokenContext::capture(raw(&token)).unwrap(), before_context);
        close_checked(token).unwrap();
        close_checked(before).unwrap();
        assert_ne!(unsafe { RevertToSelf() }, 0);
        no_impersonation().unwrap();
        close_checked(server.pipe).unwrap();
    })
    .join()
    .unwrap();
}

#[test]
fn explicit_inheritance_limited_parent_handle() {
    let server = server();
    Child::launch("inheritance", &server).finish();
    close_checked(server.pipe).unwrap();
}

#[test]
fn policy_frame_boundaries_and_single_terminal_shape() {
    let frame = Frame::new(TERMINAL, [1; 16], [2; 32], [3; 32]);
    frame
        .check(TERMINAL, &[1; 16], Some(&[2; 32]), Some(&[3; 32]))
        .unwrap();
    for index in [0, 8, 9, 10, 15, 16, 32, 64] {
        let mut altered = frame;
        altered.0[index] ^= 1;
        assert!(
            altered
                .check(TERMINAL, &[1; 16], Some(&[2; 32]), Some(&[3; 32]))
                .is_err()
        );
    }
    assert!(
        Frame::new(FINISH, [1; 16], [2; 32], [3; 32])
            .check(TERMINAL, &[1; 16], Some(&[2; 32]), Some(&[3; 32]))
            .is_err()
    );
}

#[test]
fn native_client_rejects_bad_server_challenges() {
    for mode in [
        "zero-server",
        "wrong-client",
        "wrong-ceremony",
        "reserved",
        "role",
        "oversize",
        "truncated",
    ] {
        let server = server();
        let fixture_mode = match mode {
            "oversize" => "bad-challenge-oversize",
            "truncated" => "bad-challenge-truncated",
            _ => "bad-challenge-frame",
        };
        let mut child = Child::launch(fixture_mode, &server);
        let expected = child.expected();
        let deadline = Instant::now() + LIMIT;
        connect_pipe(&server.pipe, deadline).unwrap();
        expected.bind_pipe(&server.pipe, true).unwrap();
        let hello = read_frame(&server.pipe, deadline).unwrap();
        hello.check(HELLO, &server.ceremony, None, None).unwrap();
        authenticate_message(&server.pipe, &expected).unwrap();
        let mut bytes = Frame::new(CHALLENGE, server.ceremony, [1; 32], hello.client())
            .0
            .to_vec();
        match mode {
            "zero-server" => bytes[32..64].fill(0),
            "wrong-client" => bytes[64] ^= 1,
            "wrong-ceremony" => bytes[16] ^= 1,
            "reserved" => bytes[10] = 1,
            "role" => bytes[9] = TERMINAL,
            "oversize" => bytes.push(0),
            "truncated" => {
                bytes.pop();
            }
            _ => unreachable!(),
        }
        transfer(&server.pipe, Transfer::Write(&bytes), deadline).unwrap();
        // Rejection must close the client endpoint before it sends any FINISH
        // bytes. A later timeout must not masquerade as challenge validation.
        let mut inbound = [0; FRAME_LEN];
        let after_challenge = transfer(&server.pipe, Transfer::Read(&mut inbound), deadline);
        assert!(
            matches!(
                after_challenge,
                Err(Error::Native(
                    "ReadFile",
                    ERROR_BROKEN_PIPE | ERROR_PIPE_NOT_CONNECTED
                ))
            ),
            "client sent bytes or stalled after {mode}: {after_challenge:?}"
        );
        println!("challenge {mode}: no FINISH received: {after_challenge:?}");
        child.finish();
        expected.close().unwrap();
        close_checked(server.pipe).unwrap();
        no_impersonation().unwrap();
    }
}

fn unhex(value: &str) -> Vec<u8> {
    value
        .as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
        .collect()
}
