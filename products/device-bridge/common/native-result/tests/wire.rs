use hub_relay_native_result::{
    ResultError, parse_native_result, parse_native_result_payload, result_signing_bytes,
    serialize_native_result,
};
use serde::de::{MapAccess, Visitor};
use serde_json::{Value, json};

const DER: &str = "3006020101020101";
fn payload() -> Value {
    json!({"version":"relay.native-result.v0.1", "requestDigest":"a".repeat(64), "targetId":"b".repeat(32), "profileId":"c".repeat(32), "state":"completed", "errorCode":null, "inventory":{
        "windows":{"state":"available","version":"x"}, "powershell7":{"state":"missing","version":null}, "node":{"state":"unverified","version":null}}})
}
fn envelope(p: Value) -> Value {
    json!({"payload":p,"signatureDerHex":DER})
}
fn bytes(v: &Value) -> Vec<u8> {
    serde_json::to_vec(v).unwrap()
}
fn rejects(v: &Value) {
    assert!(parse_native_result(&bytes(v)).is_err(), "{v}");
}

// Preserve decoded duplicate names and their order in a raw test witness.
// Parsing into Value here would collapse the evidence this assertion needs.
fn decoded_members(input: &str) -> Vec<(String, Value)> {
    struct Members;
    impl<'de> Visitor<'de> for Members {
        type Value = Vec<(String, Value)>;
        fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            formatter.write_str("test witness object")
        }
        fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
            let mut members = Vec::new();
            while let Some(member) = map.next_entry::<String, Value>()? {
                members.push(member);
            }
            Ok(members)
        }
    }
    let mut decoder = serde_json::Deserializer::from_str(input);
    let members = serde::Deserializer::deserialize_map(&mut decoder, Members).unwrap();
    decoder.end().unwrap();
    members
}

#[test]
fn getters_and_nonverifying_der_are_validated_at_parse_time() {
    let r = parse_native_result(&bytes(&envelope(payload()))).unwrap();
    let p = r.payload();
    assert_eq!(p.version(), "relay.native-result.v0.1");
    assert_eq!(p.request_digest(), "a".repeat(64));
    assert_eq!(p.target_id(), "b".repeat(32));
    assert_eq!(p.profile_id(), "c".repeat(32));
    assert_eq!(p.state(), "completed");
    assert_eq!(p.error_code(), None);
    let i = p.inventory().unwrap();
    assert_eq!(i.windows().version(), Some("x"));
    assert_eq!(i.windows().state(), "available");
    assert_eq!(i.powershell7().version(), None);
    assert_eq!(i.node().state(), "unverified");
    assert_eq!(r.signature_der_hex(), DER);
    let encoded = serialize_native_result(&r).unwrap();
    assert_eq!(
        serialize_native_result(&parse_native_result(&encoded).unwrap()).unwrap(),
        encoded
    );
}

#[test]
fn missing_unknown_duplicate_and_escaped_names_at_every_object_depth() {
    let base = envelope(payload());
    for path in [
        "",
        "/payload",
        "/payload/inventory",
        "/payload/inventory/windows",
        "/payload/inventory/powershell7",
        "/payload/inventory/node",
    ] {
        let object = base.pointer(path).unwrap().as_object().unwrap();
        for name in object.keys() {
            let mut v = base.clone();
            v.pointer_mut(path)
                .unwrap()
                .as_object_mut()
                .unwrap()
                .remove(name);
            rejects(&v);
            let member = serde_json::to_string(name).unwrap();
            let value = serde_json::to_string(&object[name]).unwrap();
            let ordinary = serde_json::to_string(&base).unwrap();
            // Insert into this exact object, avoiding any decoded-map intermediary.
            let original = serde_json::to_string(&base.pointer(path).unwrap()).unwrap();
            let escaped = format!("\"\\u{:04x}{}\"", name.as_bytes()[0], &name[1..]);
            for first in [&value, "null"] {
                for second in [&member, &escaped] {
                    let mut members =
                        vec![format!("{member}:{first}"), format!("{second}:{value}")];
                    members.extend(object.iter().filter(|(key, _)| *key != name).map(
                        |(key, value)| format!("{}:{}", serde_json::to_string(key).unwrap(), value),
                    ));
                    let changed = format!("{{{}}}", members.join(","));
                    let selected = decoded_members(&changed)
                        .into_iter()
                        .filter(|(key, _)| key == name)
                        .map(|(_, value)| value)
                        .collect::<Vec<_>>();
                    assert_eq!(
                        selected,
                        vec![
                            serde_json::from_str::<Value>(first).unwrap(),
                            object[name].clone()
                        ],
                        "{path}/{name}"
                    );
                    assert!(
                        parse_native_result(ordinary.replacen(&original, &changed, 1).as_bytes())
                            .is_err(),
                        "{path}/{name}"
                    );
                }
            }
            let changed = original.replacen(&member, &escaped, 1);
            assert!(
                parse_native_result(ordinary.replacen(&original, &changed, 1).as_bytes()).is_ok(),
                "{path}/{name}"
            );
        }
        let mut v = base.clone();
        v.pointer_mut(path)
            .unwrap()
            .as_object_mut()
            .unwrap()
            .insert("unknown".into(), json!(null));
        rejects(&v);
    }
}

