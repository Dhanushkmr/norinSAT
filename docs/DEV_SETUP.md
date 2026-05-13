# Developer Setup

This repo has two tiers of checks:

```bash
make test
make test-sat
make test-all
```

`make test` uses only the standard library.  `make test-sat` runs the optional
PySAT-backed tests through `uv`:

```bash
uv run --python 3.12 --with python-sat python ...
```

## Solver Selection

The PySAT-backed scripts now select a preferred available solver when
`--solver` is omitted.  The current preference order is:

```text
cadical195, kissat404, cadical153, cadical103, glucose4,
glucose42, maplechrono, gluecard4, gluecard3, maplesat,
maplecm, mergesat3, minicard, minisat22, minisatgh,
lingeling, cryptosat
```

To see which of these are available in the current environment:

```bash
make list-solvers
```

## Parallel Portfolio Runs

Most SAT solvers used here are single-core.  To use all cores, run independent
solver backends in parallel with `enc/sat_portfolio.py`.

Example bicross `Q_7` full-obstruction benchmark:

```bash
uv run --python 3.12 --with python-sat python enc/sat_portfolio.py \
  --timeout 600 \
  -- python enc/bicross_probe.py \
    -m 7 \
    --sat-pairs-hit-at-least 64 \
    --sort-zero-edges \
    --zero-red-degree-at-most-half
```

The runner defaults to all available cores.  Override with `--jobs N`.
By default it stops after the first decisive `SAT: True` or `SAT: False`.
Use `--keep-going` for benchmarking all solvers.

For external DIMACS solvers, put `{solver}` in the command template:

```bash
python3 enc/sat_portfolio.py \
  --solvers kissat,cadical \
  -- {solver} formula.cnf
```

Useful Make targets:

```bash
make bicross-q6-frontier
make bicross-q6-cubes
make bicross-q6-hit31-proof
make bicross-q6-hit30-proof
make bicross-q6-hit29-proof
make bicross-extremal-shapes
make bicross-no-cell-frontier
make bicross-dichotomy-checks
make bicross-quantitative-construction
make bicross-good-count-falsification
make bicross-bad-structure
make bicross-q7-portfolio
make bicross-q7-full-cubes
make bicross-q7-lift-search
```

`make bicross-q6-frontier` runs a solver portfolio on the hard 29-hit question.
`make bicross-q6-cubes` instead uses one preferred solver over a parallel
assumption split of the same formula.  The `hit31`, `hit30`, and `hit29` proof
targets replay the staged cube proofs; `hit29` is the exact current frontier
and uses all available cores by default.  Set `JOBS=4` or similar to cap CPU
usage.

`make bicross-extremal-shapes` samples exact Q4, Q5, and Q6 pair-hit frontier
models and prints aggregate component-incidence signatures.  This is the
fastest way to replay the current non-compute proof clue.

`make bicross-no-cell-frontier` tests the incidence-cell restriction: Q4 should
be UNSAT, Q5 should be SAT, and the Q6 quick cube pass is currently expected to
finish UNKNOWN unless the frontier has moved.

`make bicross-dichotomy-checks` tests the sharper no-cell/no-perfect-inherited
split falsification target.  Q4 should be UNSAT, Q5 should keep showing
perfect inherited splits in exact no-cell samples, and the bounded Q6 cube pass
is expected to return UNKNOWN with no SAT counter-signal.

`enc/bicross_frontier_construction.py` prints the paired-coordinate
construction that realizes the conjectured sharp bicross count
`2^floor((m-1)/2)`.

`make bicross-good-count-falsification` reproduces the `Q_6` SAT model with
38 bad vertices.  This records that vertex-count minimization is a false
proof route; the main lower-bound invariant is bad-set pair coverage.

`make bicross-bad-structure` compares the paired-coordinate `Q_6`
construction with the 38-bad SAT witness and prints the incidence cell that
carries the four bicross antipodal pairs.

`make bicross-q7-full-cubes` replays the current partial cube-and-conquer
frontier for the `Q_7` full bicross obstruction.  It is not a proof target yet;
the expected result is a shrinking UNKNOWN set.  `make bicross-q7-lift-search`
constructs the doubled `Q_6` extremal inside `Q_7` and checks its local-search
neighborhood.

For deeper nested refinements, use `enc/bicross_adaptive_cube_search.py`.  It
accepts parent cube indexes, descends only those parents to deeper prefix cubes,
and can write a JSONL stage log with `--log-file`.  This is the preferred helper
for continuing the `Q_7` depth-16/depth-20 frontier.
