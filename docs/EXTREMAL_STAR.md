# Extremal Star Pattern

This note tracks the current non-compute proof direction after the Q6 pair-hit
frontier was resolved.

## Setup

For an ordinary red/blue edge-coloring of `Q_m`, define

```text
G = {x : C_red(x) intersects C_blue(anti(x))}
Bad = V(Q_m) \ G
```

A bicross antipodal pair is an antipodal pair `{x, anti(x)}` where both
directions work:

```text
C_red(x)  intersects C_blue(anti(x))
C_blue(x) intersects C_red(anti(x))
```

The pair-hit SAT frontier maximizes the number of antipodal pairs touched by
`Bad`.  A full counterexample to the bicross lemma would need `Bad` to touch
every antipodal pair.

## New Analyzer

Script: `enc/bicross_extremal_analysis.py`

The analyzer SAT-generates high pair-hit colorings and summarizes their
component structure:

- pair profile: `both_good`, `one_good`, `both_bad`;
- red/blue component-size signatures;
- incidence cells `(red_component, blue_component)`;
- antipodal pairs lying inside one incidence cell;
- bicross meet shape;
- coordinate-slice signatures.

Useful replay command:

```bash
make bicross-extremal-shapes
```

## Observed Frontier Structure

Exact Q3 frontier, all 192 exact 2-hit models:

- Pair profile is always `both_good=2, one_good=2`.
- 144/192 models have a single incidence cell containing both bicross pairs.
- 48/192 models still have bicross pairs, but no antipodal pair lies inside one
  incidence cell.  So the incidence-cell statement is not true in full
  generality.

Q4, 100 exact 6-hit models:

- Pair profile is always `both_good=2, one_good=5, both_bad=1`.
- Every sampled model has exactly one incidence cell containing exactly two
  antipodal pairs.
- The bicross shape is constant: two bicross pairs, one common meet vertex.

Q5, first 100 unconstrained exact 12-hit models:

- Pair profile is always `both_good=4, one_good=10, both_bad=2`.
- Every sampled model has exactly one incidence cell containing exactly four
  antipodal pairs.
- The bicross shape is constant: four bicross pairs, one common meet vertex.

However, this sample was biased toward one frontier family.  Adding the SAT
restriction `--forbid-cell-pairs` finds exact 12-hit Q5 models with no
incidence-cell antipodal pair.

Q5, 20 exact 12-hit models with no incidence-cell antipodal pair:

- Pair profile is still `both_good=4, one_good=10, both_bad=2`.
- Every sampled model has a perfect inherited slice: one coordinate split has
  recursion score `(14, 0, 0)` and uniform connectors.
- The bicross shape is constant but different: four bicross pairs, two meet
  vertices, each meet vertex used four times, and no bicross pair has the same
  red/blue meet vertex.

Q6, 100 exact 28-hit models with symmetry breaks:

- Pair profile is always `both_good=4, one_good=19, both_bad=9`.
- Bad Hamming-weight histogram is always
  `{1:2, 2:8, 3:12, 4:10, 5:4, 6:1}`.
- Every sampled model has exactly one incidence cell containing exactly four
  antipodal pairs.
- The bicross shape is constant: four bicross pairs, one common meet vertex.
- Component sizes, incidence multiplicities, slice signatures, and boundary
  profiles vary across samples.  The invariant is not a single canonical
  coloring.
- In 20 resampled models with inheritance summaries, every split had
  `slice_only = 0`, but no split had perfect inheritance.

Q6 with `--forbid-cell-pairs` remains unresolved locally:

- Direct solver did not finish before being stopped.
- Depth-8 prefix cubing with 50k conflicts per cube proved 246/256 cubes UNSAT,
  leaving `0,1,4,5,12,13,15,28,29,31`.
- A 500k pass on those 10 proved cube `15` UNSAT and left
  `0,1,4,5,12,13,28,29,31`.
- Descending those 9 to depth 12 with 100k conflicts per cube gave 93 UNSAT
  descendants and 51 UNKNOWN; no SAT model appeared.

A small canonical check on three Q6 28-hit models put them in three different
cube-automorphism/global-color orbits, while preserving the same coarse
incidence-cell star shape.

## Interpretation

The useful object is now the red/blue component incidence matrix.

If an incidence cell `C_red_i intersect C_blue_j` contains both endpoints of an
antipodal pair, then that pair is automatically bicross: the two endpoints are
in the same red component and the same blue component.  This is stronger and
cleaner than finding two unrelated cross-intersections.

The initial Q4-Q6 unconstrained samples suggested that near-obstructions may be
forced to place their surviving bicross pairs inside one large incidence cell.
The Q5 no-cell models show this is false as stated.

The better current reading is a dichotomy:

> A coloring whose `Bad` set almost hits every antipodal pair either has a
> lower-dimensional inherited split, or it contains a red/blue incidence cell
> with an antipodal pair.

For Q5, the no-cell frontier family is inherited from Q4 through a perfect
uniform-connector split.  For the sampled Q6 star family, no perfect inherited
split appears.  This is the most promising induction interface currently on
the table.

## What Worked

- Reducible slices and paired slices were too rigid.
- Direct SAT proved finite cases but did not expose a clean induction.
- Pair-hit optimization found the real near-obstruction surface.
- Component incidence turned one major frontier family into a small, repeatable
  shape.
- The explicit no-cell SAT restriction found a second Q5 family that ordinary
  model sampling missed.

## What Did Not Work

- More brute force on Q7 is not the right local next step without more compute.
- Isomorphism does not collapse the frontier to one example.
- A blanket "some incidence cell contains an antipodal pair" lemma is false.
  Q3 has exact-frontier examples, and Q5 has exact-frontier examples.

## Next Proof Moves

1. Prove a dichotomy lemma: if `Bad` hits many antipodal pairs, then either
   there is a perfect inherited slice or one incidence cell contains an
   antipodal pair.
2. Relate missing target cells `(R(x), B(anti(x)))` to occupied cells
   `(R(x), B(x))`; the Q6 extremal has many bad vertices compressed into only a
   few missing target cells.
3. Study the boundary of one incidence cell.  A cell with no antipodal pair
   must have its antipode spread across other cells; cube expansion may force a
   forbidden red/blue contact.
4. Use Q4 and Q5 exact frontiers as base cases for a stability/dichotomy
   induction, with Q6 serving as the first high-dimensional stress test.
