use super::*;

fn user_buffer(sid: &[u8], attributes: u32) -> AlignedBuffer {
    let offset = std::mem::size_of::<TOKEN_USER>();
    let mut buffer = AlignedBuffer::new(offset + sid.len()).unwrap();
    let bytes = buffer.bytes_mut();
    let pointer = unsafe { bytes.as_mut_ptr().add(offset) };
    let header = bytes.as_mut_ptr().cast::<TOKEN_USER>();
    // SAFETY: each field is aligned and inside the complete header. Write the
    // fields separately so Rust never deinitializes its zeroed padding bytes.
    unsafe {
        std::ptr::addr_of_mut!((*header).User.Sid).write(pointer.cast());
        std::ptr::addr_of_mut!((*header).User.Attributes).write(attributes);
    }
    bytes[offset..].copy_from_slice(sid);
    buffer
}

#[test]
fn token_user_exact_bounds_preserve_sid_and_all_attribute_bits() {
    let sid = [1, 1, 0, 0, 0, 0, 0, 5, 42, 0, 0, 0];
    let mut buffer = user_buffer(&sid, 0xffff_ffff);
    let facts = parse_user(buffer.bytes_mut()).unwrap();
    assert_eq!(facts.sid, sid);
    assert_eq!(facts.attributes, 0xffff_ffff);
}

#[test]
fn token_user_rejects_unchecked_pointers_and_header_overlap() {
    let sid = [1, 1, 0, 0, 0, 0, 0, 5, 42, 0, 0, 0];
    let mut buffer = user_buffer(&sid, 0);
    let bytes = buffer.bytes_mut();
    let base = bytes.as_ptr() as usize;
    for pointer in [
        0,
        base - 4,
        base,
        base + 4,
        base + bytes.len(),
        usize::MAX,
        base + std::mem::size_of::<TOKEN_USER>() + 1,
    ] {
        // SAFETY: this writes the pointer value into our own aligned header;
        // no fixture pointer is dereferenced by the test.
        unsafe {
            (*bytes.as_mut_ptr().cast::<TOKEN_USER>()).User.Sid = pointer as *mut _;
        }
        assert!(parse_user(bytes).is_err());
    }
}

#[test]
fn token_user_rejects_truncated_header_sid_revision_and_count() {
    let sid = [1, 1, 0, 0, 0, 0, 0, 5, 42, 0, 0, 0];
    let mut buffer = user_buffer(&sid, 0);
    let bytes = buffer.bytes_mut();
    let header = std::mem::size_of::<TOKEN_USER>();
    assert!(parse_user(&bytes[..header - 1]).is_err());
    assert!(parse_user(&bytes[1..]).is_err());
    assert!(parse_user(&bytes[..header + 7]).is_err());
    assert!(parse_user(&bytes[..header + 8]).is_err());
    bytes[header] = 2;
    assert!(parse_user(bytes).is_err());
    bytes[header] = 1;
    bytes[header + 1] = 16;
    assert!(parse_user(bytes).is_err());
}

#[test]
fn token_user_accepts_zero_and_fifteen_subauthorities_at_exact_extent() {
    for count in [0, 15] {
        let mut sid = vec![0; 8 + usize::from(count) * 4];
        sid[0] = 1;
        sid[1] = count;
        sid[7] = 5;
        let mut buffer = user_buffer(&sid, 0x10);
        let facts = parse_user(buffer.bytes_mut()).unwrap();
        assert_eq!(facts.sid, sid);
        assert_eq!(facts.attributes, 0x10);
        let bytes = buffer.bytes_mut();
        assert!(parse_user(&bytes[..bytes.len() - 1]).is_err());
    }
}

#[test]
fn token_buffer_bounds_are_exact() {
    assert!(AlignedBuffer::new(0).is_err());
    assert_eq!(AlignedBuffer::new(65536).unwrap().bytes_mut().len(), 65536);
    assert!(AlignedBuffer::new(65537).is_err());
}

