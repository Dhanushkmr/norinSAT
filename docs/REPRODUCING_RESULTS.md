# Reproducing The Component-Chain Results

This document lists the commands used to substantiate the current proof-search
claim.

## Requirements

The dependency-free scripts run with system Python:

```bash
python3 enc/component_chain_classifier.py -n 4 --enumerate
python3 enc/test_component_chain_classifier.py
```

SAT-backed scripts need `python-sat`.  The recommended invocation is:

```bash
uv run --python 3.12 --with python-sat python <script> ...
```

For hard SAT runs, prefer the parallel portfolio runner so all cores are used:

```bash
uv run --python 3.12 --with python-sat python enc/sat_portfolio.py \
  --timeout 600 \
  -- python enc/bicross_probe.py -m 7 --sat-pairs-hit-at-least 64 --sort-zero-edges --zero-red-degree-at-most-half
```

The PySAT-backed scripts automatically choose the fastest preferred available
solver when `--solver` is omitted.  See `docs/DEV_SETUP.md` for solver lists,
Make targets, and external DIMACS portfolio examples.

The system Python on this machine is newer than the Python version used for the
PySAT runs, so the `uv --python 3.12` form is the stable path.

## Static Checks

```bash
python3 -m py_compile \
  enc/induction_probe.py \
  enc/component_chain_classifier.py \
  enc/paired_slice_witness_sat.py \
  enc/one_connector_witness_sat.py \
  enc/test_component_chain_classifier.py
```

Expected result: no output and exit code 0.

## Unit Tests

Dependency-free tests:

```bash
python3 enc/test_component_chain_classifier.py
```

Expected result:

```text
Ran 6 tests
OK (skipped=2)
```

PySAT-enabled tests:

```bash
uv run --python 3.12 --with python-sat python enc/test_component_chain_classifier.py
```

Expected result:

```text
Ran 6 tests
OK
```

The two optional tests check that:

- the one-connector-negation SAT formula is UNSAT for `Q_3` and `Q_4`;
- a SAT model with no paired-slice witness still has a one-connector
  component-chain witness.

## Exact Classifier Runs

Exact `Q_3`:

```bash
python3 enc/component_chain_classifier.py -n 3 --enumerate
```

Expected key lines:

```text
Colorings checked: 64
Without monochromatic antipodal path: 0
Requiring longer component chains (>1 connector): 0
  1: 64
```

Exact `Q_4`:

```bash
python3 enc/component_chain_classifier.py -n 4 --enumerate
```

Expected key lines:

```text
Colorings checked: 65536
Without monochromatic antipodal path: 0
Requiring longer component chains (>1 connector): 0
  1: 65536
```

## Random Classifier Runs

Random `Q_5`:

```bash
python3 enc/component_chain_classifier.py -n 5 --samples 10000
```

Expected key lines:

```text
Colorings checked: 10000
Without monochromatic antipodal path: 0
Requiring longer component chains (>1 connector): 0
  1: 10000
```

Random `Q_6`:

```bash
python3 enc/component_chain_classifier.py -n 6 --samples 1000
```

Expected key lines:

```text
Colorings checked: 1000
Without monochromatic antipodal path: 0
Requiring longer component chains (>1 connector): 0
  1: 1000
```

Random `Q_7`:

```bash
python3 enc/component_chain_classifier.py -n 7 --samples 500
```

Expected key lines:

```text
Colorings checked: 500
Without monochromatic antipodal path: 0
Requiring longer component chains (>1 connector): 0
  1: 500
```

These sampled runs are not proofs.  Their job is to make sure the phenomenon is
not an artifact of the exact small dimensions.

## Bicross Lemma Probe

The bicross probe works on arbitrary red/blue edge-colorings of an ordinary
cube `Q_m`, not antipodal edge-colorings of `Q_n`.

Exact `Q_2`, including every antipodal vertex-labeling:

```bash
python3 enc/bicross_probe.py -m 2 --enumerate --check-all-labelings
```

