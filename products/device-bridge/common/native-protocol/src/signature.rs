use crate::{ApprovalEnvelope, ProtocolError, RequestEnvelope, RequestPayload};
use p256::ecdsa::{Signature, VerifyingKey, signature::Verifier};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SignatureError {
    InvalidPublicKey,
    KeyIdMismatch,
    InvalidDer,
    VerificationFailed,
    Canonicalization,
}
impl fmt::Display for SignatureError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for SignatureError {}
const REQUEST_DOMAIN: &[u8] = b"HUB-RELAY-REQUEST-v0.1";
const APPROVAL_DOMAIN: &[u8] = b"HUB-RELAY-APPROVAL-v0.1";

#[derive(Serialize)]
struct SigningApprovalPayload<'a> {
    version: &'static str,
    request: &'a RequestPayload,
}

fn canonical_json<T: Serialize>(payload: &T) -> Result<Vec<u8>, ProtocolError> {
    serde_jcs::to_vec(payload).map_err(|_| ProtocolError::Serialization)
}

fn signing_bytes<T: Serialize>(domain: &[u8], payload: &T) -> Result<Vec<u8>, ProtocolError> {
    let canonical = canonical_json(payload)?;
    let mut bytes = Vec::with_capacity(domain.len() + 1 + canonical.len());
    bytes.extend_from_slice(domain);
    bytes.push(0);
    bytes.extend_from_slice(&canonical);
    Ok(bytes)
}

pub fn request_signing_bytes(payload: &RequestPayload) -> Result<Vec<u8>, ProtocolError> {
    signing_bytes(REQUEST_DOMAIN, payload)
}

pub fn approval_signing_bytes(request: &RequestPayload) -> Result<Vec<u8>, ProtocolError> {
    signing_bytes(
        APPROVAL_DOMAIN,
        &SigningApprovalPayload {
            version: "relay.native-approval.v0.1",
            request,
        },
    )
}

pub fn request_digest(payload: &RequestPayload) -> Result<[u8; 32], ProtocolError> {
    Ok(Sha256::digest(request_signing_bytes(payload)?).into())
}

pub fn approval_digest(request: &RequestPayload) -> Result<[u8; 32], ProtocolError> {
    Ok(Sha256::digest(approval_signing_bytes(request)?).into())
}

fn verifying_key(public_key_sec1: &[u8]) -> Result<VerifyingKey, SignatureError> {
    if public_key_sec1.len() != 65 || public_key_sec1[0] != 4 {
        return Err(SignatureError::InvalidPublicKey);
    }
    VerifyingKey::from_sec1_bytes(public_key_sec1).map_err(|_| SignatureError::InvalidPublicKey)
}

fn key_id_matches(public_key_sec1: &[u8], declared_id: &str) -> bool {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let hash = Sha256::digest(public_key_sec1);
    declared_id.bytes().eq(hash
        .iter()
        .flat_map(|byte| [HEX[(*byte >> 4) as usize], HEX[(*byte & 15) as usize]]))
}

fn der_signature(hex: &str) -> Result<Signature, SignatureError> {
    fn nibble(byte: u8) -> Result<u8, SignatureError> {
        match byte {
            b'0'..=b'9' => Ok(byte - b'0'),
            b'a'..=b'f' => Ok(byte - b'a' + 10),
            _ => Err(SignatureError::InvalidDer),
        }
    }
    if !hex.len().is_multiple_of(2) {
        return Err(SignatureError::InvalidDer);
    }
    let bytes = hex
        .as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|pair| Ok((nibble(pair[0])? << 4) | nibble(pair[1])?))
        .collect::<Result<Vec<u8>, SignatureError>>()?;
    // from_der enforces minimal DER, complete input and nonzero r/s below
    // the P-256 order. P-256 deliberately accepts both high-S and low-S.
    Signature::from_der(&bytes).map_err(|_| SignatureError::InvalidDer)
}

/// Check request-origin key consistency and the mathematical signature.
/// Success does not establish enrollment, key protection or admission.
pub fn verify_request_signature(
    envelope: &RequestEnvelope,
    public_key_sec1: &[u8],
) -> Result<(), SignatureError> {
    let key = verifying_key(public_key_sec1)?;
    if !key_id_matches(public_key_sec1, envelope.payload().broker_key_id()) {
        return Err(SignatureError::KeyIdMismatch);
    }
    let signature = der_signature(envelope.signature_der_hex())?;
    let bytes =
        request_signing_bytes(envelope.payload()).map_err(|_| SignatureError::Canonicalization)?;
    // Verifier hashes the complete domain-separated message once with SHA-256.
    // The informational digest APIs above are not passed to this verifier.
    key.verify(&bytes, &signature)
        .map_err(|_| SignatureError::VerificationFailed)
}

/// Verify the approval's complete nested request mathematically with a
/// caller-supplied key. Resolving that key from enrollment remains external.
pub fn verify_approval_signature(
    envelope: &ApprovalEnvelope,
    public_key_sec1: &[u8],
) -> Result<(), SignatureError> {
    let key = verifying_key(public_key_sec1)?;
    let signature = der_signature(envelope.signature_der_hex())?;
    let bytes =
        approval_signing_bytes(envelope.request()).map_err(|_| SignatureError::Canonicalization)?;
    key.verify(&bytes, &signature)
        .map_err(|_| SignatureError::VerificationFailed)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn jcs_preserves_unicode_values_without_normalization() {
        let object = serde_json::json!({"composed":"é", "decomposed":"e\u{301}", "escaped":"\n\t\"\\\u{c}\u{f}", "astral":"😀"});
        let expected = "{\"astral\":\"😀\",\"composed\":\"é\",\"decomposed\":\"e\u{301}\",\"escaped\":\"\\n\\t\\\"\\\\\\f\\u000f\"}";
        assert_eq!(canonical_json(&object).unwrap(), expected.as_bytes());
    }

    #[test]
    fn jcs_sorts_object_keys_by_utf16_code_units() {
        // RFC 8785 section 3.2.3 sample, including an astral key whose
        // UTF-16 order differs from Unicode scalar/UTF-8 order.
        let object = serde_json::json!({"€":"Euro Sign", "\r":"Carriage Return", "דּ":"Hebrew Letter Dalet With Dagesh", "1":"One", "😀":"Emoji: Grinning Face", "\u{80}":"Control", "ö":"Latin Small Letter O With Diaeresis"});
        let expected = "{\"\\r\":\"Carriage Return\",\"1\":\"One\",\"\u{80}\":\"Control\",\"ö\":\"Latin Small Letter O With Diaeresis\",\"€\":\"Euro Sign\",\"😀\":\"Emoji: Grinning Face\",\"דּ\":\"Hebrew Letter Dalet With Dagesh\"}";
        assert_eq!(canonical_json(&object).unwrap(), expected.as_bytes());
    }
}
