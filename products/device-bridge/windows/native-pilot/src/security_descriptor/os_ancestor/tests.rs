//! Deterministic synthetic bytes only. Fixture expectations come from the
//! adopted policy literals, not the implementation's identities or mask helpers.
use super::super::{DescriptorPolicy, OwnerDaclSnapshot, parse_snapshot};

const SYSTEM: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 5, 18, 0, 0, 0];
const EVERYONE: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0];

fn sid(authority: u8, parts: &[u32]) -> Vec<u8> {
    let mut bytes = vec![1, parts.len() as u8, 0, 0, 0, 0, 0, authority];
    for part in parts {
        bytes.extend(part.to_le_bytes());
    }
    bytes
}
fn trusted() -> Vec<Vec<u8>> {
    vec![
        SYSTEM.to_vec(),
        sid(5, &[32, 544]),
        sid(
            5,
            &[
                80, 956008885, 3418522649, 1831038044, 1853292631, 2271478464,
            ],
        ),
    ]
}
fn ace(kind: u8, flags: u8, mask: u32, trustee: &[u8]) -> Vec<u8> {
    let mut bytes = vec![kind, flags];
    bytes.extend(((8 + trustee.len()) as u16).to_le_bytes());
    bytes.extend(mask.to_le_bytes());
    bytes.extend(trustee);
    bytes
}
fn descriptor(owner: &[u8], aces: &[Vec<u8>]) -> Vec<u8> {
    let dacl = 20 + owner.len();
    let acl_len = 8 + aces.iter().map(Vec::len).sum::<usize>();
    let mut bytes = vec![1, 0, 4, 128]; // present, self-relative, unprotected
    bytes.extend(20u32.to_le_bytes());
    bytes.extend([0; 8]); // no group, no SACL
    bytes.extend((dacl as u32).to_le_bytes());
    bytes.extend(owner);
    bytes.extend([2, 0]);
    bytes.extend((acl_len as u16).to_le_bytes());
    bytes.extend((aces.len() as u16).to_le_bytes());
    bytes.extend([0, 0]);
    for entry in aces {
        bytes.extend(entry);
    }
    bytes
}
fn matches(bytes: &[u8]) -> bool {
    match OwnerDaclSnapshot::copy(bytes) {
        Ok(snapshot) => snapshot.matches_os_ancestor_policy().is_ok(),
        Err(_) => false,
    }
}
fn single(kind: u8, flags: u8, mask: u32, trustee: &[u8]) -> Vec<u8> {
    descriptor(SYSTEM, &[ace(kind, flags, mask, trustee)])
}
fn set16(bytes: &mut [u8], at: usize, value: u16) {
    bytes[at..at + 2].copy_from_slice(&value.to_le_bytes());
}
fn set32(bytes: &mut [u8], at: usize, value: u32) {
    bytes[at..at + 4].copy_from_slice(&value.to_le_bytes());
}

#[test]
fn only_exact_three_trusted_owners_and_mutators_match() {
    for identity in trusted() {
        assert!(
            matches(&descriptor(&identity, &[])),
            "trusted owner {identity:?}"
        );
        assert!(matches(&single(0, 0, 0x001f01ff, &identity)));
        for index in 8..identity.len() {
            let mut changed = identity.clone();
            changed[index] ^= 1;
            assert!(!matches(&descriptor(&changed, &[])), "owner byte {index}");
            assert!(
                !matches(&single(0, 0, 0x001f01ff, &changed)),
                "trustee byte {index}"
            );
        }
    }
    for owner in [
        sid(5, &[21, 1, 2, 3, 1001]),
        sid(5, &[80, 1, 2, 3, 4, 5]),
        sid(5, &[80, 0]),
        EVERYONE.to_vec(),
    ] {
        assert!(!matches(&descriptor(&owner, &[])));
        assert!(!matches(&single(0, 0, 2, &owner)));
    }
}

#[test]
fn each_safe_bit_and_safe_union_match_but_each_mutating_bit_refuses() {
    for mask in [
        1, 4, 8, 0x20, 0x80, 0x20000, 0x100000, 0x001200a9, 0x001200ad,
    ] {
        assert!(matches(&single(0, 0, mask, EVERYONE)), "safe {mask:#x}");
    }
    for bit in [2, 0x10, 0x40, 0x100, 0x10000, 0x40000, 0x80000] {
        assert!(!matches(&single(0, 0, bit, EVERYONE)), "mutation {bit:#x}");
        assert!(!matches(&single(0, 0, 0x001200ad | bit, EVERYONE)));
    }
}