#[test]
fn object_boundaries_are_never_positional_or_coerced() {
    for path in [
        "",
        "/payload",
        "/payload/inventory",
        "/payload/inventory/windows",
        "/payload/inventory/powershell7",
        "/payload/inventory/node",
    ] {
        for replacement in [
            json!([]),
            json!(null),
            json!("object"),
            json!(7),
            json!(false),
        ] {
            let mut v = envelope(payload());
            *v.pointer_mut(path).unwrap() = replacement;
            rejects(&v);
        }
    }
    for replacement in [
        json!([]),
        json!(null),
        json!("object"),
        json!(7),
        json!(false),
    ] {
        assert!(parse_native_result_payload(&bytes(&replacement)).is_err());
    }
}

#[test]
fn grammar_utf8_bom_controls_surrogates_and_complete_consumption() {
    let ordinary = String::from_utf8(bytes(&payload())).unwrap();
    for bad in [
        vec![],
        vec![0xff],
        vec![0xc0, 0xaf],
        vec![0xed, 0xa0, 0x80],
        [b"\xef\xbb\xbf".as_slice(), ordinary.as_bytes()].concat(),
    ] {
        assert!(parse_native_result_payload(&bad).is_err());
    }
    for suffix in ["{}", "null", "x", "\u{b}"] {
        assert!(parse_native_result_payload(format!("{ordinary}{suffix}").as_bytes()).is_err());
    }
    for bad in [
        r#""\ud800""#,
        r#""\udc00""#,
        r#""\ud800\ud800""#,
        r#""\udc00\ud800""#,
        r#""\ud800x""#,
        "NaN",
        "Infinity",
        "-Infinity",
        "\"a\nb\"",
    ] {
        assert!(
            parse_native_result_payload(ordinary.replace("\"x\"", bad).as_bytes()).is_err(),
            "{bad}"
        );
    }
    assert!(parse_native_result_payload(format!(" \t\r\n{ordinary}\r\n ").as_bytes()).is_ok());
    assert!(
        parse_native_result_payload(ordinary.replace("\"x\"", r#""\ud83d\ude80""#).as_bytes())
            .is_ok()
    );
    let p = payload();
    let reverse = p
        .as_object()
        .unwrap()
        .iter()
        .rev()
        .map(|(k, v)| format!("{}:{}", json!(k), v))
        .collect::<Vec<_>>()
        .join(",");
    assert_eq!(
        result_signing_bytes(
            &parse_native_result_payload(format!("{{{reverse}}}").as_bytes()).unwrap()
        )
        .unwrap(),
        result_signing_bytes(&parse_native_result_payload(&bytes(&p)).unwrap()).unwrap()
    );
}

#[test]
fn all_completed_field_combinations_and_closed_result_state_table() {
    let states = ["available", "missing", "unverified"];
    for a in states {
        for b in states {
            for c in states {
                let mut p = payload();
                for (name, state) in ["windows", "powershell7", "node"]
                    .into_iter()
                    .zip([a, b, c])
                {
                    p["inventory"][name] = json!({"state":state,"version":if state=="available" {json!("v")}else {Value::Null}});
                }
                assert!(parse_native_result_payload(&bytes(&p)).is_ok());
            }
        }
    }
    let table = [
        (
            "denied",
            vec![
                "NOT_AUTHORIZED",
                "EXPIRED",
                "REVOKED",
                "REPLAY",
                "BINDING_MISMATCH",
            ],
        ),
        (
            "failed",
            vec!["COLLECTOR_FAILED", "TIMEOUT", "OVERFLOW", "INTERRUPTED"],
        ),
        ("cancelled", vec!["CANCELLED"]),
    ];
    for (state, codes) in &table {
        for code in codes {
            let mut p = payload();
            p["state"] = json!(state);
            p["errorCode"] = json!(code);
            p["inventory"] = Value::Null;
            let r = parse_native_result_payload(&bytes(&p)).unwrap();
            assert_eq!(r.error_code(), Some(*code));
            assert!(r.inventory().is_none());
            for other in ["completed", "denied", "failed", "cancelled", "unknown"] {
                if other != *state {
                    let mut v = p.clone();
                    v["state"] = json!(other);
                    assert!(parse_native_result_payload(&bytes(&v)).is_err());
                }
            }
            p["inventory"] = payload()["inventory"].clone();
            assert!(parse_native_result_payload(&bytes(&p)).is_err());
        }
    }
    for state in ["completed", "denied", "failed", "cancelled", "unknown", ""] {
        let mut p = payload();
        p["state"] = json!(state);
        p["errorCode"] = json!("UNKNOWN");
        assert!(parse_native_result_payload(&bytes(&p)).is_err());
    }
    for field in ["windows", "powershell7", "node"] {
        for state in ["available", "missing", "unverified", "unknown"] {
            for version in [json!(null), json!(""), json!("v"), json!(8), json!(false)] {
                let allowed = (state == "available" && version == json!("v"))
                    || (["missing", "unverified"].contains(&state) && version.is_null());
                let mut p = payload();
                p["inventory"][field] = json!({"state":state,"version":version});
                assert_eq!(parse_native_result_payload(&bytes(&p)).is_ok(), allowed);
            }
        }
    }
}

#[test]
fn fixed_versions_and_exact_lowercase_ascii_hex() {
    for (name, n) in [("requestDigest", 64), ("targetId", 32), ("profileId", 32)] {
        for bad in [
            "a".repeat(n - 1),
            "a".repeat(n + 1),
            "A".repeat(n),
            "g".repeat(n),
            format!("0x{}", "a".repeat(n - 2)),
            format!("{}\n", "a".repeat(n - 1)),
            format!(" {}", "a".repeat(n - 1)),
            "\u{ff11}".repeat(n),
        ] {
            let mut p = payload();
            p[name] = json!(bad);
            assert!(parse_native_result_payload(&bytes(&p)).is_err(), "{name}");
        }
    }
    for bad in [
        "relay.native-result.v0.2",
        "relay.native-result.v0.1\n",
        "RELAY.native-result.v0.1",
        "",
    ] {
        let mut p = payload();
        p["version"] = json!(bad);
        assert!(parse_native_result_payload(&bytes(&p)).is_err());
    }
}

#[test]
fn unicode_scalar_bounds_preservation_and_canonical_equivalence() {
    for unit in ["x", "\u{1f680}", "e\u{301}"] {
        for n in [0, 1, 64, 128, 129] {
            let version = unit.repeat(n);
            let mut p = payload();
            p["inventory"]["windows"]["version"] = json!(version);
            let result = parse_native_result_payload(&bytes(&p));
            let count = version.chars().count();
            assert_eq!(result.is_ok(), (1..=128).contains(&count));
            if let Ok(r) = result {
                assert_eq!(
                    r.inventory().unwrap().windows().version(),
                    Some(version.as_str())
                );
            }
        }
    }
    for value in ["\0\n\t\r\u{1f}", "\u{fdd0}\u{fffe}\u{10ffff}", " a "] {
        let mut p = payload();
        p["inventory"]["windows"]["version"] = json!(value);
        let r = parse_native_result_payload(&bytes(&p)).unwrap();
        assert_eq!(r.inventory().unwrap().windows().version(), Some(value));
    }
    let p = String::from_utf8(bytes(&payload())).unwrap();
    let signing = |v: &str| {
        result_signing_bytes(
            &parse_native_result_payload(p.replace("\"x\"", v).as_bytes()).unwrap(),
        )
        .unwrap()
    };
    assert_eq!(signing("\"\u{1f680}\""), signing(r#""\ud83d\ude80""#));
    assert_eq!(signing("\"é\""), signing(r#""\u00e9""#));
    assert_ne!(signing("\"é\""), signing("\"e\u{301}\""));
    let actual = signing(r#""\u0000\n\t\u001f""#);
    assert!(
        String::from_utf8(actual)
            .unwrap()
            .contains(r#""version":"\u0000\n\t\u001f""#)
    );
}

#[test]
fn payload_and_envelope_raw_byte_caps_count_whitespace_utf8_and_escapes() {
    for spelling in ["\"x\"", "\"é\"", r#""\u00e9""#] {
        let p = String::from_utf8(bytes(&payload()))
            .unwrap()
            .replace("\"x\"", spelling);
        let e = format!(r#"{{"payload":{p},"signatureDerHex":"{DER}"}}"#);
        for (raw, is_envelope) in [(p, false), (e, true)] {
            for n in [4095, 4096, 4097] {
                let padded = format!("{}{}", raw, " ".repeat(n - raw.len()));
                assert_eq!(padded.len(), n);
                let result = if is_envelope {
                    parse_native_result(padded.as_bytes()).map(|_| ())
                } else {
                    parse_native_result_payload(padded.as_bytes()).map(|_| ())
                };
                if n <= 4096 {
                    assert!(result.is_ok());
                } else {
                    assert_eq!(result, Err(ResultError::EnvelopeTooLarge));
                }
            }
        }
    }
    assert_eq!(
        parse_native_result_payload(&vec![0xff; 4097]).unwrap_err(),
        ResultError::EnvelopeTooLarge
    );
    assert_eq!(
        parse_native_result(&vec![0xff; 4097]).unwrap_err(),
        ResultError::EnvelopeTooLarge
    );
}

#[test]
fn signature_transport_and_strict_der_rejection_matrix() {
    for bad in [
        "".into(),
        "0".into(),
        "AA".into(),
        "0x01".into(),
        "aa\n".into(),
        "00".repeat(73),
    ] {
        let mut e = envelope(payload());
        e["signatureDerHex"] = json!(bad);
        assert_eq!(
            parse_native_result(&bytes(&e)).unwrap_err(),
            ResultError::InvalidSignatureEncoding
        );
    }
    let order = "ffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551";
    let above = "ffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632552";
    let mut bad = vec![
        "3106020101020101".into(),
        "3007020101020101".into(),
        "308106020101020101".into(),
        "30800201010201010000".into(),
        "3003020101".into(),
        "3009020101020101020101".into(),
        "30050200020101".into(),
        "3006020180020101".into(),
        "3006020100020101".into(),
        "3006020101020100".into(),
        "3006020101020180".into(),
        "300702010102020001".into(),
        "30060201010201".into(),
        "3006020101030101".into(),
        "300702810101020101".into(),
        "30820006020101020101".into(),
        "300702020001020101".into(),
        "300602010102010100".into(),
        "aa".into(),
        "00".repeat(64),
    ];
    for n in [order, above] {
        bad.push(format!("3026022100{n}020101"));
        bad.push(format!("3026020101022100{n}"));
    }
    for hex in bad {
        let mut e = envelope(payload());
        e["signatureDerHex"] = json!(hex);
        assert_eq!(
            parse_native_result(&bytes(&e)).unwrap_err(),
            ResultError::InvalidDer,
            "{hex}"
        );
    }
}

#[test]
fn complete_registry_closure_is_frozen() {
    fn blocks(lock: &str) -> Vec<&str> {
        let mut records = lock
            .split("[[package]]")
            .skip(1)
            .map(str::trim)
            .filter(|b| b.contains("source ="))
            .collect::<Vec<_>>();
        records.sort_unstable();
        records
    }
    let old = include_str!("../../native-protocol/Cargo.lock");
    let new = include_str!("../Cargo.lock");
    assert_eq!(blocks(old), blocks(new));
    let locals = new
        .split("[[package]]")
        .skip(1)
        .filter(|b| !b.contains("source ="))
        .collect::<Vec<_>>();
    assert_eq!(locals.len(), 2);
    assert!(
        locals
            .iter()
            .any(|b| b.contains("name = \"hub-relay-native-result\""))
    );
    assert!(
        locals
            .iter()
            .any(|b| b.contains("name = \"hub-relay-native-protocol\""))
    );
    assert!(
        blocks(new)
            .iter()
            .all(|b| b
                .contains("source = \"registry+https://github.com/rust-lang/crates.io-index\""))
    );
}

#[test]
fn exact_positional_arrays_cannot_bypass_any_object_boundary() {
    let base = envelope(payload());
    for (path, keys) in [
        ("", vec!["payload", "signatureDerHex"]),
        (
            "/payload",
            vec![
                "version",
                "requestDigest",
                "targetId",
                "profileId",
                "state",
                "errorCode",
                "inventory",
            ],
        ),
        ("/payload/inventory", vec!["windows", "powershell7", "node"]),
        ("/payload/inventory/windows", vec!["state", "version"]),
        ("/payload/inventory/powershell7", vec!["state", "version"]),
        ("/payload/inventory/node", vec!["state", "version"]),
    ] {
        let positional = Value::Array(
            keys.iter()
                .map(|k| base.pointer(path).unwrap()[k].clone())
                .collect(),
        );
        let mut value = base.clone();
        *value.pointer_mut(path).unwrap() = positional.clone();
        rejects(&value);
        if path == "/payload" {
            assert!(parse_native_result_payload(&bytes(&positional)).is_err());
        }
    }
}

#[test]
fn state_code_inventory_cartesian_table_keeps_each_constraint_independent() {
    let codes = [
        None,
        Some("NOT_AUTHORIZED"),
        Some("EXPIRED"),
        Some("REVOKED"),
        Some("REPLAY"),
        Some("BINDING_MISMATCH"),
        Some("COLLECTOR_FAILED"),
        Some("TIMEOUT"),
        Some("OVERFLOW"),
        Some("INTERRUPTED"),
        Some("CANCELLED"),
        Some("UNKNOWN"),
    ];
    for state in ["completed", "denied", "failed", "cancelled", "unknown"] {
        for code in codes {
            for has_inventory in [false, true] {
                let mut p = payload();
                p["state"] = json!(state);
                p["errorCode"] = json!(code);
                if !has_inventory {
                    p["inventory"] = Value::Null;
                }
                let allowed = match state {
                    "completed" => code.is_none() && has_inventory,
                    "denied" => {
                        !has_inventory
                            && matches!(
                                code,
                                Some(
                                    "NOT_AUTHORIZED"
                                        | "EXPIRED"
                                        | "REVOKED"
                                        | "REPLAY"
                                        | "BINDING_MISMATCH"
                                )
                            )
                    }
                    "failed" => {
                        !has_inventory
                            && matches!(
                                code,
                                Some("COLLECTOR_FAILED" | "TIMEOUT" | "OVERFLOW" | "INTERRUPTED")
                            )
                    }
                    "cancelled" => !has_inventory && code == Some("CANCELLED"),
                    _ => false,
                };
                assert_eq!(
                    parse_native_result_payload(&bytes(&p)).is_ok(),
                    allowed,
                    "{state}/{code:?}/{has_inventory}"
                );
            }
        }
    }
}

#[test]
fn raw_grammar_gates_apply_independently_to_payload_and_envelope() {
    for is_envelope in [false, true] {
        let raw = String::from_utf8(bytes(&if is_envelope {
            envelope(payload())
        } else {
            payload()
        }))
        .unwrap();
        let accepts = |b: &[u8]| {
            if is_envelope {
                parse_native_result(b).is_ok()
            } else {
                parse_native_result_payload(b).is_ok()
            }
        };
        for malformed in [
            vec![],
            vec![0xff],
            vec![0xc0, 0xaf],
            vec![0xf4, 0x90, 0x80, 0x80],
            vec![0xed, 0xa0, 0x80],
        ] {
            assert!(!accepts(&malformed));
        }
        assert!(!accepts(
            &[b"\xef\xbb\xbf".as_slice(), raw.as_bytes()].concat()
        ));
        for suffix in ["{}", "null", "x"] {
            assert!(!accepts(format!("{raw}{suffix}").as_bytes()));
        }
        for control in 0..=31 {
            assert!(!accepts(
                raw.replace(
                    "\"x\"",
                    &format!("\"{}\"", char::from_u32(control).unwrap())
                )
                .as_bytes()
            ));
        }
        for malformed in [
            r#""\ud800""#,
            r#""\udc00""#,
            r#""\ud800\ud800""#,
            r#""\udc00\ud800""#,
            r#""\udc00\udc00""#,
            "NaN",
            "Infinity",
            "-Infinity",
        ] {
            assert!(!accepts(raw.replace("\"x\"", malformed).as_bytes()));
        }
        assert!(accepts(format!(" \t\r\n{raw}\r\n").as_bytes()));
        assert!(accepts(
            raw.replace("\"x\"", r#""\ud83d\ude80""#).as_bytes()
        ));
    }
}
