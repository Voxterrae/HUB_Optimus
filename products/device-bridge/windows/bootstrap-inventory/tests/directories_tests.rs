use bootstrap_inventory::directories::{classify_completion, completion_error, parse_drive_path, parse_guid_path, CompletionClass, MAX_PATH_UNITS};
use bootstrap_inventory::model::{Completion, Domain, Operation, Phase, Reason};
use bootstrap_inventory::os_policy::validate_descriptor;

fn units(text: &str) -> Vec<u16> { text.encode_utf16().collect() }
fn sid(rid: u32) -> Vec<u8> { let mut s=vec![1,1,0,0,0,0,0,5]; s.extend(rid.to_le_bytes()); s }
fn descriptor(owner: &[u8], aces: &[(u8,u8,u32,Vec<u8>)]) -> Vec<u8> {
    let mut b=vec![1,0,4,128]; b.extend(20u32.to_le_bytes()); b.extend([0u8;8]);
    b.extend((20u32+owner.len() as u32).to_le_bytes()); b.extend(owner);
    let length=8+aces.iter().map(|a|8+a.3.len()).sum::<usize>();
    b.extend([2,0]); b.extend((length as u16).to_le_bytes()); b.extend((aces.len() as u16).to_le_bytes()); b.extend([0u8;2]);
    for (kind,flags,mask,sid) in aces { b.extend([*kind,*flags]); b.extend(((8+sid.len()) as u16).to_le_bytes()); b.extend(mask.to_le_bytes()); b.extend(sid); }
    b
}
#[test]
fn fixed_drive_grammar_rejects_network_device_relative_and_malformed_before_io() {
    let p=units("C:\\Program Files"); let d=parse_drive_path(&p).unwrap(); assert_eq!(d.component_count(),1); assert_eq!(d.component(0),Some(&p[3..]));
    for text in ["\\\\server\\share", "\\\\?\\C:\\Program Files", "C:Program Files", "/Program Files", "1:\\Program Files", "C:/Program Files", "C:\\", "C:\\Program Files\\", "C:\\x\\..", "C:\\CON", "C:\\com¹", "C:\\NUL.txt", "C:\\x~1", "C:\\x ", "C:\\x.", "C:\\x:y", "C:\\x\\\\y"] { assert!(parse_drive_path(&units(text)).is_err(),"{text}"); }
    assert!(parse_drive_path(&[67,58,92,0xd800]).is_err()); assert!(parse_drive_path(&[67,58,92,0]).is_err());
}
#[test]
fn chain_and_component_bounds_are_exact() {
    let mut p=units("C:\\"); for i in 0..127 { if i!=0 { p.push(92); } p.push(120); }
    assert_eq!(parse_drive_path(&p).unwrap().component_count(),127); p.extend([92,120]); assert!(parse_drive_path(&p).is_err());
    let mut p=units("C:\\"); p.extend([120;255]); assert!(parse_drive_path(&p).is_ok()); p.push(120); assert!(parse_drive_path(&p).is_err());
    assert!(parse_drive_path(&vec![120;MAX_PATH_UNITS+1]).is_err());
}
#[test]
fn guid_grammar_requires_exact_root_and_component_boundaries() {
    let root=units("\\\\?\\Volume{01234567-89ab-cdef-0123-456789abcdef}\\");
    assert_eq!(parse_guid_path(&root).unwrap().component_count(),0);
    let mut path=root.clone(); path.extend(units("Program Files")); assert_eq!(parse_guid_path(&path).unwrap().component_count(),1);
    let mut bad=root.clone(); bad[11]=103; assert!(parse_guid_path(&bad).is_err());
    let mut bad=root.clone(); bad.extend(units("..")); assert!(parse_guid_path(&bad).is_err());
    assert!(parse_guid_path(&units("C:\\")).is_err());
}
#[test]
fn independent_nt_completion_fields_and_terminal_domains_survive() {
    let c=Completion{call:0,io_status:0xc0000022,information:77}; assert_eq!(classify_completion(c,4,true),CompletionClass::Reject);
    let e=completion_error(Phase::Recheck,Operation::NtQueryInformationFile,c); assert_eq!(e.domain,Domain::Ntstatus); assert_eq!(e.code,Some(0)); assert_eq!(e.completion,Some(c));
    let c=Completion{call:0,io_status:0,information:77}; let e=completion_error(Phase::Capture,Operation::NtCreateFile,c); assert_eq!(e.domain,Domain::Internal); assert_eq!(e.reason,Some(Reason::Malformed)); assert_eq!(e.completion,Some(c));
    assert_eq!(classify_completion(Completion{call:0,io_status:0,information:4},4,true),CompletionClass::Complete);
    assert_eq!(classify_completion(Completion{call:0,io_status:0,information:4},4,false),CompletionClass::Reject);
    for c in [Completion{call:0x103,io_status:0,information:1},Completion{call:0,io_status:0x103,information:1},Completion{call:0,io_status:0xc0000001,information:usize::MAX as u64}] { assert_eq!(classify_completion(c,1,true),CompletionClass::FatalPending); }
    assert_eq!(classify_completion(Completion{call:0xc0000022,io_status:0xc0000001,information:usize::MAX as u64},1,false),CompletionClass::Reject);
}
#[test]
fn os_policy_preserves_trusted_identities_masks_and_empty_dacl_semantics() {
    let system=sid(18); let admin=vec![1,2,0,0,0,0,0,5,32,0,0,0,32,2,0,0];
    let ti=vec![1,6,0,0,0,0,0,5,80,0,0,0,181,137,251,56,25,132,194,203,92,108,35,109,87,0,119,110,192,2,100,135];
    for owner in [&system,&admin,&ti] { assert!(validate_descriptor(&descriptor(owner,&[])).is_ok()); assert!(validate_descriptor(&descriptor(owner,&[(0,0,0x10000000,system.clone())])).is_ok()); }
    assert!(validate_descriptor(&descriptor(&sid(19),&[])).is_err());
    assert!(validate_descriptor(&descriptor(&system,&[(0,0,0x001200ad,sid(11))])).is_ok());
    for mask in [0,0x001200ab,0x40000000,0x10000000,0x00200000] { assert!(validate_descriptor(&descriptor(&system,&[(0,0,mask,sid(11))])).is_err()); }
    // DENY cannot subtract a later dangerous ALLOW, and inherit-only grants are validated.
    assert!(validate_descriptor(&descriptor(&system,&[(1,0,0x10000000,sid(11)),(0,0,0x10000000,sid(11))])).is_err());
    assert!(validate_descriptor(&descriptor(&system,&[(1,0,0x10000000,sid(11))])).is_ok());
    assert!(validate_descriptor(&descriptor(&system,&[(0,9,0x10000000,sid(11))])).is_ok());
}
#[test]
fn os_policy_refuses_unsupported_aces_invalid_flags_special_trustees_and_overlaps() {
    let system=sid(18);
    for (kind,flags) in [(2,0),(5,0),(0,0x20),(0,8),(0,4)] { assert!(validate_descriptor(&descriptor(&system,&[(kind,flags,0x120089,sid(11))])).is_err()); }
    for trustee in [vec![1,1,0,0,0,0,0,0,0,0,0,0],sid(10),vec![1,1,0,0,0,0,0,3,0,0,0,0]] { assert!(validate_descriptor(&descriptor(&system,&[(0,0,0x120089,trustee)])).is_err()); }
    let creator=vec![1,1,0,0,0,0,0,3,0,0,0,0]; assert!(validate_descriptor(&descriptor(&system,&[(0,9,0x10000000,creator)])).is_ok());
    let mut d=descriptor(&system,&[]); d[8..12].copy_from_slice(&20u32.to_le_bytes()); assert!(validate_descriptor(&d).is_err());
    let mut d=descriptor(&system,&[]); d[2]=0; assert!(validate_descriptor(&d).is_err());
    let mut d=descriptor(&system,&[]); d[16..20].fill(0); assert!(validate_descriptor(&d).is_err());
    let mut d=descriptor(&system,&[]); d[12..16].copy_from_slice(&20u32.to_le_bytes()); assert!(validate_descriptor(&d).is_err());
    let mut d=descriptor(&system,&[]); d[16..20].copy_from_slice(&21u32.to_le_bytes()); assert!(validate_descriptor(&d).is_err());
    let d=descriptor(&system,&[(0,0,0x120089,sid(11))]); for n in 0..d.len() { assert!(validate_descriptor(&d[..n]).is_err()); }
    assert!(validate_descriptor(&vec![0;65537]).is_err());
}
#[test]
fn exact_descriptor_cap_sid_acl_lengths_and_zero_slack_are_bounded() {
    let system=sid(18); let mut d=descriptor(&system,&[]); d.resize(65536,0); d[34..36].copy_from_slice(&(65504u16).to_le_bytes()); assert!(validate_descriptor(&d).is_ok()); d.push(0); assert!(validate_descriptor(&d).is_err());
    let original=descriptor(&system,&[(0,0,0x120089,sid(11))]);
    for length in [0u16,15,17,24] { let mut d=original.clone(); d[42..44].copy_from_slice(&length.to_le_bytes()); assert!(validate_descriptor(&d).is_err()); }
    let mut d=original.clone(); d[49]=16; assert!(validate_descriptor(&d).is_err());
    let mut d=original.clone(); d[36..38].copy_from_slice(&2u16.to_le_bytes()); assert!(validate_descriptor(&d).is_err());
    let mut d=descriptor(&system,&[]); d[34..36].copy_from_slice(&12u16.to_le_bytes()); d.extend([0,0,0,1]); assert!(validate_descriptor(&d).is_err());
    let mut d=original.clone(); d[8..12].copy_from_slice(&48u32.to_le_bytes()); assert!(validate_descriptor(&d).is_err());
    for mask in [0x80000000,0x20000000] { assert!(validate_descriptor(&descriptor(&system,&[(0,0,mask,sid(11))])).is_ok()); }
    assert!(validate_descriptor(&descriptor(&system,&[(1,0,0,sid(11))])).is_err());
}
#[test]
fn nt_unwritten_sentinel_uses_signed_call_status_and_pending_always_aborts() {
    assert_eq!(classify_completion(Completion{call:1,io_status:0xc0000001,information:usize::MAX as u64},1,true),CompletionClass::FatalPending);
    assert_eq!(classify_completion(Completion{call:0xc0000022,io_status:0x103,information:0},1,false),CompletionClass::FatalPending);
    let p=[67,58,92,0xd83d,0xde00]; assert!(parse_drive_path(&p).is_ok()); assert!(parse_drive_path(&[67,58,92,0xdc00]).is_err());
    for text in ["C:\\COM².txt","C:\\LPT³","C:\\COM¹"] { assert!(parse_drive_path(&units(text)).is_err()); }
}
