"""Classify near-cover holes in paired-block product bad targets.

The canonical product target is

    P = {x in Q_m : no paired two-coordinate block of x is 00},

with the last coordinate free when m is odd. All choices of one forbidden state
per block are equivalent by cube bit flips, so this canonical target loses no
generality for SAT feasibility. This script classifies hole sets in P up to the
symmetries preserving P and asks which near-covers can be forced bad for one
coloring.
"""

from __future__ import annotations

import argparse
import itertools
import time
from collections import Counter, defaultdict
from dataclasses import dataclass

from bicross_probe import vertex_name
from induction_probe import anti
from sat_utils import solver_help
from two_color_cross_probe import encode_target_bad_subset, product_target


@dataclass(frozen=True)
class HoleOrbitResult:
    index: int
    representative: tuple[tuple[int, ...], ...]
    orbit_size: int
    antipodal_pair: bool
    antipodal_closed: bool
    result: bool | None
    elapsed: float


def zero_forbidden_blocks(m):
    return tuple((0, 0) for _ in range(m // 2))


def canonical_product_target(m):
    return frozenset(product_target(m, zero_forbidden_blocks(m)))


def block_symmetry_transforms(block_count, has_free_coordinate=False):
    return tuple(
        (perm, swaps, free_flip)
        for perm in itertools.permutations(range(block_count))
        for swaps in itertools.product((0, 1), repeat=block_count)
        for free_flip in ((0, 1) if has_free_coordinate else (0,))
    )


def apply_block_symmetry(vertex, perm, swaps, free_flip=0):
    blocks = [list(vertex[2 * index : 2 * index + 2]) for index in range(len(perm))]
    transformed = []
    for old_index in perm:
        block = blocks[old_index][:]
        if swaps[old_index]:
            block = [block[1], block[0]]
        transformed.extend(block)
    if len(vertex) % 2:
        transformed.append(vertex[-1] ^ free_flip)
    return tuple(transformed)


def canonical_hole_set(holes, transforms):
    images = []
    for perm, swaps, free_flip in transforms:
        image = tuple(sorted(apply_block_symmetry(vertex, perm, swaps, free_flip) for vertex in holes))
        images.append(image)
    return min(images)


def hole_orbits(m, hole_count):
    target = sorted(canonical_product_target(m))
    transforms = block_symmetry_transforms(m // 2, has_free_coordinate=bool(m % 2))
    orbits = defaultdict(list)
    for holes in itertools.combinations(target, hole_count):
        orbits[canonical_hole_set(holes, transforms)].append(holes)
    return dict(orbits)


def is_antipodal_pair(holes):
    return len(holes) == 2 and anti(holes[0]) == holes[1]


def is_antipodal_closed(holes):
    hole_set = set(holes)
    return all(anti(vertex) in hole_set for vertex in holes)


def solve_hole_representative(m, holes, solver_name=None, conflict_budget=0):
    target = canonical_product_target(m) - set(holes)
    solver, *_ = encode_target_bad_subset(m, target, solver_name)
    try:
        if conflict_budget:
            solver.conf_budget(conflict_budget)
            return solver.solve_limited()
        return solver.solve()
    finally:
        solver.delete()


def analyze_hole_orbits(m, hole_count, solver_name=None, conflict_budget=0):
    started = time.monotonic()
    results = []
    for index, (representative, members) in enumerate(sorted(hole_orbits(m, hole_count).items()), start=1):
        result = solve_hole_representative(
            m,
            representative,
            solver_name=solver_name,
            conflict_budget=conflict_budget,
        )
        results.append(
            HoleOrbitResult(
                index=index,
                representative=representative,
                orbit_size=len(members),
                antipodal_pair=is_antipodal_pair(representative),
                antipodal_closed=is_antipodal_closed(representative),
                result=result,
                elapsed=time.monotonic() - started,
            )
        )
    return results


def format_holes(holes):
    return " ".join(vertex_name(vertex) for vertex in holes)


def run(args):
    target = canonical_product_target(args.m)
    orbits = hole_orbits(args.m, args.hole_count)
    orbit_sizes = Counter(len(members) for members in orbits.values())

    print(f"Dimension: Q_{args.m}")
    print("Product target: avoid 00 in each paired block")
    print(f"Target size: {len(target)}")
    print(f"Hole count: {args.hole_count}")
    print(f"Hole orbits: {len(orbits)}")
    print(f"Orbit-size distribution: {dict(sorted(orbit_sizes.items()))}")
    if args.conflict_budget:
        print(f"Conflict budget per orbit: {args.conflict_budget}")

    results = analyze_hole_orbits(
        args.m,
        args.hole_count,
        solver_name=args.solver,
        conflict_budget=args.conflict_budget,
    )
    result_counts = Counter(str(result.result) for result in results)

    for result in results:
        if args.hide_unsat_orbits and result.result is False:
            continue
        print(
            f"orbit={result.index:02d} size={result.orbit_size:3d} "
            f"holes={format_holes(result.representative)} "
            f"antipodal_pair={result.antipodal_pair} "
            f"antipodal_closed={result.antipodal_closed} "
            f"result={result.result} "
            f"elapsed={result.elapsed:.2f}s",
            flush=True,
        )
    print(f"Result counts: {dict(sorted(result_counts.items()))}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Cube dimension")
    parser.add_argument("--hole-count", type=int, default=2, help="Number of unforced vertices inside the product target")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--conflict-budget", type=int, default=0, help="Optional conflict budget per orbit")
    parser.add_argument("--hide-unsat-orbits", action="store_true", help="Print only SAT/UNKNOWN orbit details")
    return parser.parse_args()


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
