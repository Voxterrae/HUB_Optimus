#![cfg(windows)]
use bootstrap_inventory::windows::{ResourceKind,Resources};
#[test]
fn live_handle_limits_count_transient_directory_and_process_tokens_separately(){
 let mut r=Resources::new();
 for n in 0..129 { assert!(r.register(4*(n+1),ResourceKind::Directory).is_ok()); }
 assert!(r.register(600,ResourceKind::Directory).is_err());
 for n in 0..4 { assert!(r.register(700+4*n,ResourceKind::ProcessToken).is_ok()); }
 assert!(r.register(800,ResourceKind::ProcessToken).is_err());
 assert_eq!(r.live(ResourceKind::Directory),129);
 assert_eq!(r.peak(ResourceKind::Directory),129);
 assert_eq!(r.live(ResourceKind::ProcessToken),4);
}
#[test]
fn reverse_acquisition_order_survives_closed_slot_reuse(){
 let mut r=Resources::new();
 let a=r.register(4,ResourceKind::ProcessToken).unwrap();
 let b=r.register(8,ResourceKind::Directory).unwrap();
 let c=r.register(12,ResourceKind::Directory).unwrap();
 assert_eq!(r.take(b),Some(8));
 let d=r.register(16,ResourceKind::Directory).unwrap();
 assert_eq!(d,b);
 assert_eq!(r.take_reverse(),Some(16));
 assert_eq!(r.take_reverse(),Some(12));
 assert_eq!(r.take_reverse(),Some(4));
 assert_eq!(r.take_reverse(),None);
 assert_eq!(r.take(a),None);assert_eq!(r.take(c),None);
}
#[test]
fn null_pseudo_and_invalid_slots_never_become_owned_resources(){
 let mut r=Resources::new();
 assert!(r.register(0,ResourceKind::Directory).is_err());
 assert!(r.register(usize::MAX,ResourceKind::ProcessToken).is_err());
 assert_eq!(r.raw(usize::MAX),0);
 assert_eq!(r.take(usize::MAX),None);
 assert_eq!(r.live(ResourceKind::Directory),0);
}
