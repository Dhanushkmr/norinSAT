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

Dichotomy falsification pass, 2026-05-13:

- Added `perfect_inherited_splits` helpers and a pair-hit SAT option
  `--forbid-perfect-inherited-splits`.  This option completes the symbolic bad
  variables with reachability-meet clauses, then concretely post-checks and
  blocks SAT colorings whose actual structure still has a perfect inherited
  split.  The post-check is essential because the reachability variables are
  monotone and can otherwise spoof no-perfect constraints.
- Added the same restriction to `enc/bicross_cube_search.py` and
  `enc/bicross_adaptive_cube_search.py`, with per-cube post-check blocking.
- `Q_4`, hit `>=6`, `--forbid-cell-pairs`, and
  `--forbid-perfect-inherited-splits`: UNSAT.
- `Q_5`, hit `>=12`, no cell pairs, no perfect inherited split: a 5,000-model
  post-check did not find a genuine no-perfect example.  Every concrete model
  encountered still had a perfect inherited split.  A separate 500-model exact
  no-cell frontier sample also found 500/500 with exactly one perfect split.
  Important correction: uniform connectors are not forced; perfect inheritance
  is the invariant, not uniformity.
- `Q_6`, hit `>=28`, no cell pairs, no perfect inherited split: direct solving
  is too brittle locally.  Prefix cubing at depth 6 proved 60/64 cubes UNSAT at
  50k conflicts, leaving `0,1,3,7`; descending those to depth 10 proved 43/64
  descendants UNSAT at 50k conflicts, leaving 21 UNKNOWN.  No SAT
  counter-signal appeared.
- The proof target sharpened to an inherited-split/incidence-cell dichotomy.
  The next mathematical step is to prove that a high pair-hit, no-cell coloring
  must have at least one perfect inherited split, then use that split as the
  induction interface.

Slice-choice caveat, 2026-05-13:

- The one-connector lemma is existential in the coordinate split.  It should
  not be interpreted as saying that an arbitrary half-cube already contains a
  smaller-dimensional antipodal path.
- A valid monochromatic antipodal path can look like an `(n-1)`-direction path
  lying in one half, with the last dimension supplied by a connector edge.
  Relative to that terminal coordinate, this is exactly a one-connector
  witness: the in-slice path only has to reach the connector's monochromatic
  component.
- This caveat supports the inherited-split/incidence-cell direction.  The proof
  should identify a good split from the coloring's component structure, not
  assume a predetermined slice is recursively valid.

Forced opposite-half rim, 2026-05-13:

- Split `Q_n` as `(s, x)` with `s in {0,1}` and `x in Q_{n-1}`.  If an internal
  edge `(0,x)--(0,y)` is red, then its full antipodal edge
  `(1,anti(x))--(1,anti(y))` is forced blue.
- Therefore any red path inside the `0`-half has a forced blue antipodal copy
  inside the `1`-half, with all projected vertices complemented.
- If the red path runs from `(0,x)` to `(0,anti(x))` and the terminal connector
  `(0,anti(x))--(1,anti(x))` is red, then the antipodal connector
  `(0,x)--(1,x)` is blue.  So the other half also has a blue path:
  `(1,anti(x))` follows the forced blue rim to `(1,x)`, then crosses the blue
  connector to `(0,x)`.
- This means a terminal-connector red witness automatically comes paired with a
  terminal-connector blue witness on the antipodal side.  Connector colors are
  not forced by coloring one half alone; only antipodal pairs of connectors are
  forced opposite.
- This does not by itself prove that every coordinate split works.  The
  stronger statement that every split works is exactly the fixed-slice/bicross
  lemma route: for any chosen split, the connector colors define an antipodal
  vertex-labeling on one half, and bicross would force a one-connector witness
  for that split.

Bicross frontier conjecture, 2026-05-13:

- For a fixed ordinary coloring of `Q_m`, let
  `G = {x : R(x) intersects B(anti(x))}` and `Bad = V \ G`.
