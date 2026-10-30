from pathlib import Path
import shutil
import subprocess


def test_browser_web_node_suite():
    node = shutil.which("node")
    assert node, "Node.js is required to execute the browser web regression suite"
    tests = sorted(Path(__file__).resolve().parent.glob("*.test.mjs"))
    assert tests, "The browser web regression suite must not be empty"

    result = subprocess.run(
        [node, "--test", *(str(test) for test in tests)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
