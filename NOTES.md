# Norine Induction Notes

## Document Map

- `docs/EXPERIMENT_LOG.md`: chronological record of what worked, what failed,
  and why the proof-search direction changed.
- `docs/PROOF_DIRECTION.md`: current mathematical proof target and possible
  routes to a proof.
- `docs/BICROSS_LEMMA.md`: reduced ordinary-cube component theorem behind the
  one-connector lemma.
- `docs/EXTREMAL_STAR.md`: current structural direction from Q4-Q6 pair-hit
  frontier models.
- `docs/REPRODUCING_RESULTS.md`: commands and expected outputs for the current
  computational evidence.

## Goal

Use the existing SAT/verification code as a laboratory for a proof of Norine's
conjecture in all dimensions:

> Every antipodal red/blue edge-coloring of `Q_n` has a pair of antipodal
> vertices connected by a monochromatic path.

The working idea is an induction on dimension.  If every counterexample in
dimension `d` necessarily contains a coordinate slice that is really a
dimension `d-1` antipodal coloring, then a proven base range could rule out all
higher dimensions.

## Important Definitions To Keep Separate

- A full `Q_d` antipodal coloring satisfies
  `color(e) != color(anti_full(e))`, where `anti_full` complements every vertex
  coordinate.
- A coordinate slice, say `x_k = 0`, is a copy of `Q_{d-1}` using all edge
  directions except `k`.
- The slice is antipodal as a `Q_{d-1}` coloring only if
  `color(e) != color(anti_slice(e))`, where `anti_slice` complements the
  `d-1` coordinates inside the slice and keeps `x_k` fixed.

The full antipodal condition does not directly imply the slice antipodal
condition.  It relates an edge in one slice to an edge in the opposite slice,
not to the edge's antipode inside the same slice.

## Candidate Reducible-Slice Lemma

For a coordinate `k`, call the slice reducible if the `x_k = 0` slice is an
antipodal `Q_{d-1}` coloring.  Under the full `Q_d` antipodal condition, this
also forces the `x_k = 1` slice to be the same `Q_{d-1}` coloring under the
natural coordinate projection.

Candidate structural lemma:

> Every minimal counterexample in `Q_d` has at least one reducible coordinate
> slice.

This is weaker than saying every antipodal coloring has a reducible slice, and
it is the version that would actually interact with induction.

## First Code Plan

1. Add a small-dimension probe that can enumerate antipodal colorings.
2. Test whether arbitrary antipodal colorings always have a reducible slice.
3. Test the same property after filtering by monochromatic antipodal paths.
4. If the broad reducible-slice statement is false, preserve explicit
   counterexamples so the induction invariant can be tightened.

## Current Risk

The statement "a `Q_d` antipodal coloring must come from a valid `Q_{d-1}`
coloring" looks too strong unless "valid" means "counterexample-like" plus
additional minimality/symmetry hypotheses.  The next task is to find the
smallest dimension where the broad statement fails.

## Probe Results

Script: `enc/induction_probe.py`

Lift checks:

- `Q_2 -> Q_3`: checked 4 base colorings and 16 connector assignments; no
  lift violations.
- `Q_3 -> Q_4`: checked 64 base colorings and 1,024 connector assignments; no
  lift violations.

This supports the easy part of the induction idea.  If the two `Q_{d-1}` slices
are identical antipodal colorings and one slice has a monochromatic path from
`x` to `anti_slice(x)`, then the connector at `x` or the connector at
`anti_slice(x)` has that same color, because connector antipodes have opposite
colors.  Using the matching connector first or last gives a monochromatic path
between full antipodal vertices of `Q_d`.

Exact enumeration:

- `Q_3`: 64 antipodal colorings.
  - 64 have a monochromatic antipodal path.
  - 48 have at least one reducible slice.
  - 16 have no reducible slice.
  - Up to cube automorphism and global color swap there are 3 orbits; 1 orbit
    has no reducible slice.
- `Q_4`: 65,536 antipodal colorings.
  - 65,536 have a monochromatic antipodal path.
  - 3,712 have at least one reducible slice.
  - 61,824 have no reducible slice.