#[test]
fn native_record_layout_and_both_user_fixtures_preserve_defined_padding() {
    assert_eq!(size_of::<TOKEN_STATISTICS>(), 56);
    assert_eq!(size_of::<TOKEN_USER>(), 16);
    let header_length = size_of::<TOKEN_USER>();
    let padding_start = std::mem::offset_of!(TOKEN_USER, User)
        + std::mem::offset_of!(SID_AND_ATTRIBUTES, Attributes)
        + size_of::<u32>();
    assert_eq!(padding_start, 12);
    let sid = [1, 1, 0, 0, 0, 0, 0, 5, 42, 0, 0, 0];
    let mut emitted = AlignedBuffer::new(header_length + sid.len()).unwrap();
    let mut api = FakeApi::default();
    let handle = api.open_primary().unwrap();
    let reply = api.query(&handle, TokenUser, Some(emitted.bytes_mut()));
    assert!(reply.success);
    api.close(handle).unwrap();
    for buffer in [user_buffer(&sid, u32::MAX), emitted] {
        assert!(
            buffer.bytes()[padding_start..header_length]
                .iter()
                .all(|byte| *byte == 0)
        );
    }
}

// Fake IDs own no OS handle. Only NativeApi creates an OwnedHandle.
struct FakeHandle(usize);

#[derive(Clone)]
struct TokenRecord {
    sid: Vec<u8>,
    attributes: u32,
    token_type: u32,
    statistics: TOKEN_STATISTICS,
    elevation_type: u32,
    elevated: u32,
    app_container: u32,
    impersonation_level: u32,
}

fn record() -> TokenRecord {
    TokenRecord {
        sid: vec![1, 1, 0, 0, 0, 0, 0, 5, 42, 0, 0, 0],
        attributes: 0xf000_0010,
        token_type: TokenPrimary as u32,
        statistics: TOKEN_STATISTICS {
            TokenId: LUID {
                LowPart: 11,
                HighPart: 0,
            },
            AuthenticationId: LUID {
                LowPart: 7,
                HighPart: 0,
            },
            ExpirationTime: 0,
            TokenType: TokenPrimary,
            ImpersonationLevel: SecurityAnonymous,
            DynamicCharged: 0,
            DynamicAvailable: 0,
            GroupCount: 2,
            PrivilegeCount: 1,
            ModifiedId: LUID {
                LowPart: 13,
                HighPart: 0,
            },
        },
        elevation_type: TokenElevationTypeDefault as u32,
        elevated: 0,
        app_container: 0,
        impersonation_level: SecurityImpersonation as u32,
    }
}

struct QueryFault {
    class: TOKEN_INFORMATION_CLASS,
    sizing: bool,
    reply: QueryReply,
}

struct FakeApi {
    records: [TokenRecord; 3],
    thread: std::collections::VecDeque<Result<Option<FakeHandle>>>,
    primary_error: Option<Error>,
    primary_error_at: usize,
    close_errors: Vec<usize>,
    process_error_at: Option<usize>,
    query_fault: Option<QueryFault>,
    statistics_change_at: Option<(usize, bool)>,
    retained_change: bool,
    inheritable: Option<usize>,
    statistics_queries: usize,
    process_checks: usize,
    primary_opens: usize,
    closes: Vec<usize>,
    queries: Vec<(usize, TOKEN_INFORMATION_CLASS, bool)>,
}

impl Default for FakeApi {
    fn default() -> Self {
        Self {
            records: [record(), record(), record()],
            thread: Default::default(),
            primary_error: None,
            primary_error_at: 1,
            close_errors: vec![],
            process_error_at: None,
            query_fault: None,
            statistics_change_at: None,
            retained_change: false,
            inheritable: None,
            statistics_queries: 0,
            process_checks: 0,
            primary_opens: 0,
            closes: vec![],
            queries: vec![],
        }
    }
}

// This typed emitter accepts only the pinned statistics record. These exact
// offsets prove that neither its LUID members nor the record contain padding.
const _: () = {
    assert!(size_of::<LUID>() == 8);
    assert!(std::mem::offset_of!(LUID, LowPart) == 0);
    assert!(std::mem::offset_of!(LUID, HighPart) == 4);
    assert!(size_of::<TOKEN_STATISTICS>() == 56);
    assert!(align_of::<TOKEN_STATISTICS>() <= align_of::<AlignedWord>());
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, TokenId) == 0);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, AuthenticationId) == 8);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, ExpirationTime) == 16);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, TokenType) == 24);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, ImpersonationLevel) == 28);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, DynamicCharged) == 32);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, DynamicAvailable) == 36);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, GroupCount) == 40);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, PrivilegeCount) == 44);
    assert!(std::mem::offset_of!(TOKEN_STATISTICS, ModifiedId) == 48);
};

