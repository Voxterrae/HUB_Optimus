use serde::de::{DeserializeOwned, MapAccess, Visitor, value::MapAccessDeserializer};
use serde::{Deserialize, Deserializer, Serialize};
use std::{fmt, marker::PhantomData};

pub const MAX_ENVELOPE_BYTES: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProtocolError {
    EnvelopeTooLarge,
    InvalidJson,
    InvalidPayload,
    InvalidSignatureEncoding,
    Serialization,
}
impl fmt::Display for ProtocolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for ProtocolError {}

// Derived struct deserializers may accept positional arrays. Each object
// boundary uses this map-only visitor before the private closed struct's
// deserializer, which also rejects decoded duplicate and unknown keys.
fn object_only<'de, D, T>(deserializer: D) -> Result<T, D::Error>
where
    D: Deserializer<'de>,
    T: Deserialize<'de>,
{
    struct ObjectVisitor<T>(PhantomData<T>);
    impl<'de, T: Deserialize<'de>> Visitor<'de> for ObjectVisitor<T> {
        type Value = T;
        fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            f.write_str("a closed JSON object")
        }
        fn visit_map<A: MapAccess<'de>>(self, map: A) -> Result<T, A::Error> {
            T::deserialize(MapAccessDeserializer::new(map))
        }
    }
    deserializer.deserialize_map(ObjectVisitor(PhantomData))
}

struct JsonObject<T>(T);
impl<'de, T: Deserialize<'de>> Deserialize<'de> for JsonObject<T> {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        object_only(deserializer).map(Self)
    }
}