#[test]
fn all_generic_combinations_preserve_specific_mutations_and_unknown_bits() {
    // Every subset of GENERIC_READ/WRITE/EXECUTE/ALL, independently tabulated.
    for (generic, allowed) in [
        (0, true),
        (0x80000000, true),
        (0x40000000, false),
        (0x20000000, true),
        (0x10000000, false),
        (0xc0000000, false),
        (0xa0000000, true),
        (0x90000000, false),
        (0x60000000, false),
        (0x50000000, false),
        (0x30000000, false),
        (0xe0000000, false),
        (0xd0000000, false),
        (0xb0000000, false),
        (0x70000000, false),
        (0xf0000000, false),
    ] {
        assert_eq!(
            matches(&single(0, 0, generic | 4, EVERYONE)),
            allowed,
            "generic {generic:#x}"
        );
        assert!(!matches(&single(0, 0, generic | 2, EVERYONE)));
        assert!(!matches(&single(0, 0, generic | 0x02000000, SYSTEM)));
        assert!(matches(&single(0, 0, generic | 4, SYSTEM)));
    }
    assert!(matches(&single(0, 0, 0x80100004, EVERYONE)));
    assert!(matches(&single(0, 0, 0x20020009, EVERYONE)));
}

#[test]
fn generic_mapping_produces_exact_adopted_masks() {
    for (input, expected) in [
        (0x80000000, 0x00120089),
        (0x40000000, 0x00120116),
        (0x20000000, 0x001200a0),
        (0x10000000, 0x001f01ff),
        (0xc0000000, 0x0012019f),
        (0xa0000000, 0x001200a9),
        (0x90000000, 0x001f01ff),
        (0x60000000, 0x001201b6),
        (0x50000000, 0x001f01ff),
        (0x30000000, 0x001f01ff),
        (0xe0000000, 0x001201bf),
        (0xd0000000, 0x001f01ff),
        (0xb0000000, 0x001f01ff),
        (0x70000000, 0x001f01ff),
        (0xf0000000, 0x001f01ff),
        (0x80000004, 0x0012008d),
        (0x20020009, 0x001200a9),
        (0x001200ad, 0x001200ad),
    ] {
        assert_eq!(
            super::expanded_mask(input).unwrap(),
            expected,
            "mapping {input:#x}"
        );
    }
}

#[test]
fn zero_and_every_out_of_universe_bit_refuse_even_deny_or_inherit_only() {
    for (kind, flags, trustee) in [
        (0, 0, SYSTEM),
        (1, 0, EVERYONE),
        (0, 9, EVERYONE),
        (1, 9, SYSTEM),
    ] {
        assert!(!matches(&single(kind, flags, 0, trustee)));
        for bit in [
            0x200, 0x400, 0x800, 0x1000, 0x2000, 0x4000, 0x8000, 0x200000, 0x400000, 0x800000,
            0x1000000, 0x2000000, 0x4000000, 0x8000000,
        ] {
            assert!(
                !matches(&single(kind, flags, bit, trustee)),
                "invalid {bit:#x}"
            );
        }
        assert!(matches(&single(kind, flags, 0x001200ad, trustee)));
    }
}

#[test]
fn deny_order_never_rescues_unsafe_allow_and_safe_split_duplicates_match() {
    let deny = ace(1, 0, 0x001f01ff, EVERYONE);
    let unsafe_allow = ace(0, 0, 2, EVERYONE);
    assert!(!matches(&descriptor(
        SYSTEM,
        &[deny.clone(), unsafe_allow.clone()]
    )));
    assert!(!matches(&descriptor(SYSTEM, &[unsafe_allow, deny.clone()])));
    let safe = vec![
        ace(0, 0, 1, EVERYONE),
        ace(0, 0, 4, EVERYONE),
        ace(0, 0, 1, EVERYONE),
        deny,
    ];
    assert!(matches(&descriptor(SYSTEM, &safe)));
    let mut unsafe_split = safe;
    unsafe_split.push(ace(0, 0, 0x100, EVERYONE));
    assert!(!matches(&descriptor(SYSTEM, &unsafe_split)));
}