fn put_statistics(buffer: &mut [u8], value: TOKEN_STATISTICS) -> u32 {
    assert_eq!(buffer.len(), size_of::<TOKEN_STATISTICS>());
    // SAFETY: exact size and aligned allocation; the compile-time checks above
    // establish that the complete integer-only record has no padding bytes.
    unsafe {
        buffer.as_mut_ptr().cast::<TOKEN_STATISTICS>().write(value);
    }
    buffer.len() as u32
}

fn put_scalar(buffer: &mut [u8], value: u32) -> u32 {
    buffer.copy_from_slice(&value.to_ne_bytes());
    buffer.len() as u32
}

impl TokenApi for FakeApi {
    type Handle = FakeHandle;

    fn noninheritable(&mut self, handle: &Self::Handle) -> Result<()> {
        if self.inheritable == Some(handle.0) {
            Err(denied("inheritable token handle"))
        } else {
            Ok(())
        }
    }

    fn process_recheck(&mut self) -> Result<()> {
        self.process_checks += 1;
        if self.process_error_at == Some(self.process_checks) {
            Err(denied("synthetic process drift"))
        } else {
            Ok(())
        }
    }

    fn open_primary(&mut self) -> Result<Self::Handle> {
        self.primary_opens += 1;
        if self.primary_error_at == self.primary_opens
            && let Some(error) = self.primary_error.take()
        {
            return Err(error);
        }
        Ok(FakeHandle(if self.primary_opens == 1 { 1 } else { 2 }))
    }

    fn open_thread(&mut self) -> Result<Option<Self::Handle>> {
        self.thread.pop_front().unwrap_or(Ok(None))
    }

    fn close(&mut self, handle: Self::Handle) -> Result<()> {
        self.closes.push(handle.0);
        if self.close_errors.contains(&handle.0) {
            Err(native_error("synthetic token close", ERROR_INVALID_HANDLE))
        } else {
            Ok(())
        }
    }

    fn query(
        &mut self,
        handle: &FakeHandle,
        class: TOKEN_INFORMATION_CLASS,
        buffer: Option<&mut [u8]>,
    ) -> QueryReply {
        self.queries.push((handle.0, class, buffer.is_none()));
        if self
            .query_fault
            .as_ref()
            .is_some_and(|fault| fault.class == class && fault.sizing == buffer.is_none())
        {
            return self.query_fault.take().unwrap().reply;
        }
        if self.retained_change && class == TokenStatistics && self.statistics_queries == 2 {
            self.records[0].attributes ^= 1;
        }
        let record = &self.records[handle.0 - 1];
        let Some(buffer) = buffer else {
            assert_eq!(class, TokenUser);
            return QueryReply {
                success: false,
                length: (std::mem::size_of::<TOKEN_USER>() + record.sid.len()) as u32,
                code: ERROR_INSUFFICIENT_BUFFER,
            };
        };
        let length = match class {
            CLASS_USER => {
                let offset = std::mem::size_of::<TOKEN_USER>();
                assert_eq!(buffer.len(), offset + record.sid.len());
                let sid = unsafe { buffer.as_mut_ptr().add(offset) };
                let header = buffer.as_mut_ptr().cast::<TOKEN_USER>();
                // SAFETY: fields are aligned and within the complete header.
                // Separate writes preserve the initialized header padding.
                unsafe {
                    std::ptr::addr_of_mut!((*header).User.Sid).write(sid.cast());
                    std::ptr::addr_of_mut!((*header).User.Attributes).write(record.attributes);
                }
                buffer[offset..].copy_from_slice(&record.sid);
                buffer.len() as u32
            }
            CLASS_STATISTICS => {
                self.statistics_queries += 1;
                let mut stats = record.statistics;
                if let Some((at, token_id)) = self.statistics_change_at
                    && at == self.statistics_queries
                {
                    if token_id {
                        stats.TokenId.LowPart ^= 1;
                    } else {
                        stats.ModifiedId.LowPart ^= 1;
                    }
                }
                put_statistics(buffer, stats)
            }
            CLASS_TYPE => put_scalar(buffer, record.token_type),
            CLASS_ELEVATION_TYPE => put_scalar(buffer, record.elevation_type),
            CLASS_ELEVATION => put_scalar(buffer, record.elevated),
            CLASS_IS_APP_CONTAINER => put_scalar(buffer, record.app_container),
            CLASS_IMPERSONATION_LEVEL => put_scalar(buffer, record.impersonation_level),
            _ => panic!("unexpected token class"),
        };
        QueryReply {
            success: true,
            length,
            code: 0,
        }
    }
}

