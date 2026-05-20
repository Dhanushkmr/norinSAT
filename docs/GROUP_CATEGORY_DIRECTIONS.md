# Group And Category Theory Directions

This note collects proof-search ideas that use more structure than "a cube is
a graph."  The goal is to find invariants that explain why the bicross
frontier seems to have only two branches: inherited split or incidence-cell
star.

## 1. The Cube As A Cayley Graph

Write the vertex set of `Q_m` as the elementary abelian group

```text
G = F_2^m.
```

The cube is the Cayley graph of `G` with generators `e_0, ..., e_{m-1}`.  An
edge coloring is therefore a function

```text
c_i(x) in F_2
```

where `c_i(x)` is the color of the edge from `x` to `x + e_i`.  The antipodal
map is translation by

```text
omega = e_0 + e_1 + ... + e_{m-1}.
```

For the original Norine coloring of `Q_n`, the antipodal edge condition is the
anti-periodicity equation

```text
c_i(x + omega) = c_i(x) + 1.
```

For the reduced bicross lemma, there is no anti-periodicity on `c`; instead
the connector colors in a fixed slice give an anti-periodic vertex labeling

```text
h(x + omega) = h(x) + 1.
```

Useful reformulation:

> Bicross says that no edge coloring `c` can defeat every anti-periodic vertex
> labeling `h`.

So the fixed-slice problem is an equivariant obstruction problem on `F_2^m`.

## 2. Automorphisms And Orbits

The cube automorphism group is

```text
Aut(Q_m) = F_2^m semidirect S_m.
```

It acts by translations and coordinate permutations.  There is also a global
color flip.  Many SAT models that look different are genuinely in different
orbits as colorings, but their bicross-pair sets may still lie in a much
smaller orbit.

New orbit question:

> Are frontier bicross-pair sets always equivalent, under `Aut(Q_m)`, to an
> affine subspace in the antipodal quotient `G / <omega>`?

This is stronger than the current branch statement and very testable.

## 3. The Paired Construction Looks Symplectic

The sharp construction pairs coordinates:

```text
(0,1), (2,3), ...
```

and colors an edge in one coordinate by the value of its partner coordinate.
For even `m = 2k`, this has the form

```text
c_i(x) = B(x, e_i)
```

where `B` is the alternating bilinear form pairing each coordinate with its
partner.  The extremal construction is therefore a linear coloring controlled
by a symplectic form over `F_2`.

The bicross pairs in this construction are exactly the antipodal pairs whose
blocks satisfy

```text
x_{2j} + x_{2j+1} = 1
```

for every paired block.  That is an affine subspace of dimension `k` in
`F_2^{2k}`, which becomes `2^(k-1)` antipodal pairs after quotienting by
`<omega>`.  For odd `m = 2k + 1`, the same block equations leave an affine
subspace of dimension `k+1`, giving `2^k` antipodal pairs.

Thus the conjectured lower bound

```text
2^floor((m - 1) / 2)
```

is exactly the size of this affine/symplectic survivor set in the antipodal
quotient.

Possible theorem:

> Every coloring has a bicross-pair set containing an affine subspace of
> dimension `floor((m - 1) / 2)` in `G / <omega>`.

This may be too strong, but if it survives finite tests it would explain the
dimension formula much better than raw pair counting.

## 4. Edge Colorings As Cochains

Treat `c_i(x)` as a `1`-cochain on the cube.  A vertex function `f(x)` gives a
coboundary

```text
(df)_i(x) = f(x) + f(x + e_i).
```

The square curvature of a coloring is

```text
K_ij(x) = c_i(x) + c_i(x + e_j) + c_j(x) + c_j(x + e_i).
```

This is the parity of color changes around the square spanned by coordinates
`i,j`.

Why this might matter:

- The paired construction has a highly structured curvature tensor.
- Gauge-equivalent colorings have the same square curvatures.
- If high pair-hit frontier colorings have low-rank curvature, then the proof
  can reduce to a normal-form theorem for cochains.

New computational invariant:

> Compute the rank and orbit type of the square-curvature tensor for frontier
> models, then compare it with the paired-coordinate construction.

## 5. Fourier And Additive-Combinatorial View

Let

```text
pi: G -> G / <omega>
```

and let `Bad` be the set of vertices not in `G_good`.  Then

```text
hit(Bad) = |pi(Bad)|.
```

The quantitative bicross conjecture becomes

```text
|complement of pi(Bad) in G/<omega>| >= 2^floor((m - 1) / 2).
```

In the sharp construction, that complement is an affine subspace.  This
suggests additive-combinatorial tools: uncertainty principles on `F_2^m`,
small-doubling or stabilizer arguments for `pi(Bad)`, Fourier concentration of
the untouched-pair indicator, and compression under coordinate permutations.

New test:

> For SAT frontier samples, compute whether the untouched-pair set has high
> Fourier concentration on a subspace of dimension `floor((m - 1) / 2)`.

## 6. Component Partitions As Quotients

For a coloring, red and blue components define two equivalence relations:

```text
x ~R y  iff x,y are in the same red component
x ~B y  iff x,y are in the same blue component
```

Equivalently, there are quotient maps

```text
q_R: V -> V / ~R
q_B: V -> V / ~B
```

The incidence-cell map is

```text
q = (q_R, q_B): V -> (V / ~R) x (V / ~B).
```

The inherited branch says the quotient data descends along a coordinate-face
map.  The cell-star branch says a fiber of `q` contains antipodal pairs.

This suggests a descent-or-fiber lemma:

> For quotient maps `q_R,q_B` generated by complementary colored subgraphs of
> a cube, high antipodal coverage forces either descent along a coordinate
> projection or an antipodal pair in one fiber of `(q_R,q_B)`.