#[test]
fn inherit_only_excludes_current_grants_only_after_complete_validation() {
    for kind in [0, 1] {
        assert!(matches(&single(kind, 9, 0x001f01ff, EVERYONE)));
        assert!(matches(&single(kind, 10, 0x40000000, EVERYONE)));
    }
    assert!(!matches(&single(0, 1, 0x001f01ff, EVERYONE)));
    assert!(!matches(&single(0, 2, 0x40000000, EVERYONE)));
    assert!(!matches(&single(0, 0x12, 0x116, EVERYONE))); // observed ProgramData-shaped control
}

#[test]
fn all_supported_flags_match_safe_grants_and_malformed_combinations_refuse() {
    for flags in [
        0, 1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 29, 30,
        31,
    ] {
        assert!(
            matches(&single(0, flags, 0x001200ad, EVERYONE)),
            "flags {flags:#x}"
        );
        assert!(matches(&single(1, flags, 0x001f01ff, EVERYONE)));
    }
    for flags in [4, 8, 12, 20, 24, 28] {
        assert!(!matches(&single(0, flags, 1, SYSTEM)));
    }
    for high in [0x20, 0x40, 0x80] {
        for low in 0..32 {
            assert!(!matches(&single(0, high | low, 1, SYSTEM)));
        }
    }
}

#[test]
fn creator_owner_and_group_require_valid_inherit_only_even_for_deny() {
    for creator in [sid(3, &[0]), sid(3, &[1])] {
        for kind in [0, 1] {
            for flags in [9, 10, 11, 13, 14, 15, 25, 26, 27, 29, 30, 31] {
                assert!(matches(&single(kind, flags, 0x001f01ff, &creator)));
            }
            for flags in [0, 1, 2, 8, 16] {
                assert!(!matches(&single(kind, flags, 1, &creator)));
            }
            assert!(!matches(&single(kind, 9, 0x02000000, &creator)));
        }
    }
}

#[test]
fn special_trustees_refuse_in_all_ordinary_ace_contexts() {
    for trustee in [
        sid(0, &[0]),
        sid(5, &[10]),
        sid(3, &[2]),
        sid(3, &[3]),
        sid(3, &[4]),
        sid(3, &[99]),
        sid(3, &[]),
        sid(3, &[0, 1]),
    ] {
        for kind in [0, 1] {
            for flags in [0, 9, 0x1a] {
                assert!(!matches(&single(kind, flags, 1, &trustee)));
            }
        }
    }
    // Ordinary well-formed, nontrusted SID grammars stay untrusted, not invalid.
    for trustee in [
        sid(5, &[80, 0]),
        sid(5, &[21, 1, 2, 3, 1001]),
        sid(7, &[]),
        sid(255, &[1]),
    ] {
        assert!(matches(&single(0, 0, 1, &trustee)));
        assert!(!matches(&single(0, 0, 2, &trustee)));
    }
}

#[test]
fn every_unsupported_ace_type_refuses_including_inherit_only() {
    for kind in 2..=255 {
        assert!(!matches(&single(kind, 0, 1, SYSTEM)), "type {kind}");
        assert!(!matches(&single(kind, 9, 1, SYSTEM)), "IO type {kind}");
    }
}

#[test]
fn revisions_protection_empty_dacl_and_zero_slack_are_supported() {
    for revision in [2, 4] {
        for control in [0x8004, 0x9004] {
            let mut bytes = descriptor(SYSTEM, &[]);
            bytes[32] = revision;
            set16(&mut bytes, 2, control);
            assert!(matches(&bytes)); // diagnostic has no creation-capability claim
        }
    }
    let mut slack = single(0, 0, 1, EVERYONE);
    slack.extend([0; 4]);
    set16(&mut slack, 34, 32);
    assert!(matches(&slack));
    slack[63] = 1;
    assert!(!matches(&slack));
}

#[test]
fn absent_null_and_inconsistent_dacls_refuse() {
    let valid = descriptor(SYSTEM, &[]);
    for (control, dacl) in [(0x8000, 0), (0x8004, 0), (0x8000, 32)] {
        let mut bytes = valid.clone();
        set16(&mut bytes, 2, control);
        set32(&mut bytes, 16, dacl);
        assert!(!matches(&bytes));
    }
}

