"""Parallel cube-split SAT search for the two-color cross-bicross theorem.

This runs the same negation as ``two_color_cross_probe.py --sat-negation``:
find two edge-colorings C,D of Q_m such that

    G(C) intersect anti(G(D)) = empty.

The search is split by assumptions on selected edge variables from the first
coloring.  That is the coloring normalized by the available symmetry breaks.
"""

from __future__ import annotations

import argparse
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

from bicross_cube_search import batches_for_cubes, build_cubes, choose_cube_edges, parse_index_set
from bicross_probe import bad_vertices, good_vertices
from induction_probe import all_edges
from sat_utils import best_pysat_solver_name, effective_cpu_count, make_pysat_solver, solver_help
from two_color_cross_probe import (
    bad_sets_cross_cover,
    cross_bicross_witness,
    encode_cross_cover_negation,
    model_to_coloring,
)


def solve_cube_chunk(worker_id, clauses, cubes, solver_name, conflict_budget):
    solver, actual_solver = make_pysat_solver(solver_name, require_assumptions=True)
    for clause in clauses:
        solver.add_clause(clause)

    counts = Counter()
    first_sat = None
    unknown_indexes = []
    started = time.monotonic()

    for cube_index, cube in cubes:
        if conflict_budget:
            solver.conf_budget(conflict_budget)
            result = solver.solve_limited(assumptions=list(cube))
        else:
            result = solver.solve(assumptions=list(cube))

        if result is True:
            counts["sat"] += 1
            first_sat = {
                "cube_index": cube_index,
                "cube": cube,
                "model": solver.get_model(),
            }
            break
        if result is False:
            counts["unsat"] += 1
        else:
            counts["unknown"] += 1
            unknown_indexes.append(cube_index)

    solver.delete()
    return {
        "worker_id": worker_id,
        "solver": actual_solver,
        "counts": dict(counts),
        "first_sat": first_sat,
        "unknown_indexes": unknown_indexes,
        "elapsed": time.monotonic() - started,
    }


def format_index_ranges(indexes):
    values = sorted(set(indexes))
    if not values:
        return ""

    ranges = []
    start = prev = values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append(f"{start}-{prev}" if start != prev else str(start))
        start = prev = value
    ranges.append(f"{start}-{prev}" if start != prev else str(start))
    return ",".join(ranges)


def print_sat_model_summary(args, model, edges, r):
    coloring_c = model_to_coloring(model, edges, lambda u, v: r(0, u, v))
    coloring_d = model_to_coloring(model, edges, lambda u, v: r(1, u, v))
    bad_c = set(bad_vertices(coloring_c, args.m))
    bad_d = set(bad_vertices(coloring_d, args.m))
    vertices, _graph, _edges = all_edges(args.m)
    witness = cross_bicross_witness(coloring_c, coloring_d, args.m)

    print(f"Postcheck cross witness: {witness}", flush=True)
    print(f"Postcheck cross-cover: {bad_sets_cross_cover(bad_c, bad_d, vertices)}", flush=True)
    print(f"Bad sizes: C={len(bad_c)}, D={len(bad_d)}", flush=True)
    print(f"Good sizes: C={len(good_vertices(coloring_c, args.m))}, D={len(good_vertices(coloring_d, args.m))}", flush=True)


