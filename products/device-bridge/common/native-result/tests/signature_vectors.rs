use hub_relay_native_protocol::{parse_request_payload, request_digest};
use hub_relay_native_result::{
    ResultError, parse_native_result, parse_native_result_payload, result_signing_bytes,
    serialize_native_result, verify_native_result_signature,
};
use p256::ecdsa::{Signature, VerifyingKey, signature::Verifier};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
fn vectors() -> Value {
    serde_json::from_str(include_str!(
        "../proposal/vectors/native_result_signature.v0_1.json"
    ))
    .unwrap()
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn decode(value: &str) -> Vec<u8> {
    (0..value.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&value[i..i + 2], 16).unwrap())
        .collect()
}
fn text<'a>(v: &'a Value, k: &str) -> &'a str {
    v[k].as_str().unwrap()
}
fn result(case: &Value, form: &str) -> hub_relay_native_result::NativeResult {
    parse_native_result(
        &serde_json::to_vec(&json!({"payload":case["payload"],"signatureDerHex":case[form]}))
            .unwrap(),
    )
    .unwrap()
}

#[test]
fn all_eleven_frozen_results_match_bytes_digest_both_s_forms_and_envelope() {
    let v = vectors();
    let q = parse_request_payload(&serde_json::to_vec(&v["expectedRequest"]).unwrap()).unwrap();
    let key = decode(text(&v["keys"]["broker"], "publicSec1Hex"));
    assert_eq!(
        hex(&request_digest(&q).unwrap()),
        text(&v, "expectedRequestDigest")
    );
    let cases = v["results"].as_array().unwrap();
    assert_eq!(cases.len(), 11);
    for case in cases {
        let p =
            parse_native_result_payload(&serde_json::to_vec(&case["payload"]).unwrap()).unwrap();
        let signing = result_signing_bytes(&p).unwrap();
        assert_eq!(hex(&signing), text(case, "signingBytesHex"));
        assert_eq!(
            hex(&Sha256::digest(&signing)),
            text(case, "digestSha256Hex")
        );
        assert_eq!(
            &signing[b"HUB-RELAY-RESULT-v0.1\0".len()..],
            text(case, "canonicalPayload").as_bytes()
        );
        assert_eq!(
            hex(text(case, "canonicalPayload").as_bytes()),
            text(case, "canonicalUtf8Hex")
        );
        for form in ["signatureLowSDerHex", "signatureHighSDerHex"] {
            let r = result(case, form);
            assert_eq!(verify_native_result_signature(&r, &q, &key), Ok(()));
            let expected = format!(
                r#"{{"payload":{},"signatureDerHex":"{}"}}"#,
                text(case, "canonicalPayload"),
                text(case, form)
            )
            .into_bytes();
            assert_eq!(serialize_native_result(&r).unwrap(), expected);
            assert_eq!(
                serialize_native_result(&parse_native_result(&expected).unwrap()).unwrap(),
                expected
            );
        }
    }
}

#[test]
fn eight_frozen_counterexamples_isolate_binding_and_hash_domain_failures() {
    let v = vectors();
    let q = parse_request_payload(&serde_json::to_vec(&v["expectedRequest"]).unwrap()).unwrap();
    let key = decode(text(&v["keys"]["broker"], "publicSec1Hex"));
    let other = decode(text(&v["keys"]["other"], "publicSec1Hex"));
    let examples = v["counterexamples"].as_object().unwrap();
    assert_eq!(examples.len(), 8);
    for (name, case) in examples {
        for form in ["signatureLowSDerHex", "signatureHighSDerHex"] {
            let r = result(case, form);
            let expected = match name.as_str() {
                "targetId" => ResultError::TargetMismatch,
                "profileId" => ResultError::ProfileMismatch,
                "requestDigest" => ResultError::RequestDigestMismatch,
                _ => ResultError::VerificationFailed,
            };
            // Independent pinned primitive verifies the signed counterexample first,
            // so failure of signature math cannot mask a missing binding check.
            let mathematical_key = if name == "otherKey" { &other } else { &key };
            let signature = Signature::from_der(&decode(text(case, form))).unwrap();
            VerifyingKey::from_sec1_bytes(mathematical_key)
                .unwrap()
                .verify(&decode(text(case, "signingBytesHex")), &signature)
                .unwrap();
            assert_eq!(
                verify_native_result_signature(&r, &q, &key),
                Err(expected),
                "{name}/{form}"
            );
            if name == "otherKey" {
                assert_eq!(
                    verify_native_result_signature(&r, &q, &other),
                    Err(ResultError::KeyIdMismatch)
                );
            }
        }
    }
}

#[test]
fn independently_selected_request_fields_bind_the_fixed_result() {
    let v = vectors();
    let key = decode(text(&v["keys"]["broker"], "publicSec1Hex"));
    let r = result(&v["results"][0], "signatureLowSDerHex");
    for name in [
        "nonce",
        "requestId",
        "brokerKeyId",
        "enrollmentGeneration",
        "brokerStartGeneration",
    ] {
        let mut value = v["expectedRequest"].clone();
        let n = text(&value, name).len();
        value[name] = json!("7".repeat(n));
        let q = parse_request_payload(&serde_json::to_vec(&value).unwrap()).unwrap();
        assert_eq!(
            verify_native_result_signature(&r, &q, &key),
            Err(if name == "brokerKeyId" {
                ResultError::KeyIdMismatch
            } else {
                ResultError::RequestDigestMismatch
            }),
            "{name}"
        );
    }
}

#[test]
fn supplied_sec1_is_exact_uncompressed_valid_point() {
    let v = vectors();
    let q = parse_request_payload(&serde_json::to_vec(&v["expectedRequest"]).unwrap()).unwrap();
    let key = decode(text(&v["keys"]["broker"], "publicSec1Hex"));
    let r = result(&v["results"][0], "signatureLowSDerHex");
    let mut compressed = vec![3];
    compressed.extend_from_slice(&key[1..33]);
    let mut hybrid = key.clone();
    hybrid[0] = 6;
    let mut wrong_tag = key.clone();
    wrong_tag[0] = 5;
    let mut off_curve = vec![0; 65];
    off_curve[0] = 4;
    for bad in [
        vec![],
        vec![0],
        compressed,
        hybrid,
        wrong_tag,
        off_curve,
        key[..64].to_vec(),
        [key.clone(), vec![0]].concat(),
        vec![4; 65],
    ] {
        assert_eq!(
            verify_native_result_signature(&r, &q, &bad),
            Err(ResultError::InvalidPublicKey)
        );
    }
}

#[test]
fn structurally_valid_but_false_der_fails_only_mathematics() {
    let v = vectors();
    let q = parse_request_payload(&serde_json::to_vec(&v["expectedRequest"]).unwrap()).unwrap();
    let key = decode(text(&v["keys"]["broker"], "publicSec1Hex"));
    let r = parse_native_result(
        &serde_json::to_vec(
            &json!({"payload":v["results"][0]["payload"],"signatureDerHex":"3006020101020101"}),
        )
        .unwrap(),
    )
    .unwrap();
    assert_eq!(
        verify_native_result_signature(&r, &q, &key),
        Err(ResultError::VerificationFailed)
    );
}
