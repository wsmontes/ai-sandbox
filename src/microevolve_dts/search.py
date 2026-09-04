from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator, Mapping

from .model import DTSSpec
from .program import Expr


@dataclass(frozen=True, slots=True)
class SearchState:
    rows: tuple[tuple[int, ...], ...]
    used_mask: int
    depth: int


@dataclass(frozen=True, slots=True)
class SearchResult:
    found: bool
    rows: tuple[tuple[int, ...], ...] | None
    best_rows: tuple[tuple[int, ...], ...]
    max_depth: int
    nodes: int
    elapsed_seconds: float
    exhausted_budget: bool


def initial_state(spec: DTSSpec) -> SearchState:
    return SearchState(rows=((0,),), used_mask=0, depth=0)


def _bit(difference: int) -> int:
    return 1 << difference


def _add_difference_mask(used_mask: int, differences: tuple[int, ...]) -> int | None:
    mask = used_mask
    for difference in differences:
        bit = _bit(difference)
        if mask & bit:
            return None
        mask |= bit
    return mask


def expand_state(
    state: SearchState, spec: DTSSpec
) -> Iterator[tuple[SearchState, tuple[int, ...]]]:
    if len(state.rows) == spec.n and len(state.rows[-1]) == spec.marks_per_row:
        return

    if len(state.rows[-1]) == spec.marks_per_row:
        rows = state.rows + ((0,),)
    else:
        rows = state.rows

    current = rows[-1]
    remaining_after = spec.marks_per_row - (len(current) + 1)
    max_mark = spec.scope - remaining_after
    previous_width = rows[-2][-1] if len(rows) > 1 else 0

    for mark in range(current[-1] + 1, max_mark + 1):
        if remaining_after == 0 and mark < previous_width:
            continue
        new_differences = tuple(mark - old_mark for old_mark in current)
        new_mask = _add_difference_mask(state.used_mask, new_differences)
        if new_mask is None:
            continue
        new_current = current + (mark,)
        child_rows = rows[:-1] + (new_current,)
        yield (
            SearchState(
                rows=child_rows,
                used_mask=new_mask,
                depth=state.depth + 1,
            ),
            new_differences,
        )


def _range_mask(low: int, high: int) -> int:
    if high < low:
        return 0
    width = high - low + 1
    return ((1 << width) - 1) << low


def move_features(
    parent: SearchState,
    child: SearchState,
    new_differences: tuple[int, ...],
    spec: DTSSpec,
) -> Mapping[str, float]:
    scope = spec.scope
    mask = child.used_mask
    half = scope // 2
    lower_mask = _range_mask(1, half)
    upper_mask = _range_mask(half + 1, scope)

    prefix = 0
    for difference in range(1, scope + 1):
        if mask & _bit(difference):
            prefix += 1
        else:
            break

    lower_count = (mask & lower_mask).bit_count()
    upper_count = (mask & upper_mask).bit_count()
    lower_size = max(1, half)
    upper_size = max(1, scope - half)

    current = child.rows[-1]
    mark = current[-1]
    parent_mark = current[-2] if len(current) >= 2 else 0
    gaps = [right - left for left, right in zip(current, current[1:])]
    evenness = 0.0
    if gaps:
        evenness = -(max(gaps) - min(gaps)) / scope

    remaining_marks = spec.marks_per_row - len(current)
    future_room = 0.0
    if remaining_marks > 0:
        future_room = ((scope - mark) / remaining_marks) / scope

    return {
        "prefix_fill": prefix / scope,
        "lower_fill": lower_count / lower_size,
        "upper_fill": upper_count / upper_size,
        "new_diff_mean": (sum(new_differences) / len(new_differences)) / scope,
        "new_diff_spread": (
            (max(new_differences) - min(new_differences)) / scope
            if len(new_differences) > 1
            else 0.0
        ),
        "new_diff_min": min(new_differences) / scope,
        "new_diff_max": max(new_differences) / scope,
        "mark_ratio": mark / scope,
        "gap_ratio": (mark - parent_mark) / scope,
        "row_evenness": evenness,
        "future_room": future_room,
    }


def _weighted_sum(terms: list[tuple[float, str]]) -> Expr:
    nodes = [
        Expr.op("mul", Expr.const(weight), Expr.feature(feature))
        for weight, feature in terms
    ]
    if not nodes:
        raise ValueError("weighted sum needs at least one term")
    while len(nodes) > 1:
        next_level: list[Expr] = []
        for index in range(0, len(nodes), 2):
            if index + 1 < len(nodes):
                next_level.append(Expr.op("add", nodes[index], nodes[index + 1]))
            else:
                next_level.append(nodes[index])
        nodes = next_level
    return nodes[0]


def baseline_program() -> Expr:
    # Human seed: favor early coverage and balanced use of low/high differences,
    # while mildly discouraging very large jumps and uneven row gaps.
    return _weighted_sum(
        [
            (4.0, "prefix_fill"),
            (1.8, "lower_fill"),
            (1.2, "upper_fill"),
            (0.7, "new_diff_spread"),
            (0.5, "row_evenness"),
            (0.25, "future_room"),
            (-0.35, "gap_ratio"),
            (-0.10, "mark_ratio"),
        ]
    )


def beam_search(
    spec: DTSSpec,
    program: Expr,
    *,
    beam_width: int = 512,
    node_budget: int = 250_000,
) -> SearchResult:
    if beam_width <= 0:
        raise ValueError("beam_width must be positive")
    if node_budget <= 0:
        raise ValueError("node_budget must be positive")

    started = time.perf_counter()
    beam = [initial_state(spec)]
    best = beam[0]
    nodes = 0

    while beam and best.depth < spec.movable_marks:
        ranked: list[tuple[float, SearchState]] = []
        budget_hit = False

        for parent in beam:
            for child, new_differences in expand_state(parent, spec):
                nodes += 1
                if child.depth > best.depth:
                    best = child
                features = move_features(parent, child, new_differences, spec)
                score = program.evaluate(features)
                ranked.append((score, child))

                if child.depth == spec.movable_marks:
                    return SearchResult(
                        found=True,
                        rows=child.rows,
                        best_rows=child.rows,
                        max_depth=child.depth,
                        nodes=nodes,
                        elapsed_seconds=time.perf_counter() - started,
                        exhausted_budget=False,
                    )
                if nodes >= node_budget:
                    budget_hit = True
                    break
            if budget_hit:
                break

        if not ranked:
            break

        ranked.sort(key=lambda item: (item[0], item[1].rows), reverse=True)
        beam = [state for _, state in ranked[:beam_width]]
        if beam[0].depth > best.depth:
            best = beam[0]

        if budget_hit:
            return SearchResult(
                found=False,
                rows=None,
                best_rows=best.rows,
                max_depth=best.depth,
                nodes=nodes,
                elapsed_seconds=time.perf_counter() - started,
                exhausted_budget=True,
            )

    return SearchResult(
        found=False,
        rows=None,
        best_rows=best.rows,
        max_depth=best.depth,
        nodes=nodes,
        elapsed_seconds=time.perf_counter() - started,
        exhausted_budget=nodes >= node_budget,
    )
