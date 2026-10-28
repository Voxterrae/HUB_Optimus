use super::*;
use crate::relative_ntfs::tests::Fixture;
use std::panic::{AssertUnwindSafe, catch_unwind};

// Independent synthetic layout/SID literals. These cases test composition, not
// native ownership, traversal, volume approval or service isolation.
const SYNTHETIC_SYSTEM: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0];
const SYNTHETIC_EVERYONE: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0];

fn synthetic_snapshot(owner: &[u8], kind: u8, mask: u32) -> OwnerDaclSnapshot {
    let dacl = 20 + owner.len();
    let mut bytes = vec![1, 0, 4, 128]; // revision 1, DACL present, self-relative
    bytes.extend(20u32.to_le_bytes());
    bytes.extend([0; 8]); // absent group and SACL
    bytes.extend((dacl as u32).to_le_bytes());
    bytes.extend(owner);
    bytes.extend([2, 0, 28, 0, 1, 0, 0, 0]); // one ordinary 20-byte ACE
    bytes.extend([kind, 0, 20, 0]);
    bytes.extend(mask.to_le_bytes());
    bytes.extend(SYNTHETIC_EVERYONE);
    OwnerDaclSnapshot::fixture_snapshot(&bytes).unwrap()
}
fn safe_snapshot() -> OwnerDaclSnapshot {
    synthetic_snapshot(SYNTHETIC_SYSTEM, 0, 0x0012_00ad)
}
fn invalid_snapshots() -> Vec<OwnerDaclSnapshot> {
    vec![
        OwnerDaclSnapshot::fixture_snapshot(&[0; 20]).unwrap(),
        synthetic_snapshot(SYNTHETIC_EVERYONE, 0, 0x0012_00ad),
        synthetic_snapshot(SYNTHETIC_SYSTEM, 0, 0x0012_00af),
        synthetic_snapshot(SYNTHETIC_SYSTEM, 5, 0x0012_00ad),
    ]
}

