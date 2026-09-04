from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DTSSpec:
    n: int
    k: int
    scope: int

    def __post_init__(self) -> None:
        if self.n <= 0:
            raise ValueError("n must be positive")
        if self.k <= 0:
            raise ValueError("k must be positive")
        if self.scope <= 0:
            raise ValueError("scope must be positive")
        if self.required_differences > self.scope:
            raise ValueError(
                f"scope {self.scope} cannot hold {self.required_differences} unique differences"
            )

    @property
    def marks_per_row(self) -> int:
        return self.k + 1

    @property
    def required_differences(self) -> int:
        return self.n * self.k * (self.k + 1) // 2

    @property
    def movable_marks(self) -> int:
        return self.n * self.k


@dataclass(frozen=True, slots=True)
class VerificationResult:
    valid: bool
    errors: tuple[str, ...]
    used_differences: frozenset[int]
    missing_differences: tuple[int, ...]
    actual_scope: int
