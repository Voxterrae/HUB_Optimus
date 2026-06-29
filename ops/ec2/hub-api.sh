#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/hub-optimus"
API_DIR="$APP_ROOT/shared/api"
API_FILE="$API_DIR/hub_api.py"

mkdir -p "$API_DIR"

cat > "$API_FILE" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

APP_ROOT = Path("/opt/hub-optimus")
CURRENT = APP_ROOT / "current"
SHARED = APP_ROOT / "shared"


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return default


def run_command(args: list[str], input_text: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def product_status() -> dict:
    current_path = ""
    commit = ""
    if CURRENT.is_symlink():
        current_path = str(CURRENT.resolve())
        code, stdout, _ = run_command(["git", "-C", current_path, "rev-parse", "--short", "HEAD"])
        if code == 0:
            commit = stdout.strip()

    release_state = read_text(SHARED / "RELEASE_STATE")

    return {
        "product": "HUB_Optimus backend v0.1",
        "current": current_path,
        "commit": commit,
        "release_state": release_state,
        "capabilities": {
            "semantic_analyze": True,
            "scenario_runner": True,
            "deploy_rollback": True,
            "runs_registry": True,
            "public_api": False,
            "frontend": False,
        },
    }


def latest_run_id(command: str) -> str | None:
    command_dir = SHARED / "runs" / command
    if not command_dir.is_dir():
        return None
    runs = sorted(p.name for p in command_dir.iterdir() if p.is_dir())
    return runs[-1] if runs else None


class Handler(BaseHTTPRequestHandler):
    server_version = "HUBOptimusAPI/0.1"

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/status":
            self.send_json(200, product_status())
            return

        if path == "/health":
            self.send_json(200, {"status": "ok"})
            return

        self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path != "/analyze":
            self.send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.send_json(400, {"error": f"invalid JSON: {exc.msg}"})
            return

        case_dir = SHARED / "api" / "cases"
        case_dir.mkdir(parents=True, exist_ok=True)
        case_path = case_dir / "api-case.json"
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        before_latest = latest_run_id("analyze")

        code, stdout, stderr = run_command([
            "/opt/hub-optimus/shared/bin/hub-core",
            "analyze",
            str(case_path),
        ])

        after_latest = latest_run_id("analyze")

        if code != 0:
            self.send_json(
                500,
                {
                    "error": "analysis failed",
                    "stderr": stderr,
                    "stdout": stdout,
                },
            )
            return

        if not after_latest or after_latest == before_latest:
            self.send_json(
                500,
                {
                    "error": "analysis completed but run output was not detected",
                    "stdout": stdout,
                },
            )
            return

        run_path = SHARED / "runs" / "analyze" / after_latest
        result_path = run_path / "analysis_result.json"

        try:
            analysis_result = json.loads(result_path.read_text(encoding="utf-8"))
        except OSError as exc:
            self.send_json(500, {"error": f"cannot read analysis result: {exc}"})
            return
        except json.JSONDecodeError as exc:
            self.send_json(500, {"error": f"analysis result is invalid JSON: {exc.msg}"})
            return

        self.send_json(
            200,
            {
                "status": "ok",
                "run_id": after_latest,
                "run_path": str(run_path),
                "analysis_result": analysis_result,
            },
        )


def main() -> int:
    host = "127.0.0.1"
    port = 8080
    httpd = HTTPServer((host, port), Handler)
    print(f"[hub-api] listening on http://{host}:{port}", flush=True)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$API_FILE"

echo "[hub-api] Starting local API on 127.0.0.1:8080"
exec python3 "$API_FILE"
