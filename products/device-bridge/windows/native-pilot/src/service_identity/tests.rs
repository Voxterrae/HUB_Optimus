use super::*;
fn synthetic() -> (ServicePolicyCandidate, Observation) {
    let c = ServicePolicyCandidate::with_resolved_privilege((23, 0));
    let o = Observation {
        config: Config {
            kind: 16,
            start: 3,
            account: ACCOUNT.into(),
            command: r#""C:\Program Files\HUB_Relay\Personal\personal_broker_service.exe""#.into(),
            required: vec![],
            other: (0, 0, String::new(), vec![], String::new()),
        },
        state: 4,
        pid: 42,
        process: ProcessFacts {
            pid: 42,
            creation: 100,
            token_id: (7, 0),
            user: vec![1],
            session: 0,
            restricted: false,
            privileges: vec![(23, 0, 3)],
            image: r"C:\Program Files\HUB_Relay\Personal\personal_broker_service.exe".into(),
        },
    };
    (c, o)
}
#[test]
fn synthetic_full_agreement_is_policy_only() {
    let (c, o) = synthetic();
    assert_eq!(policy(&c, &[1], &[2], &o, None), Ok(()));
    assert_eq!(policy(&c, &[1], &[2], &o, Some(&o)), Ok(()));
}
#[test]
fn wrong_configuration_denies() {
    let (c, o) = synthetic();
    let mut cases = vec![];
    let mut x = o.clone();
    x.config.kind = 32;
    cases.push(x);
    let mut x = o.clone();
    x.config.kind |= 256;
    cases.push(x);
    let mut x = o.clone();
    x.config.start = 2;
    cases.push(x);
    let mut x = o.clone();
    x.config.account = "LocalSystem".into();
    cases.push(x);
    let mut x = o.clone();
    x.config.command = c.image.clone();
    cases.push(x);
    let mut x = o.clone();
    x.config.required.push("SeChangeNotifyPrivilege".into());
    cases.push(x);
    for x in cases {
        assert!(policy(&c, &[1], &[2], &x, None).is_err());
    }
}
#[test]
fn stale_pending_stopped_and_changed_capture_deny() {
    let (c, o) = synthetic();
    for state in [1, 2, 3, 5, 6, 7] {
        let mut x = o.clone();
        x.state = state;
        assert!(policy(&c, &[1], &[2], &x, None).is_err());
    }
    for pid in [0, 43] {
        let mut x = o.clone();
        x.pid = pid;
        assert!(policy(&c, &[1], &[2], &x, None).is_err());
    }
    let mut x = o.clone();
    x.process.creation += 1;
    assert!(policy(&c, &[1], &[2], &x, Some(&o)).is_err());
    let mut x = o.clone();
    x.process.token_id.0 += 1;
    assert!(policy(&c, &[1], &[2], &x, Some(&o)).is_err());
    let mut x = o.clone();
    x.config.command.push(' ');
    assert!(policy(&c, &[1], &[2], &x, Some(&o)).is_err());
}
#[test]
fn actual_user_distinctness_restrictions_session_and_image_deny() {
    let (c, o) = synthetic();
    assert!(policy(&c, &[1], &[1], &o, None).is_err());
    let mut x = o.clone();
    x.process.user = vec![3];
    assert!(policy(&c, &[1], &[2], &x, None).is_err()); // group membership cannot supply TokenUser
    let mut x = o.clone();
    x.process.session = 1;
    assert!(policy(&c, &[1], &[2], &x, None).is_err());
    let mut x = o.clone();
    x.process.restricted = true;
    assert!(policy(&c, &[1], &[2], &x, None).is_err());
    let mut x = o.clone();
    x.process.image.push('x');
    assert!(policy(&c, &[1], &[2], &x, None).is_err());
}
#[test]
fn exact_privilege_inventory_including_used_for_access_denies_drift() {
    let (c, o) = synthetic();
    for attributes in [0, 1, 2, 0x80000003] {
        let mut x = o.clone();
        x.process.privileges[0].2 = attributes;
        assert!(policy(&c, &[1], &[2], &x, None).is_err());
    }
    for attributes in [0, 2] {
        let mut x = o.clone();
        x.process.privileges.push((99, 0, attributes));
        assert!(policy(&c, &[1], &[2], &x, None).is_err());
    }
    let mut x = o.clone();
    x.process.privileges.clear();
    assert!(policy(&c, &[1], &[2], &x, None).is_err());
}

