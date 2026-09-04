import json
import os
import subprocess
import sys
from pathlib import Path


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    return subprocess.run(
        [sys.executable, "-m", "microevolve_dts", *args],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_verify_accepts_valid_certificate(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    certificate = tmp_path / "certificate.json"
    certificate.write_text(
        json.dumps(
            {
                "n": 2,
                "k": 2,
                "scope": 7,
                "rows": [[0, 1, 4], [0, 2, 7]],
            }
        )
    )
    result = _run(root, "verify", str(certificate))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["actual_scope"] == 7


def test_cli_search_solves_small_instance():
    root = Path(__file__).resolve().parents[1]
    result = _run(
        root,
        "search",
        "--n",
        "2",
        "--k",
        "2",
        "--scope",
        "7",
        "--beam-width",
        "256",
        "--node-budget",
        "50000",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["found"] is True
    assert payload["verification"]["valid"] is True