#[test]
fn policy_mode_accepts_valid_capture_and_stable_snapshot() {
    let safe = safe_snapshot();
    SnapshotMode::ProgramFilesOsPolicy
        .check_snapshot(&safe, None)
        .unwrap();
    SnapshotMode::ProgramFilesOsPolicy
        .check_snapshot(&safe, Some(&safe))
        .unwrap();
}
#[test]
fn policy_mode_refuses_stable_invalid_snapshots_before_equality() {
    for (case, invalid) in invalid_snapshots().iter().enumerate() {
        for previous in [None, Some(invalid)] {
            let result = SnapshotMode::ProgramFilesOsPolicy.check_snapshot(invalid, previous);
            assert!(
                matches!(
                    result,
                    Err(Error {
                        primary: Failure::Security(_),
                        ..
                    })
                ),
                "policy mode must refuse invalid snapshot case={case} during capture or stable recheck: {result:?}"
            );
        }
    }
}
#[test]
fn observation_mode_retains_opaque_stable_invalid_snapshots() {
    for invalid in invalid_snapshots() {
        SnapshotMode::ObservationOnly
            .check_snapshot(&invalid, None)
            .unwrap();
        SnapshotMode::ObservationOnly
            .check_snapshot(&invalid, Some(&invalid))
            .unwrap();
    }
}
#[test]
fn policy_mode_rejects_safe_to_safe_drift_and_keeps_policy_failure_primary() {
    let safe = safe_snapshot();
    let other_safe = synthetic_snapshot(SYNTHETIC_SYSTEM, 0, 0x0012_00a9);
    for mode in [
        SnapshotMode::ObservationOnly,
        SnapshotMode::ProgramFilesOsPolicy,
    ] {
        assert!(matches!(
            mode.check_snapshot(&other_safe, Some(&safe)),
            Err(Error {
                primary: Failure::Denied("owner/DACL bytes changed"),
                ..
            })
        ));
    }
    let invalid = synthetic_snapshot(SYNTHETIC_SYSTEM, 0, 2);
    let result = SnapshotMode::ProgramFilesOsPolicy.check_snapshot(&invalid, Some(&safe));
    assert!(
        matches!(
            result,
            Err(Error {
                primary: Failure::Security(_),
                ..
            })
        ),
        "current policy failure must precede descriptor drift: {result:?}"
    );
}
#[test]
fn policy_mode_checks_root_intermediate_anchor_and_preserves_original_index() {
    let safe = safe_snapshot();
    let invalid = synthetic_snapshot(SYNTHETIC_SYSTEM, 0, 2);
    // The shared production indexed loop is exercised as the retained prefix
    // grows root -> intermediate -> anchor. It does not emulate filesystem opens.
    for count in 1..=3 {
        let mut visited = vec![];
        check_indexed_steps(count, |index| {
            visited.push(index);
            SnapshotMode::ProgramFilesOsPolicy.check_snapshot(&safe, Some(&safe))
        })
        .unwrap();
        assert_eq!(visited, (0..count).collect::<Vec<_>>());
        for failed_at in 0..count {
            let mut visited = vec![];
            let result = check_indexed_steps(count, |index| {
                visited.push(index);
                let current = if index == failed_at { &invalid } else { &safe };
                SnapshotMode::ProgramFilesOsPolicy.check_snapshot(current, Some(current))
            });
            assert!(
                matches!(
                    result,
                    Err(Error { step: Some(index), primary: Failure::Security(_), .. }) if index == failed_at
                ),
                "retained prefix={count}; failure={failed_at}; result={result:?}"
            );
            assert_eq!(visited, (0..=failed_at).collect::<Vec<_>>());
        }
    }
}
#[test]
fn policy_security_primary_and_reverse_cleanup_failures_survive() {
    let invalid = synthetic_snapshot(SYNTHETIC_EVERYONE, 0, 0x0012_00ad);
    let result = finish(
        SnapshotMode::ProgramFilesOsPolicy
            .check_snapshot(&invalid, None)
            .map_err(|e| e.at_step(2)),
        finish(
            Err(error(Failure::Native("leaf CloseHandle", 6))),
            Err(error(Failure::Native("root CloseHandle", 5))),
        ),
    );
    let error = result.unwrap_err();
    assert_eq!(error.step, Some(2));
    assert!(matches!(error.primary, Failure::Security(_)));
    assert!(error.has_cleanup_failure());
    assert!(matches!(
        error.cleanup.as_slice(),
        [
            Failure::Native("leaf CloseHandle", 6),
            Failure::Native("root CloseHandle", 5)
        ]
    ));
}

fn policy_refusal(result: Result<()>, expected_step: usize) -> Result<()> {
    match result {
        Err(e)
            if e.step == Some(expected_step)
                && matches!(&e.primary, Failure::Security(_))
                && !e.has_cleanup_failure() =>
        {
            println!(
                "OWNED_POLICY_FIXTURE REFUSED step={expected_step}; checked cleanup; no positive OS evidence"
            );
            Ok(())
        }
        Err(e) => Err(e),
        Ok(()) => Err(denied("untrusted fixture unexpectedly matched OS policy")),
    }
}

#[test]
fn native_policy_capture_refuses_user_owned_fixture_with_checked_cleanup() {
    case(|f| {
        let leaf = f.os_child(0, "Anchor")?;
        let sentinel = f.sentinel(leaf, "unchanged", 0x58)?;
        let legacy = ObservedAncestorChain::fixture(f.input(0)?, &["Anchor"])?;
        let precondition = if legacy.steps.iter().all(|step| {
            step.mode == SnapshotMode::ObservationOnly
                && step.security.matches_os_ancestor_policy().is_err()
        }) {
            legacy.recheck()
        } else {
            Err(denied("fixture must remain untrusted and observation-only"))
        };
        finish(precondition, legacy.close())?;

        let attempted = match ObservedAncestorChain::fixture_with_mode(
            f.input(0)?,
            &["Anchor"],
            SnapshotMode::ProgramFilesOsPolicy,
        ) {
            Ok(chain) => finish(
                Err(denied("unexpected policy fixture acceptance")),
                chain.close(),
            ),
            Err(e) => Err(e),
        };
        f.verify_sentinel(sentinel)?;
        policy_refusal(attempted, 0)
    });
}

