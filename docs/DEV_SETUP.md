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
make bicross-q7-portfolio
```

`make bicross-q6-frontier` runs a solver portfolio on the unresolved 29-hit
question.  `make bicross-q6-cubes` instead uses one preferred solver over a
parallel assumption split of the same formula.
`make bicross-q6-hit31-proof` replays the cube proof that `Q_6` cannot have
bad vertices hitting 31 of the 32 antipodal pairs.
