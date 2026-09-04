from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .evolve import EvolutionConfig, evolve
from .model import DTSSpec, VerificationResult
from .ollama import OllamaProposer
from .program import Expr
from .search import baseline_program, beam_search
from .verify import verify_rows


def _verification_dict(result: VerificationResult) -> dict[str, Any]:
    return {
        "valid": result.valid,
        "errors": list(result.errors),
        "actual_scope": result.actual_scope,
        "used_difference_count": len(result.used_differences),
        "missing_differences": list(result.missing_differences),
    }


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_program(path: str | None) -> Expr:
    if path is None:
        return baseline_program()
    payload = _load_json(path)
    return Expr.from_dict(payload)


def _cmd_verify(args: argparse.Namespace) -> int:
    payload = _load_json(args.certificate)
    spec = DTSSpec(
        n=int(payload["n"]),
        k=int(payload["k"]),
        scope=int(payload.get("scope", max(max(row) for row in payload["rows"]))),
    )
    result = verify_rows(payload["rows"], spec)
    print(json.dumps(_verification_dict(result), indent=2, sort_keys=True))
    return 0 if result.valid else 1


def _cmd_search(args: argparse.Namespace) -> int:
    spec = DTSSpec(args.n, args.k, args.scope)
    program = _load_program(args.program)
    result = beam_search(
        spec,
        program,
        beam_width=args.beam_width,
        node_budget=args.node_budget,
    )
    verification = None
    if result.rows is not None:
        verification = _verification_dict(verify_rows(result.rows, spec))

    payload: dict[str, Any] = {
        "found": result.found,
        "n": spec.n,
        "k": spec.k,
        "scope": spec.scope,
        "max_depth": result.max_depth,
        "movable_marks": spec.movable_marks,
        "nodes": result.nodes,
        "elapsed_seconds": result.elapsed_seconds,
        "exhausted_budget": result.exhausted_budget,
        "rows": [list(row) for row in result.rows] if result.rows else None,
        "best_rows": [list(row) for row in result.best_rows],
        "program": program.to_dict(),
        "verification": verification,
    }
    if args.output and result.rows is not None:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "n": spec.n,
                    "k": spec.k,
                    "scope": spec.scope,
                    "rows": [list(row) for row in result.rows],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _default_curriculum(target_scope: int) -> tuple[DTSSpec, ...]:
    return (
        DTSSpec(2, 2, 7),
        DTSSpec(3, 2, 12),
        DTSSpec(3, 3, 22),
        DTSSpec(4, 3, 30),
        DTSSpec(7, 5, target_scope),
    )


def _cmd_evolve(args: argparse.Namespace) -> int:
    config = EvolutionConfig(
        population_size=args.population,
        generations=args.generations,
        elite_count=args.elites,
        beam_width=args.beam_width,
        node_budget=args.node_budget,
        max_program_depth=args.max_program_depth,
        seed=args.seed,
    )
    run_dir = Path(args.run_dir) if args.run_dir else Path("runs") / datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )
    proposer = None
    if args.ollama_model:
        proposer = OllamaProposer(
            model=args.ollama_model,
            max_depth=args.max_program_depth,
            base_url=args.ollama_url,
            timeout_seconds=args.ollama_timeout,
        )
    result = evolve(
        _default_curriculum(args.target_scope),
        config,
        run_dir=run_dir,
        proposal_fn=proposer,
    )
    best = result.best
    target_metric = best.metrics[-1]
    payload = {
        "run_dir": str(run_dir),
        "best_id": best.id,
        "best_fitness": best.fitness,
        "best_program": best.program.to_dict(),
        "target": target_metric.to_dict(),
        "evaluated_candidates": len(result.evaluated),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="microevolve-dts",
        description="Evolve local search heuristics for Difference Triangle Sets.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="independently verify a DTS certificate")
    verify.add_argument("certificate", help="JSON certificate containing n, k, scope, rows")
    verify.set_defaults(func=_cmd_verify)

    search = sub.add_parser("search", help="run one constructive beam search")
    search.add_argument("--n", type=int, required=True)
    search.add_argument("--k", type=int, required=True)
    search.add_argument("--scope", type=int, required=True)
    search.add_argument("--beam-width", type=int, default=512)
    search.add_argument("--node-budget", type=int, default=250_000)
    search.add_argument("--program", help="JSON heuristic expression; baseline if omitted")
    search.add_argument("--output", help="write a found certificate to this path")
    search.set_defaults(func=_cmd_search)

    evolve_parser = sub.add_parser("evolve", help="evolve heuristic programs")
    evolve_parser.add_argument("--target-scope", type=int, default=111)
    evolve_parser.add_argument("--population", type=int, default=12)
    evolve_parser.add_argument("--generations", type=int, default=8)
    evolve_parser.add_argument("--elites", type=int, default=3)
    evolve_parser.add_argument("--beam-width", type=int, default=256)
    evolve_parser.add_argument("--node-budget", type=int, default=100_000)
    evolve_parser.add_argument("--max-program-depth", type=int, default=5)
    evolve_parser.add_argument("--seed", type=int, default=20260904)
    evolve_parser.add_argument("--run-dir")
    evolve_parser.add_argument("--ollama-model")
    evolve_parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    evolve_parser.add_argument("--ollama-timeout", type=float, default=90.0)
    evolve_parser.set_defaults(func=_cmd_evolve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (KeyError, ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
