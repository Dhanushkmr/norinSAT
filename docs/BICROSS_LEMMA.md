# Bicross Lemma

This is the current reduced proof target for the one-connector route to
Norine's conjecture.

## Statement

Let `Q_m` be the ordinary `m`-dimensional cube.  Give every edge a red or blue
color, with no antipodal condition.

For a vertex `x`, write:

- `R(x)` for the red connected component containing `x`;
- `B(x)` for the blue connected component containing `x`;
- `anti(x)` for the bitwise complement of `x`.

The bicross lemma says:

> In every red/blue edge-coloring of `Q_m`, there is a vertex `x` such that
> both intersections are nonempty:
>
> ```text
> R(x) intersects B(anti(x))
> B(x) intersects R(anti(x))
> ```

Call such a pair `x, anti(x)` a bicross pair.

## Why This Would Prove Norine

The implication chain is:

```text
bicross lemma for Q_{n-1}
=> fixed-slice lemma for one coordinate split of Q_n
=> one-connector lemma for Q_n
=> Norine's conjecture for Q_n
```

The first implication is the important reduction.

Fix a coordinate split of an antipodally colored `Q_n`.  Identify the `0`-slice
with `Q_{n-1}`.  Let `h(a)` be the connector color at projected vertex `a`.
The antipodal edge-coloring condition gives:

```text
h(anti(a)) = opposite h(a)
```

Also, complementing projected vertices sends a color-`c` path in the `0`-slice
to a color-`opposite c` path in the `1`-slice.

If `x` is in

```text
C_{h(a)}(a) intersects C_{opposite h(a)}(anti(a)),
```

then the full cube has a one-connector path:

```text
(0,x) --color h(a), inside 0-slice--> (0,a)
(0,a) --color h(a), connector-------> (1,a)
(1,a) --color h(a), inside 1-slice--> (1,anti(x))
```

The endpoint `(1,anti(x))` is the full antipode of `(0,x)`.

The bicross lemma gives this fixed-slice intersection for every possible
antipodal connector-labeling `h`, so it gives a one-connector witness in every
coordinate split.

## Equivalent Fixed-Slice Lemma

The bicross lemma is equivalent to the following statement.

> For every red/blue edge-coloring of `Q_m` and every antipodal vertex-labeling
> `h` with `h(anti(a)) = opposite h(a)`, there is a vertex `a` such that
>
> ```text
> C_{h(a)}(a) intersects C_{opposite h(a)}(anti(a)).
> ```

Why:

- If a bicross pair `x, anti(x)` exists, then either value of `h(x)` works.
- If no bicross pair exists, choose for each antipodal pair one of the two
  empty cross-intersections.  This creates an antipodal labeling `h` with no
  fixed-slice witness.

## Component-Incidence Rectangle View

Build a bipartite incidence graph:

- left nodes are red components;
- right nodes are blue components;
- each cube vertex `v` gives an incidence edge `(R(v), B(v))`.

Equivalently, make a matrix whose rows are red components and whose columns are
blue components.  A cell is occupied if some cube vertex lies in that red
component and that blue component.

For antipodal vertices `x` and `anti(x)`, write their occupied cells as

```text
x       : (R_x, B_x)
anti(x) : (R_a, B_a)
```

Then:

```text
R(x) intersects B(anti(x))  <=>  cell (R_x, B_a) is occupied
B(x) intersects R(anti(x))  <=>  cell (R_a, B_x) is occupied
```

So the bicross lemma says:

> Some antipodal pair occupies two opposite corners of a rectangle whose other
> two corners are also occupied.

This is a promising graph-theory formulation.  Red edges in the cube move
inside one row of the matrix; blue edges move inside one column.  The hard part
is to use the fact that the occupied cells and row/column moves come from the
`m`-cube, not from an arbitrary bipartite incidence graph.

## Contradiction Target

Assume the bicross lemma is false.  Then for every antipodal pair, at least one
of the two cross-intersections is empty.  Choose labels so that the selected
intersection is always empty:

```text
C_{h(x)}(x) is disjoint from C_{opposite h(x)}(anti(x)).
```

This gives an antipodal family of component separations.

The key local fact is:

> If `R` is a red component and `B` is a blue component, and `R` and `B` are
> disjoint, then no cube edge joins `R` to `B`.

Reason:

- A red edge from `R` into `B` would put the endpoint in `B` into `R`.
- A blue edge from `R` into `B` would put the endpoint in `R` into `B`.

So each selected component and its selected antipodal component are separated by
graph distance at least two.

The hoped-for contradiction:

```text
antipodal component separations
=> an antipodal labeling of cube cells or vertex regions
=> Tucker/Borsuk-Ulam/Hex forces complementary adjacency
=> complementary adjacency is a forbidden cross-intersection
```

