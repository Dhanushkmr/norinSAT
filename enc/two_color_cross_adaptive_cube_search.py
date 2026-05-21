"""Adaptive nested-prefix cube search for the two-color cross theorem.

This is the two-color analogue of bicross_adaptive_cube_search.py. It starts
from a list of prefix depths, solves selected cubes at the first depth, then
descends only UNKNOWN cubes to the next depth.
"""

from __future__ import annotations

import argparse
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from bicross_adaptive_cube_search import (
    choose_ordered_cube_edges,
    cube_from_index,
    expand_indexes,
    format_index_ranges,
    parse_int_list,
    selected_at_first_depth,
    write_stage_log,
)
from bicross_cube_search import batches_for_cubes
from induction_probe import all_edges
from sat_utils import best_pysat_solver_name, effective_cpu_count, solver_help
from two_color_cross_cube_search import print_sat_model_summary, solve_cube_chunk
from two_color_cross_probe import encode_cross_cover_negation


def build_indexed_cubes(cube_literals, depth, indexes):
    return [(index, cube_from_index(cube_literals, depth, index)) for index in indexes]


def solve_stage(args, clauses, cube_literals, depth, selected_indexes, edges, r, log_path):
    indexed_cubes = build_indexed_cubes(cube_literals, depth, selected_indexes)
    jobs = max(1, min(args.jobs or effective_cpu_count(), len(indexed_cubes) or 1))
    batches = batches_for_cubes(indexed_cubes, jobs, args.batch_size)
    solver_name = best_pysat_solver_name(args.solver, require_assumptions=True)
    started = time.monotonic()

    print(f"Stage depth: {depth}", flush=True)
    print(f"Solver: {solver_name}", flush=True)
    print(f"Workers: {jobs} (available cores: {effective_cpu_count()})", flush=True)
    print(f"Cubes selected: {len(indexed_cubes)}/{2**depth}", flush=True)
    print(f"Selected ranges: {format_index_ranges(selected_indexes)}", flush=True)
    print(f"Batches: {len(batches)}", flush=True)
    if args.conflict_budget:
        print(f"Conflict budget per cube: {args.conflict_budget}", flush=True)

    totals = Counter()
    unknown_indexes = []
    first_sat = None

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
    unknown_indexes = sorted(set(unknown_indexes))
    print(f"Stage elapsed: {elapsed:.2f}s", flush=True)
    print(f"SAT cubes: {totals['sat']}", flush=True)
    print(f"UNSAT cubes: {totals['unsat']}", flush=True)
    print(f"UNKNOWN cubes: {totals['unknown']}", flush=True)
    if unknown_indexes:
        print(f"UNKNOWN ranges: {format_index_ranges(unknown_indexes)}", flush=True)

    write_stage_log(
        log_path,
        {
            "depth": depth,
            "selected": len(indexed_cubes),
            "selected_ranges": format_index_ranges(selected_indexes),
            "sat": totals["sat"],
            "unsat": totals["unsat"],
            "unknown": totals["unknown"],
            "unknown_ranges": format_index_ranges(unknown_indexes),
            "elapsed": elapsed,
            "conflict_budget": args.conflict_budget,
            "solver": solver_name,
        },
    )

    if first_sat is not None:
        print(f"SAT: True; cube_index={first_sat['cube_index']}; cube={first_sat['cube']}", flush=True)
        print_sat_model_summary(args, first_sat["model"], edges, r)

    return first_sat, unknown_indexes


def run(args):
    depths = parse_int_list(args.depths, "--depths")
    if depths != sorted(set(depths)):
        raise SystemExit("--depths must be strictly increasing")
    max_depth = depths[-1]

    if args.log_file:
        log_path = Path(args.log_file)
        log_path.write_text("")
    else:
        log_path = None

    solver, vpool, r, _bad, clauses = encode_cross_cover_negation(
        args.m,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
    )
    solver.delete()

    _vertices, _graph, edges = all_edges(args.m)
    cube_edges = choose_ordered_cube_edges(
        edges,
        max_depth,
        tail_start_depth=args.tail_start_depth,
        tail_mode=args.tail_mode,
        seed=args.seed,
    )
    cube_literals = tuple(r(0, *edge) for edge in cube_edges)

    print(f"Dimension: Q_{args.m}", flush=True)
    print("Formula: two-color cross-cover negation", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Depths: {depths}", flush=True)
    print("Cube edges: " + ", ".join(f"{u}-{v}" for u, v in cube_edges), flush=True)
    if args.sort_zero_edges:
        print("Symmetry: first coloring has sorted zero-incident colors", flush=True)
    if args.zero_red_degree_at_most_half:
        print("Symmetry: first coloring has zero red degree at most half", flush=True)
    if args.partial_sym_break:
        print(f"Symmetry: first coloring lex comparisons up to {args.partial_sym_break}", flush=True)

    selected_indexes = list(selected_at_first_depth(args, depths[0]))
    first_sat = None
    unknown_indexes = []

    for index, depth in enumerate(depths):
        if index:
            selected_indexes = expand_indexes(unknown_indexes, depths[index - 1], depth)
            if not selected_indexes:
                print("No UNKNOWN cubes remain; stopping.", flush=True)
                break

        first_sat, unknown_indexes = solve_stage(args, clauses, cube_literals, depth, selected_indexes, edges, r, log_path)
        if first_sat is not None and args.stop_on_sat:
            return 0

    if first_sat is not None:
        return 0
    if unknown_indexes:
        print(f"Final UNKNOWN ranges: {format_index_ranges(unknown_indexes)}", flush=True)
        return 124

    print("SAT: False", flush=True)
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of ordinary cube Q_m")
    parser.add_argument("--depths", required=True, help="Comma-separated strictly increasing cube depths")
    parser.add_argument("--parent-depth", type=int, help="Existing parent depth whose descendants start the run")
    parser.add_argument("--parent-indexes", help="Comma-separated parent cube indexes/ranges")
    parser.add_argument("--only-cube-indexes", help="Comma-separated cube indexes/ranges for the first requested depth")
    parser.add_argument("--tail-start-depth", type=int, default=0, help="Keep this many prefix edges before applying tail mode")
    parser.add_argument(
        "--tail-mode",
        choices=("prefix", "spread", "random"),
        default="prefix",
        help="How to choose cube edges after tail-start-depth",
    )
    parser.add_argument("--seed", type=int, default=20260521, help="Random seed for random tail mode")
    parser.add_argument("--jobs", type=int, default=0, help="Parallel workers; default uses all available cores")
    parser.add_argument("--batch-size", type=int, default=0, help="Cubes per solver batch; default keeps one batch per worker")
    parser.add_argument("--solver", default=None, help=solver_help(require_assumptions=True))
    parser.add_argument("--conflict-budget", type=int, default=0, help="Optional conflict budget per cube")
    parser.add_argument("--stop-on-sat", action="store_true", help="Return as soon as any cube is SAT")
    parser.add_argument("--sort-zero-edges", action="store_true", help="Sort colors incident to 00...0 in the first coloring")
    parser.add_argument("--zero-red-degree-at-most-half", action="store_true", help="Bound first-coloring red degree at 00...0")
    parser.add_argument("--partial-sym-break", type=int, default=0, help="First-coloring coordinate/bit-flip lex comparison cap")
    parser.add_argument("--log-file", help="Optional JSONL stage log path")
    return parser.parse_args()


def main():
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
