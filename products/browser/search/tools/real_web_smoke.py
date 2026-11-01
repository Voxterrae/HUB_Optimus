#!/usr/bin/env python3
"""Disposable, owner-dispatched real-Web QA. Never an application endpoint default."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

SEARX_COMMIT = "8b35dcd2e312d1d30fcfcbf6a9d01bda6fc52192"
REQUIREMENTS_BLOB = "0a1dec671f4d26605a66032aa884c5bffd3d6945"
SEARX_PORT = 18888
API_URL = "https://api.mwmbl.org/api/v1"


class Cancelled(Exception):
    """A supervisor interrupt; no raw signal or child output is reported."""


def check_cancellation(cancelled):
    if cancelled is not None and cancelled():
        raise Cancelled()


def validate_source(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("invalid-source")
    return value


def settings():
    return {
        "use_default_settings": {"engines": {"keep_only": ["mwmbl"]}},
        "general": {"debug": False, "enable_metrics": False},
        "search": {"formats": ["json"], "autocomplete": "", "favicon_resolver": ""},
        "server": {"bind_address": "127.0.0.1", "port": SEARX_PORT,
                   "limiter": False, "public_instance": False, "image_proxy": False},
        "valkey": {"url": False}, "redis": {"url": False}, "plugins": {},
        "outgoing": {"request_timeout": 8.0, "max_request_timeout": 8.0,
                     "retries": 0, "retry_on_http_error": False, "verify": True},
        "engines": [{"name": "mwmbl", "disabled": False, "api_url": API_URL,
                     "timeout": 8.0, "retries": 0, "retry_on_http_error": False}],
    }


def process_environment():
    # Do not give the temporary upstream process Actions credentials or ambient proxies.
    return {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "DOTNET_ROOT", "RUNNER_TEMP")
            if key in os.environ}


def searx_environment(source, temporary, secret):
    environment = process_environment()
    environment.update(PYTHONPATH=str(source), SEARXNG_SETTINGS_PATH=str(temporary / "settings.yml"),
                       SEARXNG_SECRET=secret, SEARXNG_DEBUG="false", TMPDIR=str(temporary),
                       XDG_CACHE_HOME=str(temporary / "cache"), PYTHONDONTWRITEBYTECODE="1")
    return environment


def require_free_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", port))


def stop_owned(process, seconds=5.0):
    """Only signal the Popen handle we started. A forced exit never passes cleanup."""
    if process.poll() is not None:
        return process.returncode == 0
    try:
        process.terminate()
        code = process.wait(timeout=seconds)
        return code in (0, -signal.SIGTERM)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
            process.wait(timeout=seconds)
        except (OSError, subprocess.SubprocessError):
            pass
        return False
    except (OSError, subprocess.SubprocessError):
        try:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=seconds)
        except (OSError, subprocess.SubprocessError):
            pass
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def wait_health(process, seconds=30.0, cancelled=None):
    deadline = time.monotonic() + seconds
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    while time.monotonic() < deadline:
        check_cancellation(cancelled)
        if process.poll() is not None:
            return False
        try:
            with opener.open(f"http://127.0.0.1:{SEARX_PORT}/healthz", timeout=1) as response:
                if response.status == 200 and response.read(129) == b"OK":
                    return True
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.2)
    return False


def checkout(root, expected):
    actual = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if actual != expected:
        raise ValueError("checkout-mismatch")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependency_provenance(python, source, report):
    requirements = (source / "requirements.txt").read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(requirements)).encode("ascii") + b"\0" + requirements).hexdigest()
    if blob != REQUIREMENTS_BLOB:
        raise ValueError("requirements-mismatch")
    direct = [line.strip() for line in requirements.decode("utf-8").splitlines()
              if line.strip() and not line.lstrip().startswith("#")]
    if not all(re.fullmatch(r"[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[A-Za-z0-9_.+!-]+", item)
               for item in direct):
        raise ValueError("requirements-unpinned")
    command = ("import importlib.metadata,json;print(json.dumps(sorted("
               "(d.metadata['Name'],d.version) for d in importlib.metadata.distributions())))")
    installed = json.loads(subprocess.run([str(python), "-c", command], capture_output=True,
                                          text=True, timeout=15, check=True).stdout)
    if len(installed) > 200 or any(not re.fullmatch(r"[A-Za-z0-9_.+!-]{1,100}", str(part))
                                   for pair in installed for part in pair):
        raise ValueError("dependency-report-invalid")
    return {"requirementsBlob": blob, "requirementsSha256": hashlib.sha256(requirements).hexdigest(),
            "directPins": direct, "installedVersions": installed,
            "pipInstallReportSha256": digest(report), "hermetic": False}


def official_domain(host, query_id):
    if not isinstance(host, str) or len(host) > 253 or host != host.lower():
        return False
    allowed = {"python": ("python.org", "docs.python.org"),
               "firefox": ("mozilla.org", "firefox.com")}.get(query_id, ())
    return any(host == domain or host.endswith("." + domain) for domain in allowed)


def curate_probe(value, expected_source=None):
    # Reject unexpected fields rather than emitting output controlled by product/upstream text.
    if not isinstance(value, dict) or set(value) != {"status", "passed", "source", "provenanceVerified", "reason", "stage", "ready", "queries", "cleanup"}:
        raise ValueError("probe-report-invalid")
    if value["status"] not in ("passed", "blocked") or any(type(value[key]) is not bool for key in ("ready", "passed", "provenanceVerified")):
        raise ValueError("probe-report-invalid")
    if value["source"] is not None:
        validate_source(value["source"])
    if value["passed"] != (value["status"] == "passed") or expected_source is not None and value["source"] != expected_source:
        raise ValueError("probe-report-invalid")
    if value["reason"] not in {"none", "not-started", "invalid-arguments", "source-mismatch", "host-start-failed", "host-output-limit", "host-exited-before-health", "invalid-profile-identity", "invalid-health-protocol", "health-size-limit", "web-result-blocked", "cancelled", "probe-blocked", "cleanup-failed"} or value["stage"] not in {"arguments", "provenance", "host-preflight", "health", "python", "firefox", "cleanup", "none"}:
        raise ValueError("probe-report-invalid")
    cleanup = value["cleanup"]
    if not isinstance(cleanup, dict) or set(cleanup) != {"attempted", "normalExit", "forced", "profileRemoved", "failed"} or any(type(v) is not bool for v in cleanup.values()):
        raise ValueError("probe-report-invalid")
    queries = value["queries"]
    if not isinstance(queries, list) or len(queries) > 2:
        raise ValueError("probe-report-invalid")
    for index, item in enumerate(queries):
        if not isinstance(item, dict) or set(item) != {"id", "typedWeb", "sourceVerified", "officialDomain", "topicMatched", "passed"}:
            raise ValueError("probe-report-invalid")
        if item["id"] != ("python", "firefox")[index] or any(type(item[key]) is not bool for key in ("typedWeb", "sourceVerified", "topicMatched", "passed")):
            raise ValueError("probe-report-invalid")
        if item["officialDomain"] is not None and not official_domain(item["officialDomain"], item["id"]):
            raise ValueError("probe-report-invalid")
    if value["status"] == "passed" and (not value["ready"] or not value["provenanceVerified"] or value["source"] is None or len(queries) != 2
            or cleanup != {"attempted": True, "normalExit": True, "forced": False, "profileRemoved": True, "failed": False}
            or any(not all(item[key] for key in ("typedWeb", "sourceVerified", "topicMatched", "passed"))
                   or item["officialDomain"] is None for item in queries)):
        raise ValueError("probe-report-invalid")
    return value


def cancel_probe(process):
    """Let the exact owned probe close its own host before upstream shutdown."""
    if process.poll() is None:
        try:
            process.send_signal(signal.SIGINT)
        except ProcessLookupError:
            pass
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate(timeout=5)


def execute_probe(command, environment, source, cancelled=None):
    check_cancellation(cancelled)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment)
    try:
        deadline = time.monotonic() + 90
        while True:
            check_cancellation(cancelled)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("probe-timeout")
            try:
                output, _ = process.communicate(timeout=min(0.2, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
    except BaseException:
        cancel_probe(process)
        raise
    if len(output) > 16384:
        raise ValueError("probe-report-invalid")
    result = curate_probe(json.loads(output), source)
    if (process.returncode == 0) != (result["status"] == "passed"):
        raise ValueError("probe-report-invalid")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("product-root", "harness-root", "searx-root", "searx-python", "host", "probe", "dependency-report"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--workflow", required=True)
    args = parser.parse_args()
    result = {"status": "blocked", "reason": "preflight", "sourceCommit": None,
              "workflowCommit": None, "searxCommit": SEARX_COMMIT, "searxCleanup": False}
    owned = None
    interrupted = False
    def interrupt(signum, frame):
        nonlocal interrupted
        # Do not raise between Popen creation and handle assignment, or during cleanup.
        interrupted = True
    previous_signals = {number: signal.signal(number, interrupt) for number in (signal.SIGINT, signal.SIGTERM)}
    cancelled = lambda: interrupted
    try:
        check_cancellation(cancelled)
        result.update(sourceCommit=validate_source(args.source), workflowCommit=validate_source(args.workflow))
        checkout(args.product_root, args.source)
        checkout(args.harness_root, args.workflow)
        checkout(args.searx_root, SEARX_COMMIT)
        result["dependencies"] = dependency_provenance(args.searx_python, args.searx_root, args.dependency_report)
        check_cancellation(cancelled)
        require_free_port(SEARX_PORT)
        require_free_port(17831)
        runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
        with tempfile.TemporaryDirectory(prefix="optimus-real-web-", dir=runner_temp) as temporary_name:
            temporary = Path(temporary_name)
            os.chmod(temporary, 0o700)
            config = temporary / "settings.yml"
            config.write_text(json.dumps(settings()), encoding="utf-8")
            os.chmod(config, 0o600)
            environment = searx_environment(args.searx_root.resolve(), temporary, secrets.token_hex(32))
            # Keep the venv executable path: resolving its symlink discards pyvenv.cfg.
            owned = subprocess.Popen([str(args.searx_python.absolute()), "-m", "searx.webapp"],
                                     cwd=args.searx_root, env=environment,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                if not wait_health(owned, cancelled=cancelled):
                    raise ValueError("searx-health-blocked")
                result["probe"] = execute_probe(["dotnet", str(args.probe.resolve()), "--host", str(args.host.resolve()),
                    "--profile", str(temporary / "profile"), "--source", args.source], process_environment(), args.source, cancelled)
                result["status"] = result["probe"]["status"]
                result["reason"] = "accepted" if result["status"] == "passed" else "upstream-blocked"
            finally:
                result["searxCleanup"] = stop_owned(owned)
                owned = None
                if not result["searxCleanup"]:
                    result.update(status="blocked", reason="cleanup-failed")
    except Cancelled:
        result.update(status="blocked", reason="cancelled")
    except (OSError, ValueError, subprocess.SubprocessError, KeyError, json.JSONDecodeError):
        result.update(status="blocked", reason="execution-blocked")
    finally:
        if owned is not None:
            result["searxCleanup"] = stop_owned(owned)
        if not result["searxCleanup"]:
            result["status"] = "blocked"
        if interrupted:
            result.update(status="blocked", reason="cancelled")
        for number, handler in previous_signals.items():
            signal.signal(number, handler)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    sys.exit(main())