Random sampling:

- `Q_5`: 10,000/10,000 sampled colorings had no reducible slice, while all sampled
  colorings had a monochromatic antipodal path.
- `Q_6`: 200/200 sampled colorings had no reducible slice, while all sampled
  colorings had a monochromatic antipodal path.

Environment note:

- The standalone probe is dependency-free.
- The repository's `enc/norine_general_pysat.py` SAT entry point needs
  `python-sat`.  It works via:
  `uv run --python 3.12 --with python-sat python enc/norine_general_pysat.py ...`

SAT checks, Conjecture 1 (`--conjecture1 --antipodal-coloring`):

- `n=4`, no symmetry breaking:
  - 160 variables, 552 clauses.
  - SAT models: 0.
- `n=5`, no symmetry breaking:
  - 592 variables, 2,576 clauses.
  - SAT models: 0.
- `n=6`, no symmetry breaking:
  - 2,240 variables, 12,128 clauses.
  - SAT models: 0.
- `n=7`, with partial symmetry breaking 20 and first-vertex min-degree:
  - 8,640 variables before symmetry breaking, 97,728 final clauses.
  - SAT models: 0.

Interpretation: the direct counterexample encoding is UNSAT for `n=4,5,6`, and
the repository's practical symmetry-broken `n=7` check is also UNSAT.  A fully
unsymmetrized `n=7` run was launched as a comparison but stopped after the
symmetry-broken run completed.

Conclusion so far: reducible slices are not a generic consequence of antipodal
edge-coloring, even after accounting for isomorphism.  The property "there is
some reducible coordinate slice" is invariant under hypercube automorphisms:
automorphisms only permute/complement coordinates, so they send coordinate
slices to coordinate slices and preserve the slice-antipodal inequality.  If an
induction proof works, the reducible-slice lemma must be about hypothetical
counterexamples, probably with a minimality condition or with additional
constraints extracted from the absence of monochromatic antipodal paths.

## Next Proof-Coding Direction

Encode and test stronger counterexample structure rather than arbitrary
colorings.  Useful candidate lemmas:

1. No-path colorings imply at least one reducible slice.
2. Minimal no-path colorings imply at least one reducible slice.
3. No-path colorings imply a weaker slice invariant that is enough to lift a
   `Q_{d-1}` monochromatic path into a `Q_d` monochromatic antipodal path.

For dimensions where Norine is already SAT-proven, lemma 1 is vacuous.  To get
non-vacuous feedback, the next probe should either:

- relax "no monochromatic path" into a local obstruction that can still have
  models, or
- use SAT assumptions to search directly for violations of the proposed slice
  invariant and inspect the learned structural reasons they cannot coexist with
  the full no-path constraints.

## Paired-Slice Lift Attempt

A weaker lift condition than reducible slices:

> There is a coordinate split, a color, and a projected antipodal pair
> `x, anti(x)` such that both `Q_{d-1}` slices connect `x` to `anti(x)` in that
> color.

This also forces a full monochromatic antipodal path, because the two connector
edges at `x` and `anti(x)` have opposite colors.

Probe results:

- `Q_3`: 48/64 colorings have this witness.
- `Q_4`: 64,288/65,536 colorings have this witness.
- Random `Q_5` and `Q_6` samples all had this witness, but this was misleading:
  the witness-failing cases are structured and rare.

SAT script: `enc/paired_slice_witness_sat.py`

- `n=4`: SAT.  The found model has no paired-slice witness, but still has a
  monochromatic antipodal path.
- `n=5`: SAT.  The found model has no paired-slice witness, but still has a
  monochromatic antipodal path.
- `n=6`: SAT.  The found model has no paired-slice witness, but still has a
  monochromatic antipodal path.
- `n=7`: SAT.  The found model has no paired-slice witness, but still has a
  monochromatic antipodal path.

Conclusion: paired-slice lift is a useful witness, but not a universal
dimension-reduction theorem.  The next invariant should classify the actual
monochromatic path in witness-failing models.  In component terms, the path is a
same-color chain in the quotient graph whose nodes are slice components and
whose cross-slice edges are the matching connectors.  A true counterexample must
make this quotient graph antipode-free in both colors.