- An antipodal pair is bicross exactly when both endpoints lie in `G`.
  Therefore, exactly:

  ```text
  bicross(C) = 2^(m-1) - hit(Bad(C)),
  ```

  where `hit(Bad)` is the number of antipodal pairs touched by at least one bad
  vertex.
- The current exact values suggest the extremal formula

  ```text
  B_m = min_C bicross(C) = 2^floor((m - 1) / 2)
  H_m = max_C hit(Bad(C)) = 2^(m-1) - 2^floor((m - 1) / 2).
  ```

- Known/supporting values: `B_1=1`, `B_2=1`, `B_3=2`, `B_4=2`, `B_5=4`,
  `B_6=4`; the lifted `Q_7` near-obstruction has `B=8` candidates via
  `hit=56`.
- This would strengthen the bicross lemma from "at least one bicross pair" to
  a sharp quantitative lower bound.  The proof burden is now two-sided:
  prove the hit upper bound for every coloring, and find/describe sharp
  constructions in every dimension.
- The natural recurrence target is `B_{m+2} = 2 B_m`.  Doubling a coloring gives
  one easy source of doubled profiles, but it does not by itself explain the
  parity-preserving steps where the extremal count stays the same from `Q_3`
  to `Q_4` or from `Q_5` to `Q_6`.
- Sharpness construction found: pair coordinates `(0,1), (2,3), ...`.  Color
  an edge in coordinate `2j` by the value of coordinate `2j+1`, and an edge
  in coordinate `2j+1` by the value of coordinate `2j`.  If `m` is odd,
  color the final unpaired coordinate blue.
- In one two-coordinate block, the red components are `{00}` and
  `{01,10,11}`; the blue components are `{00,01,10}` and `{11}`.  Hence
  `x in G` fails exactly when some paired block of `x` is `00`.
- Thus `G` has `3^k` vertices for `m=2k` and `2*3^k` vertices for
  `m=2k+1`.  An antipodal pair is bicross exactly when every paired block is
  `01` or `10`, giving `2^(k-1)` pairs for `m=2k` and `2^k` pairs for
  `m=2k+1`.  This is `2^floor((m-1)/2)`.
- Implemented as `enc/bicross_frontier_construction.py` with tests through
  `Q_10`.  This proves the upper-bound/sharpness half of the quantitative
  conjecture.  The remaining hard direction is the universal lower bound
  `bicross(C) >= 2^floor((m-1)/2)`.

- Failed strengthening: the paired construction also has a neat good-vertex
  count, `|G| = 3^k` for `m=2k` and `|G| = 2*3^k` for `m=2k+1`, but
  this is not an extremal lower bound.  A SAT run for `Q_6` found a coloring
  with 38 bad vertices, only 26 good vertices, and pair profile
  `both_good=4, one_good=18, both_bad=10`.  That still matches the bicross
  frontier because `Bad` hits only 28 antipodal pairs.
- Consequence: any proof based only on the size of `G` is too weak or false.
  The invariant must be antipodal-pair coverage by `Bad`, not vertex count.
  The next lower-bound target remains:

  ```text
  hit(Bad(C)) <= 2^(m-1) - 2^floor((m - 1) / 2).
  ```

- The `Q_6` threshold `bad >= 39` did not settle in a 120-second all-solver
  portfolio run.  That question is now a side frontier, not part of the main
  proof route.

Bad-set structure analysis, 2026-05-14:

- Added `enc/bad_set_structure.py` to print the component/incidence/slice
  structure of either a construction or a SAT-found model.
- Comparing the paired-coordinate `Q_6` construction with the SAT `Q_6`
  38-bad witness shows the real invariant clearly:

  ```text
  paired: pairs_hit=28, bad=37, good=27, profile=(4,19,9)
  SAT:    pairs_hit=28, bad=38, good=26, profile=(4,18,10)
  ```