#[test]
fn unchanged_selected_facts_recheck_and_close_fresh_token_first() {
    let mut api = FakeApi::default();
    let (handle, facts) = capture_with(&mut api).unwrap();
    assert_eq!(facts.user.sid, [1, 1, 0, 0, 0, 0, 0, 5, 42, 0, 0, 0]);
    assert_eq!(facts.user.attributes, 0xf000_0010);
    assert_eq!(api.closes, [2]);
    api.close(handle).unwrap();
    assert_eq!(api.closes, [2, 1]);
    assert!(api.process_checks >= 2);
}

#[test]
fn token_user_size_and_retrieval_are_single_bounded_calls() {
    for (sizing, success, length, code) in [
        (true, false, 0, ERROR_INSUFFICIENT_BUFFER),
        (true, false, 65537, ERROR_INSUFFICIENT_BUFFER),
        (true, false, 28, ERROR_ACCESS_DENIED),
        (true, true, 28, 0),
        (false, true, 27, 0),
        (false, true, 29, 0),
        (false, false, 29, ERROR_INSUFFICIENT_BUFFER),
        (false, false, 28, ERROR_ACCESS_DENIED),
    ] {
        let mut api = FakeApi {
            query_fault: Some(QueryFault {
                class: TokenUser,
                sizing,
                reply: QueryReply {
                    success,
                    length,
                    code,
                },
            }),
            ..Default::default()
        };
        assert!(capture_with(&mut api).is_err());
        assert_eq!(api.closes, [1]);
        let queries: Vec<_> = api
            .queries
            .iter()
            .filter(|(_, class, _)| *class == TokenUser)
            .collect();
        assert_eq!(queries.len(), if sizing { 1 } else { 2 });
    }
}

#[test]
fn fixed_token_classes_refuse_inexact_returned_sizes() {
    for class in [
        TokenStatistics,
        TokenType,
        TokenElevationType,
        TokenElevation,
        TokenIsAppContainer,
    ] {
        let exact = if class == TokenStatistics {
            std::mem::size_of::<TOKEN_STATISTICS>() as u32
        } else {
            4
        };
        for length in [0, exact - 1, exact + 1, 65537] {
            let mut api = FakeApi {
                query_fault: Some(QueryFault {
                    class,
                    sizing: false,
                    reply: QueryReply {
                        success: true,
                        length,
                        code: 0,
                    },
                }),
                ..Default::default()
            };
            assert!(capture_with(&mut api).is_err());
            assert_eq!(api.closes, [1]);
        }
    }
}

#[test]
fn statistics_brackets_refuse_token_or_modification_id_change() {
    for token_id in [false, true] {
        for at in [2, 4, 6] {
            let mut api = FakeApi {
                statistics_change_at: Some((at, token_id)),
                ..Default::default()
            };
            let error = capture_with(&mut api).err().unwrap();
            assert_eq!(
                error.primary,
                Failure::Denied("token changed during capture")
            );
            assert_eq!(api.closes, if at == 6 { vec![2, 1] } else { vec![1] });
        }
    }
}

#[test]
fn unchanged_retained_token_does_not_accept_different_current_primary_token() {
    let mut api = FakeApi::default();
    api.records[1].statistics.TokenId.LowPart = 99;
    let error = capture_with(&mut api).err().unwrap();
    assert_eq!(
        error.primary,
        Failure::Denied("current primary token changed")
    );
    assert_eq!(api.closes, [2, 1]);
}

