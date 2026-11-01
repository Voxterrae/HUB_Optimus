use hub_relay_native_protocol::{
    ApprovalMatchError, SignatureError,
    approval_digest, approval_signing_bytes, parse_approval_envelope, parse_request_envelope,
    request_digest, request_signing_bytes, verify_approval_for_pending_request,
    verify_approval_signature, verify_request_signature,
};
use serde_json::{Value, json};

// Fixture maps exist only in this test. Production parsing uses validated closed structs.
fn fixture() -> Value {
    serde_json::from_str(include_str!("../vectors/native_signature.v0_1.json")).unwrap()
}

fn unhex(input: &str) -> Vec<u8> {
    assert_eq!(input.len() % 2, 0);
    input
        .as_bytes()
        .as_chunks::<2>()
        .0
        .iter()
        .map(|pair| u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap())
        .collect()
}

fn key(vector: &Value, name: &str) -> Vec<u8> {
    unhex(vector["keys"][name]["publicSec1Hex"].as_str().unwrap())
}

fn envelope(vector: &Value, name: &str, signature: &str) -> Vec<u8> {
    serde_json::to_vec(&json!({"payload": vector[name]["payload"],
        "signatureDerHex": vector[name][signature]}))
    .unwrap()
}

#[test]
fn exact_request_bytes_and_digest_match_independent_node_crypto() {
    let vector = fixture();
    let request =
        parse_request_envelope(&envelope(&vector, "request", "signatureLowSDerHex")).unwrap();
    assert_eq!(
        request_signing_bytes(request.payload()).unwrap(),
        unhex(vector["request"]["signingBytesHex"].as_str().unwrap())
    );
    assert_eq!(
        request_digest(request.payload()).unwrap().as_slice(),
        unhex(vector["request"]["digestSha256Hex"].as_str().unwrap())
    );
}

#[test]
fn exact_approval_bytes_and_digest_match_independent_node_crypto() {
    let vector = fixture();
    let approval =
        parse_approval_envelope(&envelope(&vector, "approval", "signatureLowSDerHex")).unwrap();
    assert_eq!(
        approval_signing_bytes(approval.request()).unwrap(),
        unhex(vector["approval"]["signingBytesHex"].as_str().unwrap())
    );
    assert_eq!(
        approval_digest(approval.request()).unwrap().as_slice(),
        unhex(vector["approval"]["digestSha256Hex"].as_str().unwrap())
    );
    assert_ne!(
        request_digest(approval.request()).unwrap(),
        approval_digest(approval.request()).unwrap()
    );
}

#[test]
fn request_accepts_both_high_s_and_low_s_without_double_hashing() {
    let vector = fixture();
    for signature in ["signatureLowSDerHex", "signatureHighSDerHex"] {
        let request = parse_request_envelope(&envelope(&vector, "request", signature)).unwrap();
        assert!(
            verify_request_signature(&request, &key(&vector, "broker")).is_ok(),
            "{signature}"
        );
    }
}

#[test]
fn approval_accepts_both_high_s_and_low_s_without_double_hashing() {
    let vector = fixture();
    for signature in ["signatureLowSDerHex", "signatureHighSDerHex"] {
        let approval = parse_approval_envelope(&envelope(&vector, "approval", signature)).unwrap();
        assert!(
            verify_approval_signature(&approval, &key(&vector, "approver")).is_ok(),
            "{signature}"
        );
    }
}

