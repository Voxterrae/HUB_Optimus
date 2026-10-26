//! Owned, unregistered HTTP.sys resources; no channel authority.

use std::fmt;
use std::ptr::{null, null_mut};
use windows_sys::Win32::Foundation::HANDLE;
use windows_sys::Win32::Networking::HttpServer as http;

const VERSION_2: http::HTTPAPI_VERSION = http::HTTPAPI_VERSION {
    HttpApiMajorVersion: 2,
    HttpApiMinorVersion: 0,
};

/// One failed native operation, without resource IDs or handles.
#[derive(Clone, Copy, Debug)]
pub struct HttpSysFailure {
    operation: &'static str,
    status: u32,
}

impl HttpSysFailure {
    pub fn operation(&self) -> &'static str {
        self.operation
    }

    /// The unmodified Win32 return status.
    pub fn status(&self) -> u32 {
        self.status
    }
}

/// The primary failure and every subsequent failed cleanup operation.
#[derive(Debug)]
pub struct HttpSysError {
    failure: HttpSysFailure,
    cleanup_failures: Vec<HttpSysFailure>,
}

impl HttpSysError {
    pub fn failure(&self) -> &HttpSysFailure {
        &self.failure
    }

    pub fn cleanup_failures(&self) -> &[HttpSysFailure] {
        &self.cleanup_failures
    }
}

impl fmt::Display for HttpSysFailure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "{}: Windows status {:#010x}",
            self.operation, self.status
        )
    }
}

impl fmt::Display for HttpSysError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.failure.fmt(formatter)?;
        for failure in &self.cleanup_failures {
            write!(formatter, "; owned-resource cleanup failed: {failure}")?;
        }
        Ok(())
    }
}

impl std::error::Error for HttpSysError {}

fn check(status: u32, operation: &'static str) -> Result<(), HttpSysFailure> {
    if status == 0 {
        Ok(())
    } else {
        Err(HttpSysFailure { operation, status })
    }
}

/// Owns one v2 session, anonymous non-inheritable queue and empty URL group.
/// No URLs are registered and the queue is not bound to the group.
///
/// `HttpInitialize` can start the Windows HTTP driver. The native rehearsal must
/// require that driver to be Running beforehand; that check is not atomic.
/// Use `close` to check cleanup. Drop is only a best-effort fallback.
pub struct UnregisteredHttpSys {
    initialized: bool,
    session: Option<u64>,
    queue: Option<HANDLE>,
    group: Option<u64>,
}

impl UnregisteredHttpSys {
    pub fn create_owned() -> Result<Self, HttpSysError> {
        let mut owner = Self {
            initialized: false,
            session: None,
            queue: None,
            group: None,
        };
        let acquisition = (|| {
            // SAFETY: supported v2 SERVER initialization; reserved pointer is null.
            check(
                unsafe {
                    http::HttpInitialize(VERSION_2, http::HTTP_INITIALIZE_SERVER, null_mut())
                },
                "HttpInitialize",
            )?;
            owner.initialized = true;
            #[cfg(test)]
            tests::after_acquisition(tests::Stage::Initialize, &owner)?;

            let mut session = 0;
            // SAFETY: writable session output and required zero reserved value.
            check(
                unsafe { http::HttpCreateServerSession(VERSION_2, &mut session, 0) },
                "HttpCreateServerSession",
            )?;
            owner.session = Some(session);
            #[cfg(test)]
            tests::after_acquisition(tests::Stage::Session, &owner)?;

            let mut queue = null_mut();
            // SAFETY: writable output, null name creates a fresh anonymous queue;
            // null security attributes forbid handle inheritance; flags never open existing.
            check(
                unsafe { http::HttpCreateRequestQueue(VERSION_2, null(), null(), 0, &mut queue) },
                "HttpCreateRequestQueue",
            )?;
            owner.queue = Some(queue);
            #[cfg(test)]
            tests::after_acquisition(tests::Stage::Queue, &owner)?;

            let mut group = 0;
            // SAFETY: session belongs to this owner; output writable; reserved zero.
            check(
                unsafe { http::HttpCreateUrlGroup(session, &mut group, 0) },
                "HttpCreateUrlGroup",
            )?;
            owner.group = Some(group);
            #[cfg(test)]
            tests::after_acquisition(tests::Stage::Group, &owner)?;
            Ok(())
        })();
        match acquisition {
            Ok(()) => Ok(owner),
            Err(failure) => Err(HttpSysError {
                failure,
                cleanup_failures: owner.cleanup(),
            }),
        }
    }

