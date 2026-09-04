import random

import pytest

from microevolve_dts.program import (
    FEATURE_NAMES,
    Expr,
    crossover,
    mutate,
    random_expr,
)


def test_expression_evaluates_arithmetic_and_features():
    expr = Expr.op(
        "add",
        Expr.op("mul", Expr.const(2.0), Expr.feature("prefix_fill")),
        Expr.op("neg", Expr.feature("gap_ratio")),
    )
    value = expr.evaluate({"prefix_fill": 0.5, "gap_ratio": 0.25})
    assert value == pytest.approx(0.75)


def test_expression_json_round_trip():
    expr = Expr.op("max", Expr.const(0.25), Expr.feature("lower_fill"))
    restored = Expr.from_dict(expr.to_dict())
    assert restored == expr
    assert restored.evaluate({"lower_fill": 0.8}) == pytest.approx(0.8)


def test_unknown_feature_is_rejected():
    with pytest.raises(ValueError, match="unknown feature"):
        Expr.feature("magic")


def test_seeded_random_and_mutation_are_deterministic_and_bounded():
    rng_a = random.Random(123)
    rng_b = random.Random(123)
    base_a = random_expr(rng_a, max_depth=3)
    base_b = random_expr(rng_b, max_depth=3)
    assert base_a == base_b

    mutated_a = mutate(base_a, random.Random(456), max_depth=4)
    mutated_b = mutate(base_b, random.Random(456), max_depth=4)
    assert mutated_a == mutated_b
    assert mutated_a.depth <= 4
    assert set(mutated_a.features_used()).issubset(FEATURE_NAMES)


def test_crossover_returns_valid_bounded_expression():
    left = Expr.op("add", Expr.feature("lower_fill"), Expr.const(1.0))
    right = Expr.op("mul", Expr.feature("upper_fill"), Expr.feature("gap_ratio"))
    child = crossover(left, right, random.Random(99), max_depth=4)
    assert child.depth <= 4
    assert child.node_count >= 1
    assert set(child.features_used()).issubset(FEATURE_NAMES)