#[test]
fn every_selected_reopened_fact_is_compared() {
    for change in 0..16 {
        let mut api = FakeApi::default();
        let second = &mut api.records[1];
        match change {
            0 => second.sid[8] ^= 1,
            1 => second.attributes ^= 1,
            2 => second.statistics.AuthenticationId.LowPart ^= 1,
            3 => second.statistics.ExpirationTime = 1,
            4 => second.statistics.ImpersonationLevel = SecurityIdentification,
            5 => second.statistics.DynamicCharged = 1,
            6 => second.statistics.DynamicAvailable = 1,
            7 => second.statistics.GroupCount = 3,
            8 => second.statistics.PrivilegeCount = 2,
            9 => second.statistics.ModifiedId.LowPart ^= 1,
            10 => second.elevation_type = TokenElevationTypeLimited as u32,
            11 => second.elevated = 1,
            12 => second.statistics.TokenId.HighPart = 1,
            13 => second.statistics.AuthenticationId.HighPart = 1,
            14 => second.statistics.ModifiedId.HighPart = 1,
            15 => second.statistics.TokenId.LowPart ^= 1,
            _ => unreachable!(),
        }
        assert!(capture_with(&mut api).is_err());
        assert_eq!(api.closes, [2, 1]);
    }
}

#[test]
fn primary_type_known_elevation_and_exact_booleans_are_required() {
    for (class, value) in [
        (TokenType, 0),
        (TokenType, 2),
        (TokenElevationType, 0),
        (TokenElevationType, 4),
        (TokenElevation, 2),
        (TokenIsAppContainer, 2),
        (TokenIsAppContainer, 1),
    ] {
        let mut api = FakeApi::default();
        match class {
            CLASS_TYPE => api.records[0].token_type = value,
            CLASS_ELEVATION_TYPE => api.records[0].elevation_type = value,
            CLASS_ELEVATION => api.records[0].elevated = value,
            CLASS_IS_APP_CONTAINER => api.records[0].app_container = value,
            _ => unreachable!(),
        }
        assert!(capture_with(&mut api).is_err());
        assert_eq!(api.closes, [1]);
    }
    let mut api = FakeApi::default();
    api.records[0].statistics.TokenType = TokenImpersonation;
    assert!(capture_with(&mut api).is_err());
    assert_eq!(api.closes, [1]);
}

#[test]
fn known_elevation_variants_and_boolean_elevation_are_observed_without_approval() {
    for elevation_type in [1, 2, 3] {
        for elevated in [0, 1] {
            let mut api = FakeApi::default();
            for record in &mut api.records {
                record.elevation_type = elevation_type;
                record.elevated = elevated;
            }
            let (handle, facts) = capture_with(&mut api).unwrap();
            assert_eq!(facts.elevation_type, elevation_type);
            assert_eq!(facts.elevated, elevated == 1);
            api.close(handle).unwrap();
        }
    }
}

#[test]
fn thread_open_errors_never_establish_nonimpersonation() {
    for code in [
        ERROR_ACCESS_DENIED,
        ERROR_CANT_OPEN_ANONYMOUS,
        ERROR_INVALID_HANDLE,
    ] {
        for phase in 0..3 {
            let mut api = FakeApi::default();
            for _ in 0..phase {
                api.thread.push_back(Ok(None));
            }
            api.thread
                .push_back(Err(native_error("OpenThreadToken bootstrap", code)));
            let error = capture_with(&mut api).err().unwrap();
            assert_eq!(
                error.primary,
                Failure::Native("OpenThreadToken bootstrap", code)
            );
            assert_eq!(api.primary_opens, phase);
            assert_eq!(
                api.closes,
                match phase {
                    0 => vec![],
                    1 => vec![1],
                    2 => vec![2, 1],
                    _ => unreachable!(),
                }
            );
        }
    }
}

#[test]
fn returned_thread_token_is_inspected_closed_and_refused() {
    for token_type in [TokenPrimary, TokenImpersonation] {
        let mut api = FakeApi::default();
        api.records[2].token_type = token_type as u32;
        api.thread.push_back(Ok(Some(FakeHandle(3))));
        let error = capture_with(&mut api).err().unwrap();
        assert_eq!(error.primary, Failure::Denied("calling thread has a token"));
        assert_eq!(api.closes, [3]);
        assert_eq!(api.primary_opens, 0);
        let levels = api
            .queries
            .iter()
            .filter(|(_, class, _)| *class == TokenImpersonationLevel)
            .count();
        assert_eq!(levels, usize::from(token_type == TokenImpersonation));
    }
}

