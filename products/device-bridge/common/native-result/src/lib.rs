//! Experimental closed result validation and mathematical consistency only.
//! Expected-request and supplied-key provenance remain the caller's responsibility.
#![forbid(unsafe_code)]

mod signature;
mod wire;

pub use signature::{result_signing_bytes, verify_native_result_signature};
pub use wire::{
    MAX_ENVELOPE_BYTES, NativeInventory, NativeInventoryField, NativeResult, NativeResultPayload,
    ResultError, parse_native_result, parse_native_result_payload, serialize_native_result,
};
