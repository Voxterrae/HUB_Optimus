use std::env;
fn hex(s:&str,n:usize)->bool{s.len()==n&&s.bytes().all(|b|b.is_ascii_digit()||(b'a'..=b'f').contains(&b))}
fn main(){
 println!("cargo:rerun-if-env-changed=HUB_RELAY_SOURCE_COMMIT");
 println!("cargo:rerun-if-env-changed=HUB_RELAY_POLICY_SHA256");
 let release=env::var("PROFILE").as_deref()==Ok("release");
 let source=env::var("HUB_RELAY_SOURCE_COMMIT").unwrap_or_else(|_|"0000000000000000000000000000000000000000".into());
 let policy=env::var("HUB_RELAY_POLICY_SHA256").unwrap_or_else(|_|"0000000000000000000000000000000000000000000000000000000000000000".into());
 let target=env::var("TARGET").expect("build target unavailable");
 if !hex(&source,40)||!hex(&policy,64)||target.len()>128||!target.is_ascii(){panic!("invalid diagnostic build metadata");}
 if release&&(source.bytes().all(|b|b==b'0')||policy.bytes().all(|b|b==b'0')){panic!("release requires explicit source and policy claims");}
 println!("cargo:rustc-env=HUB_RELAY_BUILD_SOURCE={source}");
 println!("cargo:rustc-env=HUB_RELAY_BUILD_POLICY={policy}");
 println!("cargo:rustc-env=HUB_RELAY_BUILD_TARGET={target}");
 if target=="x86_64-pc-windows-msvc" {println!("cargo:rustc-link-arg-bin=hub-relay-bootstrap-inventory=/STACK:4194304");}
}