#[test]
fn descriptor_offsets_overlap_and_sacl_data_refuse() {
    let valid = single(0, 0, 1, EVERYONE);
    assert!(matches(&valid));
    for (field, value) in [
        (4, 0),
        (4, 4),
        (4, 21),
        (4, 60),
        (4, u32::MAX),
        (8, 20),
        (8, 32),
        (8, 21),
        (12, 20),
        (12, u32::MAX),
        (16, 20),
        (16, 33),
        (16, 60),
        (16, u32::MAX),
    ] {
        let mut bytes = valid.clone();
        set32(&mut bytes, field, value);
        assert!(!matches(&bytes), "offset {field}/{value}");
    }
    // An independent group SID is structurally valid and carries no grants.
    let mut grouped = valid;
    let group_at = grouped.len() as u32;
    grouped.extend(sid(5, &[32, 545]));
    set32(&mut grouped, 8, group_at);
    assert!(matches(&grouped));
    grouped[group_at as usize + 1] = 16;
    assert!(!matches(&grouped));
}

#[test]
fn header_acl_ace_sid_sizes_counts_and_truncations_refuse() {
    let valid = single(0, 0, 1, EVERYONE);
    assert!(matches(&valid));
    for (at, value) in [
        (0, 2),
        (1, 1),
        (32, 1),
        (33, 1),
        (38, 1),
        (20, 2),
        (21, 16),
        (48, 2),
        (49, 16),
    ] {
        let mut bytes = valid.clone();
        bytes[at] = value;
        assert!(!matches(&bytes), "byte {at}/{value}");
    }
    for (at, value) in [
        (34, 0),
        (34, 7),
        (34, 9),
        (34, 32),
        (36, 0),
        (36, 2),
        (36, u16::MAX),
        (42, 0),
        (42, 12),
        (42, 17),
        (42, 24),
    ] {
        let mut bytes = valid.clone();
        set16(&mut bytes, at, value);
        assert!(!matches(&bytes), "u16 {at}/{value}");
    }
    let mut absolute = valid.clone();
    set16(&mut absolute, 2, 4);
    assert!(!matches(&absolute));
    for end in 0..valid.len() {
        assert!(!matches(&valid[..end]), "truncation {end}");
    }
    // An oversized ordinary ACE cannot conceal trailing SID bytes.
    let mut padded = valid;
    padded.extend([0; 4]);
    set16(&mut padded, 34, 32);
    set16(&mut padded, 42, 24);
    assert!(!matches(&padded));
}

#[test]
fn max_sid_subauthority_count_and_snapshot_bound_are_enforced() {
    let largest_sid = sid(5, &[1; 15]);
    assert!(matches(&single(0, 0, 1, &largest_sid)));
    assert!(!matches(&single(0, 0, 1, &sid(5, &[1; 16]))));
    let mut bounded = descriptor(SYSTEM, &[]);
    bounded.resize(65_536, 0);
    set16(&mut bounded, 34, 65_504); // DACL fills the remaining snapshot
    assert!(matches(&bounded));
    bounded.push(0);
    assert!(!matches(&bounded));
    assert!(!matches(&[0; 19]));
    assert!(!matches(&[0; 20])); // in copy bound but no valid descriptor
}

#[test]
fn original_strict_parser_and_application_policy_remain_strict() {
    assert!(parse_snapshot(&single(1, 0, 1, EVERYONE)).is_err());
    assert!(parse_snapshot(&single(0x05, 0x10, 1, EVERYONE)).is_err());
    let service = sid(5, &[80, 1, 2, 3, 4, 5]);
    let policy = DescriptorPolicy::root_shape(service.clone()).unwrap();
    let mut exact = descriptor(
        SYSTEM,
        &[
            ace(0, 0, 0x001f01ff, SYSTEM),
            ace(0, 0, 0x001200ab, &service),
        ],
    );
    set16(&mut exact, 2, 0x9004);
    policy.compare(&parse_snapshot(&exact).unwrap()).unwrap();
    let mut duplicate = descriptor(
        SYSTEM,
        &[
            ace(0, 0, 0x001f01ff, SYSTEM),
            ace(0, 0, 0x001200ab, &service),
            ace(0, 0, 0x001f01ff, SYSTEM),
        ],
    );
    set16(&mut duplicate, 2, 0x9004);
    assert!(
        policy
            .compare(&parse_snapshot(&duplicate).unwrap())
            .is_err()
    );
    exact[41] = 0x10;
    assert!(policy.compare(&parse_snapshot(&exact).unwrap()).is_err());
}
