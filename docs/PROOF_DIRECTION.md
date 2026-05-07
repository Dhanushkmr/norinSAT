# Proof Direction: The One-Connector Lemma

This document states the current proof target in mathematical terms and explains
why it would imply Norine's conjecture.

## Basic Setup

Let `Q_n` be the `n`-dimensional cube graph.  Vertices are bitstrings
`v in {0,1}^n`.  The antipode of `v` is the bitwise complement `anti(v)`.

An edge-coloring is antipodal if every edge and its fully antipodal edge have
opposite colors.

Norine's conjecture:

> In every antipodal red/blue edge-coloring of `Q_n`, there is a monochromatic
> path from some vertex `v` to `anti(v)`.

## Coordinate Split

Fix a coordinate `i`.  This splits `Q_n` into two copies of `Q_{n-1}`:

- the `0`-slice, where `x_i = 0`;
- the `1`-slice, where `x_i = 1`;
- connector edges, which flip coordinate `i`.

For a fixed color `c`, look only at edges of color `c`.

Inside each slice, the color-`c` graph decomposes into connected components.
Each vertex belongs to exactly one color-`c` component in its slice.

## Component Quotient

For coordinate `i` and color `c`, define a quotient graph:

- nodes are slice components `(side, component_id)`;
- a connector edge of color `c` gives an edge between the component containing
  its `0`-slice endpoint and the component containing its `1`-slice endpoint.

If this quotient graph connects the component of `v` to the component of
`anti(v)`, then there is a monochromatic color-`c` path from `v` to `anti(v)`.

The number of quotient edges used is the number of connector crossings in the
full path.

## Current Candidate Lemma

The finite evidence supports the following stronger statement.

> One-connector lemma.  Every antipodal coloring of `Q_n` has a coordinate `i`,
> a color `c`, and a vertex `v` such that the color-`c` component of `v` in one
> `i`-slice is joined by a color-`c` connector to the color-`c` component of
> `anti(v)` in the other `i`-slice.

Equivalently, the component quotient contains an antipodal connection using
exactly one connector edge.

## Why This Proves Norine

Assume the one-connector lemma.

Then there are:

- a coordinate `i`;
- a color `c`;
- an antipodal pair `v, anti(v)`;
- a connector edge `x--y` of color `c`;
- a color-`c` path inside one `i`-slice from `v` to `x`;
- a color-`c` path inside the other `i`-slice from `y` to `anti(v)`.

Concatenate:

```text
v  --same-color path in slice-->  x
x  --same-color connector----->  y
y  --same-color path in slice-->  anti(v)
```

This is a monochromatic path from `v` to `anti(v)`.  Therefore Norine follows.

## Why This Is Stronger Than Prior Attempts

The reducible-slice idea required an entire coordinate slice to be antipodal as
a smaller cube.  That is false for most colorings.

The paired-slice idea required both slices to connect the same projected
antipodal endpoints in the same color.  That is also false.

The one-connector lemma only requires the connector to join the correct
components.  The connector does not need to be incident to `v` or `anti(v)`.
This is exactly why the component-chain classifier succeeds on models where the
paired-slice witness fails.

## Possible Routes To A Proof

### Route A: Component Separation

Try to prove the contrapositive.

Assume there is no one-connector witness.  For every coordinate `i`, color `c`,
and vertex `v`, every color-`c` connector leaving the component of `v` avoids
the opposite-slice component of `anti(v)`.

This says connector edges define a forbidden matching between component classes.
The antipodal edge-coloring condition may force too many opposite-color
connectors for such a separation to persist.

### Route B: Choose A Minimal Component

Fix a color and coordinate.  Pick a smallest slice component under inclusion or
boundary size.  Study its connector boundary.

The antipodal condition pairs connector colors at antipodal projected vertices.
If every connector boundary avoids the antipodal target component, there may be
a counting contradiction between a component and the antipode of its projection.

### Route C: Work In The Quotient Graph

For each coordinate and color, build the component quotient.  A counterexample
to the one-connector lemma says no quotient edge directly connects an antipodal
pair of slice components.

The goal is to show that some quotient edge must do exactly that.  This may be
more natural than reasoning about all cube vertices at once.

### Route D: Strengthen SAT Diagnostics

If a direct combinatorial proof is hard, use SAT to find unsat cores or
certificates for the one-connector-negation formula.  The negation formula is
much more structured than the original Norine counterexample formula, so it may
yield a cleaner Lean or DRAT proof pipeline.

## What A Counterexample Would Have To Do

A coloring with no one-connector witness must satisfy a very strong condition:

For every coordinate split and color, each connector edge fails to connect the
slice component of some vertex to the slice component of its full antipode.

This is much stronger than avoiding reducible slices or paired-slice witnesses.
The SAT checks show that this condition is impossible through `n = 7`.

## Current Best Next Step

Try to prove the one-connector lemma directly by contradiction:

1. Fix a coordinate `i` and color `c`.
2. Assume every color-`c` connector avoids all antipodal component targets.
3. Translate that into a statement about the connector boundary of every
   color-`c` slice component.
