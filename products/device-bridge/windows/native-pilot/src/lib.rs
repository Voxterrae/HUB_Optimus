//! Experimental Windows CNG and unregistered HTTP.sys resources; no enrollment or release authority.
#![cfg(windows)]

pub mod approval_https;
pub mod identity;

// Intentionally dormant prerequisite: no public authority or production caller.
#[allow(dead_code)]
mod bootstrap_peer;

// Dormant metadata prerequisite, never a protected-root or authority producer.
#[allow(dead_code)]
mod security_descriptor;

// Private dormant SCM observation; grants no service or storage authority.
#[allow(dead_code)]
mod service_identity;

// Private metadata agreement only; no protected-root or content capability.
#[allow(dead_code)]
mod relative_ntfs;
