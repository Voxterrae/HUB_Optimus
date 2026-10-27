//! Bounded OS-ancestor diagnostic; never application-root or creation authority.

use super::{
    Denial, MAX_SNAPSHOT, Result, SYSTEM_SID, add_region, deny, offset, region, sid_size, u16_at,
    u32_at,
};

const ADMINISTRATORS: &[u8] = &[1, 2, 0, 0, 0, 0, 0, 5, 32, 0, 0, 0, 32, 2, 0, 0];
// S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464.
// Fixed reviewed policy identity, never learned from an observed descriptor.
const TRUSTED_INSTALLER: &[u8] = &[
    1, 6, 0, 0, 0, 0, 0, 5, 80, 0, 0, 0, 181, 137, 251, 56, 25, 132, 194, 203, 92, 108, 35, 109,
    87, 0, 119, 110, 192, 2, 100, 135,
];
const CREATOR_OWNER: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0];
const CREATOR_GROUP: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 3, 1, 0, 0, 0];
const NULL_SID: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
const PRINCIPAL_SELF: &[u8] = &[1, 1, 0, 0, 0, 0, 0, 5, 10, 0, 0, 0];

fn trusted(sid: &[u8]) -> bool {
    sid == SYSTEM_SID || sid == ADMINISTRATORS || sid == TRUSTED_INSTALLER
}

fn expanded_mask(mask: u32) -> Result<u32> {
    let mut expanded = mask & 0x0fff_ffff;
    for (generic, specific) in [
        (0x8000_0000, 0x0012_0089),
        (0x4000_0000, 0x0012_0116),
        (0x2000_0000, 0x0012_00a0),
        (0x1000_0000, 0x001f_01ff),
    ] {
        if mask & generic != 0 {
            expanded |= specific;
        }
    }
    if expanded == 0 || expanded & !0x001f_01ff != 0 {
        return deny(Denial::Grants);
    }
    Ok(expanded)
}

fn compare_ace(ace: &[u8]) -> Result<()> {
    if ![0, 1].contains(&ace[0]) {
        return deny(Denial::UnsupportedAce);
    }
    let flags = ace[1];
    if flags & !0x1f != 0 || (flags & 0x0c != 0 && flags & 3 == 0) {
        return deny(Denial::AceFlags);
    }
    let sid = &ace[8..];
    if sid_size(sid)? != sid.len() {
        return deny(Denial::Layout);
    }
    // Validate every mask/trustee before IO or DENY can exclude a current grant.
    let mask = expanded_mask(u32_at(ace, 4)?)?;
    let inherit_only = flags & 8 != 0;
    if sid == NULL_SID || sid == PRINCIPAL_SELF {
        return deny(Denial::Sid);
    }
    if sid[2..8] == [0, 0, 0, 0, 0, 3]
        && !(inherit_only && (sid == CREATOR_OWNER || sid == CREATOR_GROUP))
    {
        return deny(Denial::Sid);
    }
    // Keep original ACE order. No deny subtraction, aggregation or membership
    // resolution: each self-applicable ALLOW must independently be safe.
    if ace[0] == 0 && !inherit_only && !trusted(sid) && mask & !0x0012_00ad != 0 {
        return deny(Denial::Grants);
    }
    Ok(())
}

/// One snapshot verdict only. Empty non-null DACLs can match this nonmutation
/// diagnostic; they prove neither creation rights nor effective access.
pub(super) fn compare(bytes: &[u8]) -> Result<()> {
    if !(20..=MAX_SNAPSHOT).contains(&bytes.len()) {
        return deny(Denial::Bounds);
    }
    let control = u16_at(bytes, 2)?;
    if bytes[0] != 1 || bytes[1] != 0 || control & 0x8000 == 0 {
        return deny(Denial::Layout);
    }
    let mut regions = Vec::new();
    let owner_at = offset(bytes, 4)?;
    if owner_at == 0 {
        return deny(Denial::Sid);
    }
    let owner_length = sid_size(&bytes[owner_at..])?;
    add_region(&mut regions, owner_at, owner_length)?;
    if !trusted(region(bytes, owner_at, owner_length)?) {
        return deny(Denial::Owner);
    }
    // Group layout is validated but does not expand the trusted principal set.
    let group_at = offset(bytes, 8)?;
    if group_at != 0 {
        let length = sid_size(&bytes[group_at..])?;
        add_region(&mut regions, group_at, length)?;
    }
    // GetSecurityInfo queried owner+DACL only; no SACL bytes are interpreted.
    if u32_at(bytes, 12)? != 0 {
        return deny(Denial::Layout);
    }
    let dacl_at = offset(bytes, 16)?;
    if control & 4 == 0 {
        return deny(Denial::AbsentDacl);
    }
    if dacl_at == 0 {
        return deny(Denial::NullDacl);
    }
    let header = region(bytes, dacl_at, 8)?;
    let length = u16_at(header, 2)? as usize;
    if ![2, 4].contains(&header[0])
        || header[1] != 0
        || u16_at(header, 6)? != 0
        || length < 8
        || !length.is_multiple_of(4)
    {
        return deny(Denial::Layout);
    }
    let acl = region(bytes, dacl_at, length)?;
    add_region(&mut regions, dacl_at, length)?;
    let count = u16_at(header, 4)? as usize;
    if count > (length - 8) / 16 {
        return deny(Denial::Bounds);
    }
    let mut cursor = 8;
    for _ in 0..count {
        let header = region(acl, cursor, 4)?;
        let ace_length = u16_at(header, 2)? as usize;
        if ace_length < 16 || !ace_length.is_multiple_of(4) {
            return deny(Denial::Layout);
        }
        compare_ace(region(acl, cursor, ace_length)?)?;
        cursor += ace_length; // bounded by region above, within the 64 KiB copy
    }
    // As in the strict safe parser, free ACL space must be zero-filled.
    if acl[cursor..].iter().any(|&byte| byte != 0) {
        return deny(Denial::Layout);
    }
    Ok(())
}

#[cfg(test)]
mod tests;