4. Use the antipodal edge condition to force the opposite color into the same
   obstruction.
5. Derive that one of the two colors must have a forbidden connector anyway.

If that works, the proof no longer needs induction on reducible slices.  The
dimension-reduction happens through components of a coordinate split.

## Contradiction Attempt: Reduce To One Slice

Fix a coordinate split `i`.  Write the `0`-slice as an ordinary cube
`H = Q_{n-1}`.  For a projected vertex `a in H`, let `h(a)` be the color of the
connector edge from `(0,a)` to `(1,a)`.

The antipodal edge condition implies:

- `h(anti(a)) = 1 - h(a)`;
- complementing projected vertices sends a color-`c` path in the `0`-slice to a
  color-`1-c` path in the `1`-slice.

Therefore a one-connector witness using the connector at `a` exists exactly
when

```text
C_{h(a)}(a) intersects C_{1-h(a)}(anti(a))
```

inside the `0`-slice, where `C_c(x)` means the color-`c` component of `x` in
the `0`-slice.

Indeed, if `x` is in this intersection, then:

```text
(0,x) --h(a) path--> (0,a)
(0,a) --h(a) connector--> (1,a)
(1,a) --h(a) path--> (1,anti(x))
```

The last in-slice path is obtained by complementing the color-`1-h(a)` path
from `x` to `anti(a)` in the `0`-slice.  This gives a monochromatic path from
`(0,x)` to its full antipode.

So the one-connector lemma would follow from the following fixed-slice lemma.

> Fixed-slice lemma.  In every red/blue edge-coloring of `Q_m`, and for every
> antipodal vertex-labeling `h` with `h(anti(a)) = 1 - h(a)`, there is a vertex
> `a` such that `C_{h(a)}(a)` intersects `C_{1-h(a)}(anti(a))`.

This is stronger than the original one-connector statement because it would
work for every coordinate split independently.

## Equivalent Bicross Lemma

The fixed-slice lemma is equivalent to an even cleaner edge-coloring statement.

> Bicross lemma.  In every red/blue edge-coloring of `Q_m`, there is an
> antipodal pair `x, anti(x)` such that both intersections are nonempty:
>
> ```text
> C_red(x)  intersects C_blue(anti(x))
> C_blue(x) intersects C_red(anti(x))
> ```

Why this is equivalent:

- If such an antipodal pair exists, then either choice of `h(x)` gives the
  fixed-slice witness.
- Conversely, if no such pair exists, choose for each antipodal pair a color
  whose corresponding intersection is empty.  This gives an antipodal labeling
  `h` with no fixed-slice witness.

This is now the cleanest proof target.  It no longer mentions SAT, connector
quotients, or the full antipodal edge-coloring.  It only talks about red and
blue components in an ordinary cube.

## Contradiction Shape For The Bicross Lemma

Assume the bicross lemma is false.  Then for every antipodal pair at least one
of the two cross-intersections is empty.  Choose an antipodal label `h` selecting
an empty cross-intersection for every pair.  Then the selected components

```text
S_x = C_{h(x)}(x)
S_anti(x) = C_{h(anti(x))}(anti(x))
```

are disjoint for every `x`.

A useful local fact:

> If a red component `R` and a blue component `B` are disjoint, then there is no
> cube edge directly between `R` and `B`.

Reason: a red edge from `R` into `B` would put its `B` endpoint in `R`, and a
blue edge from `R` into `B` would put its `R` endpoint in `B`.

Thus every selected component is separated from its antipodal selected
component by graph distance at least two.  The hoped-for contradiction is to
turn these separations into an antipodal labeling of the cube's cells, then use
a Tucker/Borsuk-Ulam style argument to force a complementary adjacency.  That
complementary adjacency should translate back into exactly one of the forbidden
cross-intersections.

Current honest gap: the separation-to-Tucker-label step is not yet formal.
The reduction above is solid; the remaining proof problem is a pure bicross
component theorem for edge-colorings of `Q_m`.

The standalone note `docs/BICROSS_LEMMA.md` tracks this reduced theorem.  The
probe script `enc/bicross_probe.py` checks arbitrary cube edge-colorings,
antipodal connector-labelings, and the SAT negation of the fixed-slice lemma.
The strongest current finite signal is the exact `Q_6` pair-hit frontier:
`Bad = V \ G` can hit 28 of 32 antipodal pairs, but cannot hit 29.  So in
`Q_6` every coloring has at least four bicross antipodal pairs, even before
using the full antipodal-cube structure.

The best current non-compute direction is the inherited-slice versus
incidence-cell dichotomy recorded in `docs/EXTREMAL_STAR.md`.  One major
frontier family has all surviving bicross pairs inside one red/blue
component-incidence cell; if two antipodal vertices lie in the same red
component and the same blue component, the bicross witness is immediate.
However, Q5 also has exact-frontier models with no such cell pair.  Those
models have a perfect inherited slice with uniform connectors, so the likely
proof shape is a dichotomy: near-obstructions either reduce to a smaller cube
or force an incidence-cell bicross pair.