#[test]
fn every_schema_valid_binding_change_invalidates_previous_signatures() {
    let original = fixture();
    for binding in [
        "requestId",
        "brokerKeyId",
        "targetId",
        "profileId",
        "enrollmentGeneration",
        "brokerStartGeneration",
        "nonce",
    ] {
        let mut vector = original.clone();
        let old = vector["request"]["payload"][binding].as_str().unwrap();
        let replacement = format!(
            "{}{}",
            if old.starts_with('a') { "b" } else { "a" },
            &old[1..]
        );
        vector["request"]["payload"][binding] = json!(replacement);
        vector["approval"]["payload"]["request"][binding] =
            vector["request"]["payload"][binding].clone();
        let request =
            parse_request_envelope(&envelope(&vector, "request", "signatureLowSDerHex")).unwrap();
        let approval =
            parse_approval_envelope(&envelope(&vector, "approval", "signatureLowSDerHex")).unwrap();
        assert!(
            verify_request_signature(&request, &key(&vector, "broker")).is_err(),
            "request {binding}"
        );
        assert!(
            verify_approval_signature(&approval, &key(&vector, "approver")).is_err(),
            "approval {binding}"
        );
    }
}

#[test]
fn correctly_signed_request_declaring_another_broker_key_id_fails_origin_check() {
    let vector = fixture();
    let request = parse_request_envelope(&envelope(
        &vector,
        "correctlySignedFalseBrokerKeyId",
        "signatureLowSDerHex",
    ))
    .unwrap();
    assert!(verify_request_signature(&request, &key(&vector, "broker")).is_err());
}

#[test]
fn wrong_key_invalid_point_compressed_and_short_public_keys_are_rejected() {
    let vector = fixture();
    let request =
        parse_request_envelope(&envelope(&vector, "request", "signatureLowSDerHex")).unwrap();
    let approval =
        parse_approval_envelope(&envelope(&vector, "approval", "signatureLowSDerHex")).unwrap();
    assert!(verify_request_signature(&request, &key(&vector, "approver")).is_err());
    assert!(verify_approval_signature(&approval, &key(&vector, "broker")).is_err());
    let mut compressed = vec![2];
    compressed.extend_from_slice(&key(&vector, "broker")[1..33]);
    let mut invalid_point = vec![0; 65];
    invalid_point[0] = 4;
    for invalid in [vec![], vec![4; 64], compressed, invalid_point] {
        assert!(verify_request_signature(&request, &invalid).is_err());
        assert!(verify_approval_signature(&approval, &invalid).is_err());
    }
}

#[test]
fn malformed_der_raw64_zero_out_of_range_and_trailing_bytes_are_rejected() {
    let vector = fixture();
    for (name, signature) in vector["malformedDer"].as_object().unwrap() {
        let input = serde_json::to_vec(
            &json!({"payload": vector["request"]["payload"], "signatureDerHex": signature}),
        )
        .unwrap();
        if let Ok(request) = parse_request_envelope(&input) {
            assert!(
                verify_request_signature(&request, &key(&vector, "broker")).is_err(),
                "{name}"
            );
        }
    }
}

#[test]
fn malformed_approval_der_is_rejected_with_its_correct_public_key() {
    let vector = fixture();
    for (name, signature) in vector["malformedApprovalDer"].as_object().unwrap() {
        let input = serde_json::to_vec(
            &json!({"payload": vector["approval"]["payload"], "signatureDerHex": signature}),
        )
        .unwrap();
        if let Ok(approval) = parse_approval_envelope(&input) {
            assert!(
                verify_approval_signature(&approval, &key(&vector, "approver")).is_err(),
                "{name}"
            );
        }
    }
}

#[test]
fn otherwise_correct_signatures_from_wrong_domain_are_rejected() {
    let vector = fixture();
    let request = parse_request_envelope(&envelope(
        &vector,
        "wrongRequestDomain",
        "signatureLowSDerHex",
    ))
    .unwrap();
    let approval = parse_approval_envelope(&envelope(
        &vector,
        "wrongApprovalDomain",
        "signatureLowSDerHex",
    ))
    .unwrap();
    assert!(verify_request_signature(&request, &key(&vector, "broker")).is_err());
    assert!(verify_approval_signature(&approval, &key(&vector, "approver")).is_err());
}

#[test]
fn signatures_cannot_cross_envelope_domains_even_with_same_supplied_key() {
    let vector = fixture();
    let input = serde_json::to_vec(&json!({"payload": vector["approval"]["payload"], "signatureDerHex": vector["request"]["signatureLowSDerHex"]})).unwrap();
    let approval = parse_approval_envelope(&input).unwrap();
    assert!(verify_approval_signature(&approval, &key(&vector, "broker")).is_err());
}

