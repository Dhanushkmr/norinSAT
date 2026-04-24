# From the Finite to the Infinite: Sharper Asymptotic Bounds on Norin’s Conjecture via SAT

This repository contains the code for our paper on Norin's conjecture on edge-colorings of hypercubes.

# Prerequisites

To install CaDiCaL for direct solving, run
```bash
cd dynamic
sh build-and-install.sh
cd ..
```

For the Python/PySAT workflow, use `uv`:

```bash
uv run --python 3.12 --with python-sat python <script> ...
```

Developer shortcuts and parallel SAT portfolio commands are documented in
`docs/DEV_SETUP.md`.

# Commands for Reproducing Results

We use the Python 3 script `enc/norine_general_pysat.py` to create SAT encodings.  
The generated formula can either be printed to a file or solved directly using an internal SAT solver.

---

## Conjecture Flags (Paper Order)

The conjecture flags now match the paper order directly:

- `--conjecture1`: antipodal coloring, monochromatic **path**
- `--conjecture2`: antipodal coloring, monochromatic **geodesic**
- `--conjecture3`: general coloring, path with at most one color change
- `--conjecture4`: general coloring, geodesic with at most one color change

For `--conjecture1` and `--conjecture2`, you must pass `--antipodal-coloring`.

## Example Commands

```bash
# Conjecture 1
python3 enc/norine_general_pysat.py -n <N> --conjecture1 --antipodal-coloring --first-vertex-min-degree

# Conjecture 2
python3 enc/norine_general_pysat.py -n <N> --conjecture2 --antipodal-coloring --first-vertex-min-degree

# Conjecture 3
python3 enc/norine_general_pysat.py -n <N> --conjecture3 --first-vertex-min-degree

# Conjecture 4
python3 enc/norine_general_pysat.py -n <N> --conjecture4 --first-vertex-min-degree
```

To write any encoding to a file without solving:

```bash
--tmp-file FILE --no-solve
```

To set the `maxcomparisons` parameter for symmetry breaking:

```bash
--partial-sym-break VALUE
```

Run `--help` for the full list of options.

**Note**: running with `-n 6` should terminate almost immediately, with `-n 7` it can take seconds to minutes, and for `-n 8` you may need Cube-and-Conquer.

## Computing the $f$ and $\hat{f}$ Values

To compute the **$f$ values**, run:

```bash
python3 enc/norine_general_pysat.py -n N -b B --first-vertex-min-degree
```

- Here $B = \alpha \cdot 2^{N-1}$, where $\alpha$ is the average number of color changes, and $2^{N-1}$ is the number of antipodal vertex pairs.

To compute **$\hat{f}$ values**, add the `-p` flag:

```bash
python3 enc/norine_general_pysat.py -n N -b B -p --first-vertex-min-degree
```

For example, the two encodings required to compute $\hat{f}$ for `n = 6` are:

```bash
python3 enc/norine_general_pysat.py -n 6 -b 28 --first-vertex-min-degree
python3 enc/norine_general_pysat.py -n 6 -b 29 --first-vertex-min-degree
```

## Encoding File Layout

- `enc/conjecture_encodings.py`: conjectures 1-4
- `enc/f_encoding.py`: `f`, `f'`, `b2`, `b3`, and conjecture 6 style encoding
- `enc/encoding_context.py`: hypercube construction, edge variables, antipodal edge mapping
- `enc/norine_general_pysat.py`: CLI + orchestration + symmetry-breaking / solving


## Details for reproducibility

We used `kissat` version 4.0.2, and `cadical` version 2.0.0. The cubing tool `march_cu` is available at [https://github.com/marijnheule/CnC/tree/master/march_cu](https://github.com/marijnheule/CnC/tree/master/march_cu), and `proofix` is available at [https://github.com/zaxioms0/proofix](https://github.com/zaxioms0/proofix).

For example, to cube a formula using `march_cu` using depth 12 (resulting in ~4000 cubes), run

```bash
march_cu <formula>.cnf -q -d 12 -cnf > output.icnf
```
Then, `output.icnf` will contain all the cubes at the end of the formula. We can then split `output.icnf` into as many formulas as cubes it has as follows:
to construct the formula corresponding to the $i$-th cube, copy all the lines of `output.icnf` corresponding to clauses (i.e., lines that start with a number), and then take the $i$-th line starting with `a`, which will look like
```
a <lit 1> <lit 2> .... <lit k> 0
```
and add $k$ unit clauses to the formula
```
<lit 1> 0
<lit 2> 0
...
<lit k> 0
```
