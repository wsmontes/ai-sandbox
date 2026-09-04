# MicroEvolve-DTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build a locally runnable, independently verifiable heuristic-evolution system for attacking the `(7,5)` DTS scope-111 challenge.

**Architecture:** A deterministic verifier is isolated from a constructive beam search. Beam ranking is controlled by a constrained expression-tree heuristic that can be mutated, crossed, and optionally proposed by a local Ollama model; all runs are seedable and logged.

**Tech Stack:** Python 3.11+, standard library only at runtime, pytest for development tests.

**Spec:** `docs/superpowers/specs/2026-09-04-microevolve-dts-design.md`

## Global Constraints

- Final `(7,5)` witnesses are accepted only if an independent verifier recomputes 105 globally unique positive within-row differences.
- Challenge target is scope `<= 111`; benchmark best-known documented in project references is `112`.
- Runtime core uses Python standard library only.
- Search stochasticity is explicitly seeded.
- Generated heuristic logic executes only through the constrained DSL; arbitrary generated Python is not executed.
- Search and verification remain separate modules.

---

### Task 1: Deterministic DTS verifier

**Files:**
- Create: `src/microevolve_dts/model.py`
- Create: `src/microevolve_dts/verify.py`
- Test: `tests/test_verify.py`

**Interfaces:**
- Produces: `DTSSpec(n: int, k: int, scope: int)`, `VerificationResult`, `verify_rows(rows, spec)`.

- [x] Write tests for a valid `(2,2)` certificate and for repeated-difference, shape, ordering, and scope failures.
- [x] Run `pytest tests/test_verify.py -q` and confirm failure because implementation is absent.
- [x] Implement immutable spec/result models and exact difference recomputation.
- [x] Re-run the verifier tests and confirm pass.

### Task 2: Constrained heuristic program DSL

**Files:**
- Create: `src/microevolve_dts/program.py`
- Test: `tests/test_program.py`

**Interfaces:**
- Consumes: feature mappings `Mapping[str, float]`.
- Produces: immutable `Expr`, `evaluate`, JSON serialization, random generation, mutation, crossover, complexity calculation.

- [x] Write tests covering terminals, arithmetic, serialization round-trip, deterministic mutation, maximum depth, and invalid feature rejection.
- [x] Run `pytest tests/test_program.py -q` and confirm failure.
- [x] Implement total expression evaluation and bounded genetic-programming operators.
- [x] Re-run DSL tests and confirm pass.

### Task 3: Constructive beam solver

**Files:**
- Create: `src/microevolve_dts/search.py`
- Test: `tests/test_search.py`

**Interfaces:**
- Consumes: `DTSSpec`, heuristic `Expr`, `beam_width`, `node_budget`.
- Produces: `SearchResult`, candidate feature extraction, `beam_search`.

- [x] Write tests that legal expansion never repeats a difference and that a generous beam solves `(2,2,7)`.
- [x] Run `pytest tests/test_search.py -q` and confirm failure.
- [x] Implement bitmask state expansion, safe row-width symmetry breaking, feature extraction, ranking, and budget accounting.
- [x] Re-run search tests and confirm pass.

### Task 4: Evolution and genealogy

**Files:**
- Create: `src/microevolve_dts/evolve.py`
- Test: `tests/test_evolve.py`

**Interfaces:**
- Consumes: curriculum specs, seed, population/generation counts, beam/node budgets.
- Produces: `EvolutionConfig`, `Candidate`, `EvolutionResult`, JSONL genealogy, best heuristic and optional certificate.

- [x] Write deterministic smoke tests for seeded population evolution and JSONL logging.
- [x] Run `pytest tests/test_evolve.py -q` and confirm failure.
- [x] Implement curriculum fitness, elitism, mutation/crossover, reproducible candidate IDs, and run logging.
- [x] Re-run evolution tests and confirm pass.

### Task 5: Optional local Ollama proposer

**Files:**
- Create: `src/microevolve_dts/ollama.py`
- Test: `tests/test_ollama.py`

**Interfaces:**
- Consumes: model name, leaderboard summary, allowed feature names.
- Produces: validated `Expr` or a typed proposal error.

- [x] Write tests for extracting a JSON expression from plain/fenced model text and rejecting invalid DSL output without network access.
- [x] Run `pytest tests/test_ollama.py -q` and confirm failure.
- [x] Implement `urllib` Ollama client plus strict expression parsing/validation.
- [x] Re-run Ollama tests and confirm pass.

### Task 6: CLI, packaging, benchmark and documentation

**Files:**
- Create: `src/microevolve_dts/__init__.py`
- Create: `src/microevolve_dts/__main__.py`
- Create: `src/microevolve_dts/cli.py`
- Create: `pyproject.toml`
- Create: `LICENSE`
- Modify: `README.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces commands `verify`, `search`, `evolve`.

- [x] Write CLI subprocess tests for certificate verification and small-instance search.
- [x] Run `pytest tests/test_cli.py -q` and confirm failure.
- [x] Implement argparse commands, JSON I/O, installed console script, run-directory artifacts, and concise README instructions.
- [x] Run full `pytest -q`.
- [x] Run a deterministic small benchmark and a bounded `(7,5,111)` smoke search; record results in `docs/initial-benchmark.md`.
