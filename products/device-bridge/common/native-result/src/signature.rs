use crate::{NativeResult, NativeResultPayload, ResultError};
use hub_relay_native_protocol::{RequestPayload, request_digest};
use p256::ecdsa::{Signature, VerifyingKey, signature::Verifier};
use sha2::{Digest, Sha256};

pub(crate) fn der_signature(hex: &str) -> Result<Signature, ResultError> {
    if hex.is_empty()
        || hex.len() > 144
        || !hex.len().is_multiple_of(2)
        || !crate::wire::lower_hex(hex, hex.len())
    {
        return Err(ResultError::InvalidSignatureEncoding);
    }
    fn nibble(b: u8) -> u8 {
        if b <= b'9' { b - b'0' } else { b - b'a' + 10 }
    }
    let bytes = hex
        .as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|p| (nibble(p[0]) << 4) | nibble(p[1]))
        .collect::<Vec<_>>();
    // Pinned from_der enforces complete minimal DER and nonzero scalars below
    // the P-256 order; the native rejection matrix tests those dependency gates.
    Signature::from_der(&bytes).map_err(|_| ResultError::InvalidDer)
}
/// Full domain-separated signing message. This is not a bounded wire envelope.
pub fn result_signing_bytes(payload: &NativeResultPayload) -> Result<Vec<u8>, ResultError> {
    let canonical = crate::wire::canonical_payload(payload)?;
    let mut bytes = Vec::with_capacity(20 + canonical.len());
    bytes.extend_from_slice(b"HUB-RELAY-RESULT-v0.1\0");
    bytes.extend_from_slice(&canonical);
    Ok(bytes)
}
fn digest_matches(bytes: &[u8], expected: &str) -> bool {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    expected.bytes().eq(bytes
        .iter()
        .flat_map(|b| [HEX[(b >> 4) as usize], HEX[(b & 15) as usize]]))
}
/// Verify consistency with the caller-selected expected request and supplied key.
/// Success grants no identity, enrollment, freshness, execution or admission proof.
pub fn verify_native_result_signature(
    result: &NativeResult,
    expected_request: &RequestPayload,
    provided_public_key_sec1: &[u8],
) -> Result<(), ResultError> {
    if provided_public_key_sec1.len() != 65 || provided_public_key_sec1[0] != 4 {
        return Err(ResultError::InvalidPublicKey);
    }
    let key = VerifyingKey::from_sec1_bytes(provided_public_key_sec1)
        .map_err(|_| ResultError::InvalidPublicKey)?;
    if !digest_matches(
        &Sha256::digest(provided_public_key_sec1),
        expected_request.broker_key_id(),
    ) {
        return Err(ResultError::KeyIdMismatch);
    }
    let p = result.payload();
    let digest = request_digest(expected_request).map_err(|_| ResultError::Serialization)?;
    if !digest_matches(&digest, p.request_digest()) {
        return Err(ResultError::RequestDigestMismatch);
    }
    if p.target_id() != expected_request.target_id() {
        return Err(ResultError::TargetMismatch);
    }
    if p.profile_id() != expected_request.profile_id() {
        return Err(ResultError::ProfileMismatch);
    }
    let signature = der_signature(result.signature_der_hex())?;
    // The high-level verifier hashes these complete bytes once, never a digest.
    key.verify(&result_signing_bytes(p)?, &signature)
        .map_err(|_| ResultError::VerificationFailed)
}