#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct RawRequestPayload {
    version: String,
    request_id: String,
    operation: String,
    broker_key_id: String,
    target_id: String,
    profile_id: String,
    enrollment_generation: String,
    broker_start_generation: String,
    nonce: String,
    fields: [String; 3],
    ttl_ms: u64,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct RawRequestEnvelope {
    #[serde(deserialize_with = "object_only")]
    payload: RawRequestPayload,
    signature_der_hex: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawApprovalPayload {
    version: String,
    #[serde(deserialize_with = "object_only")]
    request: RawRequestPayload,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct RawApprovalEnvelope {
    #[serde(deserialize_with = "object_only")]
    payload: RawApprovalPayload,
    signature_der_hex: String,
}

/// A request whose closed wire shape and field restrictions have been checked.
/// Its references and nonce carry no enrollment, freshness or entropy proof.
#[derive(Debug, Serialize)]
#[serde(transparent)]
pub struct RequestPayload {
    raw: RawRequestPayload,
}
impl RequestPayload {
    pub fn version(&self) -> &str {
        &self.raw.version
    }
    pub fn request_id(&self) -> &str {
        &self.raw.request_id
    }
    pub fn operation(&self) -> &str {
        &self.raw.operation
    }
    pub fn broker_key_id(&self) -> &str {
        &self.raw.broker_key_id
    }
    pub fn target_id(&self) -> &str {
        &self.raw.target_id
    }
    pub fn profile_id(&self) -> &str {
        &self.raw.profile_id
    }
    pub fn enrollment_generation(&self) -> &str {
        &self.raw.enrollment_generation
    }
    pub fn broker_start_generation(&self) -> &str {
        &self.raw.broker_start_generation
    }
    pub fn nonce(&self) -> &str {
        &self.raw.nonce
    }
    pub fn fields(&self) -> [&str; 3] {
        self.raw.fields.each_ref().map(String::as_str)
    }
    pub fn ttl_ms(&self) -> u64 {
        self.raw.ttl_ms
    }
}
#[derive(Debug, Serialize)]
pub struct ApprovalPayload {
    version: String,
    request: RequestPayload,
}
impl ApprovalPayload {
    pub fn version(&self) -> &str {
        &self.version
    }
    pub fn request(&self) -> &RequestPayload {
        &self.request
    }
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RequestEnvelope {
    payload: RequestPayload,
    signature_der_hex: String,
}
impl RequestEnvelope {
    pub fn payload(&self) -> &RequestPayload {
        &self.payload
    }
    pub fn signature_der_hex(&self) -> &str {
        &self.signature_der_hex
    }
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ApprovalEnvelope {
    payload: ApprovalPayload,
    signature_der_hex: String,
}
impl ApprovalEnvelope {
    pub fn payload(&self) -> &ApprovalPayload {
        &self.payload
    }
    pub fn request(&self) -> &RequestPayload {
        self.payload.request()
    }
    pub fn signature_der_hex(&self) -> &str {
        &self.signature_der_hex
    }
}

fn parse_object<T: DeserializeOwned>(input: &[u8]) -> Result<T, ProtocolError> {
    if input.len() > MAX_ENVELOPE_BYTES {
        return Err(ProtocolError::EnvelopeTooLarge);
    }
    let text = std::str::from_utf8(input).map_err(|_| ProtocolError::InvalidJson)?;
    serde_json::from_str::<JsonObject<T>>(text)
        .map(|object| object.0)
        .map_err(|_| ProtocolError::InvalidJson)
}

fn lower_hex(input: &str, length: usize) -> bool {
    input.len() == length
        && input
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn validate_request(raw: RawRequestPayload) -> Result<RequestPayload, ProtocolError> {
    if raw.version != "relay.native-request.v0.1"
        || raw.operation != "windows.runtime_inventory.v0_1"
        || raw.fields != ["windows", "powershell7", "node"]
        || raw.ttl_ms != 60000
        || !lower_hex(&raw.broker_key_id, 64)
        || !lower_hex(&raw.nonce, 64)
        || [
            &raw.request_id,
            &raw.target_id,
            &raw.profile_id,
            &raw.enrollment_generation,
            &raw.broker_start_generation,
        ]
        .iter()
        .any(|value| !lower_hex(value, 32))
    {
        return Err(ProtocolError::InvalidPayload);
    }
    Ok(RequestPayload { raw })
}

fn validate_signature_hex(hex: &str) -> Result<(), ProtocolError> {
    if hex.is_empty()
        || hex.len() > 144
        || !hex.len().is_multiple_of(2)
        || !lower_hex(hex, hex.len())
    {
        return Err(ProtocolError::InvalidSignatureEncoding);
    }
    Ok(())
}

/// Validate a request payload before obtaining a signature.
/// Success grants no enrollment, freshness, origin or admission authority.
pub fn parse_request_payload(input: &[u8]) -> Result<RequestPayload, ProtocolError> {
    let raw: RawRequestPayload = parse_object(input)?;
    validate_request(raw)
}

pub fn parse_request_envelope(input: &[u8]) -> Result<RequestEnvelope, ProtocolError> {
    let raw: RawRequestEnvelope = parse_object(input)?;
    let payload = validate_request(raw.payload)?;
    validate_signature_hex(&raw.signature_der_hex)?;
    Ok(RequestEnvelope {
        payload,
        signature_der_hex: raw.signature_der_hex,
    })
}

pub fn parse_approval_envelope(input: &[u8]) -> Result<ApprovalEnvelope, ProtocolError> {
    let raw: RawApprovalEnvelope = parse_object(input)?;
    if raw.payload.version != "relay.native-approval.v0.1" {
        return Err(ProtocolError::InvalidPayload);
    }
    let request = validate_request(raw.payload.request)?;
    validate_signature_hex(&raw.signature_der_hex)?;
    Ok(ApprovalEnvelope {
        payload: ApprovalPayload {
            version: raw.payload.version,
            request,
        },
        signature_der_hex: raw.signature_der_hex,
    })
}

pub fn serialize_request_envelope(envelope: &RequestEnvelope) -> Result<Vec<u8>, ProtocolError> {
    serialize_capped(envelope)
}
pub fn serialize_approval_envelope(envelope: &ApprovalEnvelope) -> Result<Vec<u8>, ProtocolError> {
    serialize_capped(envelope)
}

fn serialize_capped<T: Serialize>(value: &T) -> Result<Vec<u8>, ProtocolError> {
    let bytes = serde_json::to_vec(value).map_err(|_| ProtocolError::Serialization)?;
    if bytes.len() > MAX_ENVELOPE_BYTES {
        return Err(ProtocolError::EnvelopeTooLarge);
    }
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn serializer_limits_complete_envelope_bytes() {
        // Internal serializer stress fixture: the public validated payload
        // cannot contain variable free text or construct an oversized value.
        let mut object =
            serde_json::json!({"payload":{"content":""}, "signatureDerHex":"0".repeat(144)});
        let overhead = serde_json::to_vec(&object).unwrap().len();
        object["payload"]["content"] = serde_json::json!("x".repeat(MAX_ENVELOPE_BYTES - overhead));
        assert_eq!(serialize_capped(&object).unwrap().len(), MAX_ENVELOPE_BYTES);
        object["payload"]["content"] =
            serde_json::json!("x".repeat(MAX_ENVELOPE_BYTES + 1 - overhead));
        assert_eq!(
            serialize_capped(&object).unwrap_err(),
            ProtocolError::EnvelopeTooLarge
        );
        // The payload alone fits; the complete envelope, including signature,
        // exceeds the cap. Counting characters would miss the UTF-8 boundary.
        object["payload"]["content"] =
            serde_json::json!("é".repeat((MAX_ENVELOPE_BYTES - overhead) / 2 + 1));
        assert!(serde_json::to_vec(&object["payload"]).unwrap().len() < MAX_ENVELOPE_BYTES);
        assert_eq!(
            serialize_capped(&object).unwrap_err(),
            ProtocolError::EnvelopeTooLarge
        );
    }
}
