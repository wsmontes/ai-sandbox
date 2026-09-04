# AI Sandbox — MicroEvolve-DTS

A public experiment in **small-scale AI-assisted algorithm discovery**.

The first challenge asks a deliberately concrete question:

> Can a consumer machine evolve a better search strategy for a real open combinatorial construction problem, and perhaps improve the best-known result?

The target is a **`(7,5)` Difference Triangle Set (DTS) with scope `<= 111`**. The published best-known upper bound is currently `112`, and HorizonMath lists “strictly less than 112” as an open construction benchmark.

## The math in one minute

A `(7,5)` DTS contains seven rows of six increasing integers, each starting at zero. Within each row, take every positive pairwise difference. Across the whole object, **all differences must be unique**.

There are:

```text
7 × C(6,2) = 105 differences
```

At scope `111`, a successful solution therefore uses 105 different values out of `1..111` and leaves only six unused.

The repository includes the published scope-112 witness from Shehadeh, Kingsford, and Kschischang in `data/best-known-112.json`. The independent verifier confirms that it contains exactly 105 globally unique differences.

## What is being evolved?

The system does not ask an AI to guess 42 integers directly.

Instead, a constructive beam search builds DTS rows mark by mark. A small **heuristic program** decides which partial states survive the beam. Those heuristic programs are expression trees over measurable search features such as low-difference coverage, proposed gap size, and remaining room.

The experiment then:

1. evaluates heuristic programs on a curriculum of DTS instances;
2. retains the strongest programs;
3. mutates and crosses their expression trees;
4. optionally asks a local Ollama model to propose structurally different programs;
5. repeats while logging the full genealogy.

The final mathematical witness is always checked by a deterministic verifier that is completely independent of the heuristic machinery.

## Current first result

With a deliberately small target-search budget (`beam_width=64`, `node_budget=100000`):

- human-written baseline heuristic: **18 / 35 movable marks**;
- automatically discovered heuristic: **19 / 35 movable marks**.

The evolved winner simplified to:

```json
{
  "op": "mul",
  "args": [
    {"feature": "gap_ratio"},
    {"const": -0.42012724485620057}
  ]
}
```

Because the beam ranks larger scores first, this is essentially the rule **“prefer smaller gaps.”** It is modest, but it is already a machine-discovered search policy that beats the supplied baseline under the same budget. See `docs/initial-benchmark.md`.

No scope-111 witness has been found by this repository yet.

## Install

Python 3.11+ is enough for the reference implementation.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

The runtime core uses only the Python standard library.

## Verify the published scope-112 witness

```bash
python -m microevolve_dts verify data/best-known-112.json
```

A valid result reports:

```text
valid: true
actual_scope: 112
used_difference_count: 105
```

## Run one target search

```bash
python -m microevolve_dts search \
  --n 7 \
  --k 5 \
  --scope 111 \
  --beam-width 64 \
  --node-budget 100000
```

The human baseline is used unless `--program path/to/program.json` is supplied.

## Evolve heuristics locally

A small run:

```bash
python -m microevolve_dts evolve \
  --population 8 \
  --generations 4 \
  --elites 2 \
  --beam-width 64 \
  --node-budget 100000 \
  --seed 20260904
```

Each run writes:

```text
runs/<timestamp>/
├── best.json
├── config.json
├── genealogy.jsonl
└── certificate.json   # only when the target is solved
```

`genealogy.jsonl` records every evaluated program, its parent IDs, fitness, and per-problem metrics.

## Add a local LLM with Ollama

The evolutionary engine works without an LLM. If Ollama is already running locally, any installed model can also propose new heuristic programs:

```bash
python -m microevolve_dts evolve \
  --ollama-model YOUR_LOCAL_MODEL \
  --population 12 \
  --generations 8
```

The model cannot execute arbitrary generated Python. It can only return programs in the repository's small expression DSL, which are parsed and validated before evaluation.

## Independent certificate format

```json
{
  "n": 7,
  "k": 5,
  "scope": 111,
  "rows": [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0]
  ]
}
```

The zero-filled example above is only the schema. A real certificate must contain strictly increasing rows and pass all 105 difference checks.

## Success levels

**Level 1 — search improvement:** an evolved heuristic beats the supplied baseline under identical deterministic budgets. **Achieved in the initial benchmark.**

**Level 2 — rediscovery:** independently find a valid scope-112 construction.

**Level 3 — new result:** produce a scope-111-or-better certificate accepted by the independent verifier.

## References

- Mohannad Shehadeh, William Kingsford, Frank R. Kschischang, “New Difference Triangle Sets by a Field-Programmable Gate Array-Based Search Technique,” *Journal of Combinatorial Designs* 34(1), 2026. DOI: `10.1002/jcd.22009`.
- HorizonMath, “Minimum-Scope Difference Triangle Set (7,5)”: https://ewang26.github.io/HorizonMath/

The paper's Appendix A is the source of `data/best-known-112.json`; its omitted all-zero first column is restored in the repository copy.

## License

MIT.