#[test]
fn thread_inspection_and_cleanup_failures_are_both_retained() {
    let mut api = FakeApi::default();
    api.thread.push_back(Ok(Some(FakeHandle(3))));
    api.query_fault = Some(QueryFault {
        class: TokenType,
        sizing: false,
        reply: QueryReply {
            success: false,
            length: 0,
            code: ERROR_ACCESS_DENIED,
        },
    });
    api.close_errors.push(3);
    let error = capture_with(&mut api).err().unwrap();
    assert_eq!(
        error.primary,
        Failure::Native("GetTokenInformation TokenType", ERROR_ACCESS_DENIED)
    );
    assert_eq!(
        error.cleanup,
        [Failure::Native(
            "synthetic token close",
            ERROR_INVALID_HANDLE
        )]
    );
    assert_eq!(api.closes, [3]);
}

#[test]
fn thread_token_during_final_bracket_refuses_and_closes_retained_token() {
    let mut api = FakeApi::default();
    api.thread
        .extend([Ok(None), Ok(None), Ok(Some(FakeHandle(3)))]);
    assert!(capture_with(&mut api).is_err());
    assert_eq!(api.closes, [2, 3, 1]);
}

#[test]
fn primary_and_reverse_cleanup_failures_are_all_retained() {
    let mut api = FakeApi::default();
    api.records[1].statistics.TokenId.LowPart = 99;
    api.close_errors.extend([1, 2]);
    let error = capture_with(&mut api).err().unwrap();
    assert_eq!(
        error.primary,
        Failure::Denied("current primary token changed")
    );
    assert_eq!(
        error.cleanup,
        [
            Failure::Native("synthetic token close", ERROR_INVALID_HANDLE),
            Failure::Native("synthetic token close", ERROR_INVALID_HANDLE)
        ]
    );
    assert_eq!(api.closes, [2, 1]);
}

#[test]
fn close_failure_cannot_become_partial_success_or_be_retried() {
    let mut api = FakeApi::default();
    api.close_errors.push(2);
    assert!(capture_with(&mut api).is_err());
    assert_eq!(api.closes, [2, 1]);
}

#[test]
fn process_rechecks_bracket_acceptance_and_cleanup() {
    for at in [1, 2, 3] {
        let mut api = FakeApi {
            process_error_at: Some(at),
            ..Default::default()
        };
        let error = capture_with(&mut api).err().unwrap();
        assert_eq!(error.primary, Failure::Denied("synthetic process drift"));
        assert_eq!(
            api.closes,
            match at {
                1 => vec![],
                2 => vec![1],
                3 => vec![2, 1],
                _ => unreachable!(),
            }
        );
    }
}

#[test]
fn own_primary_account_capture_recheck_and_checked_close_are_native() {
    let process = OwnProcessObservation::capture_current().unwrap();
    let account = process.capture_primary_account().unwrap();
    assert!((8..=68).contains(&account.facts.user.sid.len()));
    assert!(account.facts.token_type == TokenPrimary as u32);
    assert!(!account.facts.app_container);
    account.recheck().unwrap();
    account.close().unwrap();
    process.recheck().unwrap();
    process.close().unwrap();
}

#[test]
fn native_primary_account_observations_have_independent_owners() {
    let first_process = OwnProcessObservation::capture_current().unwrap();
    let second_process = OwnProcessObservation::capture_current().unwrap();
    let first = first_process.capture_primary_account().unwrap();
    let second = second_process.capture_primary_account().unwrap();
    assert!(first.facts == second.facts);
    assert!(raw(&first.token) != raw(&second.token));
    first.close().unwrap();
    first_process.close().unwrap();
    second.recheck().unwrap();
    second.close().unwrap();
    second_process.close().unwrap();
}

#[test]
fn successful_capture_queries_only_the_selected_classes_without_retries() {
    let mut api = FakeApi::default();
    let (handle, _) = capture_with(&mut api).unwrap();
    let one_capture = [
        (TokenStatistics, false),
        (TokenUser, true),
        (TokenUser, false),
        (TokenType, false),
        (TokenElevationType, false),
        (TokenElevation, false),
        (TokenIsAppContainer, false),
        (TokenStatistics, false),
    ];
    let expected: Vec<_> = [1, 1, 2]
        .into_iter()
        .flat_map(|handle| {
            one_capture
                .into_iter()
                .map(move |(class, sizing)| (handle, class, sizing))
        })
        .collect();
    assert_eq!(api.queries, expected);
    api.close(handle).unwrap();
}

