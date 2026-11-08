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