#[test]
fn bounded_utf16_and_multi_sz_parse_only_valid_interior_data() {
    let b = [9u8, 9, 9, 9, 65, 0, 0, 0, 66, 0, 0, 0, 0, 0];
    assert_eq!(
        parse_strings(&[0; 8], 100, 104, 4, true, false).unwrap(),
        Vec::<String>::new()
    );
    assert_eq!(
        parse_strings(&b, 100, 104, 4, false, false).unwrap(),
        vec!["A"]
    );
    assert_eq!(
        parse_strings(&b, 100, 104, 4, true, false).unwrap(),
        vec!["A", "B"]
    );
    for pointer in [0, 99, 100, 102, 103, 105, 114, usize::MAX] {
        assert!(parse_strings(&b, 100, pointer, 4, true, false).is_err());
    }
    assert!(parse_strings(&b[..13], 100, 104, 4, true, false).is_err());
    assert!(parse_strings(&[0, 0, 0, 0, 0, 0xd8, 0, 0], 100, 104, 4, false, false).is_err());
    assert!(parse_strings(&[0, 0, 0, 0, 0, 0], 100, 104, 4, true, false).is_err());
    assert!(parse_strings(&[0; 8193], 100, 104, 4, false, false).is_err());
}
#[test]
fn config_allocation_excludes_rounding_padding_and_invalid_sizes() {
    for length in [0, 7, 8193, usize::MAX] {
        assert!(ConfigBuffer::allocate(length, 8).is_err());
    }
    let mut b = ConfigBuffer::allocate(11, 8).unwrap();
    let base = b.data.as_ptr() as usize;
    let bytes = unsafe {
        std::slice::from_raw_parts_mut(
            b.data.as_mut_ptr().cast::<u8>(),
            size_of_val(b.data.as_slice()),
        )
    };
    bytes[8..12].copy_from_slice(&[65, 0, 0, 0]);
    assert!(b.text((base + 8) as *const u16, 8, false, false).is_err());
    assert!(ConfigBuffer::allocate(8192, 8).is_ok());
}
#[test]
fn primary_and_all_cleanup_errors_are_preserved() {
    let result: Result<()> = finish(
        finish(Err(denial("primary")), Err(denial("token"))),
        finish(Err(denial("service")), Err(denial("manager"))),
    );
    let e = result.unwrap_err();
    assert_eq!(e.primary, Failure::Denied("primary"));
    assert_eq!(
        e.cleanup,
        vec![
            Failure::Denied("token"),
            Failure::Denied("service"),
            Failure::Denied("manager")
        ]
    );
    assert_eq!(
        finish(Ok(()), Err(denial("close"))).unwrap_err().primary,
        Failure::Denied("close")
    );
}
fn current() -> ExpectedPeer {
    let h = unsafe {
        OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
            0,
            GetCurrentProcessId(),
        )
    };
    assert!(!h.is_null());
    ExpectedPeer::from_owned(unsafe { OwnedHandle::from_raw_handle(h) }).unwrap()
}
#[test]
fn native_local_connect_and_fixed_absent_service_exact_1060() {
    let manager = ScHandle::manager().unwrap();
    let result = match manager.personal() {
        Ok(service) => {
            service.close().unwrap();
            panic!("fixed personal service unexpectedly exists; fixture never mutates it")
        }
        Err(e) => e,
    };
    assert_eq!(
        result.primary,
        Failure::Native("OpenServiceW personal", ERROR_SERVICE_DOES_NOT_EXIST)
    );
    manager.close().unwrap();
    let transport = current();
    let result =
        HeldScmProcessBinding::capture(ServicePolicyCandidate::personal().unwrap(), &transport);
    let error = match result {
        Ok(binding) => {
            binding.close().unwrap();
            panic!("unexpected personal binding")
        }
        Err(e) => e,
    };
    assert_eq!(
        error.primary,
        Failure::Native("OpenServiceW personal", ERROR_SERVICE_DOES_NOT_EXIST)
    );
    assert!(error.cleanup.is_empty());
    transport.close().unwrap();
}
#[test]
fn native_held_current_primary_process_recheck_and_noninheritability() {
    let peer = current();
    let facts = process_facts(&peer).unwrap();
    assert_eq!(facts.pid, unsafe { GetCurrentProcessId() });
    assert!(!facts.user.is_empty());
    assert!(!facts.image.is_empty());
    let mut flags = 0;
    assert_ne!(
        unsafe { GetHandleInformation(peer.process_handle(), &mut flags) },
        0
    );
    assert_eq!(flags & HANDLE_FLAG_INHERIT, 0);
    peer.recheck().unwrap();
    peer.close().unwrap();
}
struct Child(std::process::Child);
impl Child {
    fn launch() -> Self {
        use std::os::windows::process::CommandExt;
        Self(
            std::process::Command::new(std::env::current_exe().unwrap())
                .args([
                    "--ignored",
                    "--exact",
                    "service_identity::tests::native_child_entry",
                    "--test-threads=1",
                ])
                .creation_flags(CREATE_NO_WINDOW)
                .stdin(std::process::Stdio::null())
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .spawn()
                .unwrap(),
        )
    }
    fn peer(&self) -> ExpectedPeer {
        let h = unsafe {
            OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE,
                0,
                self.0.id(),
            )
        };
        assert!(!h.is_null());
        ExpectedPeer::from_owned(unsafe { OwnedHandle::from_raw_handle(h) }).unwrap()
    }
    fn stop(&mut self) {
        self.0.kill().unwrap();
        self.0.wait().unwrap();
    }
}
impl Drop for Child {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}
#[test]
#[ignore = "owned child helper; never counted as a security pass"]
fn native_child_entry() {
    std::thread::sleep(std::time::Duration::from_secs(30));
}
#[test]
fn native_same_user_child_denies_even_if_expected_user_matches() {
    let transport = current();
    let mut child = Child::launch();
    let peer = child.peer();
    assert_eq!(peer.user(), transport.user());
    // Native measured user equality cannot satisfy distinct virtual-principal
    // policy even under the synthetic most-permissive expected-user equality.
    let (candidate, mut observation) = synthetic();
    // Only measured TokenUser is inserted; every other policy field is the
    // accepting synthetic control, isolating the same-user rejection.
    observation.process.user = peer.user().to_vec();
    assert_eq!(
        policy(
            &candidate,
            peer.user(),
            transport.user(),
            &observation,
            None
        ),
        Err("service primary principal")
    );
    peer.close().unwrap();
    transport.close().unwrap();
    child.stop();
}
#[test]
fn native_exited_retained_child_denies() {
    let mut child = Child::launch();
    let peer = child.peer();
    peer.recheck().unwrap();
    child.stop();
    assert_eq!(
        peer.recheck(),
        Err(bootstrap_peer::Error::Denied("process exited"))
    );
    peer.close().unwrap();
}
#[test]
fn native_preexisting_impersonation_is_preserved() {
    std::thread::spawn(|| {
        let transport = current();
        let candidate = ServicePolicyCandidate::personal().unwrap();
        assert_ne!(unsafe { ImpersonateSelf(SecurityIdentification) }, 0);
        struct Restore;
        impl Drop for Restore {
            fn drop(&mut self) {
                assert_ne!(unsafe { RevertToSelf() }, 0);
            }
        }
        let _restore = Restore;
        let snapshot = || {
            let mut h = null_mut();
            assert_ne!(
                unsafe { OpenThreadToken(GetCurrentThread(), TOKEN_QUERY, 1, &mut h) },
                0
            );
            let mut s: TOKEN_STATISTICS = unsafe { std::mem::zeroed() };
            let mut n = 0;
            assert_ne!(
                unsafe {
                    GetTokenInformation(
                        h,
                        TokenStatistics,
                        (&mut s as *mut TOKEN_STATISTICS).cast(),
                        size_of::<TOKEN_STATISTICS>() as u32,
                        &mut n,
                    )
                },
                0
            );
            assert_ne!(unsafe { CloseHandle(h) }, 0);
            (s.TokenId.LowPart, s.TokenId.HighPart)
        };
        let before = snapshot();
        let error = match HeldScmProcessBinding::capture(candidate, &transport) {
            Err(e) => e,
            Ok(b) => {
                b.close().unwrap();
                panic!("impersonation accepted")
            }
        };
        assert_eq!(
            error.primary,
            Failure::Peer(bootstrap_peer::Error::Denied("preexisting impersonation"))
        );
        assert_eq!(snapshot(), before);
        transport.close().unwrap();
    })
    .join()
    .unwrap();
}
