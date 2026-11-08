use hub_relay_native_protocol::{
    MAX_ENVELOPE_BYTES, ProtocolError, parse_request_envelope, parse_request_payload,
    request_digest, request_signing_bytes, serialize_request_envelope, verify_request_signature,
};
use serde_json::{Value, json};

// Fictitious, frozen Node crypto vectors provide independent expected bytes.
fn fixture() -> Value {
    serde_json::from_str(include_str!("../vectors/native_signature.v0_1.json")).unwrap()
}

fn payload_bytes(vector: &Value) -> Vec<u8> {
    serde_json::to_vec(&vector["request"]["payload"]).unwrap()
}

fn unhex(input: &str) -> Vec<u8> {
    input
        .as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
        .collect()
}

#[test]
fn test_payload_validated_before_signature() {
    let vector = fixture();
    let payload = parse_request_payload(&payload_bytes(&vector)).unwrap();
    assert_eq!(
        request_signing_bytes(&payload).unwrap(),
        unhex(vector["request"]["signingBytesHex"].as_str().unwrap())
    );
    assert_eq!(
        request_digest(&payload).unwrap().as_slice(),
        unhex(vector["request"]["digestSha256Hex"].as_str().unwrap())
    );
}

#[test]
fn reordered_object_keys_keep_frozen_signing_bytes() {
    let vector = fixture();
    let object = vector["request"]["payload"].as_object().unwrap();
    let members: Vec<_> = object
        .iter()
        .rev()
        .map(|(key, value)| format!("{}:{value}", serde_json::to_string(key).unwrap()))
        .collect();
    let input = format!("{{{}}}", members.join(","));
    assert_ne!(input.as_bytes(), payload_bytes(&vector));
    let payload = parse_request_payload(input.as_bytes()).unwrap();
    assert_eq!(
        request_signing_bytes(&payload).unwrap(),
        unhex(vector["request"]["signingBytesHex"].as_str().unwrap())
    );
}

#[test]
fn payload_parser_rejects_ambiguous_or_non_object_json() {
    let input = String::from_utf8(payload_bytes(&fixture())).unwrap();
    let mut missing = fixture()["request"]["payload"].clone();
    missing.as_object_mut().unwrap().remove("requestId");
    for bytes in [
        input
            .replacen(
                '{',
                r#"{"request\u0049d":"11111111111111111111111111111111","#,
                1,
            )
            .into_bytes(),
        input.replacen('{', r#"{"unknown":0,"#, 1).into_bytes(),
        format!("[{input}]").into_bytes(),
        format!("{input}{{}}").into_bytes(),
        vec![0xff, 0xfe],
        serde_json::to_vec(&missing).unwrap(),
    ] {
        assert_eq!(
            parse_request_payload(&bytes).unwrap_err(),
            ProtocolError::InvalidJson
        );
    }
}

#[test]
fn payload_parser_enforces_existing_field_restrictions_and_integer_lexemes() {
    let vector = fixture();
    for (field, value) in [
        ("version", json!("relay.native-request.v0.2")),
        ("operation", json!("windows.shell.v0_1")),
        ("fields", json!(["node", "powershell7", "windows"])),
        ("requestId", json!("é".repeat(16))),
        ("requestId", json!("A".repeat(32))),
        ("ttlMs", json!(60001)),
    ] {
        let mut payload = vector["request"]["payload"].clone();
        payload[field] = value;
        assert_eq!(
            parse_request_payload(&serde_json::to_vec(&payload).unwrap()).unwrap_err(),
            ProtocolError::InvalidPayload,
            "{field}"
        );
    }
    let input = String::from_utf8(payload_bytes(&vector)).unwrap();
    for ttl in ["60000.0", "6e4"] {
        // Preserve raw number spelling: a Value roundtrip would erase this distinction.
        let input = input.replace("60000", ttl);
        assert_eq!(
            parse_request_payload(input.as_bytes()).unwrap_err(),
            ProtocolError::InvalidJson
        );
    }
}

#[test]
fn payload_parser_checks_exact_byte_cap_before_parsing() {
    let mut input = payload_bytes(&fixture());
    input.resize(MAX_ENVELOPE_BYTES, b' ');
    assert!(parse_request_payload(&input).is_ok());
    input.push(b' ');
    assert_eq!(
        parse_request_payload(&input).unwrap_err(),
        ProtocolError::EnvelopeTooLarge
    );
}

#[test]
fn prepared_payload_composes_with_real_fixture_signature_and_final_envelope_cap() {
    let vector = fixture();
    let payload = parse_request_payload(&payload_bytes(&vector)).unwrap();
    let input = serde_json::to_vec(&json!({
        "payload": payload,
        "signatureDerHex": vector["request"]["signatureLowSDerHex"],
    }))
    .unwrap();
    let envelope = parse_request_envelope(&input).unwrap();
    let public_key = unhex(vector["keys"]["broker"]["publicSec1Hex"].as_str().unwrap());
    verify_request_signature(&envelope, &public_key).unwrap();
    let mut final_bytes = serialize_request_envelope(&envelope).unwrap();
    assert!(final_bytes.len() <= MAX_ENVELOPE_BYTES);
    final_bytes.resize(MAX_ENVELOPE_BYTES, b' ');
    let envelope = parse_request_envelope(&final_bytes).unwrap();
    verify_request_signature(&envelope, &public_key).unwrap();
    final_bytes.push(b' ');
    assert_eq!(
        parse_request_envelope(&final_bytes).unwrap_err(),
        ProtocolError::EnvelopeTooLarge
    );
}
