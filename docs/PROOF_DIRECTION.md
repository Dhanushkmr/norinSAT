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
