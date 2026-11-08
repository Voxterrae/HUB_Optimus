use serde::de::{DeserializeOwned, MapAccess, Visitor, value::MapAccessDeserializer};
use serde::{Deserialize, Deserializer, Serialize};
use std::{fmt, marker::PhantomData};

pub const MAX_ENVELOPE_BYTES: usize = 4096;

/// Bounded local failures; no input or underlying parser error is retained.
#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum ResultError {
    EnvelopeTooLarge,
    InvalidJson,
    InvalidPayload,
    InvalidSignatureEncoding,
    InvalidDer,
    InvalidPublicKey,
    KeyIdMismatch,
    RequestDigestMismatch,
    TargetMismatch,
    ProfileMismatch,
    VerificationFailed,
    Serialization,
}
impl fmt::Display for ResultError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}
impl std::error::Error for ResultError {}

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
// The adapter attribute also makes absence fail: a missing-field deserializer
// cannot silently supply Option::None for this required wire member.
fn required_nullable<'de, D, T>(deserializer: D) -> Result<Option<T>, D::Error>
where
    D: Deserializer<'de>,
    T: Deserialize<'de>,
{
    Option::deserialize(deserializer)
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct RawEnvelope {
    #[serde(deserialize_with = "object_only")]
    payload: RawPayload,
    signature_der_hex: String,
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct RawPayload {
    version: String,
    request_digest: String,
    target_id: String,
    profile_id: String,
    state: String,
    #[serde(deserialize_with = "required_nullable")]
    error_code: Option<String>,
    #[serde(deserialize_with = "required_nullable")]
    inventory: Option<JsonObject<RawInventory>>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawInventory {
    #[serde(deserialize_with = "object_only")]
    windows: RawField,
    #[serde(deserialize_with = "object_only")]
    powershell7: RawField,
    #[serde(deserialize_with = "object_only")]
    node: RawField,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawField {
    state: String,
    #[serde(deserialize_with = "required_nullable")]
    version: Option<String>,
}

/// Parsed, closed result. This value conveys no enrollment or admission authority.
#[derive(Debug)]
pub struct NativeResult {
    payload: NativeResultPayload,
    signature_der_hex: String,
}
impl NativeResult {
    pub fn payload(&self) -> &NativeResultPayload {
        &self.payload
    }
    pub fn signature_der_hex(&self) -> &str {
        &self.signature_der_hex
    }
}
#[derive(Debug)]
pub struct NativeResultPayload {
    version: String,
    request_digest: String,
    target_id: String,
    profile_id: String,
    state: String,
    error_code: Option<String>,
    inventory: Option<NativeInventory>,
}
impl NativeResultPayload {
    pub fn version(&self) -> &str {
        &self.version
    }
    pub fn request_digest(&self) -> &str {
        &self.request_digest
    }
    pub fn target_id(&self) -> &str {
        &self.target_id
    }
    pub fn profile_id(&self) -> &str {
        &self.profile_id
    }
    pub fn state(&self) -> &str {
        &self.state
    }
    pub fn error_code(&self) -> Option<&str> {
        self.error_code.as_deref()
    }
    pub fn inventory(&self) -> Option<&NativeInventory> {
        self.inventory.as_ref()
    }
}
#[derive(Debug)]
pub struct NativeInventory {
    windows: NativeInventoryField,
    powershell7: NativeInventoryField,
    node: NativeInventoryField,
}
impl NativeInventory {
    pub fn windows(&self) -> &NativeInventoryField {
        &self.windows
    }
    pub fn powershell7(&self) -> &NativeInventoryField {
        &self.powershell7
    }
    pub fn node(&self) -> &NativeInventoryField {
        &self.node
    }
}
#[derive(Debug)]
pub struct NativeInventoryField {
    state: String,
    version: Option<String>,
}
impl NativeInventoryField {
    pub fn state(&self) -> &str {
        &self.state
    }
    pub fn version(&self) -> Option<&str> {
        self.version.as_deref()
    }
}

fn parse_object<T: DeserializeOwned>(input: &[u8]) -> Result<T, ResultError> {
    if input.len() > MAX_ENVELOPE_BYTES {
        return Err(ResultError::EnvelopeTooLarge);
    }
    let text = std::str::from_utf8(input).map_err(|_| ResultError::InvalidJson)?;
    if text.starts_with('\u{feff}') {
        return Err(ResultError::InvalidJson);
    }
    serde_json::from_str::<JsonObject<T>>(text)
        .map(|object| object.0)
        .map_err(|_| ResultError::InvalidJson)
}
pub(crate) fn lower_hex(value: &str, n: usize) -> bool {
    value.len() == n
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn validate_field(raw: RawField) -> Result<NativeInventoryField, ResultError> {
    let valid = match raw.state.as_str() {
        "available" => raw
            .version
            .as_ref()
            .is_some_and(|v| (1..=128).contains(&v.chars().count())),
        "missing" | "unverified" => raw.version.is_none(),
        _ => false,
    };
    if !valid {
        return Err(ResultError::InvalidPayload);
    }
    Ok(NativeInventoryField {
        state: raw.state,
        version: raw.version,
    })
}
fn validate_payload(raw: RawPayload) -> Result<NativeResultPayload, ResultError> {
    if raw.version != "relay.native-result.v0.1"
        || !lower_hex(&raw.request_digest, 64)
        || !lower_hex(&raw.target_id, 32)
        || !lower_hex(&raw.profile_id, 32)
    {
        return Err(ResultError::InvalidPayload);
    }
    let valid = match raw.state.as_str() {
        "completed" => raw.error_code.is_none() && raw.inventory.is_some(),
        "denied" => {
            matches!(
                raw.error_code.as_deref(),
                Some("NOT_AUTHORIZED" | "EXPIRED" | "REVOKED" | "REPLAY" | "BINDING_MISMATCH")
            ) && raw.inventory.is_none()
        }
        "failed" => {
            matches!(
                raw.error_code.as_deref(),
                Some("COLLECTOR_FAILED" | "TIMEOUT" | "OVERFLOW" | "INTERRUPTED")
            ) && raw.inventory.is_none()
        }
        "cancelled" => raw.error_code.as_deref() == Some("CANCELLED") && raw.inventory.is_none(),
        _ => false,
    };
    if !valid {
        return Err(ResultError::InvalidPayload);
    }
    let inventory = raw
        .inventory
        .map(|JsonObject(i)| {
            Ok(NativeInventory {
                windows: validate_field(i.windows)?,
                powershell7: validate_field(i.powershell7)?,
                node: validate_field(i.node)?,
            })
        })
        .transpose()?;
    Ok(NativeResultPayload {
        version: raw.version,
        request_digest: raw.request_digest,
        target_id: raw.target_id,
        profile_id: raw.profile_id,
        state: raw.state,
        error_code: raw.error_code,
        inventory,
    })
}

/// Validate raw payload bytes before an external signer is invoked.
pub fn parse_native_result_payload(input: &[u8]) -> Result<NativeResultPayload, ResultError> {
    validate_payload(parse_object(input)?)
}
/// Validate raw envelope bytes, including strict minimal DER before returning.
pub fn parse_native_result(input: &[u8]) -> Result<NativeResult, ResultError> {
    let raw: RawEnvelope = parse_object(input)?;
    let payload = validate_payload(raw.payload)?;
    crate::signature::der_signature(&raw.signature_der_hex)?;
    Ok(NativeResult {
        payload,
        signature_der_hex: raw.signature_der_hex,
    })
}

// Only these private closed views implement Serialize; validated public types
// have no general-purpose serde serialization or deserialization interface.
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct PayloadView<'a> {
    version: &'a str,
    request_digest: &'a str,
    target_id: &'a str,
    profile_id: &'a str,
    state: &'a str,
    error_code: Option<&'a str>,
    inventory: Option<InventoryView<'a>>,
}
#[derive(Serialize)]
struct InventoryView<'a> {
    windows: FieldView<'a>,
    powershell7: FieldView<'a>,
    node: FieldView<'a>,
}
#[derive(Serialize)]
struct FieldView<'a> {
    state: &'a str,
    version: Option<&'a str>,
}
fn field_view(f: &NativeInventoryField) -> FieldView<'_> {
    FieldView {
        state: f.state(),
        version: f.version(),
    }
}
fn payload_view(p: &NativeResultPayload) -> PayloadView<'_> {
    PayloadView {
        version: p.version(),
        request_digest: p.request_digest(),
        target_id: p.target_id(),
        profile_id: p.profile_id(),
        state: p.state(),
        error_code: p.error_code(),
        inventory: p.inventory().map(|i| InventoryView {
            windows: field_view(i.windows()),
            powershell7: field_view(i.powershell7()),
            node: field_view(i.node()),
        }),
    }
}
pub(crate) fn canonical_payload(p: &NativeResultPayload) -> Result<Vec<u8>, ResultError> {
    serde_jcs::to_vec(&payload_view(p)).map_err(|_| ResultError::Serialization)
}
fn serialize_capped<T: Serialize>(value: &T) -> Result<Vec<u8>, ResultError> {
    let bytes = serde_jcs::to_vec(value).map_err(|_| ResultError::Serialization)?;
    if bytes.len() > MAX_ENVELOPE_BYTES {
        return Err(ResultError::EnvelopeTooLarge);
    }
    Ok(bytes)
}
/// Serialize the complete validated envelope as bounded JCS, without a newline.
pub fn serialize_native_result(result: &NativeResult) -> Result<Vec<u8>, ResultError> {
    #[derive(Serialize)]
    #[serde(rename_all = "camelCase")]
    struct EnvelopeView<'a> {
        payload: PayloadView<'a>,
        signature_der_hex: &'a str,
    }
    serialize_capped(&EnvelopeView {
        payload: payload_view(result.payload()),
        signature_der_hex: result.signature_der_hex(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn final_jcs_envelope_caps_include_signature_and_multibyte_content() {
        let mut v =
            serde_json::json!({"payload":{"content":"é"},"signatureDerHex":"0".repeat(144)});
        let overhead = serde_jcs::to_vec(&v).unwrap().len() - "é".len();
        for n in [4095, 4096, 4097] {
            v["payload"]["content"] =
                serde_json::json!(format!("é{}", "x".repeat(n - overhead - 2)));
            assert_eq!(serde_jcs::to_vec(&v).unwrap().len(), n);
            assert!(serde_jcs::to_vec(&v["payload"]).unwrap().len() < 4096);
            let encoded = serialize_capped(&v);
            if n <= 4096 {
                assert_eq!(encoded.unwrap().len(), n);
            } else {
                assert_eq!(encoded, Err(ResultError::EnvelopeTooLarge));
            }
        }
    }
}
