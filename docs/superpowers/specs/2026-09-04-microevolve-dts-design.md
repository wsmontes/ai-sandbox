# MicroEvolve-DTS Design

## Goal

Build a public, reproducible experiment that tests whether a consumer Apple Silicon machine can improve the search strategy used to attack a current mathematical construction problem: finding a valid `(7,5)` Difference Triangle Set (DTS) with scope at most `111`, improving the best-known published upper bound of `112`.

## Scientific framing

A `(n,k)` DTS contains `n` rows of `k+1` strictly increasing non-negative integers, each normalized to start at zero. Every positive pairwise difference formed within a row must be globally unique across all rows. A `(7,5)` DTS therefore contains `7 * C(6,2) = 105` distinct differences. At scope `111`, a successful construction occupies 105 of the 111 possible positive difference values, leaving exactly six unused.

The experiment separates discovery from verification. Search methods may be stochastic, learned, evolved, or LLM-proposed, but a final witness is accepted only by a deterministic verifier that recomputes all differences from the returned rows.

## Current benchmark

As of 2026-09-04, HorizonMath lists the `(7,5)` DTS task with benchmark best-known scope `112`, citing Shehadeh, Kingsford, and Kschischang, *Journal of Combinatorial Designs* 34(1), 2026. The paper reports improvements found with purpose-built FPGA search. The public challenge in this repository is to find a valid scope `<= 111` witness.

Primary references:

- https://doi.org/10.1002/jcd.22009
- https://ewang26.github.io/HorizonMath/

## Architecture

The repository has five independent units.

1. **Verifier** — pure deterministic certificate validation. It knows nothing about the search strategy.
2. **Constructive beam solver** — builds rows mark-by-mark, rejecting any move that introduces a repeated difference. It uses Python integer bitmasks for the used-difference set.
3. **Heuristic program DSL** — a small expression-tree language over measurable search features. Search ranking is therefore code-like and evolvable without allowing arbitrary generated Python execution.
4. **Evolution engine** — evaluates heuristic programs, keeps elites, mutates/crosses programs, records genealogy, and promotes heuristics that let the beam search survive deeper or solve cases with fewer nodes.
5. **Optional local LLM proposer** — an Ollama adapter can ask any locally installed model for candidate heuristic programs in the same constrained DSL. The deterministic evolutionary engine remains usable without an LLM.

## Search state and invariants

A search state contains completed/partial rows and a bitmask of already used differences. Adding a mark `x` to the current row creates differences `x-a` for every earlier mark `a` in that row. The move is legal exactly when none of those difference bits are already set.

Rows are constructed sequentially. When a row is completed, its final width must be at least the previous completed row width. Because DTS rows are unordered, every solution can be permuted into nondecreasing width order; this removes row-permutation symmetry without removing solutions.

The solver also reserves at least one integer step for every mark still needed in the current row, so it does not explore partial rows that cannot fit under the scope.

## Heuristic features

Candidate moves expose only cheap, normalized features so millions of evaluations remain practical:

- `prefix_fill`: fraction of the low-end consecutive difference prefix already occupied.
- `lower_fill`: fraction of differences in the lower half of the scope occupied.
- `upper_fill`: fraction of differences in the upper half occupied.
- `new_diff_mean`: mean of the differences introduced by the move, normalized by scope.
- `new_diff_spread`: span of the new differences, normalized by scope.
- `new_diff_min` / `new_diff_max`: normalized extrema of new differences.
- `mark_ratio`: candidate mark divided by scope.
- `gap_ratio`: gap from the previous mark divided by scope.
- `row_evenness`: negative normalized spread of current row gaps; larger is more even.
- `future_room`: remaining numerical room per still-needed mark, normalized by scope.

A heuristic program maps these features to a scalar beam-ranking score.

## DSL

Expressions are JSON-serializable trees composed of:

- terminal nodes: numeric constants and named features;
- unary operations: `neg`, `abs`;
- binary operations: `add`, `sub`, `mul`, `min`, `max`.

Evaluation is total: non-finite intermediate values are converted to a bounded finite score. Program depth and node count are capped by mutation/generation utilities.

## Evolution

Each candidate has an ID, generation number, parent IDs, expression, fitness, and per-case metrics. Initial population contains a human baseline plus random programs. Each generation:

1. evaluate all candidates on a curriculum ending in `(7,5,111)`;
2. sort by fitness and retain elites;
3. create descendants through expression mutation and crossover;
4. optionally insert constrained proposals from a local Ollama model;
5. write one JSONL record per evaluated candidate so the genealogy is inspectable.

Fitness rewards, in order: finding a complete valid witness, reaching deeper construction depth, and using fewer nodes. A small complexity penalty prevents expression bloat.

## Reproducibility

All stochastic components accept explicit seeds. The CLI records the configuration, seed, best program, metrics, and any discovered certificate under a run directory. A certificate produced by search must also pass the standalone verifier command.

## Success levels

- **Level 1:** evolved/LLM-proposed heuristic beats the fixed baseline on the same deterministic benchmark budget.
- **Level 2:** the system independently finds a valid scope-112 `(7,5)` DTS.
- **Level 3:** the verifier accepts a scope-111-or-better `(7,5)` DTS, improving the currently documented best-known upper bound.

## Non-goals for the first version

The first version does not claim optimality, does not execute arbitrary LLM-generated Python, and does not require cloud inference. Native/compiled acceleration can be added only after the Python reference implementation establishes correctness and benchmark semantics.
