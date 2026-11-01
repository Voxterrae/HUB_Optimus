//! Read-only diagnostic candidate. No receipt or module creates authority.
pub mod model;
pub mod arena;
pub mod errors;
pub mod wire;
pub mod token_buffer;
pub mod process;
pub mod directories;
pub mod os_policy;
#[cfg(windows)]
pub mod windows;