    /// Attempts every applicable cleanup operation once and consumes the owner.
    /// A cleanup failure is reported; Drop does not retry an uncertain handle/ID.
    pub fn close(mut self) -> Result<(), HttpSysError> {
        let mut failures = self.cleanup().into_iter();
        match failures.next() {
            None => Ok(()),
            Some(failure) => Err(HttpSysError {
                failure,
                cleanup_failures: failures.collect(),
            }),
        }
    }

    fn cleanup(&mut self) -> Vec<HttpSysFailure> {
        let mut failures = Vec::new();
        // Clear ownership before each attempt: a failed close must never be
        // retried by Drop against an ID/handle which may already be invalidated.
        if let Some(group) = self.group.take() {
            // SAFETY: this URL group was successfully created by this owner.
            collect(&mut failures, "HttpCloseUrlGroup", unsafe {
                http::HttpCloseUrlGroup(group)
            });
        }
        if let Some(queue) = self.queue.take() {
            // SAFETY: use the HTTP-specific closer on this owned request queue.
            collect(&mut failures, "HttpCloseRequestQueue", unsafe {
                http::HttpCloseRequestQueue(queue)
            });
        }
        if let Some(session) = self.session.take() {
            // SAFETY: this server session was successfully created by this owner.
            collect(&mut failures, "HttpCloseServerSession", unsafe {
                http::HttpCloseServerSession(session)
            });
        }
        if std::mem::take(&mut self.initialized) {
            // SAFETY: exactly matches this owner's successful SERVER initialization.
            collect(&mut failures, "HttpTerminate", unsafe {
                http::HttpTerminate(http::HTTP_INITIALIZE_SERVER, null_mut())
            });
        }
        failures
    }
}

fn collect(failures: &mut Vec<HttpSysFailure>, operation: &'static str, status: u32) {
    #[cfg(test)]
    let status = tests::cleanup_status(operation, status);
    if status != 0 {
        failures.push(HttpSysFailure { operation, status });
    }
}