- The SAT witness gains one bad vertex, but it does not hit another
  antipodal pair.  It merely turns one already-hit pair from `one_bad` into
  `both_bad`.
- Both colorings have exactly one occupied red/blue incidence cell containing
  all four bicross antipodal pairs.  In both cases that cell has size 8 and
  no bad vertices.
- The missing target cell multiplicities are also close:

  ```text
  paired: [1, 3, 3, 3, 9, 9, 9]
  SAT:    [1, 3, 3, 4, 9, 9, 9]
  ```

- Proof signal: high pair-hit colorings seem to pay for extra bad vertices by
  double-covering pairs, while a protected incidence cell remains forced to
  carry the bicross pairs.  The next lemma should be a pair-coverage/cell-star
  statement, not a good-set-size statement.

Branch classifier, 2026-05-15:

- Added `frontier_branch` to `enc/bicross_extremal_analysis.py`.  It records
  whether a frontier model has the incidence-cell star branch, the perfect
  inherited-split branch, both, or neither.
- Current replay target: `make bicross-branch-samples`.
- Compact finite table from sampled frontier models:

  Q4 hit=6, ordinary frontier:      cell_star
  Q5 hit=12, ordinary frontier:     both
  Q5 hit=12, no-cell restriction:   inherited
  Q6 hit=28, ordinary frontier:     cell_star

- A `Q5` SAT search for `hit>=12 + no cell pairs + no perfect inherited split`
  still produced no concrete counterexample after 500 postchecked blocked
  colorings in the latest run.  Earlier longer notes record 5,000 blocked
  colorings.  The relaxed SAT encoding can spoof the no-perfect condition, so
  concrete postcheck remains mandatory.
- The best current lemma is therefore a branch statement: high pair-hit implies
  the cell-star branch or the perfect inherited-split branch.
- Implemented the exact postchecked falsification mode as
  `--forbid-frontier-branches`.  It searches for high pair-hit colorings whose
  concrete branch is `neither`: no cell-star branch and no perfect inherited
  split.  Symbolic no-perfect-split clauses are used only as pruning.
- Latest branch-falsification runs:

  ```text
  Q4 hit>=6:  blocked 23 cell_star models, then SAT False.
  Q5 hit>=12: blocked 999 models, no neither model within limit.
  Q6 hit>=28: blocked 99 cell_star models, no neither model within limit.
  ```

- The Q5 blocked models included `inherited`, `both`, and `cell_star` branches.
  The Q6 blocked models were all `cell_star` in the bounded run.
- Extended `enc/bicross_cube_search.py` and
  `enc/bicross_adaptive_cube_search.py` with the same
  `--forbid-frontier-branches` postcheck.  This lets the neither-branch
  falsification target run as a parallel cube-and-conquer job instead of a
  single repeated model-blocking loop.
- New replay targets:

  ```text
  make bicross-branch-cubes
  make bicross-branch-adaptive-cubes
  ```

  The first target proves the small `Q_4` neither-branch case by cubing and
  then runs a bounded `Q_6` pass.  The second target descends UNKNOWN `Q_6`
  cubes adaptively.  These are still falsification tools, not proof
  certificates, unless all selected cubes finish UNSAT with no UNKNOWN.
- Latest cube replay, 2026-05-16:

  ```text
  Q4 hit>=6 branch cubes: 16/16 cubes UNSAT, SAT False.
  Q6 hit>=28 branch cubes, depth 6: 60/64 UNSAT, UNKNOWN 0,1,3,7, no SAT.
  Q6 adaptive descendants, depth 8: 6/16 UNSAT, UNKNOWN 0-1,4-5,12-13,15,28-29,31.
  Q6 adaptive descendants, depth 10: 20/40 UNSAT, UNKNOWN 0-1,3,7,16-17,19,23,49-51,54-55,62,115-117,119,124-125.
  Q6 adaptive descendants, depth 12: 27/80 UNSAT, UNKNOWN 53, no SAT.
  ```

  This is useful but not decisive.  It says the branch lemma has survived the
  first parallel Q6 stress pass; the remaining work is either a higher-budget
  pass on the 53 depth-12 UNKNOWN cubes or a stronger symbolic encoding of the
  branch conditions.