## Component-Chain Classifier

Script: `enc/component_chain_classifier.py`

For a coloring, coordinate `i`, and color `c`:

1. Split `Q_n` into the two slices `x_i = 0` and `x_i = 1`.
2. Compress each slice into its monochromatic `c`-components.
3. Build a quotient graph whose nodes are `(side, component_id)`.
4. Add a quotient edge for each connector edge of color `c`.
5. Search for a quotient path from the component of `v` to the component of
   `anti(v)`.  The quotient path length is the number of connector crossings.

The classifier reconstructs a full vertex path on request and asserts agreement
with the existing full-graph `monochromatic_antipodal_path` checker.

Results:

- Exact `Q_3`: all 64 colorings have a 1-connector component-chain witness.
- Exact `Q_4`: all 65,536 colorings have a 1-connector component-chain witness.
- Random `Q_5`: 10,000/10,000 sampled colorings have a 1-connector witness.
- Random `Q_6`: 1,000/1,000 sampled colorings have a 1-connector witness.
- Random `Q_7`: 500/500 sampled colorings have a 1-connector witness.
- SAT models with no paired-slice witness for `n = 4,5,6,7` all still have a
  1-connector component-chain witness.

Useful commands:

```bash
python3 enc/component_chain_classifier.py -n 4 --enumerate
python3 enc/component_chain_classifier.py -n 5 --samples 10000
uv run --python 3.12 --with python-sat python enc/paired_slice_witness_sat.py -n 6 --analyze-model
```

Best current candidate lemma:

> In every antipodal coloring of `Q_n`, there exist a coordinate `i`, a color
> `c`, and an antipodal vertex pair `v, anti(v)` such that one connector edge of
> color `c` joins the `c`-component of `v` in one `i`-slice to the `c`-component
> of `anti(v)` in the other `i`-slice.

This is stronger than the paired-slice condition because the connector can be at
any vertex in the two slice components, not necessarily at `v` or
`anti_slice(v)`.  If this lemma is true, Norine follows immediately by taking a
same-color path inside the first slice component, crossing the connector, and
then taking a same-color path inside the second slice component.

## One-Connector Witness SAT Test

Script: `enc/one_connector_witness_sat.py`

This encodes the negation of the current candidate lemma: an antipodal coloring
with no one-connector component-chain witness in any coordinate split or color.
Reachability roots are forced true, so zero-length in-slice path segments are
handled correctly.

Results:

- `n=3`: UNSAT.  204 variables, 576 clauses.
- `n=4`: UNSAT.  1,056 variables, 3,840 clauses.
- `n=5`: UNSAT.  5,200 variables, 23,680 clauses.
- `n=6`: UNSAT.  24,768 variables, 136,704 clauses.
- `n=7`: UNSAT with `--solver cadical195 --partial-sym-break 20
  --first-vertex-min-degree`.
  - 115,136 variables before symmetry breaking.
  - 749,056 clauses before symmetry breaking.
  - 790,272 clauses after symmetry breaking and min-degree constraints.
- `n=8`: attempted with the same symmetry-broken command and stopped after
  roughly six minutes without a result.  This should be rerun as a longer
  compute job, preferably with unbuffered progress and/or external CNF solving.

Useful commands:

```bash
uv run --python 3.12 --with python-sat python enc/one_connector_witness_sat.py -n 7 --solver cadical195 --partial-sym-break 20 --first-vertex-min-degree
uv run --python 3.12 --with python-sat python enc/one_connector_witness_sat.py -n 8 --solver cadical195 --partial-sym-break 20 --first-vertex-min-degree
```

Interpretation: through the verified `n <= 7` range, Norine holds for the
stronger reason that every coloring has a one-connector component-chain witness.
This is now the best proof target.

## Regression Tests

Script: `enc/test_component_chain_classifier.py`

Dependency-free tests:

- Exhaustively enumerate `Q_3` and assert all 64 colorings have a valid
  one-connector witness with a reconstructed path.