impl Drop for UnregisteredHttpSys {
    fn drop(&mut self) {
        // Fallback cannot communicate failure. Explicit close is the checked path.
        let _ = self.cleanup();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use windows_sys::Win32::Foundation::{
        ERROR_INVALID_HANDLE, ERROR_INVALID_PARAMETER, GetHandleInformation, GetLastError,
        HANDLE_FLAG_INHERIT,
    };

    #[derive(Clone, Copy, Debug, PartialEq, Eq)]
    pub(super) enum Stage {
        Initialize,
        Session,
        Queue,
        Group,
    }

    // Snapshots never leave this test module or become usable public references.
    #[derive(Clone, Copy)]
    struct Snapshot {
        session: Option<u64>,
        queue: Option<HANDLE>,
        group: Option<u64>,
    }

    impl Snapshot {
        fn of(owner: &UnregisteredHttpSys) -> Self {
            Self {
                session: owner.session,
                queue: owner.queue,
                group: owner.group,
            }
        }
    }

    #[derive(Default)]
    struct Faults {
        stage: Option<Stage>,
        captured: Option<Snapshot>,
        fail_cleanup: bool,
        calls: Vec<(&'static str, u32)>,
    }

    thread_local! {
        static FAULTS: RefCell<Faults> = RefCell::new(Faults::default());
    }

    pub(super) fn after_acquisition(
        stage: Stage,
        owner: &UnregisteredHttpSys,
    ) -> Result<(), HttpSysFailure> {
        FAULTS.with(|faults| {
            let mut faults = faults.borrow_mut();
            if faults.stage == Some(stage) {
                let snapshot = Snapshot::of(owner);
                assert_live(snapshot);
                faults.captured = Some(snapshot);
                return Err(HttpSysFailure {
                    operation: "injected setup failure",
                    status: 0xE001,
                });
            }
            Ok(())
        })
    }

    // Every real native closer runs first. Only its reported result is faulted;
    // real statuses are retained, so injected failures cannot conceal leaked tests.
    pub(super) fn cleanup_status(operation: &'static str, status: u32) -> u32 {
        FAULTS.with(|faults| {
            let mut faults = faults.borrow_mut();
            faults.calls.push((operation, status));
            if faults.fail_cleanup {
                0xE100 + faults.calls.len() as u32
            } else {
                status
            }
        })
    }

    fn reset() {
        FAULTS.with(|faults| *faults.borrow_mut() = Faults::default());
    }

    fn session_probe(id: u64) -> u32 {
        let mut state = http::HTTP_STATE_INFO::default();
        let mut returned = 0;
        // SAFETY: writable correctly sized/aligned generated property structure.
        unsafe {
            http::HttpQueryServerSessionProperty(
                id,
                http::HttpServerStateProperty,
                (&mut state as *mut http::HTTP_STATE_INFO).cast(),
                size_of::<http::HTTP_STATE_INFO>() as u32,
                &mut returned,
            )
        }
    }

    fn group_probe(id: u64) -> u32 {
        let mut state = http::HTTP_STATE_INFO::default();
        let mut returned = 0;
        // SAFETY: same supported property and writable generated structure as live control.
        unsafe {
            http::HttpQueryUrlGroupProperty(
                id,
                http::HttpServerStateProperty,
                (&mut state as *mut http::HTTP_STATE_INFO).cast(),
                size_of::<http::HTTP_STATE_INFO>() as u32,
                &mut returned,
            )
        }
    }

    fn queue_probe(handle: HANDLE) -> u32 {
        let mut length: u32 = 0;
        let mut returned = 0;
        // SAFETY: ULONG property output is writable; reserved arguments are zero/null.
        unsafe {
            http::HttpQueryRequestQueueProperty(
                handle,
                http::HttpServerQueueLengthProperty,
                (&mut length as *mut u32).cast(),
                size_of::<u32>() as u32,
                0,
                &mut returned,
                null(),
            )
        }
    }

    fn assert_live(snapshot: Snapshot) {
        if let Some(id) = snapshot.session {
            assert_eq!(session_probe(id), 0, "live session control");
        }
        if let Some(handle) = snapshot.queue {
            assert_eq!(queue_probe(handle), 0, "live queue control");
            let mut flags = 0;
            // SAFETY: live queue control with a writable DWORD.
            assert_ne!(unsafe { GetHandleInformation(handle, &mut flags) }, 0);
        }
        if let Some(id) = snapshot.group {
            assert_eq!(group_probe(id), 0, "live group control");
        }
    }

    fn assert_closed(snapshot: Snapshot, observer: &UnregisteredHttpSys) {
        // Same probes succeed immediately beforehand on independently live controls.
        // The observer prevents uninitialized-API errors masquerading as deleted IDs.
        assert_live(Snapshot::of(observer));
        if let Some(id) = snapshot.session {
            assert_eq!(session_probe(id), ERROR_INVALID_PARAMETER, "closed session");
        }
        if let Some(handle) = snapshot.queue {
            let mut flags = 0;
            // SAFETY: query only the captured owned value, never close it here.
            let valid = unsafe { GetHandleInformation(handle, &mut flags) };
            // SAFETY: immediately read this thread's query failure status.
            let status = unsafe { GetLastError() };
            assert_eq!(valid, 0, "closed queue handle");
            assert_eq!(status, ERROR_INVALID_HANDLE);
        }
        if let Some(id) = snapshot.group {
            assert_eq!(group_probe(id), ERROR_INVALID_PARAMETER, "closed group");
        }
        assert_live(Snapshot::of(observer));
    }

    const CLOSES: [&str; 4] = [
        "HttpCloseUrlGroup",
        "HttpCloseRequestQueue",
        "HttpCloseServerSession",
        "HttpTerminate",
    ];

    fn assert_real_cleanup(expected: &[&str]) {
        FAULTS.with(|faults| {
            let faults = faults.borrow();
            assert_eq!(
                faults.calls.iter().map(|(op, _)| *op).collect::<Vec<_>>(),
                expected
            );
            assert!(
                faults.calls.iter().all(|(_, status)| *status == 0),
                "real cleanup must succeed"
            );
        });
    }

    #[test]
    fn real_owned_resources_close_explicitly() {
        reset();
        let observer = UnregisteredHttpSys::create_owned().unwrap();
        let owner = UnregisteredHttpSys::create_owned().expect("create owned HTTP.sys resources");
        let snapshot = Snapshot::of(&owner);
        assert_live(snapshot);
        let mut flags = 0;
        // SAFETY: querying only the live owned queue handle into a writable DWORD.
        assert_ne!(
            unsafe { GetHandleInformation(snapshot.queue.unwrap(), &mut flags) },
            0
        );
        assert_eq!(flags & HANDLE_FLAG_INHERIT, 0);
        owner.close().expect("close all owned resources");
        assert_real_cleanup(&CLOSES);
        assert_closed(snapshot, &observer);
        observer.close().unwrap();
    }

    #[test]
    fn two_live_owners_close_independently() {
        reset();
        let observer = UnregisteredHttpSys::create_owned().unwrap();
        let first = UnregisteredHttpSys::create_owned().unwrap();
        let second = UnregisteredHttpSys::create_owned().unwrap();
        let a = Snapshot::of(&first);
        let b = Snapshot::of(&second);
        assert_ne!(a.session, b.session);
        assert_ne!(a.queue, b.queue);
        assert_ne!(a.group, b.group);
        assert_live(a);
        assert_live(b);
        first.close().unwrap();
        assert_closed(a, &second);
        second.close().unwrap();
        assert_closed(b, &observer);
        observer.close().unwrap();
    }

    #[test]
    fn repeated_owned_lifecycles_release_each_resource() {
        reset();
        let observer = UnregisteredHttpSys::create_owned().unwrap();
        for _ in 0..8 {
            let owner = UnregisteredHttpSys::create_owned().unwrap();
            let snapshot = Snapshot::of(&owner);
            assert_live(snapshot);
            reset();
            owner.close().unwrap();
            assert_real_cleanup(&CLOSES);
            assert_closed(snapshot, &observer);
        }
        observer.close().unwrap();
    }

    #[test]
    fn setup_failure_after_each_acquisition_cleans_only_owned_resources() {
        reset();
        let observer = UnregisteredHttpSys::create_owned().unwrap();
        for (stage, expected) in [
            (Stage::Initialize, &CLOSES[3..]),
            (Stage::Session, &CLOSES[2..]),
            (Stage::Queue, &CLOSES[1..]),
            (Stage::Group, &CLOSES[..]),
        ] {
            reset();
            FAULTS.with(|faults| faults.borrow_mut().stage = Some(stage));
            let error = match UnregisteredHttpSys::create_owned() {
                Err(error) => error,
                Ok(owner) => {
                    owner.close().unwrap();
                    panic!("injected setup must fail");
                }
            };
            let snapshot = FAULTS.with(|faults| faults.borrow().captured.unwrap());
            FAULTS.with(|faults| faults.borrow_mut().stage = None);
            assert_eq!(error.failure().operation(), "injected setup failure");
            assert_eq!(error.failure().status(), 0xE001);
            assert!(error.cleanup_failures().is_empty());
            assert_real_cleanup(expected);
            assert_closed(snapshot, &observer);
        }
        observer.close().unwrap();
    }

    #[test]
    fn setup_failure_preserves_primary_and_all_cleanup_failures() {
        reset();
        let observer = UnregisteredHttpSys::create_owned().unwrap();
        FAULTS.with(|faults| {
            let mut faults = faults.borrow_mut();
            faults.stage = Some(Stage::Group);
            faults.fail_cleanup = true;
        });
        let error = match UnregisteredHttpSys::create_owned() {
            Err(error) => error,
            Ok(owner) => {
                owner.close().unwrap();
                panic!("injected setup must fail");
            }
        };
        let snapshot = FAULTS.with(|faults| faults.borrow().captured.unwrap());
        FAULTS.with(|faults| {
            let mut faults = faults.borrow_mut();
            faults.stage = None;
            faults.fail_cleanup = false;
        });
        assert_eq!(error.failure().operation(), "injected setup failure");
        assert_eq!(error.failure().status(), 0xE001);
        assert_eq!(
            error
                .cleanup_failures()
                .iter()
                .map(|failure| (failure.operation(), failure.status()))
                .collect::<Vec<_>>(),
            vec![
                ("HttpCloseUrlGroup", 0xE101),
                ("HttpCloseRequestQueue", 0xE102),
                ("HttpCloseServerSession", 0xE103),
                ("HttpTerminate", 0xE104)
            ]
        );
        assert_real_cleanup(&CLOSES);
        assert_closed(snapshot, &observer);
        observer.close().unwrap();
    }

    #[test]
    fn explicit_close_reports_every_failure_without_drop_retry() {
        reset();
        let observer = UnregisteredHttpSys::create_owned().unwrap();
        let owner = UnregisteredHttpSys::create_owned().unwrap();
        let snapshot = Snapshot::of(&owner);
        assert_live(snapshot);
        FAULTS.with(|faults| faults.borrow_mut().fail_cleanup = true);
        let error = owner.close().expect_err("all cleanup errors must surface");
        FAULTS.with(|faults| faults.borrow_mut().fail_cleanup = false);
        assert_eq!(
            (error.failure().operation(), error.failure().status()),
            ("HttpCloseUrlGroup", 0xE101)
        );
        assert_eq!(
            error
                .cleanup_failures()
                .iter()
                .map(|failure| (failure.operation(), failure.status()))
                .collect::<Vec<_>>(),
            vec![
                ("HttpCloseRequestQueue", 0xE102),
                ("HttpCloseServerSession", 0xE103),
                ("HttpTerminate", 0xE104)
            ]
        );
        assert_real_cleanup(&CLOSES);
        assert_closed(snapshot, &observer);
        observer.close().unwrap();
    }

    #[test]
    fn native_queue_close_error_survives_and_other_cleanup_continues() {
        reset();
        let observer = UnregisteredHttpSys::create_owned().unwrap();
        let owner = UnregisteredHttpSys::create_owned().unwrap();
        let snapshot = Snapshot::of(&owner);
        assert_live(snapshot);
        let queue = snapshot.queue.unwrap();
        let mut flags = 0;
        // SAFETY: positive control on this live owned queue, with writable output.
        assert_ne!(unsafe { GetHandleInformation(queue, &mut flags) }, 0);
        // Test-only external invalidation of this exact owned queue. No queue is
        // created between this close and owner.close; no unrelated handle is used.
        // SAFETY: this is a live queue created solely by this test's owner.
        assert_eq!(unsafe { http::HttpCloseRequestQueue(queue) }, 0);
        // SAFETY: query the stale owned value; the API reports invalid handles.
        let valid = unsafe { GetHandleInformation(queue, &mut flags) };
        // SAFETY: capture the previous call's thread-local error immediately.
        let last_error = unsafe { GetLastError() };
        assert_eq!(valid, 0);
        assert_eq!(last_error, ERROR_INVALID_HANDLE);
        let error = owner.close().expect_err("native queue error must survive");
        let native_status = FAULTS.with(|faults| {
            let faults = faults.borrow();
            assert_eq!(
                faults.calls.len(),
                4,
                "all closers run once, including termination"
            );
            for (index, (operation, status)) in faults.calls.iter().enumerate() {
                assert_eq!(*operation, CLOSES[index]);
                if index != 1 {
                    assert_eq!(*status, 0, "other native cleanup must succeed");
                }
            }
            faults.calls[1].1
        });
        assert_ne!(native_status, 0, "native closer must actually fail");
        println!("HTTP_SYS_OWNED_QUEUE_CLOSE_ERROR status={native_status:#010x}");
        assert_eq!(error.failure().operation(), "HttpCloseRequestQueue");
        assert_eq!(
            error.failure().status(),
            native_status,
            "preserve raw native status"
        );
        assert!(error.cleanup_failures().is_empty());
        assert_closed(snapshot, &observer);
        observer.close().unwrap();
    }
}
