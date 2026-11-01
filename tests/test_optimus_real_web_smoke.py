"""Local synthetic checks only: no external network or real provider queries."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "products/browser/search/tools/real_web_smoke.py"
spec = importlib.util.spec_from_file_location("optimus_real_web_smoke", SCRIPT)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


@pytest.mark.parametrize("value", ["main", "A" * 40, "a" * 39, "a" * 41, "a" * 40 + "\n", "$(false)", "a" * 39 + "g"])
def test_source_guard_rejects_refs_and_injection(value):
    with pytest.raises(ValueError):
        smoke.validate_source(value)


def test_source_guard_accepts_only_complete_lowercase_sha():
    assert smoke.validate_source("a" * 40) == "a" * 40


def test_upstream_config_is_one_ordinary_engine_and_no_shared_state():
    value = smoke.settings()
    assert value["use_default_settings"] == {"engines": {"keep_only": ["mwmbl"]}}
    assert value["engines"] == [{"name": "mwmbl", "disabled": False, "api_url": "https://api.mwmbl.org/api/v1",
                                "timeout": 8.0, "retries": 0, "retry_on_http_error": False}]
    assert value["server"] == {"bind_address": "127.0.0.1", "port": 18888, "limiter": False,
                               "public_instance": False, "image_proxy": False}
    assert value["search"] == {"formats": ["json"], "autocomplete": "", "favicon_resolver": ""}
    assert value["general"] == {"debug": False, "enable_metrics": False}
    assert value["plugins"] == {} and value["valkey"]["url"] is False and value["redis"]["url"] is False
    assert value["outgoing"]["retries"] == 0 and value["outgoing"]["retry_on_http_error"] is False


def test_upstream_child_receives_only_needed_environment(monkeypatch, tmp_path):
    for key in ("GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "HTTP_PROXY", "https_proxy"):
        monkeypatch.setenv(key, "sensitive-fixture")
    environment = smoke.searx_environment(tmp_path, tmp_path, "ephemeral-fixture")
    assert environment["SEARXNG_SECRET"] == "ephemeral-fixture"
    assert environment["TMPDIR"] == str(tmp_path)
    assert not any(key in environment for key in ("GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "HTTP_PROXY", "https_proxy"))
    assert "ephemeral-fixture" not in json.dumps(smoke.settings())


def test_probe_receives_the_runner_temp_ownership_boundary(monkeypatch, tmp_path):
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    assert smoke.process_environment()["RUNNER_TEMP"] == str(tmp_path)


def child(ignore=False):
    program = ("import signal,time; signal.signal(signal.SIGTERM," +
               ("signal.SIG_IGN" if ignore else "lambda *args: exit(0)") +
               "); print('ready',flush=True); time.sleep(60)")
    process = subprocess.Popen([sys.executable, "-c", program], stdout=subprocess.PIPE, text=True)
    assert process.stdout.readline().strip() == "ready"
    return process


def test_cleanup_stops_only_exact_owned_child():
    own, independent = child(), child()
    try:
        assert smoke.stop_owned(own, 0.5)
        assert own.poll() == 0 and independent.poll() is None
    finally:
        smoke.stop_owned(independent, 0.5)


def test_forced_cleanup_is_failure_and_does_not_touch_independent_child():
    own, independent = child(ignore=True), child()
    try:
        assert not smoke.stop_owned(own, 0.1)
        assert own.poll() is not None and independent.poll() is None
    finally:
        if own.poll() is None:
            own.kill(); own.wait()
        smoke.stop_owned(independent, 0.5)


def test_nonzero_early_exit_is_not_clean():
    process = subprocess.Popen([sys.executable, "-c", "raise SystemExit(3)"])
    process.wait()
    assert not smoke.stop_owned(process)


def passing_report():
    return {"status": "passed", "passed": True, "source": "a" * 40, "provenanceVerified": True,
            "reason": "none", "stage": "none", "ready": True,
            "queries": [{"id": key, "typedWeb": True, "sourceVerified": True,
                         "officialDomain": host, "topicMatched": True, "passed": True}
                        for key, host in (("python", "docs.python.org"), ("firefox", "www.mozilla.org"))],
            "cleanup": {"attempted": True, "normalExit": True, "forced": False, "profileRemoved": True, "failed": False}}


def test_report_accepts_two_relevant_queries_with_clean_exit():
    value = passing_report()
    assert smoke.curate_probe(value) == value


@pytest.mark.parametrize("case", ["empty", "wrong-domain", "missing-source", "forced", "raw-output", "wrong-order"])
def test_report_never_turns_missing_irrelevant_or_unclean_evidence_green(case):
    value = passing_report()
    if case == "empty": value["queries"] = []
    elif case == "wrong-domain": value["queries"][0]["officialDomain"] = "python.org.attacker.example"
    elif case == "missing-source": value["queries"][0]["sourceVerified"] = False
    elif case == "forced": value["cleanup"]["forced"] = True
    elif case == "raw-output": value["rawLog"] = "token=private-fixture"
    elif case == "wrong-order": value["queries"].reverse()
    with pytest.raises(ValueError): smoke.curate_probe(value)


def test_blocked_report_may_not_print_arbitrary_reason_text():
    value = passing_report()
    value.update(status="blocked", reason="token=private fixture")
    with pytest.raises(ValueError): smoke.curate_probe(value)


def test_alphabetic_private_reason_is_not_a_curated_stage():
    value = passing_report()
    value.update(status="blocked", passed=False, reason="private-profile")
    with pytest.raises(ValueError): smoke.curate_probe(value)


def test_probe_source_must_match_the_input_even_when_its_own_flag_is_true():
    with pytest.raises(ValueError): smoke.curate_probe(passing_report(), "b" * 40)


def test_profile_cleanup_is_required_for_a_passing_report():
    value = passing_report()
    value["cleanup"]["profileRemoved"] = False
    with pytest.raises(ValueError): smoke.curate_probe(value)


def test_health_is_only_fixed_query_free_local_endpoint(monkeypatch):
    calls = []
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return b"OK"
    class Opener:
        def open(self, url, timeout): calls.append((url, timeout)); return Response()
    monkeypatch.setattr(smoke.urllib.request, "build_opener", lambda *args: Opener())
    class Running:
        def poll(self): return None
    assert smoke.wait_health(Running(), 0.5)
    assert calls == [("http://127.0.0.1:18888/healthz", 1)]


def test_health_redirect_cannot_contact_another_endpoint(monkeypatch):
    contacts = []
    class Target(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            contacts.append("redirect-target")
            self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    target = HTTPServer(("127.0.0.1", 0), Target)
    class Redirect(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{target.server_port}/unexpected")
            self.end_headers()
    health = HTTPServer(("127.0.0.1", 0), Redirect)
    threads = [threading.Thread(target=server.serve_forever, daemon=True) for server in (health, target)]
    for thread in threads: thread.start()
    monkeypatch.setattr(smoke, "SEARX_PORT", health.server_port)
    class Running:
        def poll(self): return None
    try:
        assert not smoke.wait_health(Running(), 0.01)
        assert contacts == []
    finally:
        for server in (health, target): server.shutdown(); server.server_close()
        for thread in threads: thread.join(timeout=2)


def test_main_starts_upstream_inside_its_symlinked_venv(monkeypatch, tmp_path, capsys):
    """The real interpreter must see packages installed only in the new venv."""
    import socket
    environment = tmp_path / "isolated-venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", "--symlinks", str(environment)],
                   check=True, capture_output=True, timeout=15)
    python = environment / "bin" / "python"
    assert python.is_symlink()
    library = Path(subprocess.check_output([str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], text=True).strip())
    (library / "optimus_qa_venv_marker.py").write_text("INSTALLED_ONLY_IN_THIS_VENV = True\n")
    source = tmp_path / "upstream"
    package = source / "searx"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    marker = tmp_path / "observed-prefix"
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    (package / "webapp.py").write_text(
        "import sys\nimport optimus_qa_venv_marker\nfrom http.server import BaseHTTPRequestHandler, HTTPServer\n"
        f"open({str(marker)!r}, 'w').write(sys.prefix)\n"
        "class Health(BaseHTTPRequestHandler):\n"
        " def log_message(self, *args): pass\n"
        " def do_GET(self):\n"
        "  self.send_response(200); self.end_headers(); self.wfile.write(b'OK')\n"
        f"HTTPServer(('127.0.0.1', {port}), Health).serve_forever()\n")
    monkeypatch.setattr(smoke, "SEARX_PORT", port)
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setattr(smoke, "checkout", lambda *args: None)
    monkeypatch.setattr(smoke, "dependency_provenance", lambda *args: {"hermetic": False})
    monkeypatch.setattr(smoke, "execute_probe", lambda *args: passing_report())
    argv = ["real-web", "--source", "a" * 40, "--workflow", "b" * 40]
    for name, value in {"product-root": tmp_path, "harness-root": tmp_path,
                        "searx-root": source, "searx-python": python,
                        "host": tmp_path / "host.dll", "probe": tmp_path / "probe.dll",
                        "dependency-report": tmp_path / "report.json"}.items():
        argv.extend(["--" + name, str(value)])
    monkeypatch.setattr(sys, "argv", argv)
    assert smoke.main() == 0
    assert marker.read_text() == str(environment)
    assert json.loads(capsys.readouterr().out)["searxCleanup"] is True


@pytest.mark.parametrize("interruption", [signal.SIGTERM, signal.SIGINT])
def test_wrapper_cancellation_joins_probe_then_upstream(interruption, tmp_path):
    """Cancel the operator's actual entrypoint PID, rather than its probe alone."""
    import socket
    events = tmp_path / "events"
    source = tmp_path / "upstream"
    package = source / "searx"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    record = f"def record(value):\n with open({str(events)!r}, 'a') as out: out.write(value + '\\n')\n"
    (package / "webapp.py").write_text(
        "import json,os,signal\nfrom http.server import BaseHTTPRequestHandler, HTTPServer\n" + record +
        "record('upstream-start:' + str(os.getpid()))\n"
        "def stop(*args): record('upstream-stop'); raise SystemExit(0)\n"
        "signal.signal(signal.SIGTERM, stop)\n"
        "class Health(BaseHTTPRequestHandler):\n"
        " def log_message(self, *args): pass\n"
        " def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b'OK')\n"
        "port=json.load(open(os.environ['SEARXNG_SETTINGS_PATH']))['server']['port']\n"
        "HTTPServer(('127.0.0.1', port), Health).serve_forever()\n")
    probe = tmp_path / "probe.py"
    probe.write_text("import os,signal,time\n" + record +
        "def stop(*args): record('probe-stop'); raise SystemExit(0)\n"
        "signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)\n"
        "record('probe-start:' + str(os.getpid()))\n"
        "while True: time.sleep(0.05)\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    muxer = binary / "dotnet"
    muxer.write_text(f"#!{sys.executable}\nimport os\nos.execv({sys.executable!r}, [{sys.executable!r}, {str(probe)!r}])\n")
    muxer.chmod(0o700)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    arguments = ["real-web", "--source", "a" * 40, "--workflow", "b" * 40]
    for name, value in {"product-root": tmp_path, "harness-root": tmp_path,
                        "searx-root": source, "searx-python": sys.executable,
                        "host": tmp_path / "host.dll", "probe": tmp_path / "probe.dll",
                        "dependency-report": tmp_path / "report.json"}.items():
        arguments.extend(["--" + name, str(value)])
    driver = ("import importlib.util,sys\n"
        f"spec=importlib.util.spec_from_file_location('qa_smoke', {str(SCRIPT)!r})\n"
        "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\n"
        "m.checkout=lambda *args: None\nm.dependency_provenance=lambda *args: {'hermetic':False}\n"
        f"m.SEARX_PORT={port}\nsys.argv={arguments!r}\nraise SystemExit(m.main())\n")
    environment = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"], RUNNER_TEMP=str(tmp_path))
    wrapper = subprocess.Popen([sys.executable, "-c", driver], env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    independent = child()
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            lines = events.read_text().splitlines() if events.exists() else []
            if any(line.startswith("probe-start:") for line in lines): break
            assert wrapper.poll() is None, "Wrapper must reach the actual probe before cancellation"
            time.sleep(0.02)
        else: pytest.fail("Synthetic probe did not start")
        wrapper.send_signal(interruption)
        output, _ = wrapper.communicate(timeout=12)
        lines = events.read_text().splitlines()
        assert "probe-stop" in lines and "upstream-stop" in lines, "Wrapper must join both exact children"
        assert lines.index("probe-stop") < lines.index("upstream-stop"), "Stop the probe before its upstream"
        result = json.loads(output)
        assert wrapper.returncode == 2 and result["status"] == "blocked" and result["reason"] == "cancelled"
        assert result["searxCleanup"] is True and independent.poll() is None
    finally:
        if wrapper.poll() is None:
            wrapper.kill(); wrapper.wait(timeout=3)
        # These IDs were recorded by this test's own two children; never look up process names.
        for line in events.read_text().splitlines() if events.exists() else []:
            if line.startswith(("probe-start:", "upstream-start:")):
                try: os.kill(int(line.split(":")[1]), signal.SIGTERM)
                except ProcessLookupError: pass
        smoke.stop_owned(independent, 0.5)


def workflow():
    return yaml.load((ROOT / ".github/workflows/optimus-real-web-smoke.yml").read_text(), Loader=yaml.BaseLoader)


def test_manual_job_has_only_full_sha_input_and_disposable_read_only_runner():
    value = workflow()
    assert set(value["on"]) == {"workflow_dispatch"}
    inputs = value["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"source_commit"} and inputs["source_commit"]["required"] == "true"
    assert smoke.validate_source(inputs["source_commit"]["default"])
    assert value["permissions"] == {"contents": "read"}
    job = value["jobs"]["real-web"]
    assert job["runs-on"] == "ubuntu-24.04" and job["timeout-minutes"] == "15"
    assert "services" not in job


@pytest.mark.parametrize("value,accepted", [("a" * 40, True), ("main", False), ("A" * 40, False),
    ("a" * 39, False), ("a" * 41, False), ("a" * 40 + "\n", False), ("$(false)", False), ("a" * 39 + "g", False)])
def test_actual_before_checkout_shell_guard(value, accepted):
    script = workflow()["jobs"]["real-web"]["steps"][0]["run"]
    environment = smoke.process_environment()
    environment.update(OPTIMUS_SOURCE_COMMIT=value, OPTIMUS_WORKFLOW_COMMIT="b" * 40)
    result = subprocess.run(["bash", "-c", script], env=environment, capture_output=True, timeout=3)
    assert (result.returncode == 0) == accepted


def test_actual_workflow_guard_denies_each_untrusted_dispatch_context():
    expression = workflow()["jobs"]["real-web"]["if"]
    assert "||" not in expression
    import re
    terms = re.findall(r"(github\.[a-z_.]+)\s*==\s*(?:'([^']+)'|(false))", expression)
    assert len(terms) == 8
    expected = {key: (False if boolean else text) for key, text, boolean in terms}
    assert expected == {"github.event_name": "workflow_dispatch", "github.repository": "Voxterrae/HUB_Optimus",
                        "github.repository_id": "1115264109", "github.event.repository.private": False,
                        "github.ref": "refs/heads/main", "github.actor_id": "249308740",
                        "github.actor": "Voxterrae", "github.triggering_actor": "Voxterrae"}
    def permitted(context): return all(context[key] == value for key, value in expected.items())
    assert permitted(expected)
    for key in expected:
        altered = dict(expected); altered[key] = True if expected[key] is False else "untrusted"
        assert not permitted(altered)


def test_workflow_separates_harness_product_and_official_upstream_before_execution():
    job = workflow()["jobs"]["real-web"]
    steps = job["steps"]
    assert "[0-9a-f]{40}" in steps[0]["run"] and "uses" not in steps[0]
    checkouts = [step for step in steps if "uses" in step]
    assert len(checkouts) == 3
    assert all(step["uses"] == "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" for step in checkouts)
    assert all(step["with"]["persist-credentials"] == "false" for step in checkouts)
    assert checkouts[0]["with"]["ref"] == "${{ github.workflow_sha }}"
    assert checkouts[1]["with"]["ref"] == "${{ inputs.source_commit }}"
    assert checkouts[2]["with"]["repository"] == "searxng/searxng"
    assert checkouts[2]["with"]["ref"] == smoke.SEARX_COMMIT
    all_commands = "\n".join(step.get("run", "") for step in steps)
    assert 'OptimusProductRoot=$GITHUB_WORKSPACE/product' in all_commands
    assert all_commands.count('SourceRevisionId=$OPTIMUS_SOURCE_COMMIT') == 2
    assert '--no-cache-dir --report' in all_commands
    assert not any(word in all_commands for word in ("docker", "apt install", "--restart", "upload-artifact"))
    assert all("cache" not in step.get("uses", "") for step in steps)
