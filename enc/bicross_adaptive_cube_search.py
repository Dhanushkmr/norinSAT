"""Adaptive nested-prefix cube search for bicross pair-hit formulas.

This is a small proof-workflow wrapper around ``bicross_cube_search``.  It
solves a selected set of prefix cubes, records UNKNOWN cube indexes, then
descends only those UNKNOWN cubes to the next requested depth.

The cube indexing agrees with ``bicross_cube_search.build_cubes``: at depth
``d``, index ``i`` is the length-``d`` binary pattern for the first ``d`` edge
variables, with the last edge changing fastest.  Thus a depth-``d`` cube has
depth-``D`` descendants ``i * 2^(D-d)`` through
``(i + 1) * 2^(D-d) - 1``.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from bicross_cube_search import (
    batches_for_cubes,
    model_to_coloring,
    parse_index_set,
    print_sat_model_summary,
    solve_cube_chunk,
)
from bicross_probe import encode_pair_hit_bound
from induction_probe import all_edges
from sat_utils import best_pysat_solver_name, effective_cpu_count, solver_help


def parse_int_list(raw, name):
    values = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not values:
        raise SystemExit(f"{name} must contain at least one integer")
    return values


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


def cube_from_index(literals, depth, index):
    if index < 0 or index >= 2**depth:
        raise ValueError(f"cube index {index} out of range for depth {depth}")
    cube = []
    for offset, literal in enumerate(literals[:depth]):
        bit = (index >> (depth - offset - 1)) & 1
        cube.append(literal if bit else -literal)
    return tuple(cube)


def expand_indexes(indexes, old_depth, new_depth):
    if new_depth < old_depth:
        raise ValueError("new depth must be at least old depth")
    factor = 2 ** (new_depth - old_depth)
    expanded = []
    for index in sorted(set(indexes)):
        start = index * factor
        expanded.extend(range(start, start + factor))
    return expanded


def choose_ordered_cube_edges(edges, max_depth, tail_start_depth=0, tail_mode="prefix", seed=20260425):
    if max_depth < 0:
        raise ValueError("max depth must be nonnegative")
    if tail_start_depth < 0:
        raise ValueError("tail start depth must be nonnegative")
    if tail_start_depth > max_depth:
        raise ValueError("tail start depth cannot exceed max depth")
    if max_depth > len(edges):
        raise ValueError(f"max depth {max_depth} exceeds edge count {len(edges)}")

    prefix = list(edges[:tail_start_depth])
    tail_depth = max_depth - tail_start_depth
    candidates = list(edges[tail_start_depth:])

    if tail_depth == 0:
        return tuple(prefix)

    if tail_mode == "prefix":
        tail = candidates[:tail_depth]
    elif tail_mode == "spread":
        if tail_depth == 1:
            tail = [candidates[0]]
        else:
            tail = [candidates[round(i * (len(candidates) - 1) / (tail_depth - 1))] for i in range(tail_depth)]
    elif tail_mode == "random":
        rng = random.Random(seed)
        tail = rng.sample(candidates, tail_depth)
    else:
        raise ValueError(f"unknown tail mode: {tail_mode}")

    return tuple(prefix + tail)


def selected_at_first_depth(args, first_depth):
    if args.parent_depth is not None:
        parent_indexes = parse_index_set(args.parent_indexes)
        if parent_indexes is None:
            raise SystemExit("--parent-indexes is required when --parent-depth is set")
        if args.parent_depth >= first_depth:
            raise SystemExit("--parent-depth must be less than the first requested depth")
        return expand_indexes(parent_indexes, args.parent_depth, first_depth)

    selected = parse_index_set(args.only_cube_indexes)
    if selected is None:
        return range(2**first_depth)
    return sorted(selected)


def build_indexed_cubes(cube_literals, depth, indexes):
    return [(index, cube_from_index(cube_literals, depth, index)) for index in indexes]


def write_stage_log(path, payload):
    if path is None:
        return
    with path.open("a") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def solve_stage(args, clauses, cube_literals, depth, selected_indexes, edges, r, log_path):
    indexed_cubes = build_indexed_cubes(cube_literals, depth, selected_indexes)
    jobs = max(1, min(args.jobs or effective_cpu_count(), len(indexed_cubes) or 1))
    batches = batches_for_cubes(indexed_cubes, jobs, args.batch_size)
    solver_name = best_pysat_solver_name(args.solver)
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
            executor.submit(solve_cube_chunk, worker_id, clauses, batch, args.solver, args.conflict_budget)
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

    solver, vpool, r, _, _, clauses = encode_pair_hit_bound(
        args.m,
        args.hit_bound,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
        forbid_cell_pairs=args.forbid_cell_pairs,
    )
    solver.delete()

    _, _, edges = all_edges(args.m)
    tail_start_depth = args.tail_start_depth
    if tail_start_depth is None:
        tail_start_depth = args.parent_depth or 0
    cube_edges = choose_ordered_cube_edges(
        edges,
        max_depth,
        tail_start_depth=tail_start_depth,
        tail_mode=args.tail_mode,
        seed=args.seed,
    )
    cube_literals = tuple(r(*edge) for edge in cube_edges)
    selected_indexes = list(selected_at_first_depth(args, depths[0]))

    print(f"Dimension: Q_{args.m}", flush=True)
    print(f"Pair-hit lower bound: {args.hit_bound}", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    if args.forbid_cell_pairs:
        print("Restriction: no antipodal pair may share both red and blue components", flush=True)
    print(f"Depth schedule: {','.join(str(depth) for depth in depths)}", flush=True)
    print(f"Tail start depth: {tail_start_depth}", flush=True)
    print(f"Tail mode: {args.tail_mode}", flush=True)
    print("Cube edges: " + ", ".join(f"{u}-{v}" for u, v in cube_edges), flush=True)

    current_depth = depths[0]
    for depth in depths:
        if depth != current_depth:
            selected_indexes = expand_indexes(selected_indexes, current_depth, depth)
            current_depth = depth

        first_sat, unknown_indexes = solve_stage(args, clauses, cube_literals, depth, selected_indexes, edges, r, log_path)
        if first_sat is not None:
            return 0
        if not unknown_indexes:
            print("Selected cubes SAT: False", flush=True)
            return 0
        selected_indexes = unknown_indexes

    print("SAT: Unknown", flush=True)
    return 124


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of ordinary cube Q_m")
    parser.add_argument("--hit-bound", type=int, required=True, help="Pair-hit lower bound")
    parser.add_argument("--depths", required=True, help="Comma-separated nested prefix depths to run")
    parser.add_argument("--parent-depth", type=int, help="Depth of --parent-indexes to descend before first stage")
    parser.add_argument("--parent-indexes", help="Comma-separated parent cube indexes/ranges")
    parser.add_argument("--only-cube-indexes", help="Comma-separated cube indexes/ranges at the first requested depth")
    parser.add_argument("--tail-start-depth", type=int, help="Keep this many initial prefix edges before tail selection")
    parser.add_argument(
        "--tail-mode",
        choices=("prefix", "spread", "random"),
        default="prefix",
        help="How to choose split edges after --tail-start-depth",
    )
    parser.add_argument("--seed", type=int, default=20260425, help="Random seed for --tail-mode random")
    parser.add_argument("--jobs", type=int, default=0, help="Parallel workers; default uses all available cores")
    parser.add_argument("--batch-size", type=int, default=8, help="Cubes per solver batch")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--conflict-budget", type=int, default=0, help="Optional conflict budget per cube")
    parser.add_argument("--stop-on-sat", action="store_true", help="Return as soon as any cube is SAT")
    parser.add_argument("--log-file", help="Optional JSONL stage log path")
    parser.add_argument("--sort-zero-edges", action="store_true", help="Sort colors incident to 00...0")
    parser.add_argument("--zero-red-degree-at-most-half", action="store_true", help="Bound red degree at 00...0")
    parser.add_argument("--partial-sym-break", type=int, default=0, help="Coordinate/bit-flip lex comparison cap")
    parser.add_argument("--forbid-cell-pairs", action="store_true", help="Forbid antipodal pairs inside one red/blue incidence cell")
    return parser.parse_args()


def main():
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