- A portfolio check with `kissat404` found a tooling issue: PySAT Kissat does
  not support assumptions and crashes under repeated cube assumptions.  The SAT
  helper now rejects assumption-incompatible solvers for cube runners, while
  leaving them available for one-shot formulas.

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

Group/category proof directions, 2026-05-20:

- Added `docs/GROUP_CATEGORY_DIRECTIONS.md` to collect non-SAT proof ideas
  from group theory, cohomology, additive combinatorics, and category theory.
- View `Q_m` as the Cayley graph of `G = F_2^m`.  An edge coloring is a
  function `c_i(x)`, and antipodes are translation by
  `omega = e_0 + ... + e_{m-1}`.  The original antipodal edge condition is
  the anti-periodicity equation `c_i(x + omega) = c_i(x) + 1`.
- In the reduced bicross problem, connector colors become anti-periodic vertex
  labelings `h(x + omega) = h(x) + 1`.  Thus the fixed-slice theorem says no
  ordinary edge coloring can defeat every anti-periodic vertex labeling.
- The paired-coordinate sharpness construction looks symplectic: for even
  dimension it has the linear form `c_i(x)=B(x,e_i)` for the alternating
  bilinear form pairing coordinates `(0,1), (2,3), ...`.
- In that construction, bicross pairs are exactly the affine equations
  `x_{2j}+x_{2j+1}=1`, modulo antipodes.  This explains the count
  `2^floor((m-1)/2)` as the size of an affine survivor set in
  `G/<omega>`.
- New strongest candidate theorem to test:

  ```text
  Every coloring has a bicross-pair set containing an affine subspace
  of dimension floor((m - 1) / 2) in G/<omega>.
  ```

  This may be false, but it is concrete and would explain the quantitative
  formula better than pair-counting alone.
- New probes to implement next: affine survivor detector, square-curvature
  rank for edge-color cochains, Fourier concentration of untouched-pair sets,
  stabilizers of bicross-pair sets under `Aut(Q_m)`, and a quotient/descent
  test for component maps `(q_R,q_B)`.
- Category-theoretic translation: red and blue components are quotient maps
  `q_R,q_B`; incidence cells are fibers of `(q_R,q_B)`; a one-connector
  witness is a nonempty pullback after slicing; a perfect inherited split is
  descent data along a face map; a cell-star witness is an antipodal pair in
  one fiber.  The branch lemma becomes a descent-or-fiber theorem for
  connectivity quotients of products `[1]^m`.

Affine-survivor experiments, 2026-05-20:

- Added `enc/group_structure_probe.py` and tests.  The main target is now:

  ```text
  Every coloring of Q_m has a bicross-pair set containing an affine
  subspace of dimension floor((m - 1) / 2) in F_2^m / <omega>.
  ```

- Exact `Q_3` enumeration: all `4096` ordinary edge colorings contain the
  target affine survivor.
- Paired construction: the bicross set is exactly affine for `m=1..8` in
  tests; for `Q_6`, the four bicross pairs are an affine plane.
- Random checks: no failures in `Q_4` 2000 samples, `Q_5` 2000 samples, or
  `Q_6` 1000 samples.
- SAT frontier checks: sampled frontier bicross sets were not just containing
  affine survivors; the whole bicross set was affine.

  ```text
  Q4 hit=6:                 23/23 affine
  Q5 hit=12 ordinary:      100/100 affine
  Q5 hit=12 no-cell:       100/100 affine
  Q6 hit=28 ordinary:       50/50 affine
  ```

- Direct SAT negation `--sat-no-affine-survivor` proves the affine-survivor
  theorem through `Q_5`: `Q_3`, `Q_4`, and `Q_5` are UNSAT.
