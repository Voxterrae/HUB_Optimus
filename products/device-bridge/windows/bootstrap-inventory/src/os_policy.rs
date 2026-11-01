//! Bounded, allocation-free owner/DACL grammar and conservative OS policy.
//! A matching snapshot is diagnostic data, never effective access or authority.
use crate::model::{Error, Operation, Phase, Reason, Result};

pub const MAX_DESCRIPTOR_BYTES: usize = 65_536;
const SYSTEM: &[u8] = &[1,1,0,0,0,0,0,5,18,0,0,0];
const ADMINISTRATORS: &[u8] = &[1,2,0,0,0,0,0,5,32,0,0,0,32,2,0,0];
// Reviewed fixed S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464.
const TRUSTED_INSTALLER: &[u8] = &[1,6,0,0,0,0,0,5,80,0,0,0,181,137,251,56,25,132,194,203,92,108,35,109,87,0,119,110,192,2,100,135];
const CREATOR_OWNER: &[u8] = &[1,1,0,0,0,0,0,3,0,0,0,0];
const CREATOR_GROUP: &[u8] = &[1,1,0,0,0,0,0,3,1,0,0,0];
const NULL_SID: &[u8] = &[1,1,0,0,0,0,0,0,0,0,0,0];
const PRINCIPAL_SELF: &[u8] = &[1,1,0,0,0,0,0,5,10,0,0,0];
fn denied(reason: Reason) -> Error { Error::internal(Phase::Capture,Operation::Validate,reason) }
fn region(bytes: &[u8], start: usize, length: usize) -> Result<&[u8]> {
    let end=start.checked_add(length).ok_or_else(||denied(Reason::Bound))?;
    bytes.get(start..end).ok_or_else(||denied(Reason::Malformed))
}
fn u16_at(bytes: &[u8], at: usize) -> Result<u16> { let b=region(bytes,at,2)?; Ok(u16::from_le_bytes([b[0],b[1]])) }
fn u32_at(bytes: &[u8], at: usize) -> Result<u32> { let b=region(bytes,at,4)?; Ok(u32::from_le_bytes([b[0],b[1],b[2],b[3]])) }
fn sid_size(bytes: &[u8]) -> Result<usize> {
    let header=region(bytes,0,8)?;
    if header[0]!=1 || header[1]>15 { return Err(denied(Reason::Malformed)); }
    let length=8+usize::from(header[1])*4; region(bytes,0,length)?; Ok(length)
}
fn offset(bytes: &[u8], field: usize) -> Result<usize> {
    let at=u32_at(bytes,field)? as usize;
    if at!=0 && (at<20 || at%4!=0 || at>=bytes.len()) { return Err(denied(Reason::Malformed)); }
    Ok(at)
}
// Header, owner, optional group, DACL: no heap and at most four regions.
struct Regions { ranges: [(usize,usize);4], count: usize }
impl Regions {
    fn new() -> Self { Self {ranges:[(0,20),(0,0),(0,0),(0,0)],count:1} }
    fn add(&mut self, start: usize, length: usize) -> Result<()> {
        let end=start.checked_add(length).ok_or_else(||denied(Reason::Bound))?;
        if self.count==4 || self.ranges[..self.count].iter().any(|&(a,b)|start<b && a<end) { return Err(denied(Reason::Malformed)); }
        self.ranges[self.count]=(start,end); self.count+=1; Ok(())
    }
}
fn trusted(sid: &[u8]) -> bool { sid==SYSTEM || sid==ADMINISTRATORS || sid==TRUSTED_INSTALLER }
fn expanded_mask(mask: u32) -> Result<u32> {
    let mut expanded=mask&0x0fff_ffff;
    for (generic,specific) in [(0x8000_0000,0x0012_0089),(0x4000_0000,0x0012_0116),(0x2000_0000,0x0012_00a0),(0x1000_0000,0x001f_01ff)] {
        if mask&generic!=0 { expanded|=specific; }
    }
    if expanded==0 || expanded&!0x001f_01ff!=0 { return Err(denied(Reason::Policy)); }
    Ok(expanded)
}
fn validate_ace(ace: &[u8]) -> Result<()> {
    if ![0,1].contains(&ace[0]) { return Err(denied(Reason::Unsupported)); }
    let flags=ace[1];
    if flags&!0x1f!=0 || (flags&0x0c!=0 && flags&3==0) { return Err(denied(Reason::Policy)); }
    let sid=&ace[8..];
    if sid_size(sid)?!=sid.len() { return Err(denied(Reason::Malformed)); }
    // Validate DENY and inherit-only entries too; no deny subtraction or SID lookup.
    let mask=expanded_mask(u32_at(ace,4)?)?;
    let inherit_only=flags&8!=0;
    if sid==NULL_SID || sid==PRINCIPAL_SELF { return Err(denied(Reason::Policy)); }
    if sid[2..8]==[0,0,0,0,0,3] && !(inherit_only && (sid==CREATOR_OWNER || sid==CREATOR_GROUP)) { return Err(denied(Reason::Policy)); }
    if ace[0]==0 && !inherit_only && !trusted(sid) && mask&!0x0012_00ad!=0 { return Err(denied(Reason::Policy)); }
    Ok(())
}
/// Preserve ACE order and all flags. Empty non-null DACLs may match this
/// nonmutation diagnostic; absent/null DACLs and unsupported ACE layouts refuse.
pub fn validate_descriptor(bytes: &[u8]) -> Result<()> {
    if !(20..=MAX_DESCRIPTOR_BYTES).contains(&bytes.len()) { return Err(denied(Reason::Bound)); }
    let control=u16_at(bytes,2)?;
    if bytes[0]!=1 || bytes[1]!=0 || control&0x8000==0 { return Err(denied(Reason::Malformed)); }
    let mut regions=Regions::new();
    let owner_at=offset(bytes,4)?;
    if owner_at==0 { return Err(denied(Reason::Policy)); }
    let owner_length=sid_size(&bytes[owner_at..])?;
    regions.add(owner_at,owner_length)?;
    if !trusted(region(bytes,owner_at,owner_length)?) { return Err(denied(Reason::Policy)); }
    let group_at=offset(bytes,8)?;
    if group_at!=0 { let length=sid_size(&bytes[group_at..])?; regions.add(group_at,length)?; }
    // This capture requested owner+DACL only, never SACL or account names.
    if u32_at(bytes,12)?!=0 { return Err(denied(Reason::Malformed)); }
    let dacl_at=offset(bytes,16)?;
    if control&4==0 || dacl_at==0 { return Err(denied(Reason::Policy)); }
    let header=region(bytes,dacl_at,8)?;
    let length=usize::from(u16_at(header,2)?);
    if ![2,4].contains(&header[0]) || header[1]!=0 || u16_at(header,6)?!=0 || length<8 || length%4!=0 { return Err(denied(Reason::Malformed)); }
    let acl=region(bytes,dacl_at,length)?; regions.add(dacl_at,length)?;
    let count=usize::from(u16_at(header,4)?);
    if count>(length-8)/16 { return Err(denied(Reason::Bound)); }
    let mut cursor=8;
    for _ in 0..count {
        let header=region(acl,cursor,4)?;
        let ace_length=usize::from(u16_at(header,2)?);
        if ace_length<16 || ace_length%4!=0 { return Err(denied(Reason::Malformed)); }
        validate_ace(region(acl,cursor,ace_length)?)?;
        cursor+=ace_length;
    }
    if acl[cursor..].iter().any(|&b|b!=0) { return Err(denied(Reason::Malformed)); }
    Ok(())
}
