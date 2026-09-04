# Initial Benchmark — 2026-09-04

This benchmark establishes the first reproducible checkpoint for MicroEvolve-DTS. It is not a performance claim about Apple M4 hardware; it was run in the ChatGPT execution sandbox to validate the experiment design before running it on the target consumer machine.

## Reference validation

`data/best-known-112.json`, transcribed from Appendix A of Shehadeh, Kingsford, and Kschischang (2026), passes the repository verifier:

- `(n,k) = (7,5)`
- actual scope: `112`
- unique positive within-row differences: `105`
- unused differences in `1..112`: `74, 76, 77, 78, 84, 85, 96`

This is the positive control for the verifier.

## Target baseline

Command:

```bash
PYTHONPATH=src python3 -m microevolve_dts search \
  --n 7 --k 5 --scope 111 \
  --beam-width 64 \
  --node-budget 100000
```

Result:

- found: `false`
- maximum construction depth: `18 / 35` movable marks
- legal child nodes considered: `47,667`
- search terminated because the beam became empty, not because the 100,000-node budget was exhausted

The exact wall-clock time is environment-dependent and is therefore not used as a fitness signal.

## Evolution run

Command:

```bash
PYTHONPATH=src python3 -m microevolve_dts evolve \
  --population 8 \
  --generations 4 \
  --elites 2 \
  --beam-width 64 \
  --node-budget 100000 \
  --max-program-depth 5 \
  --seed 20260904 \
  --run-dir /tmp/microevolve-benchmark
```

The run evaluated 32 heuristic candidates. The best overall candidate was:

```json
{
  "op": "mul",
  "args": [
    {"feature": "gap_ratio"},
    {"const": -0.42012724485620057}
  ]
}
```

Its target result was:

- found: `false`
- maximum construction depth: `19 / 35` movable marks
- legal child nodes considered: `55,418`

Under identical beam and node budgets, the automated heuristic search therefore improved target depth from `18` to `19` marks.

## Genealogy note

The eventual winner did not appear fully formed in generation zero. Its recorded lineage was:

1. generation 0: `prefix_fill`;
2. generation 1: `mark_ratio * -0.42012724485620057`;
3. generation 2: `gap_ratio * -0.42012724485620057`;
4. generation 3: elite retention of the generation-2 program.

The target depth itself reached 19 in the initial random population as well, so the scientifically precise claim is that **automated heuristic search found policies that outperform the supplied human baseline**, while later selection/mutation substantially improved total curriculum fitness. We do not claim that mutation alone created the first target-depth improvement.

## Next experimental step

Run the same seeded benchmark on the Apple M4, then increase population, generations, and target-search budgets. An Ollama model can be enabled as an additional program proposer without changing verifier semantics.