- `Q_6` no-affine negation remains locally unresolved.  No SAT counterexample
  appeared, but cube-and-conquer hit a compute wall:

  ```text
  depth 6,  50k conflicts: 60/64 UNSAT, UNKNOWN 0,1,3,7
  depth 8,  50k conflicts: 5/16 selected UNSAT, 11 UNKNOWN
  depth 10, 50k conflicts: 23/44 selected UNSAT, 21 UNKNOWN
  depth 12, 50k conflicts: 30/84 selected UNSAT, 54 UNKNOWN
  depth 12, 200k conflicts on those 54: 1 UNSAT, 53 UNKNOWN
  glucose4 depth 12, 50k: 0 UNSAT, 54 UNKNOWN
  ```

- Current depth-12 UNKNOWN list for Q6 no-affine:

  ```text
  0,1,2,3,6,7,14,15,30,31,66,67,68,69,70,71,76,77,78,79,92,93,94,95,198,199,200,201,202,203,206,207,216,217,218,219,222,223,249,251,462,463,464,465,466,467,470,471,478,479,497,499,503
  ```

- Dead-end correction: square curvature is not the right cohomology invariant
  for the symplectic construction.  The paired-coordinate coloring has zero
  square curvature because it is the derivative of a quadratic potential.  The
  useful object is the directional derivative/Hessian of the edge-color
  functions.
- Best next proof target: prove that component quotient structure forces an
  affine survivor in `F_2^m/<omega>`.  The Q5 UNSAT result makes this stronger
  than a visual pattern, but Q6 still needs either a proof idea or a stronger
  encoding.
- Stabilizer/frontier refinement: all sampled exact frontier bicross sets have
  exactly one target affine flat, no larger affine flat, and the expected
  translation stabilizer.

  ```text
  Q4 hit=6:  target flats=1, max affine dimension=1, translation stabilizer=2
  Q5 hit=12: target flats=1, max affine dimension=2, translation stabilizer=4
  Q6 hit=28: target flats=1, max affine dimension=2, translation stabilizer=4
  ```

- The Q6 frontier quotient-cube stabilizer is `192`, matching the paired
  construction.  Q5 frontier stabilizer is `32`; Q4 frontier stabilizer is
  `16`.
- Near-frontier samples show where the stronger statement stops.  The bicross
  set itself is no longer affine one step away from the frontier, but affine
  survivors persist:

  ```text
  Q5 hit=11: target flats=1, max affine dimension=2, bicross set not affine
  Q5 hit=10: target flats=3, max affine dimension=2, bicross set not affine
  Q6 hit=27: target flats=1, max affine dimension=2, bicross set not affine
  Q6 hit=26: target flats=3, max affine dimension=2, bicross set not affine
  ```

- Finite-geometry baseline: arbitrary quotient subsets of the same size usually
  do not contain the needed flat.  So the affine survivor is not a counting
  tautology.

  ```text
  F2^4, 4-subsets: 140/1820 are affine planes
  F2^5, 4-subsets: 1240/35960 are affine planes
  F2^5, 5-subsets: 34720/201376 contain an affine plane
  F2^5, random 6-subsets: about 9441/20000 contain an affine plane
  ```

- Current sharpened statement:

  ```text
  At the extremal pair-hit frontier, the bicross survivor set is exactly
  one affine flat of dimension floor((m - 1) / 2) in F_2^m/<omega>.
  Away from the frontier, the exact-affine property fails, but affine
  survivor containment persists in all tests.
  ```

Quotient/descent proof attempt, 2026-05-21:

- The incidence quotient still looks like the right language.  Each vertex maps
  to `(R(v), B(v))`; a bicross pair is an antipodal rectangle whose two
  cross-cells are occupied, and an incidence cell containing both endpoints of
  an antipodal pair gives bicross immediately.