#[test]
fn native_policy_child_failure_closes_child_and_retained_observation_ancestors() {
    case(|f| {
        let middle = f.os_child(0, "Middle")?;
        let leaf = f.os_child(middle, "Anchor")?;
        let sentinel = f.sentinel(leaf, "unchanged", 0x59)?;
        // These ancestors deliberately retain legacy observation mode; native
        // user ownership cannot manufacture a positive policy chain fixture.
        let chain = ObservedAncestorChain::fixture(f.input(0)?, &["Middle"])?;
        let attempted = (|| {
            let parent = chain.steps.last().unwrap();
            let name = OsPathComponent::new(&utf16("Anchor"))?;
            let expected = parent.path.append(&name)?;
            let child = parent.directory.child(&name)?;
            match RetainedStep::capture(child, expected, SnapshotMode::ProgramFilesOsPolicy)
                .map_err(|e| e.at_step(2))
            {
                Err(e) => Err(e),
                Ok(step) => finish(
                    Err(denied("unexpected policy child acceptance")),
                    step.directory.close().map_err(Error::from),
                ),
            }
        })();
        let checked = finish(attempted, chain.close());
        f.verify_sentinel(sentinel)?;
        policy_refusal(checked, 2)
    });
}

#[test]
fn native_fixed_program_files_os_policy_diagnostic_labels_acceptance_or_refusal() {
    let acquire: fn() -> Result<ObservedAncestorChain> =
        ObservedAncestorChain::observe_program_files_os_policy;
    match acquire() {
        Ok(chain) => {
            let count = chain.steps.len();
            let outcome = catch_unwind(AssertUnwindSafe(|| {
                let source = chain.source.as_ref().expect("fixed known-folder source");
                assert_eq!(source.anchor, PersonalAnchor::ProgramFiles);
                assert_eq!(count, source.path.components.len() + 1);
                assert!(
                    chain
                        .steps
                        .iter()
                        .all(|step| { step.mode == SnapshotMode::ProgramFilesOsPolicy })
                );
                chain.recheck()
            }));
            let closed = chain.close();
            assert!(closed.is_ok(), "policy diagnostic close failed: {closed:?}");
            match outcome {
                Ok(result) => result.unwrap(),
                Err(panic) => std::panic::resume_unwind(panic),
            }
            println!(
                "REAL_PROGRAM_FILES_OS_POLICY DIAGNOSTIC_ACCEPTED steps={count}; no approved volume/bootstrap/root/service authority"
            );
        }
        Err(e) => {
            assert!(
                !e.has_cleanup_failure(),
                "policy diagnostic cleanup failed: {e:?}"
            );
            println!(
                "REAL_PROGRAM_FILES_OS_POLICY DIAGNOSTIC_REFUSED {e:?}; not acceptance or operational readiness"
            );
        }
    }
}

#[test]
fn native_owned_multilevel_space_unicode_chain() {
    let mut fixture = Fixture::ancestor().expect("exclusive owned ancestor fixture");
    let outcome = catch_unwind(AssertUnwindSafe(|| {
        let first = fixture.os_child(0, "Program Files").unwrap();
        let leaf = fixture
            .os_child(first, "Donn\u{e9}es \u{6771}\u{4eac}")
            .unwrap();
        let sentinel = fixture.sentinel(leaf, "sentinel", 0x51).unwrap();
        let observed = ObservedAncestorChain::fixture(
            fixture.input(0).unwrap(),
            &["Program Files", "Donn\u{e9}es \u{6771}\u{4eac}"],
        );
        let result = match observed {
            Ok(chain) => {
                let checked = (|| {
                    assert_eq!(chain.steps.len(), 3);
                    for step in &chain.steps {
                        step.directory.exact_rights_live()?;
                    }
                    chain.recheck()
                })();
                finish(checked, chain.close())
            }
            Err(error) => Err(error),
        };
        fixture.verify_sentinel(sentinel).unwrap();
        result
    }));
    let cleanup = fixture.cleanup();
    assert!(cleanup.is_ok(), "fixture cleanup failed: {cleanup:?}");
    assert!(
        matches!(outcome, Ok(Ok(()))),
        "owned multilevel ancestor chain must be observed: {outcome:?}"
    );
}