- Exhaustively enumerate `Q_4` and assert all 65,536 colorings have a valid
  one-connector witness.
- Sample 200 `Q_5` colorings and assert reconstructed paths validate.
- Check all 64,288 `Q_4` colorings with a paired-slice witness also classify as
  one-connector witnesses.

Optional PySAT tests, run via `uv --with python-sat`:

- Encode the one-connector negation for `Q_3` and `Q_4` and assert UNSAT.
- Construct a `Q_4` SAT model with no paired-slice witness and assert the
  component-chain classifier still finds a one-connector witness.

Verification commands:

```bash
python3 -m py_compile enc/induction_probe.py enc/component_chain_classifier.py enc/paired_slice_witness_sat.py enc/one_connector_witness_sat.py enc/test_component_chain_classifier.py
python3 enc/test_component_chain_classifier.py
uv run --python 3.12 --with python-sat python enc/test_component_chain_classifier.py
```

Latest results:

- Plain Python: 6 tests, OK, 2 optional SAT tests skipped.
- PySAT via `uv`: 6 tests, OK.

## April 24, 2026: Contradiction Proof Attempt

The one-connector lemma can be reduced to a cleaner fixed-slice statement.

Fix any coordinate split and write the `0`-slice as `H = Q_{n-1}`.  Let `h(a)`
be the connector color at projected vertex `a`.  The full antipodal condition
gives `h(anti(a)) = 1 - h(a)`, and complementing projected vertices swaps
color-`c` paths in the `0`-slice with color-`1-c` paths in the `1`-slice.

So a one-connector witness at connector `a` exists exactly when, inside the
`0`-slice,

```text
C_{h(a)}(a) intersects C_{1-h(a)}(anti(a)).
```

This suggests the following fixed-slice lemma:

> For every edge-coloring of `Q_m` and every antipodal vertex-labeling `h`,
> `h(anti(a)) = 1 - h(a)`, some vertex `a` satisfies
> `C_{h(a)}(a) intersect C_{1-h(a)}(anti(a)) != empty`.

Equivalently, it is enough to prove the bicross lemma:

> In every red/blue edge-coloring of `Q_m`, some antipodal pair `x, anti(x)`
> satisfies both
> `C_red(x) intersect C_blue(anti(x)) != empty` and
> `C_blue(x) intersect C_red(anti(x)) != empty`.

This is now the best contradiction target.  If it is false, choose for every
antipodal pair whichever of the two intersections is empty.  This gives an
antipodal labeling `h` whose selected component at `x` is disjoint from the
selected component at `anti(x)` for every `x`.

Useful local observation:

- A disjoint red component and blue component cannot even be adjacent by a cube
  edge.  A red edge would merge the endpoint into the red component; a blue edge
  would merge the other endpoint into the blue component.

Therefore a counterexample to the bicross lemma would create an antipodal
family of component separations, all at graph distance at least two.  The likely
next proof move is to convert those separations into a Tucker/Borsuk-Ulam style
labeling and force a complementary adjacency, which should be the forbidden
cross-intersection.

Quick SAT sanity check for the fixed-slice negation:

- `m=4`: UNSAT with 560 variables and 2,608 clauses.
- `m=5`: UNSAT with 2,160 variables and 12,384 clauses.
- `m=6`: launched with 8,448 variables and 57,536 clauses, then stopped after
  it did not finish quickly.

Interpretation: the reduction is not just cosmetically simpler.  It appears to
isolate the real theorem: a pure component-crossing fact about arbitrary
red/blue edge-colorings of the cube.

Implemented probe: `enc/bicross_probe.py`

Useful commands:

```bash
python3 enc/bicross_probe.py -m 3 --enumerate
python3 enc/bicross_probe.py -m 3 --enumerate --check-all-labelings
python3 enc/bicross_probe.py -m 4 --samples 10000
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-fixed-slice --solver cadical195
```

Current probe results:

- Exact `Q_2`: all 16 ordinary edge-colorings satisfy bicross; all 64
  coloring/antipodal-labeling pairs have a fixed-slice witness.