def run(args):
    solver, vpool, r, _bad, clauses = encode_cross_cover_negation(
        args.m,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
    )
    solver.delete()

    _vertices, _graph, edges = all_edges(args.m)
    cube_edges = choose_cube_edges(edges, args.cube_depth, args.cube_mode, args.seed, offset=args.cube_offset)
    cube_literals = tuple(r(0, *edge) for edge in cube_edges)
    cubes = list(build_cubes(cube_literals))
    if args.shuffle_cubes:
        rng = random.Random(args.seed)
        rng.shuffle(cubes)

    selected_indexes = parse_index_set(args.only_cube_indexes)
    indexed_cubes = list(enumerate(cubes))
    if selected_indexes is not None:
        indexed_cubes = [(index, cube) for index, cube in indexed_cubes if index in selected_indexes]

    jobs = max(1, min(args.jobs or effective_cpu_count(), len(indexed_cubes) or 1))
    batches = batches_for_cubes(indexed_cubes, jobs, args.batch_size)
    solver_name = best_pysat_solver_name(args.solver, require_assumptions=True)
    started = time.monotonic()

    print(f"Dimension: Q_{args.m}", flush=True)
    print("Formula: two-color cross-cover negation", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Solver: {solver_name}", flush=True)
    if args.sort_zero_edges:
        print("Symmetry: first coloring has sorted zero-incident colors", flush=True)
    if args.zero_red_degree_at_most_half:
        print("Symmetry: first coloring has zero red degree at most half", flush=True)
    if args.partial_sym_break:
        print(f"Symmetry: first coloring lex comparisons up to {args.partial_sym_break}", flush=True)
    print(f"Workers: {jobs} (available cores: {effective_cpu_count()})", flush=True)
    print(f"Cube depth: {args.cube_depth}", flush=True)
    print(f"Cube mode: {args.cube_mode}", flush=True)
    print(f"Cubes selected: {len(indexed_cubes)}/{len(cubes)}", flush=True)
    if selected_indexes is not None:
        print(f"Selected ranges: {format_index_ranges(selected_indexes)}", flush=True)
    print(f"Batches: {len(batches)}", flush=True)
    print("Cube edges: " + ", ".join(f"{u}-{v}" for u, v in cube_edges), flush=True)
    if args.conflict_budget:
        print(f"Conflict budget per cube: {args.conflict_budget}", flush=True)

    totals = Counter()
    first_sat = None
    unknown_indexes = []

    with ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = [
            executor.submit(
                solve_cube_chunk,
                worker_id,
                clauses,
                batch,
                args.solver,
                args.conflict_budget,
            )
            for worker_id, batch in enumerate(batches)
        ]
        for future in as_completed(futures):
            result = future.result()
            totals.update(result["counts"])
            unknown_indexes.extend(result["unknown_indexes"])
            print(
                f"batch={result['worker_id']} solver={result['solver']} "
                f"counts={result['counts']} elapsed={result['elapsed']:.2f}s",
                flush=True,
            )
            if result["first_sat"] is not None and first_sat is None:
                first_sat = result["first_sat"]
                if args.stop_on_sat:
                    for pending in futures:
                        pending.cancel()
                    break

    elapsed = time.monotonic() - started
    solved = totals["sat"] + totals["unsat"] + totals["unknown"]
    unknown_indexes = sorted(set(unknown_indexes))
    print(f"Elapsed: {elapsed:.2f}s", flush=True)
    print(f"Selected cubes solved: {solved}/{len(indexed_cubes)}", flush=True)
    print(f"Total cube space: {len(cubes)}", flush=True)
    print(f"SAT cubes: {totals['sat']}", flush=True)
    print(f"UNSAT cubes: {totals['unsat']}", flush=True)
    print(f"UNKNOWN cubes: {totals['unknown']}", flush=True)
    if unknown_indexes:
        print(f"UNKNOWN ranges: {format_index_ranges(unknown_indexes)}", flush=True)

    if first_sat is not None:
        print(f"SAT: True; cube_index={first_sat['cube_index']}; cube={first_sat['cube']}", flush=True)
        print_sat_model_summary(args, first_sat["model"], edges, r)
        return 0

    if totals["unknown"]:
        print("SAT: Unknown", flush=True)
        return 124

    if totals["unsat"] == len(indexed_cubes):
        if selected_indexes is None:
            print("SAT: False", flush=True)
        else:
            print("Selected cubes SAT: False", flush=True)
        return 0

    print("SAT: Incomplete", flush=True)
    return 125


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of ordinary cube Q_m")
    parser.add_argument("--cube-depth", type=int, default=8, help="Number of first-coloring edge variables to cube on")
    parser.add_argument(
        "--cube-mode",
        choices=("prefix", "spread", "random", "window", "zero-pattern-tail"),
        default="spread",
        help="How to choose first-coloring edge variables for cubes",
    )
    parser.add_argument("--cube-offset", type=int, default=0, help="Start offset into edge list for prefix/window/random/spread")
    parser.add_argument("--seed", type=int, default=20260521, help="Random seed for cube selection/shuffle")
    parser.add_argument("--jobs", type=int, default=0, help="Parallel workers; default uses all available cores")
    parser.add_argument("--batch-size", type=int, default=0, help="Cubes per solver batch; default keeps one batch per worker")
    parser.add_argument("--solver", default=None, help=solver_help(require_assumptions=True))
    parser.add_argument("--conflict-budget", type=int, default=0, help="Optional conflict budget per cube")
    parser.add_argument("--shuffle-cubes", action="store_true", help="Shuffle cube order before assigning workers")
    parser.add_argument("--only-cube-indexes", help="Comma-separated cube indexes/ranges to run after cube ordering")
    parser.add_argument("--stop-on-sat", action="store_true", help="Return as soon as any cube is SAT")
    parser.add_argument("--sort-zero-edges", action="store_true", help="Sort colors incident to 00...0 in the first coloring")
    parser.add_argument("--zero-red-degree-at-most-half", action="store_true", help="Bound first-coloring red degree at 00...0")
    parser.add_argument("--partial-sym-break", type=int, default=0, help="First-coloring coordinate/bit-flip lex comparison cap")
    return parser.parse_args()


def main():
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