#[test]
fn changed_request_has_different_approval_digest_without_claiming_admission() {
    let mut vector = fixture();
    let original =
        parse_approval_envelope(&envelope(&vector, "approval", "signatureLowSDerHex")).unwrap();
    vector["approval"]["payload"]["request"]["requestId"] =
        json!("77777777777777777777777777777777");
    let changed =
        parse_approval_envelope(&envelope(&vector, "approval", "signatureLowSDerHex")).unwrap();
    assert_ne!(
        approval_digest(original.request()).unwrap(),
        approval_digest(changed.request()).unwrap()
    );
    assert_ne!(
        request_digest(original.request()).unwrap(),
        request_digest(changed.request()).unwrap()
    );
}

#[test]
fn valid_signatures_for_distinct_pending_requests_cannot_be_crossed() {
    let vector = fixture();
    let broker = key(&vector, "broker");
    let approver = key(&vector, "approver");
    let pair = |v: &Value, sig: &str| {
        (
            parse_request_envelope(&envelope(v, "request", sig)).unwrap(),
            parse_approval_envelope(&envelope(v, "approval", sig)).unwrap(),
        )
    };
    let (pending_a, approval_a) = pair(&vector, "signatureLowSDerHex");

    // Only the nonce differs. Using the public fixture scalars 1 and 2,
    // Node crypto.sign("sha256", domain || NUL || JCS(payload), key)
    // signed the modified request and approval respectively.
    let mut other = vector.clone();
    other["request"]["payload"]["nonce"] = json!("a".repeat(64));
    other["approval"]["payload"]["request"] = other["request"]["payload"].clone();
    other["request"]["otherSignature"] = json!(concat!(
        "3045022100beead2e208c7e41d435346a6896d25654e2f0a44d303bc241762df045a373f420",
        "220517faa752a34f1516be826c33623803f4d80f78c2e4825d744f8d18158d55951"
    ));
    other["approval"]["otherSignature"] = json!(concat!(
        "3046022100aa388cfa208953cce195e23acd26b0032e005985fd16261c1432113934b73b91",
        "022100d428f20d606b6c60f4dc3d8a1223e6de31ecd014b029e6e2f15fdfb830789f96"
    ));
    let (pending_b, approval_b) = pair(&other, "otherSignature");

    for (pending, approval) in [(&pending_a, &approval_a), (&pending_b, &approval_b)] {
        assert_eq!(
            verify_approval_for_pending_request(pending, &broker, approval, &approver),
            Ok(())
        );
    }
    for (pending, approval) in [(&pending_a, &approval_b), (&pending_b, &approval_a)] {
        assert_eq!(
            verify_approval_for_pending_request(pending, &broker, approval, &approver),
            Err(ApprovalMatchError::PendingMismatch)
        );
    }
}

#[test]
fn matching_payload_still_requires_both_role_signatures() {
    let vector = fixture();
    let broker = key(&vector, "broker");
    let approver = key(&vector, "approver");
    let request = |name| {
        parse_request_envelope(&envelope(&vector, name, "signatureLowSDerHex")).unwrap()
    };
    let approval = |name| {
        parse_approval_envelope(&envelope(&vector, name, "signatureLowSDerHex")).unwrap()
    };
    assert_eq!(
        verify_approval_for_pending_request(
            &request("wrongRequestDomain"),
            &broker,
            &approval("approval"),
            &approver,
        ),
        Err(ApprovalMatchError::RequestSignature(SignatureError::VerificationFailed))
    );
    assert_eq!(
        verify_approval_for_pending_request(
            &request("request"),
            &broker,
            &approval("wrongApprovalDomain"),
            &approver,
        ),
        Err(ApprovalMatchError::ApprovalSignature(SignatureError::VerificationFailed))
    );
}