- Exact `Q_3`: all 4,096 ordinary edge-colorings satisfy bicross; all 65,536
  coloring/antipodal-labeling pairs have a fixed-slice witness.
- Random `Q_4`: 10,000/10,000 sampled ordinary edge-colorings satisfy bicross.
- SAT fixed-slice negation for `Q_4`: UNSAT with 560 variables and 2,608
  clauses.
- SAT fixed-slice negation for `Q_5`: UNSAT with 2,160 variables and 12,384
  clauses.
- SAT fixed-slice negation for `Q_6`: UNSAT with light symmetry breaking
  (`h(00...0)=red` and sorted colors incident to `00...0`), with 8,448
  variables and 57,542 clauses.
- SAT fixed-slice negation for `Q_7`: attempted with the same symmetry breaking
  and stopped without a result.  The formula has 33,344 variables and 262,535
  clauses.  Use `enc/bicross_probe.py --no-solve` to export it for an external
  solver.

Counting route:

- Define `G = {x : R(x) intersects B(anti(x))}`.
- A bicross pair is exactly an antipodal pair contained in `G`.
- It is enough to prove `|G| > 2^{m-1}`.
- Exact `Q_2`: minimum `|G| = 3`.
- Exact `Q_3`: minimum `|G| = 6`.
- Pair-hit SAT frontiers:
  `Q_2` max hit pairs = 1 of 2,
  `Q_3` max hit pairs = 2 of 4,
  `Q_4` max hit pairs = 6 of 8,
  `Q_5` max hit pairs = 12 of 16,
  `Q_6` max hit pairs = 28 of 32.
  The `Q_6` maximum is already above the pure doubling lower bound of 24.
- SAT `Q_4`: no coloring has 8 bad vertices, but a coloring with 7 bad
  vertices exists; therefore minimum `|G| = 9`.
- SAT `Q_5`: a coloring with 14 bad vertices exists, so `|G| = 18` is
  attainable.  The search for 15 bad vertices did not finish quickly.
- Pair-hit SAT `Q_5`: bad vertices can hit 12 of the 16 antipodal pairs, but
  cannot hit 13.  So every `Q_5` coloring has at least four bicross pairs.
- Pair-hit SAT `Q_6`: bad vertices can hit 28 of the 32 antipodal pairs, but
  not 29.  So every `Q_6` coloring has at least four bicross pairs.
- Earlier 90-second and 300-second portfolio sweeps for `Q_6` at 29 hit pairs
  timed out.  The later cube proof shows this was a coarse-search limitation,
  not a satisfying obstruction.
- The direct `Q_7` full-obstruction CNF has 33,420 variables and 246,175
  clauses with the zero-vertex symmetry breaks.  A 180-second `cadical195` run
  timed out, so this is now a benchmark, not a result.
- Local search in `Q_5` rediscovers 12- and 14-bad colorings, but short runs
  still leave multiple antipodal pairs with both endpoints in `G`.
- The fixed-slice negation is exactly the assertion that `Bad` hits every
  antipodal pair.  The counting lemma `|Bad| < 2^{m-1}` is a stronger
  sufficient condition.
- Doubling a 7-bad `Q_4` coloring with a constant new-coordinate color gives a
  14-bad `Q_5` coloring, so extremal-looking examples can lift by dimension
  doubling.  This gives `max_bad(Q_{m+1}) >= 2 * max_bad(Q_m)`.
- Implemented this as `doubled_coloring` in `enc/bicross_probe.py` and tested
  that it exactly doubles bad vertices and antipodal pair profiles for every
  `Q_2` coloring, every inserted coordinate, and either uniform connector
  color.

Slice-recursion route:

- For a split, full bad vertices project to two sets `Bad_0, Bad_1` in
  `Q_{m-1}`.
- If full bad vertices hit every antipodal pair, then
  `Bad_0 union anti(Bad_1) = Q_{m-1}` and
  `Bad_1 union anti(Bad_0) = Q_{m-1}`.
- Implemented `--show-slices` in `enc/bicross_probe.py` to compare full bad
  sets with bad sets of induced slice colorings.
