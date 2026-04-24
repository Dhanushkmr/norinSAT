# Experiment Log: Norine Proof-Search

This document records the proof-search path so far: what was tried, what broke,
what survived, and why the current direction looks promising.

## Baseline

Norine's conjecture says:

> Every antipodal red/blue edge-coloring of `Q_n` has a pair of antipodal
> vertices connected by a monochromatic path.

The existing repository already encodes counterexamples to the conjecture as SAT
instances.  The new work in this branch does not replace that encoding.  It
tries to find a stronger structural reason why the SAT formulas are UNSAT.

Confirmed baseline checks:

- Conjecture 1 counterexample formula is UNSAT for `n = 4, 5, 6` without added
  symmetry breaking.
- Conjecture 1 counterexample formula is UNSAT for `n = 7` with the repository's
  practical symmetry-breaking flags.

## Attempt 1: Reducible Slices

Initial idea:

> Every valid `Q_n` antipodal coloring might come from a valid `Q_{n-1}`
> coloring in some coordinate slice.

For coordinate `i`, call a slice reducible if the `x_i = 0` slice is antipodal
as a `Q_{n-1}` coloring.  In a full antipodal coloring, this also forces the
opposite slice to be the same projected `Q_{n-1}` coloring.

What worked:

- If a reducible slice exists, and the lower-dimensional coloring has a
  monochromatic antipodal path, that path lifts to a full `Q_n` monochromatic
  antipodal path regardless of connector colors.
- This lift was checked exhaustively for `Q_2 -> Q_3` and `Q_3 -> Q_4`.

What failed:

- Reducible slices are not generic.
- Exact `Q_3`: 16 of 64 antipodal colorings have no reducible slice.
- Exact `Q_4`: 61,824 of 65,536 antipodal colorings have no reducible slice.
- Modulo cube automorphism and global color swap, `Q_3` still has a whole orbit
  with no reducible slice.

Why it failed:

The full antipodal condition relates an edge to the fully complemented edge in
the opposite slice.  It does not relate an edge to its slice-antipode inside the
same slice.  So "full antipodal" does not imply "some slice is antipodal."

Conclusion:

The reducible-slice lemma is too strong for arbitrary colorings.  It might still
hold under a hypothetical counterexample/minimality assumption, but the data does
not suggest it is the cleanest route.

## Attempt 2: Paired-Slice Lift

Weakened idea:

> It may be enough for both `Q_{n-1}` slices to connect the same projected
> antipodal pair in the same color.

This condition also lifts immediately: the two antipodal connector edges have
opposite colors, so one of them completes a monochromatic path.

What worked:

- The condition captures many more colorings than reducible slices.
- Exact `Q_4`: 64,288 of 65,536 colorings have this witness.
- Random `Q_5` and `Q_6` samples all had this witness.

What failed:

- SAT can construct colorings with no paired-slice witness for `n = 4, 5, 6, 7`.
- Every such model still has a monochromatic antipodal path.

Why it failed:

The connector that completes the path does not need to sit at one of the two
projected antipodal endpoints.  It only needs to connect the correct
monochromatic slice components.  The paired-slice condition was still too
endpoint-focused.

Conclusion:

The actual mechanism is not "same endpoint pair connected in both slices."  It
is "one connector joins the right two same-color slice components."

## Attempt 3: Component-Chain Classification

Current successful refinement:

For a coordinate `i` and color `c`:

1. Split `Q_n` into slices `x_i = 0` and `x_i = 1`.
2. Compress each slice into monochromatic `c`-components.
3. Add quotient edges for connector edges of color `c`.
4. Search the quotient graph for a path from the component of `v` to the
   component of `anti(v)`.

The quotient path length is the number of connector crossings in the full
monochromatic path.

What worked:

- Exact `Q_3`: every coloring has a 1-connector component-chain witness.
- Exact `Q_4`: every coloring has a 1-connector component-chain witness.
- Random samples:
  - `Q_5`: 10,000/10,000 have a 1-connector witness.
  - `Q_6`: 1,000/1,000 have a 1-connector witness.
  - `Q_7`: 500/500 have a 1-connector witness.
- SAT models constructed to avoid the paired-slice witness for `n = 4, 5, 6, 7`
  still have a 1-connector component-chain witness.

Why it worked better:

It captures the actual path construction:

```text
same-color path inside one slice
then one same-color connector
then same-color path inside the other slice
```

The connector can start and end anywhere inside the two relevant slice
components.  That is exactly what the paired-slice condition missed.

## Attempt 4: SAT Negation of the One-Connector Lemma

Candidate lemma:

> Every antipodal coloring of `Q_n` has a monochromatic antipodal path that
> crosses exactly one connector in some coordinate split.

The SAT script `enc/one_connector_witness_sat.py` encodes the negation: an
antipodal coloring with no one-connector component-chain witness in any
coordinate split or color.

Results:

- `n=3`: UNSAT.
- `n=4`: UNSAT.
- `n=5`: UNSAT.
- `n=6`: UNSAT.
- `n=7`: UNSAT with CaDiCaL 1.95 and the same style of symmetry breaking used by
  the repository's practical `n=7` proof.
- `n=8`: attempted with the same symmetry-broken command and stopped after
  roughly six minutes without a result.

Interpretation:

Through `n <= 7`, Norine holds for the stronger reason that a one-connector
component-chain witness always exists.  This is stronger than just saying there
is some monochromatic antipodal path.

## Current Status

The current best proof target is the one-connector lemma, not the original
reducible-slice lemma.

The finite data supports:

```text
antipodal coloring
  => exists coordinate split and color
  => one connector joins the slice component of v to the opposite-slice
     component of anti(v)
  => monochromatic antipodal path
```

What remains open:

- Prove the one-connector lemma combinatorially.
- Or push the SAT negation to `n=8` and beyond using longer external solves,
  cube-and-conquer, or a Lean/CNF-backed certificate workflow.