The gap is the middle step: building the correct discrete topological labeling.

## Probe

Script:

```bash
python3 enc/bicross_probe.py -m 3 --enumerate
python3 enc/bicross_probe.py -m 3 --enumerate --check-all-labelings
python3 enc/bicross_probe.py -m 4 --samples 10000
uv run --python 3.12 --with python-sat python enc/bicross_probe.py -m 4 --sat-fixed-slice --solver cadical195
```

Current results:

- Exact `Q_2`: all 16 edge-colorings satisfy bicross, and all 64
  coloring/labeling pairs have a fixed-slice witness.
- Exact `Q_3`: all 4,096 edge-colorings satisfy bicross, and all 65,536
  coloring/labeling pairs have a fixed-slice witness.
- Random `Q_4`: 10,000/10,000 sampled edge-colorings satisfy bicross.
- SAT fixed-slice negation for `Q_4`: UNSAT, with 560 variables and 2,608
  clauses.
- SAT fixed-slice negation for `Q_5`: UNSAT, with 2,160 variables and 12,384
  clauses.
- SAT fixed-slice negation for `Q_6`: UNSAT with `h(00...0)=red` and sorted
  colors incident to `00...0`, with 8,448 variables and 57,542 clauses.
- SAT fixed-slice negation for `Q_7`: attempted with the same light symmetry
  breaking and stopped after a few minutes without a result.

## Related Literature

Feder and Subi studied edge labellings of hypercubes and conjectured that even
without antipodality there is always an antipodal path with at most one color
switch.  That is close to the one-switch geodesic route above, but the bicross
lemma asks for a stronger component-crossing condition tailored to the
one-connector proof.

References:

- Norine problem page: `https://dwest.web.illinois.edu/regs/antipcol.html`
- Feder and Subi, "On hypercube labellings and antipodal monochromatic paths":
  `https://doi.org/10.1016/j.dam.2012.12.025`

## Next Lemmas To Try

1. Boundary lemma:

   ```text
   The external edge boundary of a red component consists only of blue edges,
   and vice versa.
   ```

2. Antipodal separation lemma:

   ```text
   A family of selected antipodal red/blue component separations cannot cover
   all antipodal vertex pairs of Q_m.
   ```

3. Tucker-label lemma:

   ```text
   From a bicross-free coloring, construct an antipodal labeling of an
   appropriate cubical subdivision with no complementary adjacent labels.
   ```

4. Contradiction:

   ```text
   Tucker's lemma forces a complementary adjacent pair, contradicting the
   component separation.
   ```

The topological route is promising because the statement is now exactly about
antipodal symmetry and forbidden complementary contact.

## Counting Route

Define

```text
G = {x : R(x) intersects B(anti(x))}.
```

A bicross pair is exactly an antipodal pair whose two vertices both lie in
`G`, because

```text
anti(x) in G
<=> R(anti(x)) intersects B(x)
<=> B(x) intersects R(anti(x)).
```

Therefore it is enough to prove the counting lemma:

> `|G| > 2^{m-1}` for every red/blue edge-coloring of `Q_m`.

Then `G` has more vertices than an antipodal half-cube, so some antipodal pair
is contained in `G`.

Current evidence:

- Exact `Q_2`: minimum `|G|` is 3.
- Exact `Q_3`: minimum `|G|` is 6.
- SAT for `Q_4`: there is no coloring with 8 bad vertices, but there is one
  with 7 bad vertices.  Thus the exact minimum `|G|` is 9.
- SAT for `Q_5`: a coloring with 14 bad vertices exists, so `|G| = 18` is
  attainable.  The search for 15 bad vertices did not finish quickly, so the
  exact optimum is not known.

This route may be easier than Tucker directly: prove that the bad set

```text
Bad = {x : R(x) is disjoint from B(anti(x))}
```

cannot contain one representative from every antipodal pair.

## One-Switch Geodesic Route

If there is an antipodal geodesic from `x` to `anti(x)` whose edge colors are
all red first and then all blue, then `x in G`.  The transition vertex lies in
both `R(x)` and `B(anti(x))`.

The converse is false from `Q_4` onward: some good vertices need non-geodesic
component paths.  Still, the geodesic route may be strong enough if one can
prove that more than half the vertices start a red-then-blue antipodal geodesic.

Probe results:

- Exact `Q_3`: good vertices and red-then-blue geodesic starts are identical
  for all 4,096 colorings.
- Random `Q_4`: red-then-blue geodesic starts are always a subset of `G`, but
  some colorings have extra good vertices that require non-geodesic component
  paths.