- In the 14-bad `Q_5` SAT model, some coordinate splits have both sides equal
  to 7-bad `Q_4` slices, with full bad exactly matching slice bad.  This is a
  strong hint that a slice induction may be possible.
- Added a recursion score for each split:
  `(overlap, extra_full, slice_only)`.
  Perfect inheritance is `extra_full = slice_only = 0`.
- The 14-bad `Q_5` model has three perfect-inheritance splits with score
  `(14, 0, 0)`.
- A 28-pair-hit `Q_6` model has no perfect split, but still has
  `slice_only = 0` in every coordinate.  A random `Q_3` check finds
  `slice_only > 0`, so this is not a general monotonicity theorem; it may be a
  near-obstruction signature.

Isomorphism note:

- I checked all 4,096 `Q_3` edge colorings up to signed coordinate
  permutations and global color swap.  They collapse to 76 orbits.
- The extremal `|G| = 6` colorings still occupy 8 distinct orbits.  So
  isomorphism reduction is useful computationally, but the proof should not
  expect a single canonical extremal shape even in dimension 3.

Dev/SAT setup note:

- Added `enc/sat_utils.py` so PySAT-backed scripts default to the fastest
  preferred available solver instead of PySAT's generic default.  In the local
  `uv --with python-sat` environment this selects `cadical195`.
- Added `enc/sat_portfolio.py`, a parallel portfolio runner.  It launches the
  preferred solver backends concurrently, defaults to all available cores, and
  stops after the first decisive SAT/UNSAT result unless `--keep-going` is set.
- Added a `Makefile` with `make test`, `make test-sat`, `make test-all`,
  `make list-solvers`, `make bicross-q6-frontier`, and
  `make bicross-q7-portfolio`.
- Local solver discovery currently finds:
  `cadical195`, `kissat404`, `cadical153`, `cadical103`, `glucose4`,
  `glucose42`, `maplechrono`, `gluecard4`, `gluecard3`, `maplesat`,
  `maplecm`, `mergesat3`, `minicard`, `minisat22`, `lingeling`.
- Added `enc/bicross_cube_search.py` for parallel assumption-cube searches on
  pair-hit formulas.

Latest experiment log:

- Full portfolio, `Q_6`, pair-hit `>=29`, zero-vertex breaks, 300 seconds per
  solver: every available PySAT backend timed out.  This was a solver-budget
  roadblock, not evidence for a model.
- Spread cube split for `Q_6`, pair-hit `>=29`, depth 8, 100k conflicts per
  cube: 128 UNSAT cubes and 128 UNKNOWN cubes.
- Prefix cube split for `Q_6`, pair-hit `>=29`, depth 8, 20k conflicts per
  cube: 240 UNSAT cubes and 16 UNKNOWN cubes.  Increasing those 16 to 500k
  conflicts left all 16 UNKNOWN.
- Added optional coordinate/bit-flip lex symmetry breaking to the pair-hit
  encoding (`--partial-sym-break`).
- With `--partial-sym-break 20`, `Q_6`, pair-hit `>=32` is UNSAT in a short
  Cadical run, confirming the stronger symmetry path preserves the known full
  obstruction result.
- With `--partial-sym-break 20`, `Q_6`, pair-hit `>=31` is UNSAT by prefix
  cube proof:
  first 247/256 cubes proved UNSAT at 20k conflicts, 7 of 9 remaining cubes
  proved UNSAT at 500k conflicts, and the last two cubes (`12,29`) proved
  UNSAT at 2M conflicts.  Therefore every `Q_6` coloring has at least two
  bicross antipodal pairs.
- With `--partial-sym-break 20`, `Q_6`, pair-hit `>=30` is UNSAT by a focused
  cube proof:
  first 246/256 depth-8 prefix cubes proved UNSAT at 20k conflicts, 7 of the
  10 remaining depth-8 cubes proved UNSAT at 2M conflicts, descendants of the
  three survivors (`4,12,29`) at depth 12 reduced to 9 UNKNOWN cubes, and those
  9 depth-12 cubes proved UNSAT at 2M conflicts.  Therefore every `Q_6`
  coloring has at least three bicross antipodal pairs.