- The descent branch has a precise leak.  If a full obstruction descends
  perfectly along a coordinate split, with slice colorings `C_0,C_1`, then the
  inherited bad sets satisfy

  ```text
  Bad(C_0) union anti(Bad(C_1)) = Q_{m-1}
  Bad(C_1) union anti(Bad(C_0)) = Q_{m-1}.
  ```

  Equivalently,

  ```text
  G(C_0) intersect anti(G(C_1)) = empty.
  ```

- Therefore perfect descent does not produce a smaller one-color bicross
  counterexample.  It produces a two-color cross-obstruction.  The clean
  induction invariant would be:

  ```text
  For all edge-colorings C,D of Q_m,
  G(C) intersect anti(G(D)) is nonempty.
  ```

  The original bicross lemma is the special case `C = D`.
- Quick checks: exhaustive dimensions 1, 2, and 3 satisfy this two-color
  theorem; a direct SAT encoding proves the cross-cover negation UNSAT in
  `Q_4`.  A quick `Q_6` run was inconclusive, not a counterexample.
- Updated proof target: the branch statement must be
  `cell-star or descent into the two-color cross theorem`, or else replaced
  by a direct incidence-rectangle theorem that avoids the descent leak.

Two-color cross experiments, 2026-05-21:

- Added `enc/two_color_cross_probe.py` and `make two-color-cross-probes`.
  The probe has two modes:

  ```text
  --sat-negation       search for two colorings C,D with
                       G(C) intersect anti(G(D)) = empty
  --cover-paired-left  fix C to the paired-coordinate construction and ask
                       whether some D can make anti(G(C)) bad
  ```

- Exact distinct-bad-set enumeration proves the two-color cross theorem for
  `Q_1,Q_2,Q_3`.  The number of distinct bad sets is:

  ```text
  Q1: 1
  Q2: 5
  Q3: 25
  ```

- Direct SAT proves the full two-color cross-cover negation UNSAT for:

  ```text
  Q4: UNSAT
  Q5: UNSAT with 200k conflict budget, symmetry on the first coloring
  ```

- A direct `Q_6` full two-color cross-cover SAT run with first-coloring
  symmetry and a 1M conflict budget returned UNKNOWN.
- Fixed-left paired construction test: no coloring can cover the paired
  construction's antipodal good set through `Q_6`:

  ```text
  Q4 target size  9: UNSAT
  Q5 target size 18: UNSAT
  Q6 target size 27: UNSAT
  Q7 target size 54: UNKNOWN at 1M conflicts
  ```

- Interpretation: the two-color descent invariant is now stronger than a
  scratch conjecture.  It is verified through `Q_5` in full and through
  `Q_6` for the sharp paired-coordinate frontier target.  The next compute
  step is a cube-and-conquer version of `--sat-negation` for `Q_6`, or a
  specialized proof/encoding for fixed paired-left targets.

Two-color cube/product follow-up, 2026-05-21:

- Added `enc/two_color_cross_cube_search.py`,
  `enc/two_color_cross_adaptive_cube_search.py`, `make two-color-cross-cubes`,
  and `make two-color-cross-adaptive-cubes`.  These cube the full two-color
  cross-cover negation on first-coloring edge variables, where the symmetry
  breaks act.
