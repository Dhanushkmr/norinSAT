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

Fixed-slice negation SAT check:

```bash
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-fixed-slice --solver cadical195
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 5 --sat-fixed-slice --solver cadical195
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
