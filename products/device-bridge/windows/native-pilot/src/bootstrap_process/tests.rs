use super::*;

#[test]
fn current_process_observation_retains_identity_and_noninheritable_handle() {
    let observation = OwnProcessObservation::capture_current().unwrap();
    assert_eq!(observation.facts.pid, unsafe { GetCurrentProcessId() });
    assert!(observation.facts.creation > 0);
    assert!(!observation.facts.win32_image.is_empty());
    assert!(!observation.facts.native_image.is_empty());
    noninheritable(raw(&observation.process)).unwrap();
    observation.recheck().unwrap();
    observation.close().unwrap();
}

#[test]
fn independent_observations_have_independent_ownership() {
    let first = OwnProcessObservation::capture_current().unwrap();
    let second = OwnProcessObservation::capture_current().unwrap();
    assert_eq!(first.facts, second.facts);
    assert_ne!(raw(&first.process), raw(&second.process));
    first.close().unwrap();
    second.recheck().unwrap();
    second.close().unwrap();
}

#[test]
fn changed_retained_fact_is_refused_then_owned_handle_is_closed() {
    let mut observation = OwnProcessObservation::capture_current().unwrap();
    observation.facts.pid ^= 1;
    let refusal = observation.recheck().unwrap_err();
    assert_eq!(
        refusal.primary,
        Failure::Denied("own process observation changed")
    );
    observation.close().unwrap();
}

#[test]
fn setup_failure_closes_only_the_newly_owned_handle() {
    let control = OwnProcessObservation::capture_current().unwrap();
    let owned = duplicate_current().unwrap();
    let value = raw(&owned);
    assert_ne!(unsafe { GetProcessId(value) }, 0);
    let result: Result<()> = finish(
        Err(denied("synthetic after acquisition")),
        close_checked(owned),
    );
    // CloseHandle success is retained by finish without querying a handle
    // value that Windows may already have reused for another thread.
    let error = result.unwrap_err();
    assert_eq!(
        error.primary,
        Failure::Denied("synthetic after acquisition")
    );
    assert!(error.cleanup.is_empty());
    control.recheck().unwrap();
    control.close().unwrap();
}

#[test]
fn cleanup_error_is_preserved_with_the_original_failure() {
    let result: Result<()> = finish(
        Err(denied("synthetic capture failure")),
        Err(Error {
            primary: Failure::Native("synthetic close", ERROR_INVALID_HANDLE),
            cleanup: vec![],
        }),
    );
    let error = result.unwrap_err();
    assert_eq!(error.primary, Failure::Denied("synthetic capture failure"));
    assert_eq!(
        error.cleanup,
        [Failure::Native("synthetic close", ERROR_INVALID_HANDLE)]
    );
}

#[test]
fn image_extent_preserves_utf16_and_refuses_invalid_boundaries() {
    assert_eq!(bounded_image(&[0xd800, 0, 9], 1).unwrap(), [0xd800]);
    let mut maximum = vec![1; MAX_IMAGE_UNITS - 1];
    maximum[MAX_IMAGE_UNITS - 2] = 0;
    assert_eq!(
        bounded_image(&maximum, MAX_IMAGE_UNITS - 2).unwrap().len(),
        MAX_IMAGE_UNITS - 2
    );
    for (buffer, count) in [
        (vec![0], 0),
        (vec![1], 1),
        (vec![1, 2], 1),
        (vec![1, 0, 0], 2),
        (vec![1; MAX_IMAGE_UNITS], MAX_IMAGE_UNITS - 1),
        (vec![1; MAX_IMAGE_UNITS], MAX_IMAGE_UNITS),
    ] {
        assert!(bounded_image(&buffer, count).is_err());
    }
}