That is almost exactly the current branch lemma, but stated without SAT
language.

## 7. Category-Theoretic Translation

There are three categorical objects hiding here.

First, the cube is a product:

```text
Q_m = [1]^m
```

in the category of graphs.  Coordinate slices are face maps, and adding a
coordinate is product with `[1]`.

Second, each color gives a quotient functor from the connected-component
category of the colored subgraph:

```text
Q_m^red  -> pi_0(Q_m^red)
Q_m^blue -> pi_0(Q_m^blue)
```

Third, the incidence matrix is a pullback/fiber-product question.  A cross
intersection such as

```text
R(x) intersect B(anti x)
```

is exactly the nonemptiness of a fiber product of a red-component fiber and a
blue-component fiber.

In this language:

- a one-connector witness is a nonempty pullback after slicing;
- a perfect inherited split is descent data along a face projection;
- a cell-star witness is an antipodal fixed pair inside a fiber of `(q_R,q_B)`;
- a failed bicross coloring would be a coherent choice of empty pullbacks for
  every antipodal pair.

Possible categorical lemma:

> In the cube category, two complementary connectivity quotients cannot admit
> an antipodal coherent system of empty cross-pullbacks.

This is still vague, but it points at a proof shape: use functoriality under
faces and products, not only graph paths.

## 8. Best New Concrete Probes

The most promising next experiments are structure probes on existing frontier
models, not larger SAT runs.

1. Affine survivor test.  Compute the untouched/bicross antipodal pairs in
   `G / <omega>` and test whether they contain an affine subspace of dimension
   `floor((m - 1) / 2)`.
2. Symplectic normal-form test.  Compute whether an edge-color cochain is
   close to a linear form `c_i(x)=B(x,e_i)+a_i` after cube automorphisms and
   gauge transforms.
3. Curvature-rank test.  Compute square curvatures `K_ij(x)` and compare
   ranks/signatures for the paired construction, Q5 inherited models, and Q6
   cell-star models.
4. Quotient-fiber descent test.  For each split, record whether the component
   quotient map factors through the lower-dimensional cube.  This is a
   categorical version of perfect inheritance and may reveal weaker descent
   patterns.
5. Stabilizer test.  Compute the automorphism stabilizer size of the
   bicross-pair set, not the full coloring.  If bicross sets have large
   stabilizers while colorings do not, the proof should target the survivor
   set rather than the coloring.

## Current Bet

The best bet is the affine survivor test.

The reason is simple: the sharp count

```text
1, 2, 2, 4, 4, 8, 8, ...
```

looks exactly like the minimum size of an affine subspace surviving in the
antipodal quotient.  The paired-coordinate construction realizes that survivor
set using a symplectic pairing of coordinates.  If arbitrary frontier models
also contain such an affine survivor, the lower-bound proof may become:

```text
component quotients
=> forced affine survivor in G/<omega>
=> at least 2^floor((m - 1) / 2) bicross pairs.
```

That would explain both the count and the paired-coordinate extremal examples.

## Experiment Update, 2026-05-20

Implemented `enc/group_structure_probe.py`.

The main theorem tested is: every coloring of `Q_m` has a bicross-pair set
containing an affine subspace of dimension `floor((m - 1) / 2)` in
`F_2^m / <omega>`.

What survived:

- Exact `Q_3` enumeration: `4096/4096` colorings contain the target affine
  survivor.
- The paired-coordinate construction has the bicross set exactly affine for
  `m=1..8` in tests; in `Q_6` the four bicross pairs form an affine plane in
  the quotient.
- Random samples found no failures: `Q_4` 2000/2000, `Q_5` 2000/2000,
  `Q_6` 1000/1000.
- SAT frontier samples found no failures, and the whole bicross set was
  affine in every sampled frontier model: `Q_4` 23/23, `Q_5` ordinary
  100/100, `Q_5` no-cell 100/100, `Q_6` ordinary 50/50.
- The direct SAT negation `--sat-no-affine-survivor` proves the theorem
  through `Q_5`: `Q_3`, `Q_4`, and `Q_5` are UNSAT.

For `Q_6`, the direct solver did not settle quickly.  Cube-and-conquer on the
no-affine negation found no SAT counterexample but hit a local compute wall:

```text
depth 6,  50k conflicts: 60/64 UNSAT, UNKNOWN 0,1,3,7
depth 8,  50k conflicts: 5/16 selected UNSAT, 11 UNKNOWN
depth 10, 50k conflicts: 23/44 selected UNSAT, 21 UNKNOWN
depth 12, 50k conflicts: 30/84 selected UNSAT, 54 UNKNOWN
depth 12, 200k conflicts on those 54: 1 UNSAT, 53 UNKNOWN
```

An assumption-capable solver-diversity pass with `glucose4` did not help:
`54/54` remained UNKNOWN at 50k conflicts.

Current Q6 no-affine UNKNOWN list at depth 12:

```text
0,1,2,3,6,7,14,15,30,31,66,67,68,69,70,71,76,77,78,79,92,93,94,95,198,199,200,201,202,203,206,207,216,217,218,219,222,223,249,251,462,463,464,465,466,467,470,471,478,479,497,499,503
```

One dead-end correction: square curvature is probably not the right
cohomology invariant for the symplectic construction.  The paired-coordinate
coloring has zero square curvature because it is the derivative of a
quadratic potential.  The useful linear-algebra object is instead the
directional derivative/Hessian of the edge-color functions.

New best proof direction: component quotient structure should force an
affine survivor in `F_2^m / <omega>`, which then gives the quantitative
bicross lower bound.  The `Q_5` UNSAT result makes this a serious candidate
lemma rather than just a pretty interpretation.
