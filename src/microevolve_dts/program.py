from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Mapping

FEATURE_NAMES = frozenset(
    {
        "prefix_fill",
        "lower_fill",
        "upper_fill",
        "new_diff_mean",
        "new_diff_spread",
        "new_diff_min",
        "new_diff_max",
        "mark_ratio",
        "gap_ratio",
        "row_evenness",
        "future_room",
    }
)

_UNARY = {"neg", "abs"}
_BINARY = {"add", "sub", "mul", "min", "max"}
_ALL_OPS = tuple(sorted(_UNARY | _BINARY))


@dataclass(frozen=True, slots=True)
class Expr:
    kind: str
    value: float | str | None = None
    args: tuple["Expr", ...] = ()

    @staticmethod
    def const(value: float) -> "Expr":
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("constant must be finite")
        return Expr("const", value, ())

    @staticmethod
    def feature(name: str) -> "Expr":
        if name not in FEATURE_NAMES:
            raise ValueError(f"unknown feature: {name}")
        return Expr("feature", name, ())

    @staticmethod
    def op(name: str, *args: "Expr") -> "Expr":
        if name in _UNARY:
            expected = 1
        elif name in _BINARY:
            expected = 2
        else:
            raise ValueError(f"unknown operation: {name}")
        if len(args) != expected:
            raise ValueError(f"operation {name} expects {expected} args")
        return Expr("op", name, tuple(args))

    @property
    def depth(self) -> int:
        if not self.args:
            return 1
        return 1 + max(arg.depth for arg in self.args)

    @property
    def node_count(self) -> int:
        return 1 + sum(arg.node_count for arg in self.args)

    def features_used(self) -> tuple[str, ...]:
        found: set[str] = set()

        def walk(node: "Expr") -> None:
            if node.kind == "feature":
                found.add(str(node.value))
            for child in node.args:
                walk(child)

        walk(self)
        return tuple(sorted(found))

    def evaluate(self, features: Mapping[str, float]) -> float:
        def ev(node: "Expr") -> float:
            if node.kind == "const":
                return float(node.value)
            if node.kind == "feature":
                name = str(node.value)
                if name not in features:
                    raise KeyError(f"missing feature: {name}")
                return float(features[name])
            if node.kind != "op":
                raise ValueError(f"invalid expression kind: {node.kind}")

            name = str(node.value)
            values = [ev(arg) for arg in node.args]
            if name == "neg":
                result = -values[0]
            elif name == "abs":
                result = abs(values[0])
            elif name == "add":
                result = values[0] + values[1]
            elif name == "sub":
                result = values[0] - values[1]
            elif name == "mul":
                result = values[0] * values[1]
            elif name == "min":
                result = min(values)
            elif name == "max":
                result = max(values)
            else:
                raise ValueError(f"unknown operation: {name}")

            if not math.isfinite(result):
                return 0.0
            return max(-1_000_000.0, min(1_000_000.0, result))

        value = ev(self)
        if not math.isfinite(value):
            return 0.0
        return value

    def to_dict(self) -> dict[str, Any]:
        if self.kind == "const":
            return {"const": float(self.value)}
        if self.kind == "feature":
            return {"feature": str(self.value)}
        if self.kind == "op":
            return {
                "op": str(self.value),
                "args": [arg.to_dict() for arg in self.args],
            }
        raise ValueError(f"invalid expression kind: {self.kind}")

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "Expr":
        if not isinstance(data, Mapping):
            raise ValueError("expression must be an object")
        keys = set(data)
        if keys == {"const"}:
            return Expr.const(float(data["const"]))
        if keys == {"feature"}:
            return Expr.feature(str(data["feature"]))
        if keys == {"op", "args"}:
            raw_args = data["args"]
            if not isinstance(raw_args, list):
                raise ValueError("args must be a list")
            return Expr.op(str(data["op"]), *(Expr.from_dict(arg) for arg in raw_args))
        raise ValueError("invalid expression object")


def random_expr(rng: random.Random, max_depth: int = 4) -> Expr:
    if max_depth < 1:
        raise ValueError("max_depth must be >= 1")
    if max_depth == 1 or rng.random() < 0.32:
        if rng.random() < 0.72:
            return Expr.feature(rng.choice(tuple(sorted(FEATURE_NAMES))))
        return Expr.const(rng.uniform(-2.0, 2.0))

    op = rng.choice(_ALL_OPS)
    if op in _UNARY:
        return Expr.op(op, random_expr(rng, max_depth - 1))
    return Expr.op(
        op,
        random_expr(rng, max_depth - 1),
        random_expr(rng, max_depth - 1),
    )


def _paths(node: Expr, prefix: tuple[int, ...] = ()) -> list[tuple[int, ...]]:
    paths = [prefix]
    for index, child in enumerate(node.args):
        paths.extend(_paths(child, prefix + (index,)))
    return paths


def _subtree(node: Expr, path: tuple[int, ...]) -> Expr:
    current = node
    for index in path:
        current = current.args[index]
    return current


def _replace(node: Expr, path: tuple[int, ...], replacement: Expr) -> Expr:
    if not path:
        return replacement
    index = path[0]
    new_args = list(node.args)
    new_args[index] = _replace(new_args[index], path[1:], replacement)
    return Expr(node.kind, node.value, tuple(new_args))


def mutate(expr: Expr, rng: random.Random, max_depth: int = 5) -> Expr:
    paths = _paths(expr)
    path = rng.choice(paths)
    old = _subtree(expr, path)
    allowed_subtree_depth = max(1, max_depth - len(path))

    if old.kind == "const" and rng.random() < 0.55:
        replacement = Expr.const(float(old.value) + rng.gauss(0.0, 0.5))
    elif old.kind == "feature" and rng.random() < 0.45:
        choices = sorted(FEATURE_NAMES - {str(old.value)})
        replacement = Expr.feature(rng.choice(choices))
    elif old.kind == "op" and rng.random() < 0.35:
        old_name = str(old.value)
        pool = sorted(_UNARY if old_name in _UNARY else _BINARY)
        replacement = Expr.op(rng.choice(pool), *old.args)
    else:
        replacement = random_expr(rng, allowed_subtree_depth)

    candidate = _replace(expr, path, replacement)
    if candidate.depth > max_depth:
        return expr
    return candidate


def crossover(left: Expr, right: Expr, rng: random.Random, max_depth: int = 5) -> Expr:
    left_path = rng.choice(_paths(left))
    right_path = rng.choice(_paths(right))
    candidate = _replace(left, left_path, _subtree(right, right_path))
    if candidate.depth <= max_depth:
        return candidate
    return left