- Corrected adaptive Q6 full two-color cross-cover cube replay with
  first-coloring symmetry:

  ```text
  depth 6,  200k conflicts: 60/64 UNSAT, UNKNOWN 0-1,3,7
  depth 8,  200k conflicts on descendants: 4/16 UNSAT,
                                 UNKNOWN 0-1,3-5,7,12-13,15,28-29,31
  depth 10, 200k conflicts on descendants: 24/48 UNSAT,
                                 UNKNOWN 0-1,3,7,15-17,19,23,31,
                                         49-51,54-55,62-63,
                                         115-117,119,124-125,127
  depth 12, 200k conflicts on descendants: 38/96 UNSAT,
                                 UNKNOWN 0-3,6-7,14-15,30-31,63,
                                         66-71,76-79,92-95,125,127,
                                         198-203,206-207,216-219,222-223,
                                         249,251,255,
                                         462-467,470-471,478-479,
                                         497,499,503,511
  depth 14, 200k conflicts on descendants: 84/232 UNSAT,
                                 UNKNOWN count 148, no SAT
  depth 16, 200k conflicts on descendants: 209/592 UNSAT,
                                 UNKNOWN count 383, no SAT
  ```

  No SAT model appeared.  The hard region is again highly concentrated near
  low prefix patterns, like the earlier bicross frontier cube runs.  The
  earlier hand-expanded depth-8/depth-10/depth-12 replay used a wrong
  descendant range for one branch; the adaptive run above is the authoritative
  prefix-cube record.
- Product-target experiment: for each paired coordinate block, choose one of
  `00,01,10,11` as forbidden and force every vertex avoiding the forbidden
  state in every block to be bad.  This is a `3^k`-sized target, with the
  odd leftover coordinate free.  Every such target is impossible through Q6:

  ```text
  Q4: 16/16 targets UNSAT
  Q5: 16/16 targets UNSAT
  Q6: 64/64 targets UNSAT
  ```

  Q7 is currently beyond the direct target encoding: three representative
  product targets of size 54 all returned UNKNOWN at 1M conflicts, including
  the paired-left target with forbidden block `11,11,11`.

- Added `enc/two_color_product_hole_analysis.py` and
  `make two-color-product-holes` to classify near-cover holes in the
  canonical product box `P={no paired block is 00}`.  Max-bad checks give:

  ```text
  Q2: |P|=3,  max bad in P = 1
  Q3: |P|=6,  max bad in P = 2
  Q4: |P|=9,  max bad in P = 7
  Q5: |P|=18, max bad in P = 14
  Q6: |P|=27, max bad in P = 25
  ```

  The near-cover orbit classifications are sharper:

  ```text
  Q4: 8 two-hole orbits; exactly one SAT, the antipodal middle-pair orbit
  Q5: 238 four-hole orbits; exactly one SAT, two antipodal middle pairs
  Q6: 20 two-hole orbits; exactly one SAT, the antipodal middle-pair orbit
  ```

  Thus a Q6 coloring can cover 25 of the 27 vertices in `P`, but the only
  extremal shape seen by the orbit solver leaves a middle antipodal pair such
  as `010101,101010`.  The Q5 extremal leaves the doubled odd-dimensional
  version, e.g. `01010,01011,10100,10101`.  The tempting stronger statement
  that the middle flat itself must meet `G(C)` is false in Q6: all eight
  middle vertices can be forced bad, although then the full product box has
  seven good vertices.

  Representative extremal SAT models are even more structured: in Q4 and Q6,
  when `P` is covered up to the two middle antipodal holes, the entire good
  set has size `|P|` and is itself a product target for a crossed coordinate
  pairing, avoiding `11` in every crossed pair.  The models found:

  ```text
  Q4 good set: pairs (0,3),(1,2), forbidden states 11,11
  Q6 good set: pairs (0,3),(1,5),(2,4), forbidden states 11,11,11
  ```

  Q7 now has a matching extremal witness in the canonical product box:
  forcing 50 of 54 vertices bad is SAT, with the four good product-box
  vertices exactly `0101010,0101011,1010100,1010101`.  The next lower-bound
  question remains open computationally: forcing at least 51 of the 54
  product-box vertices bad returned UNKNOWN at 1M conflicts, and three fixed
  three-hole near-covers also returned UNKNOWN at 1M.

- This suggests a narrower human-scale lemma:

  ```text
  No coloring of Q_m has Bad containing a product set that keeps
  three states out of four in each paired coordinate block.
  ```

  The paired-coordinate frontier obstruction is one instance of this product
  target.  Proving this would not prove the full two-color theorem, but it
  would explain why the sharp symplectic/paired construction cannot appear as
  one side of a descent obstruction.