Expected key lines:

```text
Edge colorings checked: 16
With bicross witness: 16
Without bicross witness: 0
Fixed-slice labelings checked: 64
```

Exact `Q_3`, including every antipodal vertex-labeling:

```bash
python3 enc/bicross_probe.py -m 3 --enumerate --check-all-labelings
```

Expected key lines:

```text
Edge colorings checked: 4096
With bicross witness: 4096
Without bicross witness: 0
Fixed-slice labelings checked: 65536
```

Random `Q_4`:

```bash
python3 enc/bicross_probe.py -m 4 --samples 10000
python3 enc/bicross_probe.py -m 4 --samples 1000 --analyze-monotone
```

Expected key lines:

```text
Edge colorings checked: 10000
With bicross witness: 10000
Without bicross witness: 0
```

Local search for near-obstructions:

```bash
python3 enc/bicross_probe.py -m 5 --local-search-bad 5000 --restarts 20 --local-search-objective bad --seed 2026
python3 enc/bicross_probe.py -m 5 --local-search-bad 5000 --restarts 20 --local-search-objective pairs-hit --seed 2026
```

Expected behavior:

- The `bad` objective can rediscover 14-bad `Q_5` colorings.
- The `pairs-hit` objective still leaves multiple `both_good` antipodal pairs
  in the best short runs.

Counting SAT checks for `Q_4`:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-bad-at-least 8 --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-bad-at-least 7 --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 5 --sat-bad-at-least 14 --solver cadical195
```

Expected behavior:

```text
Bad-vertex lower bound: 8
SAT: False

Bad-vertex lower bound: 7
SAT: True
Actual bad vertices: 7
Actual good vertices: 9

Bad-vertex lower bound: 14
SAT: True
Actual bad vertices: 14
Actual good vertices: 18
```

Pair-hit SAT checks:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-pairs-hit-at-least 8 --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-pairs-hit-at-least 7 --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-pairs-hit-at-least 6 --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 5 --sat-pairs-hit-at-least 13 --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 5 --sat-pairs-hit-at-least 12 --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 6 --sat-pairs-hit-at-least 28 --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 6 --sat-pairs-hit-at-least 32 --solver cadical195 --sort-zero-edges --zero-red-degree-at-most-half
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 7 --sat-pairs-hit-at-least 64 --solver cadical195 --sort-zero-edges --zero-red-degree-at-most-half --no-solve --tmp-file /tmp/q7_pairhit64.cnf
```

Expected behavior:

```text
Q_4, pair-hit lower bound 8: SAT: False
Q_4, pair-hit lower bound 7: SAT: False
Q_4, pair-hit lower bound 6: SAT: True
Q_5, pair-hit lower bound 13: SAT: False
Q_5, pair-hit lower bound 12: SAT: True
Q_6, pair-hit lower bound 28: SAT: True
Q_6, pair-hit lower bound 32 with symmetry breaks: SAT: False
Q_7, pair-hit lower bound 64 with symmetry breaks: writes a 33,420-variable, 246,175-clause CNF
```

`Q_6` searches for 29, 30, and 31 pair hits were started and stopped after they
did not finish quickly.  A later 90-second-per-solver sweep for 29 hit pairs
also timed out for `cadical195`, `glucose4`, `maplechrono`, and `kissat404`.
A 180-second `cadical195` run on the `Q_7` 64-hit formula also timed out.
The recommended next run is the all-core portfolio version:

```bash
make bicross-q7-portfolio
```

For quick exploratory work on the `Q_6` 29-hit formula, there are two all-core
helpers:

```bash
make bicross-q6-frontier
make bicross-q6-cubes
```

The current strongest `Q_6` pair-hit result is exact:

```bash
make bicross-q6-hit29-proof
```

Expected behavior: the intermediate stages intentionally report some UNKNOWN
cubes and continue; the final stage reports `Selected cubes SAT: False`.  The
proof covers all depth-8 prefix cubes by recursively descending only the
survivors:

