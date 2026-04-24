# Norine Induction Notes

## Document Map

- `docs/EXPERIMENT_LOG.md`: chronological record of what worked, what failed,
  and why the proof-search direction changed.
- `docs/PROOF_DIRECTION.md`: current mathematical proof target and possible
  routes to a proof.
- `docs/BICROSS_LEMMA.md`: reduced ordinary-cube component theorem behind the
  one-connector lemma.
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

Counting route:

- Define `G = {x : R(x) intersects B(anti(x))}`.
- A bicross pair is exactly an antipodal pair contained in `G`.
- It is enough to prove `|G| > 2^{m-1}`.
- Exact `Q_2`: minimum `|G| = 3`.
- Exact `Q_3`: minimum `|G| = 6`.
- SAT `Q_4`: no coloring has 8 bad vertices, but a coloring with 7 bad
  vertices exists; therefore minimum `|G| = 9`.
- SAT `Q_5`: a coloring with 14 bad vertices exists, so `|G| = 18` is
  attainable.  The search for 15 bad vertices did not finish quickly.

One-switch geodesic route:

- If an antipodal geodesic from `x` to `anti(x)` has all red edges first and
  then all blue edges, then `x in G`.
- Exact `Q_3`: this characterizes `G`.
- Random `Q_4`: some good vertices require non-geodesic component paths, so the
  geodesic statement is only a sufficient condition in higher dimension.