#[test]
fn changed_retained_facts_refuse_before_current_primary_reopen() {
    let mut api = FakeApi {
        retained_change: true,
        ..Default::default()
    };
    let error = capture_with(&mut api).err().unwrap();
    assert_eq!(
        error.primary,
        Failure::Denied("retained primary token changed")
    );
    assert_eq!(api.primary_opens, 1);
    assert_eq!(api.closes, [1]);
}

#[test]
fn token_handles_must_be_noninheritable_and_still_close_once() {
    for id in [1, 2, 3] {
        let mut api = FakeApi {
            inheritable: Some(id),
            ..Default::default()
        };
        if id == 3 {
            api.thread.push_back(Ok(Some(FakeHandle(3))));
        }
        let error = capture_with(&mut api).err().unwrap();
        assert_eq!(error.primary, Failure::Denied("inheritable token handle"));
        assert_eq!(
            api.closes,
            match id {
                1 => vec![1],
                2 => vec![2, 1],
                3 => vec![3],
                _ => unreachable!(),
            }
        );
    }
}

#[test]
fn unknown_thread_token_type_and_level_refuse_after_checked_close() {
    for (token_type, level) in [
        (0, 0),
        (3, 0),
        (TokenImpersonation, 4),
        (TokenImpersonation, -1),
    ] {
        let mut api = FakeApi::default();
        api.records[2].token_type = token_type as u32;
        api.records[2].impersonation_level = level as u32;
        api.thread.push_back(Ok(Some(FakeHandle(3))));
        assert!(capture_with(&mut api).is_err());
        assert_eq!(api.closes, [3]);
        assert_eq!(api.primary_opens, 0);
    }
}

#[test]
fn returned_thread_impersonation_level_error_and_cleanup_error_survive() {
    let mut api = FakeApi::default();
    api.records[2].token_type = TokenImpersonation as u32;
    api.thread.push_back(Ok(Some(FakeHandle(3))));
    api.query_fault = Some(QueryFault {
        class: TokenImpersonationLevel,
        sizing: false,
        reply: QueryReply {
            success: false,
            length: 0,
            code: ERROR_ACCESS_DENIED,
        },
    });
    api.close_errors.push(3);
    let error = capture_with(&mut api).err().unwrap();
    assert_eq!(
        error.primary,
        Failure::Native(
            "GetTokenInformation TokenImpersonationLevel",
            ERROR_ACCESS_DENIED
        )
    );
    assert_eq!(
        error.cleanup,
        [Failure::Native(
            "synthetic token close",
            ERROR_INVALID_HANDLE
        )]
    );
    assert_eq!(api.closes, [3]);
}

#[test]
fn primary_open_failure_returns_no_partial_owner() {
    for at in [1, 2] {
        let mut api = FakeApi {
            primary_error: Some(native_error("synthetic primary open", ERROR_ACCESS_DENIED)),
            primary_error_at: at,
            ..Default::default()
        };
        let error = capture_with(&mut api).err().unwrap();
        assert_eq!(
            error.primary,
            Failure::Native("synthetic primary open", ERROR_ACCESS_DENIED)
        );
        assert_eq!(api.closes, if at == 1 { vec![] } else { vec![1] });
    }
}

#[test]
fn native_retained_token_is_noninheritable_and_solely_owned() {
    let process = OwnProcessObservation::capture_current().unwrap();
    let control = process.capture_primary_account().unwrap();
    let account = process.capture_primary_account().unwrap();
    assert_ne!(raw(&control.token), raw(&account.token));
    let mut flags = 0;
    assert_ne!(
        unsafe { GetHandleInformation(raw(&account.token), &mut flags) },
        0
    );
    assert_eq!(flags & HANDLE_FLAG_INHERIT, 0);
    let token = account.token;
    let mut api = NativeApi { process: &process };
    let error = finish::<()>(
        Err(denied("synthetic after token capture")),
        api.close(token),
    )
    .unwrap_err();
    assert_eq!(
        error.primary,
        Failure::Denied("synthetic after token capture")
    );
    assert!(error.cleanup.is_empty());
    control.recheck().unwrap();
    control.close().unwrap();
    process.close().unwrap();
}
