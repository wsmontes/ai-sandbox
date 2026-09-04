import json
from pathlib import Path

from microevolve_dts.model import DTSSpec
from microevolve_dts.verify import verify_rows


def test_published_scope_112_reference_certificate_verifies():
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "data" / "best-known-112.json").read_text())
    result = verify_rows(payload["rows"], DTSSpec(payload["n"], payload["k"], payload["scope"]))
    assert result.valid, result.errors
    assert result.actual_scope == 112
    assert len(result.used_differences) == 105