- depth 8 leaves `0,4,12,28,29` after the 2M pass;
- depth 12 leaves `70,78,198,200,202,206,462` after the 2M pass;
- depth 16 leaves `1123,1125,1126,1127,1257,3171,3173,3175,3238,3239,3241,3243,3303,3305,3307,3309,7399,7403`;
- those last 18 depth-16 cubes all prove UNSAT at 2M conflicts per cube.

Together with the direct SAT model for 28 hit pairs, this proves that the exact
`Q_6` pair-hit maximum is 28 of 32.

The shorter historical proof targets are still available:

```bash
make bicross-q6-hit31-proof
make bicross-q6-hit30-proof
```

The `hit31` target proves at least two bicross pairs in every `Q_6` coloring;
the `hit30` target strengthens this to at least three bicross pairs.  The
`hit29` target is the exact frontier and strengthens this to at least four
bicross pairs.

A 28-hit model can be checked directly:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py \
  -m 6 \
  --sat-pairs-hit-at-least 28 \
  --solver cadical195 \
  --sort-zero-edges \
  --zero-red-degree-at-most-half \
  --partial-sym-break 20
```

Expected behavior: `SAT: True` and `Encoded hit pairs: 28`.

To replay the current extremal-shape samples:

```bash
make bicross-extremal-shapes
```

Expected high-level behavior:

- `Q_4`, 100 exact 6-hit samples: `cell_antipodal_pairs` has one distinct
  signature, `pair_count=2`, `cells_with_pairs=1`; `bicross_shape` has one
  distinct signature with one common meet vertex.
- `Q_5`, 100 exact 12-hit samples: `cell_antipodal_pairs` has one distinct
  signature, `pair_count=4`, `cells_with_pairs=1`; `bicross_shape` has one
  distinct signature with one common meet vertex.  This is a representative
  sample of one frontier family, not an exhaustive classification.
- `Q_6`, 100 exact 28-hit samples: `cell_antipodal_pairs` has one distinct
  signature, `pair_count=4`, `cells_with_pairs=1`; `bicross_shape` has one
  distinct signature with one common meet vertex.

The incidence-cell restriction can be tested directly:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py \
  -m 4 \
  --sat-pairs-hit-at-least 6 \
  --forbid-cell-pairs \
  --solver cadical195

uv run --python 3.12 --with python-sat python enc/bicross_probe.py \
  -m 5 \
  --sat-pairs-hit-at-least 12 \
  --forbid-cell-pairs \
  --solver cadical195
```

Expected behavior:

```text
Q_4, pair-hit >= 6, no cell pairs: SAT: False
Q_5, pair-hit >= 12, no cell pairs: SAT: True
```

The Q5 model should report `Cell antipodal pairs: 0` and the same pair profile
as the ordinary 12-hit frontier: `both_good=4, one_good=10, both_bad=2`.

Current `Q_7` full-obstruction frontier:

```bash
make bicross-q7-full-cubes
make bicross-q7-lift-search
```

Expected behavior for `bicross-q7-full-cubes`: the target is still partial.
The first stage proves 248/256 depth-8 prefix cubes UNSAT at 20k conflicts and
leaves `0,1,2,3,6,7,14,15` UNKNOWN.  Later stages descend the current hard set
but still leave UNKNOWN cubes.

For deeper refinements, use the adaptive helper.  The current depth-20 map was
produced from the 197 hard depth-16 cubes with:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_adaptive_cube_search.py \
  -m 7 \
  --hit-bound 64 \
  --parent-depth 16 \
  --parent-indexes <depth-16-unknown-ranges> \
  --depths 20 \
  --batch-size 8 \
  --conflict-budget 10000 \
  --sort-zero-edges \
  --zero-red-degree-at-most-half \
  --partial-sym-break 20 \
  --log-file /tmp/q7_depth20_10k.jsonl
