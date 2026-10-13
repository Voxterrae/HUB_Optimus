use hub_relay_native_protocol::{
    MAX_ENVELOPE_BYTES, parse_approval_envelope, parse_request_envelope,
    serialize_approval_envelope, serialize_request_envelope,
};

const SIG: &str = "3006020101020101";

fn payload() -> String {
    format!(
        r#"{{"version":"relay.native-request.v0.1","requestId":"{}","operation":"windows.runtime_inventory.v0_1","brokerKeyId":"{}","targetId":"{}","profileId":"{}","enrollmentGeneration":"{}","brokerStartGeneration":"{}","nonce":"{}","fields":["windows","powershell7","node"],"ttlMs":60000}}"#,
        "1".repeat(32),
        "2".repeat(64),
        "3".repeat(32),
        "4".repeat(32),
        "5".repeat(32),
        "6".repeat(32),
        "7".repeat(64),
    )
}

fn request(raw_payload: &str) -> String {
    format!(r#"{{"payload":{raw_payload},"signatureDerHex":"{SIG}"}}"#)
}

fn approval(raw_payload: &str) -> String {
    format!(
        r#"{{"payload":{{"version":"relay.native-approval.v0.1","request":{raw_payload}}},"signatureDerHex":"{SIG}"}}"#
    )
}

fn reject_both(raw_payload: &str) {
    assert!(parse_request_envelope(request(raw_payload).as_bytes()).is_err());
    assert!(parse_approval_envelope(approval(raw_payload).as_bytes()).is_err());
}

#[test]
fn valid_envelopes_preserve_all_bindings_and_roundtrip() {
    let input = request(&payload());
    let envelope = parse_request_envelope(input.as_bytes()).expect("valid request");
    let p = envelope.payload();
    assert_eq!(p.version(), "relay.native-request.v0.1");
    assert_eq!(p.request_id(), "1".repeat(32));
    assert_eq!(p.operation(), "windows.runtime_inventory.v0_1");
    assert_eq!(p.broker_key_id(), "2".repeat(64));
    assert_eq!(p.target_id(), "3".repeat(32));
    assert_eq!(p.profile_id(), "4".repeat(32));
    assert_eq!(p.enrollment_generation(), "5".repeat(32));
    assert_eq!(p.broker_start_generation(), "6".repeat(32));
    assert_eq!(p.nonce(), "7".repeat(64));
    assert_eq!(p.fields(), ["windows", "powershell7", "node"]);
    assert_eq!(p.ttl_ms(), 60000);
    assert_eq!(envelope.signature_der_hex(), SIG);
    assert_eq!(
        serialize_request_envelope(&envelope).unwrap(),
        input.as_bytes()
    );
    let input = approval(&payload());
    let envelope = parse_approval_envelope(input.as_bytes()).expect("valid approval");
    assert_eq!(envelope.payload().version(), "relay.native-approval.v0.1");
    assert_eq!(envelope.request().request_id(), "1".repeat(32));
    assert_eq!(envelope.payload().request().request_id(), "1".repeat(32));
    assert_eq!(envelope.signature_der_hex(), SIG);
    assert_eq!(
        serialize_approval_envelope(&envelope).unwrap(),
        input.as_bytes()
    );
}

#[test]
fn exact_byte_limit_accepts_4096_and_rejects_4097() {
    for input in [request(&payload()), approval(&payload())] {
        let mut bytes = input.into_bytes();
        bytes.resize(MAX_ENVELOPE_BYTES, b' ');
        if bytes.starts_with(b"{\"payload\":{\"version\":\"relay.native-request") {
            assert!(parse_request_envelope(&bytes).is_ok());
            bytes.push(b' ');
            assert!(parse_request_envelope(&bytes).is_err());
        } else {
            assert!(parse_approval_envelope(&bytes).is_ok());
            bytes.push(b' ');
            assert!(parse_approval_envelope(&bytes).is_err());
        }
    }
}

#[test]
fn byte_limit_counts_multibyte_utf8_before_json_validation() {
    // A forbidden field makes this structurally invalid; only the byte-limit
    // error proves that length was measured before parsing, in UTF-8 bytes.
    let prefix = r#"{"extra":""#;
    let suffix = "\"}";
    let mut input = format!("{prefix}{}{suffix}", "é".repeat(2042)).into_bytes();
    input.resize(4096, b' ');
    assert_eq!(input.len(), 4096);
    let error = parse_request_envelope(&input).unwrap_err();
    assert_ne!(
        error,
        hub_relay_native_protocol::ProtocolError::EnvelopeTooLarge
    );
    input.push(b' ');
    assert_eq!(
        parse_request_envelope(&input).unwrap_err(),
        hub_relay_native_protocol::ProtocolError::EnvelopeTooLarge
    );
    assert_eq!(
        parse_approval_envelope(&input).unwrap_err(),
        hub_relay_native_protocol::ProtocolError::EnvelopeTooLarge
    );
}

#[test]
fn duplicates_and_escaped_duplicates_reject_at_every_object() {
    for key in [
        "payload",
        "paylo\\u0061d",
        "signatureDerHex",
        "signatureDerH\\u0065x",
    ] {
        let value = if key.starts_with("paylo") {
            payload()
        } else {
            format!("\"{SIG}\"")
        };
        let input = request(&payload()).replacen('{', &format!("{{\"{key}\":{value},"), 1);
        assert!(parse_request_envelope(input.as_bytes()).is_err());
    }
    for key in ["requestId", "request\\u0049d"] {
        reject_both(&payload().replacen('{', &format!("{{\"{key}\":\"{}\",", "1".repeat(32)), 1));
    }
    for key in ["version", "vers\\u0069on", "request", "requ\\u0065st"] {
        let value = if key.starts_with("vers") {
            "\"relay.native-approval.v0.1\"".into()
        } else {
            payload()
        };
        let nested = format!(
            r#"{{"{key}":{value},"version":"relay.native-approval.v0.1","request":{}}}"#,
            payload()
        );
        let input = format!(r#"{{"payload":{nested},"signatureDerHex":"{SIG}"}}"#);
        assert!(parse_approval_envelope(input.as_bytes()).is_err());
    }
    let input = approval(&payload()).replacen(
        '{',
        &format!(
            "{{\"paylo\\u0061d\":{{\"version\":\"relay.native-approval.v0.1\",\"request\":{}}},",
            payload()
        ),
        1,
    );
    assert!(parse_approval_envelope(input.as_bytes()).is_err());
    for key in ["signatureDerHex", "signatureDerH\\u0065x"] {
        let input = approval(&payload()).replacen('{', &format!("{{\"{key}\":\"{SIG}\","), 1);
        assert!(parse_approval_envelope(input.as_bytes()).is_err());
    }
}

#[test]
fn unknown_and_missing_fields_reject_at_every_object() {
    reject_both(&payload().replacen('{', "{\"unknown\":0,", 1));
    for key in [
        "version",
        "requestId",
        "operation",
        "brokerKeyId",
        "targetId",
        "profileId",
        "enrollmentGeneration",
        "brokerStartGeneration",
        "nonce",
        "fields",
        "ttlMs",
    ] {
        let mut object: serde_json::Value = serde_json::from_str(&payload()).unwrap();
        object.as_object_mut().unwrap().remove(key);
        reject_both(&object.to_string());
    }
    for input in [
        r#"{}"#.to_string(),
        request(&payload()).replacen('{', "{\"unknown\":0,", 1),
        request(&payload()).replace(&format!(",\"signatureDerHex\":\"{SIG}\""), ""),
    ] {
        assert!(parse_request_envelope(input.as_bytes()).is_err());
    }
    for nested in [
        format!(
            r#"{{"version":"relay.native-approval.v0.1","request":{},"extra":true}}"#,
            payload()
        ),
        format!(r#"{{"request":{}}}"#, payload()),
        r#"{"version":"relay.native-approval.v0.1"}"#.into(),
    ] {
        assert!(
            parse_approval_envelope(
                format!(r#"{{"payload":{nested},"signatureDerHex":"{SIG}"}}"#).as_bytes()
            )
            .is_err()
        );
    }
    let input = approval(&payload()).replacen('{', "{\"unknown\":0,", 1);
    assert!(parse_approval_envelope(input.as_bytes()).is_err());
}

#[test]
fn ids_are_exact_ascii_lower_hex_and_types_are_closed() {
    for key in [
        "requestId",
        "brokerKeyId",
        "targetId",
        "profileId",
        "enrollmentGeneration",
        "brokerStartGeneration",
        "nonce",
    ] {
        let mut object: serde_json::Value = serde_json::from_str(&payload()).unwrap();
        let length = object[key].as_str().unwrap().len();
        for value in [
            serde_json::json!("A".repeat(length)),
            serde_json::json!("g".repeat(length)),
            serde_json::json!("é".repeat(length)),
            serde_json::json!(format!("{}\n", "1".repeat(length - 1))),
            serde_json::json!(format!("{}\r", "1".repeat(length - 1))),
            serde_json::json!("1".repeat(length - 1)),
            serde_json::json!("1".repeat(length + 1)),
            serde_json::json!(1),
            serde_json::json!(null),
            serde_json::json!([]),
        ] {
            object[key] = value;
            reject_both(&object.to_string());
        }
    }
    for raw in [
        "null",
        "true",
        "[]",
        r#"["relay.native-request.v0.1"]"#,
        "42",
        r#""text""#,
    ] {
        reject_both(raw);
    }
    assert!(parse_request_envelope(b"[]").is_err());
    assert!(parse_approval_envelope(b"[]").is_err());
    assert!(parse_request_envelope(format!(r#"[{},"{SIG}"]"#, payload()).as_bytes()).is_err());
}

#[test]
fn constants_field_order_and_integer_ttl_are_exact() {
    for key in ["version", "operation", "fields"] {
        for value in [
            serde_json::json!(null),
            serde_json::json!(true),
            serde_json::json!(60000),
            serde_json::json!({}),
        ] {
            let mut object: serde_json::Value = serde_json::from_str(&payload()).unwrap();
            object[key] = value;
            reject_both(&object.to_string());
        }
    }
    for (old, new) in [
        ("relay.native-request.v0.1", "fixture.v0.1"),
        ("windows.runtime_inventory.v0_1", "windows.shell.v0_1"),
        (
            r#"["windows","powershell7","node"]"#,
            r#"["node","powershell7","windows"]"#,
        ),
        (
            r#"["windows","powershell7","node"]"#,
            r#"["windows","powershell7"]"#,
        ),
        (
            r#"["windows","powershell7","node"]"#,
            r#"["windows","powershell7","node","extra"]"#,
        ),
        (
            r#"["windows","powershell7","node"]"#,
            r#"["windows","powershell7",1]"#,
        ),
    ] {
        reject_both(&payload().replace(old, new));
    }
    for ttl in [
        "60000.0",
        "6e4",
        "60000e0",
        "60000.000",
        "-60000",
        "60001",
        "0",
        "9007199254740992",
        "18446744073709551616",
        "NaN",
        "Infinity",
        "\"60000\"",
        "null",
        "true",
    ] {
        reject_both(&payload().replace("60000", ttl));
    }
    assert!(
        parse_approval_envelope(
            approval(&payload())
                .replace("relay.native-approval.v0.1", "fixture.v0.1")
                .as_bytes()
        )
        .is_err()
    );
}

#[test]
fn malformed_encoding_and_trailing_input_reject_without_input_echo() {
    let valid = request(&payload());
    let invalids = [
        format!("\u{feff}{valid}").into_bytes(),
        format!("{valid}{{}}").into_bytes(),
        format!("{valid}x").into_bytes(),
        valid
            .replace("relay.native-request.v0.1", r"\ud800")
            .into_bytes(),
        vec![0xff, 0xfe],
        valid.replace("60000", "060000").into_bytes(),
    ];
    for bytes in invalids {
        let error = parse_request_envelope(&bytes).unwrap_err();
        assert!(!error.to_string().contains("relay.native"));
        assert!(!format!("{error:?}").contains("requestId"));
    }
    for raw in [
        "",
        "0",
        "AA",
        "gg",
        "00 0",
        "0x00",
        "000",
        r"300602010102010\n",
        r"300602010102010\r",
        &"0".repeat(146),
    ] {
        assert!(parse_request_envelope(valid.replace(SIG, raw).as_bytes()).is_err());
        assert!(
            parse_approval_envelope(approval(&payload()).replace(SIG, raw).as_bytes()).is_err()
        );
    }
}

#[test]
fn equivalent_escaped_keys_and_values_decode_before_validation() {
    let input = request(&payload())
        .replace("requestId", r"request\u0049d")
        .replace("powershell7", r"powershell\u0037");
    assert!(parse_request_envelope(input.as_bytes()).is_ok());
    let input = approval(&payload()).replace("requestId", r"request\u0049d");
    assert!(parse_approval_envelope(input.as_bytes()).is_ok());
}
