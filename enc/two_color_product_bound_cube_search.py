"""Cube search for product-target bad-count bounds.

This probes formulas of the form:

    at least B vertices of the canonical paired-block product target are bad.

The canonical product target keeps all vertices whose paired two-coordinate
blocks avoid 00, with the final coordinate free in odd dimensions.
"""

from __future__ import annotations

import argparse
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

from bicross_cube_search import (
    batches_for_cubes,
    build_cubes,
    choose_cube_edges,
    parse_index_set,
    solve_cube_chunk,
)
from bicross_probe import bad_vertices, good_vertices, vertex_name
from induction_probe import all_edges
from sat_utils import best_pysat_solver_name, effective_cpu_count, solver_help
from two_color_cross_probe import encode_target_bad_subset, model_to_coloring, product_target


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


def canonical_product_target(m):
    return tuple(sorted(product_target(m, tuple((0, 0) for _ in range(m // 2)))))


def encode_product_bad_bound(m, bad_bound, solver_name=None):
    try:
        from pysat.card import CardEnc, EncType
    except ModuleNotFoundError as exc:
        raise SystemExit(f"python-sat is required for product bad-bound solving: {exc}") from exc

    target = canonical_product_target(m)
    solver, vpool, r, bad, clauses = encode_target_bad_subset(m, (), solver_name)
    cardinality = CardEnc.atleast(
        lits=[bad(vertex) for vertex in target],
        bound=bad_bound,
        vpool=vpool,
        encoding=EncType.seqcounter,
    )
    clauses = list(clauses) + list(cardinality.clauses)
    for clause in cardinality.clauses:
        solver.add_clause(clause)
    return solver, vpool, r, bad, clauses, target


def print_sat_model_summary(args, model, edges, r, target):
    coloring = model_to_coloring(model, edges, r)
    target_set = set(target)
    actual_bad = set(bad_vertices(coloring, args.m))
    actual_good = set(good_vertices(coloring, args.m))
    product_good = sorted(target_set & actual_good)

    print(f"Actual product bad: {len(target_set & actual_bad)}/{len(target)}", flush=True)
    print(f"Actual total bad: {len(actual_bad)}/{2 ** args.m}", flush=True)
    print("Actual product good: " + " ".join(vertex_name(vertex) for vertex in product_good), flush=True)


def run(args):
    solver, vpool, r, _bad, clauses, target = encode_product_bad_bound(args.m, args.bad_bound, args.solver)
    solver.delete()

    _vertices, _graph, edges = all_edges(args.m)
    cube_edges = choose_cube_edges(edges, args.cube_depth, args.cube_mode, args.seed, offset=args.cube_offset)
    cube_literals = tuple(r(*edge) for edge in cube_edges)
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
    print("Formula: canonical product target bad-at-least", flush=True)
    print(f"Target size: {len(target)}", flush=True)
    print(f"Bad bound: {args.bad_bound}", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Solver: {solver_name}", flush=True)
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
    print(f"SAT cubes: {totals['sat']}", flush=True)
    print(f"UNSAT cubes: {totals['unsat']}", flush=True)
    print(f"UNKNOWN cubes: {totals['unknown']}", flush=True)
    if unknown_indexes:
        print(f"UNKNOWN ranges: {format_index_ranges(unknown_indexes)}", flush=True)

    if first_sat is not None:
        print(f"SAT: True; cube_index={first_sat['cube_index']}; cube={first_sat['cube']}", flush=True)
        print_sat_model_summary(args, first_sat["model"], edges, r, target)
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
    parser.add_argument("--bad-bound", type=int, required=True, help="Bad vertices forced inside the product target")
    parser.add_argument("--cube-depth", type=int, default=8, help="Number of edge variables to cube on")
    parser.add_argument(
        "--cube-mode",
        choices=("prefix", "spread", "random", "window", "zero-pattern-tail"),
        default="prefix",
        help="How to choose edge variables for cubes",
    )
    parser.add_argument("--cube-offset", type=int, default=0, help="Start offset into edge list for prefix/window/random/spread")
    parser.add_argument("--seed", type=int, default=20260522, help="Random seed for cube selection/shuffle")
    parser.add_argument("--jobs", type=int, default=0, help="Parallel workers; default uses all available cores")
    parser.add_argument("--batch-size", type=int, default=0, help="Cubes per solver batch; default keeps one batch per worker")
    parser.add_argument("--solver", default=None, help=solver_help(require_assumptions=True))
    parser.add_argument("--conflict-budget", type=int, default=0, help="Optional conflict budget per cube")
    parser.add_argument("--shuffle-cubes", action="store_true", help="Shuffle cube order before assigning workers")
    parser.add_argument("--only-cube-indexes", help="Comma-separated cube indexes/ranges to run after cube ordering")
    parser.add_argument("--stop-on-sat", action="store_true", help="Return as soon as any cube is SAT")
    return parser.parse_args()


def main():
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
