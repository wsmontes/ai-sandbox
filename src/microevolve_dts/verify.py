from __future__ import annotations

from collections.abc import Sequence

from .model import DTSSpec, VerificationResult


def verify_rows(rows: Sequence[Sequence[int]], spec: DTSSpec) -> VerificationResult:
    errors: list[str] = []
    used: set[int] = set()
    actual_scope = 0

    if len(rows) != spec.n:
        errors.append(f"expected {spec.n} rows, got {len(rows)}")

    for row_index, raw_row in enumerate(rows):
        row = list(raw_row)
        if len(row) != spec.marks_per_row:
            errors.append(
                f"row {row_index} expected {spec.marks_per_row} marks, got {len(row)}"
            )
            continue
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in row):
            errors.append(f"row {row_index} must contain integers only")
            continue
        if row[0] != 0:
            errors.append(f"row {row_index} must start at 0")
        if any(left >= right for left, right in zip(row, row[1:])):
            errors.append(f"row {row_index} must be strictly increasing")
        row_scope = max(row, default=0)
        actual_scope = max(actual_scope, row_scope)
        if row_scope > spec.scope:
            errors.append(f"row {row_index} exceeds scope {spec.scope}: {row_scope}")
        if any(value < 0 for value in row):
            errors.append(f"row {row_index} contains a negative mark")

        for right_index in range(1, len(row)):
            for left_index in range(right_index):
                difference = row[right_index] - row[left_index]
                if difference <= 0:
                    continue
                if difference in used:
                    errors.append(
                        f"repeated difference {difference} at row {row_index}, "
                        f"marks {left_index},{right_index}"
                    )
                else:
                    used.add(difference)

    missing = tuple(value for value in range(1, spec.scope + 1) if value not in used)
    if not errors and len(used) != spec.required_differences:
        errors.append(
            f"expected {spec.required_differences} unique differences, got {len(used)}"
        )

    return VerificationResult(
        valid=not errors,
        errors=tuple(errors),
        used_differences=frozenset(used),
        missing_differences=missing,
        actual_scope=actual_scope,
    )
