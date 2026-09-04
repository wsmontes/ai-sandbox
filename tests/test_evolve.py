import json
from pathlib import Path

from microevolve_dts.evolve import EvolutionConfig, evolve
from microevolve_dts.model import DTSSpec


def test_seeded_evolution_is_reproducible_and_logs_genealogy(tmp_path: Path):
    config = EvolutionConfig(
        population_size=6,
        generations=2,
        elite_count=2,
        beam_width=48,
        node_budget=4_000,
        max_program_depth=4,
        seed=2026,
    )
    curriculum = (DTSSpec(2, 2, 7), DTSSpec(3, 2, 12))

    first = evolve(curriculum, config, run_dir=tmp_path / "run-a")
    second = evolve(curriculum, config, run_dir=tmp_path / "run-b")

    assert first.best.fitness == second.best.fitness
    assert first.best.program.to_dict() == second.best.program.to_dict()
    assert len(first.evaluated) == config.population_size * config.generations

    lines = (tmp_path / "run-a" / "genealogy.jsonl").read_text().splitlines()
    assert len(lines) == config.population_size * config.generations
    record = json.loads(lines[0])
    assert {"id", "generation", "parents", "fitness", "program", "metrics"} <= set(record)


def test_evolution_best_candidate_has_metrics_for_every_case(tmp_path: Path):
    config = EvolutionConfig(
        population_size=4,
        generations=1,
        elite_count=1,
        beam_width=32,
        node_budget=2_000,
        seed=7,
    )
    curriculum = (DTSSpec(2, 2, 7), DTSSpec(3, 2, 12))
    result = evolve(curriculum, config, run_dir=tmp_path / "run")

    assert len(result.best.metrics) == len(curriculum)
    assert all(metric.max_depth > 0 for metric in result.best.metrics)
    assert result.best.fitness > 0
