from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "ops" / "ec2" / "preflight-deploy.sh"
EVIDENCE = ROOT / "ops" / "ec2" / "intake-smoke-evidence.py"
RUNBOOK = ROOT / "ops" / "ec2" / "ISSUE_1831_RUNBOOK.md"


def test_host_preflight_is_noninteractive_and_fails_closed() -> None:
    text = PREFLIGHT.read_text(encoding="utf-8")
    command_inventory = text.split("for command_name in", 1)[1].split("; do", 1)[0]

    assert "MIN_DISK_KIB=3145728" in text
    assert "MIN_FREE_INODES=50000" in text
    assert "MIN_AVAILABLE_MEMORY_KIB=524288" in text
    assert "MAX_LOAD_1M=2.00" in text
    assert "sudo -n true" in text
    assert "sudo -n systemctl is-active --quiet hub-api.service" in text
    assert 'df -Pk "$APP_ROOT"' in text
    assert 'df -Pi "$APP_ROOT"' in text
    assert "free -k" in text
    assert "/proc/loadavg" in text
    assert 'git ls-remote "$REPO_URL" HEAD' in text
    assert "--proto '=https'" in text
    assert "current_launcher_sha256=" in text
    assert "previous_launcher_sha256=" in text
    assert "previous_state_status=" in text
    assert 'PREVIOUS_STATE_STATUS="legacy-unattested-not-deploy-rollback-target"' in text
    assert 'validate_release "$CURRENT_RELEASE" "$SHARED_RELEASE_STATE" "yes"' in text
    assert 'cmp -s "$CURRENT_RELEASE_STATE" "$SHARED_RELEASE_STATE"' in text
    assert '[ "$SHARED_LAUNCHER_SHA256" = "$CURRENT_LAUNCHER_SHA256" ]' in text
    for command_name in (
        "basename",
        "cat",
        "cp",
        "dirname",
        "head",
        "stat",
        "tee",
        "tr",
    ):
        assert command_name in command_inventory
    assert "systemctl restart" not in text


def test_runbook_retains_reviewed_tools_and_uses_allowlisted_evidence() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "<fresh-reviewed-main-sha>" in text
    assert "9d6771994095e4fc04e8fdbf2caa644ccb002ab1" in text
    assert "shared/reviewed-tools/$TARGET_SHA" in text
    assert "Do not put it behind an" in text
    assert "preflight-deploy.sh" in text
    assert "adopt-legacy-current.sh" in text
    assert text.index("adopt-legacy-current.sh") < text.index("preflight-deploy.sh")
    assert "LEGACY_RELEASE_STATE" in text
    assert "legacy_state_sha256=" in text
    assert "legacy-unattested-not-deploy-rollback-target" in text
    assert "sudo -n systemctl restart hub-api.service" in text
    assert "intake-smoke-evidence.py" in text
    assert '"running_commit": status.get("running_commit")' in text
    assert 'expected_launcher_sha256 = sys.argv[4]' in text
    assert 'evidence["running_launcher_sha256"] != expected_launcher_sha256' in text
    assert 'cmp -s "$DEPLOYED_RELEASE_STATE" "$APP_ROOT/shared/RELEASE_STATE"' in text
    assert 'cmp -s "$RESTORED_RELEASE_STATE" "$APP_ROOT/shared/RELEASE_STATE"' in text
    assert 'if release_state_raw != shared_state_raw:' in text
    assert 'if versioned_launcher_raw != shared_launcher_raw:' in text
    assert 'evidence["running_release"] != expected_release' in text
    assert 'evidence["configured_current_release"] != expected_release' in text
    assert "--fail-with-body" in text
    assert 'install -m 0600 /dev/null "$RESPONSE"' in text
    assert text.index('install -m 0600 /dev/null "$RESPONSE"') < text.index(
        "set +e\nHTTP_CODE="
    )
    assert text.index("CURL_RC=$?") < text.index(
        'python3 "$DEPLOYED_RELEASE/ops/ec2/intake-smoke-evidence.py"'
    )
    assert '"release_state": status.get(' not in text
    assert "python3 -m json.tool" not in text
    assert "DNS, TLS, nginx" in text
    assert "PY_ROLLBACK_STATE" in text
    assert "PY_ROLLBACK_STATUS" in text
    assert '"to_launcher_sha256"' in text
    assert 'evidence["running_commit"] != expected_commit' in text


def test_smoke_evidence_ignores_text_and_every_unknown_field(
    tmp_path: Path,
) -> None:
    secret_text = "ARTICLE BODY MUST NEVER BE PRINTED"
    response = tmp_path / "response.json"
    response.write_text(
        json.dumps(
            {
                "status": "ok",
                "final_url": "https://example.com/article",
                "source_domain": "example.com",
                "retrieved_at_utc": "2026-08-02T12:00:00+00:00",
                "text": secret_text,
                "content_type": "text/html; charset=utf-8",
                "bytes_read": 4096,
                "truncated": False,
                "verification_status": "unreviewed",
                "title": "Must not escape",
                "message": "Must not escape",
                "debug": {"raw_body": "Must not escape"},
                "body": "Must not escape",
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(EVIDENCE),
            str(response),
            "200",
            "0",
            "a" * 40,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert secret_text not in result.stdout
    assert "Must not escape" not in result.stdout
    evidence = json.loads(result.stdout)
    assert set(evidence) == {
        "bytes_read",
        "content_type",
        "curl_exit_code",
        "error_code",
        "final_domain",
        "final_url",
        "http_status",
        "response_status",
        "retrieved_at_utc",
        "source_domain",
        "target_commit",
        "text_characters",
        "text_present",
        "text_sha256",
        "truncated",
        "verification_status",
    }
    assert evidence["text_present"] is True
    assert evidence["text_characters"] == len(secret_text)
    assert len(evidence["text_sha256"]) == 64
    assert "text" not in evidence
    assert "title" not in evidence
    assert "message" not in evidence
    assert "debug" not in evidence
    assert "body" not in evidence


def test_controlled_failure_evidence_exposes_only_stable_error_code(
    tmp_path: Path,
) -> None:
    response = tmp_path / "response.json"
    response.write_text(
        json.dumps(
            {
                "status": "error",
                "error": "url_fetch_failed",
                "message": "upstream body or debug detail",
                "url": "https://example.com/article",
                "verification_status": "unreviewed",
                "unexpected_body": "secret",
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [str(EVIDENCE), str(response), "502", "22", "b" * 40],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "required HTTP 200" in result.stderr
    assert "upstream body" not in result.stdout
    assert "secret" not in result.stdout
    evidence = json.loads(result.stdout)
    assert evidence["response_status"] == "error"
    assert evidence["error_code"] == "url_fetch_failed"
    assert "message" not in evidence
    assert "unexpected_body" not in evidence


def test_success_payload_is_rejected_without_http_200(
    tmp_path: Path,
) -> None:
    response = tmp_path / "response.json"
    response.write_text(
        json.dumps(
            {
                "status": "ok",
                "final_url": "https://example.com/article",
                "source_domain": "example.com",
                "retrieved_at_utc": "2026-08-02T12:00:00+00:00",
                "text": "retained but never printed",
                "content_type": "text/html",
                "bytes_read": 256,
                "truncated": False,
                "verification_status": "unreviewed",
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [str(EVIDENCE), str(response), "201", "0", "c" * 40],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "required HTTP 200" in result.stderr
    assert "retained but never printed" not in result.stdout
    evidence = json.loads(result.stdout)
    assert evidence["http_status"] == 201
    assert evidence["response_status"] == "ok"