- With `--partial-sym-break 20`, `Q_6`, pair-hit `>=29` is also UNSAT by a
  deeper cube proof:
  depth 8 left cubes `0,4,12,28,29` UNKNOWN after the 2M pass; their depth-12
  descendants reduced to 7 UNKNOWN cubes (`70,78,198,200,202,206,462`); their
  depth-16 descendants reduced to 18 UNKNOWN cubes; and those final 18
  depth-16 cubes all proved UNSAT at 2M conflicts.  Since a 28-pair-hit model
  exists, the exact `Q_6` pair-hit maximum is 28 of 32.
- Consequence: every `Q_6` coloring has at least four bicross antipodal pairs.
  This matches the exact `Q_5` bicross-pair guarantee, even though the `Q_6`
  search space is much larger.
- Started the analogous `Q_7` full-obstruction search (`pair-hit >=64`).
  With `--partial-sym-break 20`, depth-8 prefix cubing proves 248/256 cubes
  UNSAT at 20k conflicts, leaving `0,1,2,3,6,7,14,15` UNKNOWN.  A 500k pass on
  those eight proves cubes `1` and `3` UNSAT, leaving `0,2,6,7,14,15`.
- Descending the six `Q_7` depth-8 survivors to depth 12 gives 96 subcubes:
  67 UNSAT and 29 UNKNOWN at 50k conflicts.  A 500k pass reduces the 29 to 27
  UNKNOWN.  Descending those to depth 16 gives 432 subcubes: 235 UNSAT and 197
  UNKNOWN at 50k conflicts.  No SAT cube has appeared.
- Added `enc/bicross_adaptive_cube_search.py` to run nested-prefix refinement
  without hand-expanding child cube ranges.  It keeps a JSONL proof trail and
  can descend parent UNKNOWN indexes automatically.
- Descending the 197 hard `Q_7` depth-16 cubes to depth 20 with the prefix edge
  order gives 3,152 descendants.  At 10k conflicts per cube, 1,520 prove UNSAT
  and 1,632 remain UNKNOWN; no SAT cube appears.
- A 50k pass over those 1,632 depth-20 survivors was stopped after the early
  batches were overwhelmingly UNKNOWN.  Local 11-core compute is useful for
  mapping, but not enough to brute-force this frontier comfortably.
- A spread-tail split that keeps the first 16 prefix edges but chooses the next
  four variables spread across the remaining edge list is worse than the prefix
  tail on the tested hard parents.  Prefix-tail remains the better local split.
- A depth-8 spread cubing for `Q_7` is worse: only 128/256 cubes UNSAT at 20k
  conflicts.  Raising the partial symmetry cap from 20 to 40 does not change
  the prefix depth-8 survivor set.
- Added `enc/bicross_lift_search.py`.  It solves a high-hit seed in `Q_6`,
  doubles it into `Q_7`, and searches locally from that lifted near-obstruction.
  The exact `Q_6` 28-hit model doubles to a `Q_7` 56-hit coloring with profile
  `both_good=8, one_good=38, both_bad=18`.
- The doubled `Q_6` extremal is a one-edge local optimum for the `Q_7`
  pair-hit objective: a full one-flip scan finds 0 improving edges and 152
  neutral edges.  A kicked/annealed search over 8 restarts and 15k flips per
  restart did not improve beyond 56 hit pairs.

Extremal-star route:

- Added `enc/bicross_extremal_analysis.py` to sample high pair-hit models and
  aggregate component/incidence signatures.
- Added `make bicross-extremal-shapes` to replay 100 exact frontier samples for
  `Q_4`, `Q_5`, and `Q_6`.
- Exact `Q_3` frontier: all 192 exact 2-hit models have profile
  `both_good=2, one_good=2`; 144 have a single incidence cell containing both
  bicross pairs, while 48 do not.  So "some incidence cell contains an
  antipodal pair" is not a universal theorem.
- `Q_4`, 100 exact 6-hit samples: all have profile
  `both_good=2, one_good=5, both_bad=1`; all have exactly one incidence cell
  containing exactly two antipodal pairs; all bicross pairs share one meet
  vertex.
