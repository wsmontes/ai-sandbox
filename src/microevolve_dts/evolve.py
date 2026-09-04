from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .model import DTSSpec
from .program import Expr, crossover, mutate, random_expr
from .search import baseline_program, beam_search


@dataclass(frozen=True, slots=True)
class EvolutionConfig:
    population_size: int = 12
    generations: int = 8
    elite_count: int = 3
    beam_width: int = 256
    node_budget: int = 100_000
    max_program_depth: int = 5
    seed: int = 20260904

    def __post_init__(self) -> None:
        if self.population_size < 2:
            raise ValueError("population_size must be >= 2")
        if self.generations < 1:
            raise ValueError("generations must be >= 1")
        if not 1 <= self.elite_count < self.population_size:
            raise ValueError("elite_count must be between 1 and population_size - 1")
        if self.beam_width < 1 or self.node_budget < 1:
            raise ValueError("beam_width and node_budget must be positive")
        if self.max_program_depth < 2:
            raise ValueError("max_program_depth must be >= 2")


@dataclass(frozen=True, slots=True)
class CaseMetric:
    n: int
    k: int
    scope: int
    found: bool
    max_depth: int
    nodes: int
    rows: tuple[tuple[int, ...], ...] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "n": self.n,
            "k": self.k,
            "scope": self.scope,
            "found": self.found,
            "max_depth": self.max_depth,
            "nodes": self.nodes,
            "rows": [list(row) for row in self.rows] if self.rows is not None else None,
        }


@dataclass(frozen=True, slots=True)
class Candidate:
    id: str
    generation: int
    parents: tuple[str, ...]
    program: Expr
    fitness: float
    metrics: tuple[CaseMetric, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "generation": self.generation,
            "parents": list(self.parents),
            "fitness": self.fitness,
            "program": self.program.to_dict(),
            "program_nodes": self.program.node_count,
            "program_depth": self.program.depth,
            "metrics": [metric.to_dict() for metric in self.metrics],
        }


@dataclass(frozen=True, slots=True)
class EvolutionResult:
    best: Candidate
    evaluated: tuple[Candidate, ...]
    run_dir: Path | None


ProposalFn = Callable[[Sequence[Candidate], random.Random], Expr | None]


def _candidate_id(
    generation: int,
    ordinal: int,
    parents: tuple[str, ...],
    program: Expr,
) -> str:
    payload = json.dumps(
        {
            "generation": generation,
            "ordinal": ordinal,
            "parents": parents,
            "program": program.to_dict(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _evaluate(
    program: Expr,
    curriculum: Sequence[DTSSpec],
    config: EvolutionConfig,
) -> tuple[float, tuple[CaseMetric, ...]]:
    metrics: list[CaseMetric] = []
    fitness = 0.0
    case_count = len(curriculum)

    for index, spec in enumerate(curriculum):
        result = beam_search(
            spec,
            program,
            beam_width=config.beam_width,
            node_budget=config.node_budget,
        )
        metric = CaseMetric(
            n=spec.n,
            k=spec.k,
            scope=spec.scope,
            found=result.found,
            max_depth=result.max_depth,
            nodes=result.nodes,
            rows=result.rows,
        )
        metrics.append(metric)

        # Later curriculum cases matter more because they are closer to the target.
        weight = 1.0 if case_count == 1 else 1.0 + index / (case_count - 1)
        progress = result.max_depth / spec.movable_marks
        case_score = 250.0 * progress
        if result.found:
            efficiency = max(0.0, 1.0 - result.nodes / config.node_budget)
            case_score += 1_000.0 + 100.0 * efficiency
        fitness += weight * case_score

    fitness -= 0.02 * program.node_count
    return fitness, tuple(metrics)


def _write_candidate(log_path: Path, candidate: Candidate) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(candidate.to_dict(), sort_keys=True) + "\n")


def evolve(
    curriculum: Sequence[DTSSpec],
    config: EvolutionConfig,
    *,
    run_dir: str | Path | None = None,
    proposal_fn: ProposalFn | None = None,
) -> EvolutionResult:
    if not curriculum:
        raise ValueError("curriculum must contain at least one DTS spec")

    rng = random.Random(config.seed)
    output_dir = Path(run_dir) if run_dir is not None else None
    log_path: Path | None = None
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        log_path = output_dir / "genealogy.jsonl"
        log_path.write_text("", encoding="utf-8")
        (output_dir / "config.json").write_text(
            json.dumps(
                {
                    "config": {
                        "population_size": config.population_size,
                        "generations": config.generations,
                        "elite_count": config.elite_count,
                        "beam_width": config.beam_width,
                        "node_budget": config.node_budget,
                        "max_program_depth": config.max_program_depth,
                        "seed": config.seed,
                    },
                    "curriculum": [
                        {"n": s.n, "k": s.k, "scope": s.scope} for s in curriculum
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    population: list[tuple[Expr, tuple[str, ...]]] = [(baseline_program(), ())]
    while len(population) < config.population_size:
        population.append((random_expr(rng, config.max_program_depth), ()))

    evaluated: list[Candidate] = []
    best: Candidate | None = None

    for generation in range(config.generations):
        generation_candidates: list[Candidate] = []
        for ordinal, (program, parents) in enumerate(population):
            fitness, metrics = _evaluate(program, curriculum, config)
            candidate = Candidate(
                id=_candidate_id(generation, ordinal, parents, program),
                generation=generation,
                parents=parents,
                program=program,
                fitness=fitness,
                metrics=metrics,
            )
            generation_candidates.append(candidate)
            evaluated.append(candidate)
            if log_path is not None:
                _write_candidate(log_path, candidate)
            if best is None or candidate.fitness > best.fitness:
                best = candidate

        generation_candidates.sort(key=lambda c: (c.fitness, c.id), reverse=True)
        if generation + 1 >= config.generations:
            break

        elites = generation_candidates[: config.elite_count]
        next_population: list[tuple[Expr, tuple[str, ...]]] = [
            (elite.program, (elite.id,)) for elite in elites
        ]

        if proposal_fn is not None and len(next_population) < config.population_size:
            proposal = proposal_fn(elites, rng)
            if proposal is not None and proposal.depth <= config.max_program_depth:
                next_population.append((proposal, tuple(elite.id for elite in elites[:2])))

        while len(next_population) < config.population_size:
            if len(elites) >= 2 and rng.random() < 0.35:
                left, right = rng.sample(elites, 2)
                child = crossover(
                    left.program,
                    right.program,
                    rng,
                    max_depth=config.max_program_depth,
                )
                if rng.random() < 0.75:
                    child = mutate(child, rng, max_depth=config.max_program_depth)
                parents = (left.id, right.id)
            else:
                parent = rng.choice(elites)
                child = mutate(parent.program, rng, max_depth=config.max_program_depth)
                parents = (parent.id,)
            next_population.append((child, parents))

        population = next_population

    assert best is not None
    if output_dir is not None:
        (output_dir / "best.json").write_text(
            json.dumps(best.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        target_metric = best.metrics[-1]
        if target_metric.rows is not None:
            (output_dir / "certificate.json").write_text(
                json.dumps(
                    {
                        "n": target_metric.n,
                        "k": target_metric.k,
                        "scope": target_metric.scope,
                        "rows": [list(row) for row in target_metric.rows],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

    return EvolutionResult(best=best, evaluated=tuple(evaluated), run_dir=output_dir)