```

Expected behavior: 1,520/3,152 depth-20 descendants UNSAT at 10k conflicts,
with 1,632 UNKNOWN and no SAT cube.

Expected behavior for `bicross-q7-lift-search`: the script solves the exact
`Q_6` 28-hit seed, doubles it into `Q_7`, and reports a stable 56-hit coloring
with profile `both_good=8, one_good=38, both_bad=18`.  The one-flip scan reports
0 improving edges and 152 neutral edges.

Slice-recursion diagnostics for a `Q_5` near-extremal:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py \
  -m 5 \
  --sat-bad-at-least 14 \
  --solver cadical195 \
  --show-examples \
  --show-slices
```

Expected behavior:

- `Actual bad vertices: 14`
- some coordinate summaries have `full_bad=(7,7)` and `slice_bad=(7,7)`;
- those summaries have `recursion_score=(overlap=14, extra_full=0, slice_only=0)`;
- in those summaries, full bad and slice bad match on both sides.

Fixed-slice negation SAT check:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-fixed-slice --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 5 --sat-fixed-slice --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 6 --sat-fixed-slice --solver cadical195 --fix-zero-label --sort-zero-edges
```

Expected key lines for `m = 4`:

```text
Top variable: 560
Clauses: 2608
SAT: False
```

Expected key lines for `m = 5`:

```text
Top variable: 2160
Clauses: 12384
SAT: False
```

Expected key lines for `m = 6`:

```text
Top variable: 8448
Clauses: 57542
Symmetry: h(00...0)=red
Symmetry: incident colors at 00...0 sorted
SAT: False
```

Dimension `m = 7` was attempted with the same light symmetry breaking and
stopped without a result.  The generated formula has 33,344 variables and
262,535 clauses.

To write the `m = 7` formula for an external solver:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py \
  -m 7 \
  --sat-fixed-slice \
  --fix-zero-label \
  --sort-zero-edges \
  --no-solve \
  --tmp-file bicross_fixed_slice_m7.cnf
```

Interpretation:

This is evidence for the reduced ordinary-cube theorem:

```text
bicross lemma for Q_{n-1}
=> fixed-slice lemma
=> one-connector lemma
=> Norine
```

## Paired-Slice Failure Models

Generate a coloring with no paired-slice witness and immediately classify it:

```bash
uv run --python 3.12 --with python-sat python enc/paired_slice_witness_sat.py -n 4 --analyze-model --show-path
uv run --python 3.12 --with python-sat python enc/paired_slice_witness_sat.py -n 5 --analyze-model --show-path
uv run --python 3.12 --with python-sat python enc/paired_slice_witness_sat.py -n 6 --analyze-model
uv run --python 3.12 --with python-sat python enc/paired_slice_witness_sat.py -n 7 --analyze-model
```

Expected behavior:

- `SAT: True`
- `Verified paired-slice lift witness: None`
- `Component-chain witness: ... connector_crossings=1 ...`

Interpretation:

The paired-slice condition is not the right theorem.  SAT can avoid it.  But
the component-chain condition still finds a one-connector path.

## Inherited-Split / Incidence-Cell Dichotomy Checks

The current falsification target is high pair-hit with neither branch of the
candidate dichotomy:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py \
  -m 4 \
  --sat-pairs-hit-at-least 6 \
  --forbid-cell-pairs \
  --forbid-perfect-inherited-splits \
  --solver cadical195
```

Expected result:

```text
SAT: False
```

For Q5, use concrete post-check blocking.  The run below does not prove UNSAT;
it tries to find an actual no-perfect coloring and reports when only spurious
symbolic models are found.

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py \
  -m 5 \
  --sat-pairs-hit-at-least 12 \
  --forbid-cell-pairs \
  --forbid-perfect-inherited-splits \
  --solver cadical195 \
  --postcheck-limit 5000 \
  --postcheck-report-first 3 \
  --postcheck-report-every 500
```

Observed result on 2026-05-13: no genuine no-perfect model in 5,000
post-checked SAT colorings; every concrete coloring still had a perfect
inherited split.

