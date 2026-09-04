from microevolve_dts.model import DTSSpec
from microevolve_dts.verify import verify_rows


def test_valid_small_dts_certificate():
    spec = DTSSpec(n=2, k=2, scope=7)
    result = verify_rows([[0, 1, 4], [0, 2, 7]], spec)
    assert result.valid
    assert result.used_differences == frozenset({1, 2, 3, 4, 5, 7})
    assert result.missing_differences == (6,)
    assert result.actual_scope == 7


def test_rejects_global_repeated_difference():
    spec = DTSSpec(n=2, k=2, scope=7)
    result = verify_rows([[0, 1, 4], [0, 2, 5]], spec)
    assert not result.valid
    assert any("repeated difference 3" in error for error in result.errors)


def test_rejects_wrong_shape_order_and_scope():
    spec = DTSSpec(n=2, k=2, scope=7)
    result = verify_rows([[0, 4, 3], [1, 2, 8]], spec)
    assert not result.valid
    joined = " | ".join(result.errors)
    assert "strictly increasing" in joined
    assert "must start at 0" in joined
    assert "exceeds scope 7" in joined
