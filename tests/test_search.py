from microevolve_dts.model import DTSSpec
from microevolve_dts.search import (
    baseline_program,
    beam_search,
    expand_state,
    initial_state,
)
from microevolve_dts.verify import verify_rows


def test_expansion_never_introduces_repeated_difference():
    spec = DTSSpec(n=2, k=2, scope=7)
    state = initial_state(spec)
    first = next(child for child, _ in expand_state(state, spec) if child.rows[-1] == (0, 1))
    second = next(child for child, _ in expand_state(first, spec) if child.rows[-1] == (0, 1, 4))
    next_row_children = list(expand_state(second, spec))

    # Difference 1 is already used by the first row, so mark 1 cannot start row two.
    assert all(child.rows[-1] != (0, 1) for child, _ in next_row_children)
    for child, new_differences in next_row_children:
        assert len(new_differences) == len(set(new_differences))
        for difference in new_differences:
            assert difference > 0


def test_beam_search_solves_small_instance_and_certificate_verifies():
    spec = DTSSpec(n=2, k=2, scope=7)
    result = beam_search(
        spec,
        baseline_program(),
        beam_width=256,
        node_budget=50_000,
    )
    assert result.found
    assert result.rows is not None
    assert result.max_depth == spec.movable_marks
    verification = verify_rows(result.rows, spec)
    assert verification.valid, verification.errors


def test_baseline_program_respects_default_evolution_depth_limit():
    assert baseline_program().depth <= 5