## Wild proof directions

These are deliberately more speculative than the SAT-backed frontier notes.
The goal is to find proof languages that explain why bicross survivors keep
forming affine flats instead of treating the affine pattern as a coincidence.

1. Finite-geometry blocking sets.  Work in the antipodal quotient
   `F_2^m/<omega>`.  If no affine survivor of the predicted dimension exists,
   then the projected bad set is a blocking set: it must hit every target
   affine flat.  Finite-geometry blocking-set theorems may force such a set
   to look hyperplane-like, which would match the inherited-slice branch of
   the current proof picture.

2. Reed-Muller and polynomial method.  Represent the bicross survivor
   indicator as a Boolean function on the quotient.  The affine-survivor
   theorem says this function is nonzero on an entire affine flat of dimension
   `floor((m - 1) / 2)`.  If component reachability imposes low-degree
   structure, Reed-Muller duality, Chevalley-Warning, or a cube version of
   Combinatorial Nullstellensatz might force such a flat.

3. Median-graph and Helly methods.  The hypercube is a median graph.  Red and
   blue components need not be convex, but their gated hulls, interval hulls,
   or median closures may satisfy Helly-type constraints.  A possible route is
   to prove bicross after passing to hulls, then show the hull witness can be
   pulled back to actual monochromatic components.

4. Hex or strategy-stealing formulation.  A missing bicross witness can be
   interpreted as a two-phase reachability separator: no red-then-blue route
   and no blue-then-red route across an antipodal pair.  The cube with
   antipodal boundary has a self-dual flavor similar to Hex, so a separator
   strategy may contradict the dual separator forced by the opposite color.

5. Equivariant nerve or Tucker lemma.  Build a nerve from red and blue
   component covers, with the antipodal map acting on the indexing complex.
   A failed bicross/affine-survivor statement should produce an equivariant
   map into a low-index complex.  The hope is a Tucker/Borsuk-Ulam obstruction,
   but using labels that come from component separations rather than arbitrary
   signed coordinates.

6. Categorical descent.  View red and blue component quotients as cosheaves on
   the cube face category.  The two observed outcomes then look like a descent
   dichotomy: either the coloring descends cleanly along some coordinate split
   (the inherited-slice branch), or the product quotient has a fixed fiber
   containing an antipodal affine block (the cell-star branch).

7. Incidence rectangles and concept lattices.  Put each vertex into the cell
   `(R(v), B(v))` of the red-component by blue-component incidence matrix.
   Bicross is exactly an antipodal rectangle-completion phenomenon.  Formal
   concept analysis or forbidden-rectangle theorems with bounded cube VC
   dimension may turn the empirical cell-star pattern into a theorem.

8. Entropy and junta structure.  A no-affine-survivor bad set has to block
   many affine flats, which looks high-complexity.  Component reachability may
   force low influence or junta-like behavior in some coordinate split.  That
   would explain why unresolved cases keep drifting back toward inherited
   lower-dimensional structure.

9. Harmonic/electrical picture.  Treat badness as a potential separating each
   vertex from its antipode in the red-blue reachability graph.  Energy or
   flow duality on the cube may force either a low-energy affine survivor or a
   coordinate with nearly all current, again pointing to the dichotomy.

10. Binary matroid language.  The quotient geometry is a binary matroid.  The
    survivor flat is a flat of this matroid, while a bad set hitting all such
    flats is a blocking object with a critical-number flavor.  Matroid
    blocking and density theorems may give a cleaner extremal statement than
    the raw cube formulation.

Most concrete next experiment: add a blocking-set analyzer for
`pi(Bad) subset F_2^m/<omega>`.  For frontier and near-frontier models, measure
whether `pi(Bad)` contains or is close to hyperplanes, whether it is a minimal
blocking set for the target affine flats, and whether the residual obstruction
is exactly the paired-coordinate/symplectic construction in disguise.