fn case(test: impl FnOnce(&mut Fixture) -> Result<()>) {
    let mut fixture = Fixture::ancestor().expect("exclusive owned ancestor fixture");
    let outcome = catch_unwind(AssertUnwindSafe(|| test(&mut fixture)));
    let cleanup = fixture.cleanup();
    assert!(
        cleanup.is_ok(),
        "operation={outcome:?}; cleanup={cleanup:?}"
    );
    assert!(matches!(outcome, Ok(Ok(()))), "operation={outcome:?}");
}
fn refused(result: Result<ObservedAncestorChain>, wanted: &str) -> Result<()> {
    match result {
        Ok(chain) => finish(Err(denied("unexpected chain acceptance")), chain.close()),
        Err(error) => {
            println!("ANCESTOR_REFUSAL expected={wanted} {error:?}");
            if !error.has_cleanup_failure()
                && matches!(&error.primary, Failure::Relative(e) if crate::relative_ntfs::tests::expected_refusal(e, wanted))
            {
                Ok(())
            } else {
                Err(error)
            }
        }
    }
}
#[test]
fn native_missing_component_and_static_stepped_leaf_junctions() {
    case(|f| {
        let parent = f.os_child(0, "Middle")?;
        let leaf = f.os_child(parent, "Leaf")?;
        let target = f.os_child(0, "OwnedTarget")?;
        let sentinel = f.sentinel(target, "outside", 0x37)?;
        refused(
            ObservedAncestorChain::fixture(f.input(0)?, &["Absent"]),
            "missing",
        )?;
        f.junction(leaf, target)?;
        refused(
            ObservedAncestorChain::fixture(f.input(0)?, &["Middle", "Leaf"]),
            "reparse",
        )?;
        refused(
            ObservedAncestorChain::fixture(f.input(0)?, &["Middle", "Leaf", "Absent"]),
            "reparse",
        )?;
        f.verify_sentinel(sentinel)?;
        Ok(())
    });
}
#[test]
fn native_retained_same_id_dacl_drift() {
    case(|f| {
        let leaf = f.os_child(0, "Leaf")?;
        let chain = ObservedAncestorChain::fixture(f.input(0)?, &["Leaf"])?;
        let result = (|| {
            f.set_dacl(leaf, "D:P(D;;0x2;;;WD)(A;ID;FA;;;WD)(A;;FA;;;SY)")?;
            match chain.recheck() {
                Err(e)
                    if !e.has_cleanup_failure()
                        && matches!(e.primary, Failure::Denied("owner/DACL bytes changed")) =>
                {
                    Ok(())
                }
                other => {
                    println!("DACL_DRIFT unexpected={other:?}");
                    Err(denied("same-ID DACL drift not identified"))
                }
            }
        })();
        finish(result, chain.close())
    });
}
#[test]
fn native_ordered_denied_inherited_chain_is_observation_only() {
    case(|f| {
        let sentinel = f.sentinel(0, "outside", 0x64)?;
        let parent = f.os_child(0, "Inheritance parent")?;
        f.set_dacl(
            parent,
            "D:P(D;OICI;0x2;;;WD)(A;OICI;FA;;;WD)(A;OICI;FA;;;SY)",
        )?;
        f.os_child(parent, "Opaque ACL")?;
        let chain =
            ObservedAncestorChain::fixture(f.input(0)?, &["Inheritance parent", "Opaque ACL"])?;
        let observed = catch_unwind(AssertUnwindSafe(|| {
            let headers = chain.steps.last().unwrap().security.fixture_ace_headers();
            println!("ANCESTOR_NATIVE ordered ACE headers={headers:?}");
            assert_eq!(
                headers.iter().map(|&(kind, _)| kind).collect::<Vec<_>>(),
                vec![1, 0, 0],
                "native deny then allow order"
            );
            assert!(
                headers.iter().all(|&(_, flags)| flags & 0x10 != 0),
                "native inherited precondition"
            );
            chain.recheck()
        }));
        let closed = chain.close();
        let unchanged = f.verify_sentinel(sentinel);
        assert!(
            closed.is_ok(),
            "operation={observed:?}; chain close={closed:?}; sentinel={unchanged:?}"
        );
        unchanged?;
        match observed {
            Ok(result) => result,
            Err(panic) => std::panic::resume_unwind(panic),
        }
    });
}
#[test]
fn native_read_control_denial_is_not_absence_or_acceptance() {
    case(|f| {
        let leaf = f.os_child(0, "Denied")?;
        // OWNER RIGHTS removes the implicit owner's READ_CONTROL grant here.
        f.set_dacl(leaf, "D:P(D;;RC;;;OW)(D;;RC;;;WD)(A;;FA;;;WD)(A;;FA;;;SY)")?;
        refused(
            ObservedAncestorChain::fixture(f.input(0)?, &["Denied"]),
            "access",
        )
    });
}
#[test]
fn native_fixed_resolver_and_labelled_real_chain_outcomes() {
    for anchor in [PersonalAnchor::ProgramData, PersonalAnchor::ProgramFiles] {
        // Resolver acceptance is separate from chain acceptance. No raw path output.
        let resolved = ResolvedAnchor::resolve(anchor).expect("fixed known-folder resolver");
        assert!(!resolved.path.components.is_empty());
        resolved.recheck().unwrap();
        match ObservedAncestorChain::observe(anchor) {
            Ok(chain) => {
                let count = chain.steps.len();
                let checked = finish(chain.recheck(), chain.close());
                checked.unwrap();
                println!("REAL_CHAIN anchor={anchor:?} OBSERVED steps={count}; no authority");
            }
            Err(e) => {
                assert!(
                    !e.has_cleanup_failure(),
                    "real-chain cleanup failure: {e:?}"
                );
                println!("REAL_CHAIN anchor={anchor:?} REFUSED {e:?}; not acceptance");
            }
        }
    }
}
#[test]
fn native_impersonation_refuses_without_clearing_token() {
    std::thread::spawn(|| {
        use windows_sys::Win32::Security::{ImpersonateSelf, RevertToSelf, SecurityIdentification};
        if unsafe { ImpersonateSelf(SecurityIdentification) } == 0 {
            panic!("impersonation fixture precondition");
        }
        let before = crate::relative_ntfs::tests::thread_token_id();
        let result = ResolvedAnchor::resolve(PersonalAnchor::ProgramData);
        let policy_result: Result<()> =
            match ObservedAncestorChain::observe_program_files_os_policy() {
                Ok(chain) => finish(
                    Err(denied("policy route accepted impersonation")),
                    chain.close(),
                ),
                Err(e) => Err(e),
            };
        let after = crate::relative_ntfs::tests::thread_token_id();
        if unsafe { RevertToSelf() } == 0 {
            std::process::abort();
        }
        assert!(before.is_ok() && after.is_ok());
        assert_eq!(before.unwrap(), after.unwrap());
        assert!(matches!(
            result,
            Err(Error {
                primary: Failure::Relative(ref e),
                ..
            }) if crate::relative_ntfs::tests::expected_refusal(e, "impersonation")
        ));
        assert!(matches!(
            policy_result,
            Err(Error {
                primary: Failure::Relative(ref e),
                ..
            }) if crate::relative_ntfs::tests::expected_refusal(e, "impersonation")
        ));
    })
    .join()
    .unwrap();
}
fn utf16(s: &str) -> Vec<u16> {
    s.encode_utf16().collect()
}
#[test]
fn drive_path_preserves_spaces_unicode_and_rejects_namespace_repairs() {
    let original = utf16("C:\\Program Files\\Donn\u{e9}es \u{6771}\u{4eac}");
    let path = parse_drive_path(&original).unwrap();
    assert_eq!(path.original, original);
    assert_eq!(path.components.len(), 2);
    for bad in [
        r"\\server\share",
        r"\\?\C:\Path",
        r"\??\C:\Path",
        r"C:relative",
        r"C:/Path",
        r"C:\A\\B",
        r"C:\A\",
        r"C:\..\A",
        r"C:\A.",
        r"C:\A ",
        r"C:\A:stream",
        "C:\\A\0B",
        r"C:\PROGRA~1",
    ] {
        assert!(parse_drive_path(&utf16(bad)).is_err(), "accepted {bad:?}");
    }
    assert!(parse_drive_path(&[67, 58, 92, 0xd800]).is_err());
}
#[test]
fn os_component_bounds_reserved_superscripts_and_surrogates() {
    for name in [
        "CON",
        "nul.txt",
        "LPT9",
        "com\u{b9}",
        "LPT\u{b2}.txt",
        "COM\u{b3}",
        "A~B",
        "A/B",
        "A\\B",
        "A\0B",
        "A\u{1f}",
        ".",
        "..",
        "tail.",
        "tail ",
    ] {
        assert!(
            OsPathComponent::new(&utf16(name)).is_err(),
            "accepted {name}"
        );
    }
    for name in [
        "Program Files",
        "Donn\u{e9}es",
        "\u{1f331}",
        "COM0",
        "LPT10",
    ] {
        assert_eq!(
            OsPathComponent::new(&utf16(name)).unwrap().units(),
            utf16(name)
        );
    }
    assert!(OsPathComponent::new(&vec![65; 255]).is_ok());
    assert!(OsPathComponent::new(&vec![65; 256]).is_err());
    assert!(OsPathComponent::new(&[]).is_err());
    assert!(OsPathComponent::new(&[0xdc00]).is_err());
    let within = format!("C:\\{}", vec!["A"; 127].join("\\"));
    assert!(parse_drive_path(&utf16(&within)).is_ok());
    let beyond = format!("{within}\\A");
    assert!(parse_drive_path(&utf16(&beyond)).is_err());
    assert!(parse_drive_path(&vec![65; MAX_PATH_UNITS + 1]).is_err());
}
const GUID_ROOT: &str = r"\\?\Volume{12345678-1234-1234-1234-123456789abc}\";
#[test]
fn full_guid_sequence_rejects_prefix_alias_and_comparison_failure() {
    let expected = GuidPath::parse(&utf16(&format!("{GUID_ROOT}Program Files\\Leaf"))).unwrap();
    let lower = GuidPath::parse(&utf16(&format!("{GUID_ROOT}program files\\leaf"))).unwrap();
    expected.agrees(&lower).unwrap();
    for suffix in [
        "Program Files",
        "Program Files\\Leaf\\More",
        "Program FilesX\\Leaf",
        "Elsewhere\\Leaf",
    ] {
        let different = GuidPath::parse(&utf16(&format!("{GUID_ROOT}{suffix}"))).unwrap();
        assert!(expected.agrees(&different).is_err());
    }
    let failure = expected.agrees_using(&expected, |_, _| {
        Err(error(Failure::Native("CompareStringOrdinal", 87)))
    });
    assert!(matches!(
        failure,
        Err(Error {
            primary: Failure::Native("CompareStringOrdinal", 87),
            ..
        })
    ));
    assert!(GuidPath::parse(&utf16(r"\\?\Volume{bad}\A")).is_err());
    assert!(GuidPath::parse(&utf16(&format!("{GUID_ROOT}A\\"))).is_err());
}
#[test]
fn resolver_com_and_allocation_accounting_preserves_failure() {
    use std::cell::Cell;
    for status in [0, 1] {
        let calls = Cell::new(0);
        let freed = Cell::new(0);
        let result: Result<()> = initialized_com(
            status,
            || {
                allocated_path(
                    0x80004005u32 as i32,
                    || panic!("failed known-folder result must never be copied"),
                    || freed.set(freed.get() + 1),
                )
            },
            || calls.set(calls.get() + 1),
        );
        assert!(matches!(
            result,
            Err(Error {
                primary: Failure::Native("SHGetKnownFolderPath", 0x80004005),
                ..
            })
        ));
        assert_eq!((calls.get(), freed.get()), (1, 1));
    }
    let calls = Cell::new(0);
    let result: Result<()> = initialized_com(
        0x80010106u32 as i32,
        || panic!("changed mode cannot resolve"),
        || calls.set(calls.get() + 1),
    );
    assert!(result.is_err());
    assert_eq!(calls.get(), 0);
    let freed = Cell::new(0);
    let copied = allocated_path(0, || Ok(vec![65u16]), || freed.set(1)).unwrap();
    assert_eq!(copied, vec![65]);
    assert_eq!(freed.get(), 1);
    let result: Result<()> =
        allocated_path(0, || Err(denied("malformed copied path")), || freed.set(2));
    assert!(result.is_err());
    assert_eq!(freed.get(), 2);
}
#[test]
fn primary_and_all_reverse_cleanup_failures_survive() {
    let result: Result<()> = finish(
        Err(denied("primary")),
        finish(Err(denied("leaf close")), Err(denied("root close"))),
    );
    let error = result.unwrap_err();
    assert!(matches!(error.primary, Failure::Denied("primary")));
    assert!(matches!(
        error.cleanup.as_slice(),
        [Failure::Denied("leaf close"), Failure::Denied("root close")]
    ));
}
#[test]
fn fixture_parent_is_exact_task_and_versioned_run() {
    use crate::relative_ntfs::tests::guarded_parent;
    use std::path::Path;
    let work = Path::new(r"C:\owned\work");
    for path in [
        r"20261027-hub-relay-ancestor-chain\runs\ancestor-v001\ancestor-fixtures",
        r"20261027-hub-relay-ancestor-chain\runs\red-v1234\ancestor-fixtures",
    ] {
        assert!(guarded_parent(&work.join(path), work, "ancestor-fixtures"));
    }
    for path in [
        r"elsewhere\runs\ancestor-v001\ancestor-fixtures",
        r"20261027-hub-relay-ancestor-chain\runs\no-version\ancestor-fixtures",
        r"20261027-hub-relay-ancestor-chain\runs\a-v001\ancestor-fixtures\child",
        r"20261027-hub-relay-ancestor-chain\runs\a-v001\ntfs-fixtures",
    ] {
        assert!(!guarded_parent(&work.join(path), work, "ancestor-fixtures"));
    }
}

#[test]
fn native_retained_empty_ancestor_conversion_is_refused() {
    case(|f| {
        let leaf = f.os_child(0, "Empty")?;
        let target = f.os_child(0, "Target")?;
        f.prepare_junction(leaf)?;
        let chain = ObservedAncestorChain::fixture(f.input(0)?, &["Empty"])?;
        let result = (|| {
            f.junction(leaf, target)?;
            match chain.recheck() {
                Err(e)
                    if !e.has_cleanup_failure()
                        && matches!(&e.primary, Failure::Relative(r) if crate::relative_ntfs::tests::expected_refusal(r, "reparse")) =>
                {
                    Ok(())
                }
                other => {
                    println!("RETAINED_REPARSE unexpected={other:?}");
                    Err(denied("retained ancestor tag drift not identified"))
                }
            }
        })();
        finish(result, chain.close())
    });
}