- `Q_5`, first 100 unconstrained exact 12-hit samples: all have profile
  `both_good=4, one_good=10, both_bad=2`; all have exactly one incidence cell
  containing exactly four antipodal pairs; all bicross pairs share one meet
  vertex.  This was a biased sample, not the whole frontier.
- Added `--forbid-cell-pairs` to the pair-hit SAT encoding and cube helpers.
  This explicitly forbids antipodal pairs inside one red/blue incidence cell.
- With `--forbid-cell-pairs`, `Q_4` pair-hit `>=6` is UNSAT.  So the Q4
  frontier really forces an incidence-cell antipodal pair.
- With `--forbid-cell-pairs`, `Q_5` pair-hit `>=12` is SAT.  These no-cell
  frontier models still have profile `both_good=4, one_good=10, both_bad=2`;
  in 20 exact samples they all have one perfect inherited split with recursion
  score `(14, 0, 0)` and uniform connectors.  Their bicross shape is also
  stable: four bicross pairs, two meet vertices, each used four times, with no
  same-meet pair.
- `Q_6`, 100 exact 28-hit samples with symmetry breaks: all have profile
  `both_good=4, one_good=19, both_bad=9`; all have bad weight histogram
  `{1:2, 2:8, 3:12, 4:10, 5:4, 6:1}`; all have exactly one incidence cell
  containing exactly four antipodal pairs; all bicross pairs share one meet
  vertex.
- In 20 Q6 frontier samples with inheritance summaries, all six splits have
  `slice_only = 0`, but no split has perfect inheritance.
- `Q_6`, pair-hit `>=28` with `--forbid-cell-pairs` is unresolved locally.
  A direct `cadical195` run was stopped after several minutes.  Prefix cubing
  proved 246/256 depth-8 cubes UNSAT at 50k conflicts, then 1 of the 10
  survivors UNSAT at 500k conflicts, then 93/144 depth-12 descendants UNSAT at
  100k conflicts.  No SAT model appeared; 51 depth-12 descendants remain
  UNKNOWN.
- In the Q6 sample, component sizes, incidence multiplicities, slice shapes,
  and boundary profiles vary.  Three earlier canonical Q6 samples also landed
  in three different automorphism/color-swap orbits.  The stable object is not
  one coloring up to isomorphism; it is the incidence-cell star.
- Candidate next lemma: if `Bad` comes close to hitting every antipodal pair,
  then either the coloring has a perfect inherited split, or some red/blue
  incidence cell `C_red_i intersect C_blue_j` contains an antipodal pair.  The
  second branch immediately gives a bicross pair, because both endpoints lie in
  the same red component and the same blue component.

One-switch geodesic route:

- If an antipodal geodesic from `x` to `anti(x)` has all red edges first and
  then all blue edges, then `x in G`.
- Exact `Q_3`: this characterizes `G`.
- Random `Q_4`: some good vertices require non-geodesic component paths, so the
  geodesic statement is only a sufficient condition in higher dimension.

Two-layer reachability route:

- `x in G` iff `(x, red phase)` reaches `(anti(x), blue phase)` in the directed
  automaton with red edges in the lower layer, blue edges in the upper layer,
  and directed switch edges from lower to upper at every vertex.
- A fixed-slice obstruction would require antipodally consistent directed cuts
  separating selected sources from their antipodal targets.
- This reframes the remaining proof as a directed separation theorem on the
  cube.

Shortest-separation/Tucker candidate:

- Under a hypothetical fixed-slice obstruction, each selected component pair
  `A_x = C_h(x)(x)` and `B_x = C_{1-h(x)}(anti(x))` is separated by distance
  at least two.
- Choose a closest pair of vertices between `A_x` and `B_x`; label `x` by a
  signed coordinate on which that closest pair differs.
- Antipodes swap the two components, so a symmetric tie-break should make this
  an antipodal signed-coordinate labeling.
- Arbitrary antipodal signed-coordinate labelings of cube vertices do not force
  complementary adjacent labels, so the missing lemma must use the fact that
  the labels arise from shortest red/blue component separations.