Independent Q5 frontier sampling:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_extremal_analysis.py \
  -m 5 \
  --hit-bound 12 \
  --models 500 \
  --exact-hit \
  --forbid-cell-pairs \
  --summary-only \
  --solver cadical195
```

Expected key lines:

```text
cell_antipodal_pairs: 1 distinct ... pair_count 0
inheritance_shape: ... perfect_splits 1 ...
```

Bounded Q6 stress test:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_cube_search.py \
  -m 6 \
  --hit-bound 28 \
  --forbid-cell-pairs \
  --forbid-perfect-inherited-splits \
  --cube-depth 6 \
  --cube-mode prefix \
  --jobs 0 \
  --batch-size 4 \
  --conflict-budget 50000 \
  --stop-on-sat \
  --solver cadical195 \
  --sort-zero-edges \
  --zero-red-degree-at-most-half \
  --partial-sym-break 20 \
  --postcheck-limit-per-cube 5
```

Observed result on 2026-05-13: 60/64 cubes UNSAT, no SAT cubes, UNKNOWN
indexes `0,1,3,7`.

## One-Connector Negation SAT Runs

These are the most important checks.  They encode the negation of the current
candidate lemma.

Small and medium dimensions:

```bash
uv run --python 3.12 --with python-sat python enc/one_connector_witness_sat.py -n 3 --solver cadical195
uv run --python 3.12 --with python-sat python enc/one_connector_witness_sat.py -n 4 --solver cadical195
uv run --python 3.12 --with python-sat python enc/one_connector_witness_sat.py -n 5 --solver cadical195
uv run --python 3.12 --with python-sat python enc/one_connector_witness_sat.py -n 6 --solver cadical195
```

Expected result for each:

```text
SAT: False
```

Dimension 7:

```bash
uv run --python 3.12 --with python-sat python enc/one_connector_witness_sat.py \
  -n 7 \
  --solver cadical195 \
  --partial-sym-break 20 \
  --first-vertex-min-degree
```

Expected key lines:

```text
Top variable: 115136
Clauses: 749056
Clauses after symmetry breaking: 767879
Clauses after first-vertex min-degree: 790272
SAT: False
```

Interpretation:

No coloring through `n = 7` avoids the one-connector component-chain witness.

## Dimension 8 Status

Command attempted:

```bash
uv run --python 3.12 --with python-sat python enc/one_connector_witness_sat.py \
  -n 8 \
  --solver cadical195 \
  --partial-sym-break 20 \
  --first-vertex-min-degree
```

The run was stopped after roughly six minutes without a result.  This does not
give evidence either way.  It should be treated as an unfinished compute job.

Recommended next attempt:

1. Generate the CNF using `--no-solve --tmp-file`.
2. Run a standalone SAT solver with logging and a longer timeout.
3. If it remains hard, use cube-and-conquer or add a dedicated symmetry-breaking
   layer to the one-connector-negation formula.

## Original Norine Counterexample Encoding

The original Conjecture 1 counterexample formula can still be checked:

```bash
uv run --python 3.12 --with python-sat python enc/norine_general_pysat.py -n 4 --conjecture1 --antipodal-coloring --use-pysat-solver --partial-sym-break 0
uv run --python 3.12 --with python-sat python enc/norine_general_pysat.py -n 5 --conjecture1 --antipodal-coloring --use-pysat-solver --partial-sym-break 0
uv run --python 3.12 --with python-sat python enc/norine_general_pysat.py -n 6 --conjecture1 --antipodal-coloring --use-pysat-solver --partial-sym-break 0
uv run --python 3.12 --with python-sat python enc/norine_general_pysat.py -n 7 --conjecture1 --antipodal-coloring --use-pysat-solver --partial-sym-break 20 --first-vertex-min-degree
```

Expected result:

```text
Number of models: 0
```

This substantiates the original theorem through the known range.  The
one-connector-negation checks substantiate the stronger current proof target.
