"""Parallel cube-split SAT search for bicross pair-hit formulas.

This is an experimental helper for hard pair-hit frontiers.  It builds the
same encoding as ``bicross_probe.py --sat-pairs-hit-at-least`` and then splits
the search by assumptions on selected edge-color variables.
"""

from __future__ import annotations

import argparse
import itertools
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

from bicross_probe import (
    antipodal_pair_profile,
    bad_vertices,
    bad_vertices_hit_every_antipodal_pair,
    bicross_witness,
    cell_antipodal_pairs,
    encode_pair_hit_bound,
    format_dimension_list,
    format_frontier_branch_summary,
    frontier_branch_summary,
    literal_is_true,
    perfect_inherited_splits,
)
from induction_probe import all_edges
from sat_utils import best_pysat_solver_name, effective_cpu_count, make_pysat_solver, solver_help


def choose_cube_edges(edges, depth, mode, seed, offset=0):
    if depth < 0:
        raise ValueError("--cube-depth must be nonnegative")
    if offset < 0:
        raise ValueError("--cube-offset must be nonnegative")
    if offset + depth > len(edges):
        raise ValueError(f"cube offset {offset} plus depth {depth} exceeds edge count {len(edges)}")

    if mode == "prefix":
        return tuple(edges[offset : offset + depth])

    if mode == "random":
        rng = random.Random(seed)
        return tuple(rng.sample(edges[offset:], depth))

    if mode == "spread":
        if depth == 0:
            return ()
        if depth == 1:
            return (edges[offset],)
        window = edges[offset:]
        indexes = [round(i * (len(window) - 1) / (depth - 1)) for i in range(depth)]
        return tuple(window[i] for i in indexes)

    if mode == "window":
        return tuple(edges[offset : offset + depth])

    if mode == "zero-pattern-tail":
        dimension = len(edges[0][0]) if edges else 0
        zero_pattern_edges = edges[:dimension]
        tail_depth = depth - len(zero_pattern_edges)
        if tail_depth <= 0:
            return tuple(zero_pattern_edges[:depth])
        tail_start = max(offset, len(zero_pattern_edges))
        if tail_start + tail_depth > len(edges):
            raise ValueError(f"not enough tail edges from offset {tail_start} for cube depth {depth}")
        return tuple(zero_pattern_edges + edges[tail_start : tail_start + tail_depth])

    raise ValueError(f"unknown cube selection mode: {mode}")


def build_cubes(literals):
    for bits in itertools.product((False, True), repeat=len(literals)):
        yield tuple(lit if bit else -lit for lit, bit in zip(literals, bits))


def chunked(items, chunks):
    buckets = [[] for _ in range(chunks)]
    for index, item in enumerate(items):
        buckets[index % chunks].append((index, item))
    return [bucket for bucket in buckets if bucket]


def batches_for_cubes(indexed, jobs, batch_size):
    if batch_size:
        return [indexed[start : start + batch_size] for start in range(0, len(indexed), batch_size)]
    buckets = [[] for _ in range(jobs)]
    for offset, item in enumerate(indexed):
        buckets[offset % jobs].append(item)
    return [bucket for bucket in buckets if bucket]


def model_to_coloring_from_edge_literals(model, edge_literals):
    model_set = set(model)
    return {edge: literal_is_true(model_set, literal) for edge, literal in edge_literals}


def solve_cube_chunk(
    worker_id,
    clauses,
    cubes,
    solver_name,
    conflict_budget,
    edge_literals=None,
    m=None,
    forbid_perfect_inherited_splits=False,
    forbid_frontier_branches=False,
    postcheck_limit_per_cube=0,
):
    solver, actual_solver = make_pysat_solver(solver_name, require_assumptions=True)
    for clause in clauses:
        solver.add_clause(clause)

    counts = Counter()
    first_sat = None
    unknown_indexes = []
    postcheck_rejections = 0
    started = time.monotonic()

    for cube_index, cube in cubes:
        rejected_for_cube = 0
        while True:
            if conflict_budget:
                solver.conf_budget(conflict_budget)
                result = solver.solve_limited(assumptions=list(cube))
            else:
                result = solver.solve(assumptions=list(cube))

            if result is True:
                model = solver.get_model()
                if forbid_perfect_inherited_splits or forbid_frontier_branches:
                    coloring = model_to_coloring_from_edge_literals(model, edge_literals)
                    if forbid_frontier_branches:
                        branch_summary = frontier_branch_summary(coloring, m)
                        reject_model = branch_summary["branch"] != "neither"
                    else:
                        reject_model = bool(perfect_inherited_splits(coloring, m))
                    if reject_model:
                        postcheck_rejections += 1
                        rejected_for_cube += 1
                        if postcheck_limit_per_cube and rejected_for_cube >= postcheck_limit_per_cube:
                            counts["unknown"] += 1
                            unknown_indexes.append(cube_index)
                            break
                        solver.add_clause([(-literal if coloring[edge] else literal) for edge, literal in edge_literals])
                        continue

                counts["sat"] += 1
                first_sat = {
                    "cube_index": cube_index,
                    "cube": cube,
                    "model": model,
                }
                break
            if result is False:
                counts["unsat"] += 1
            else:
                counts["unknown"] += 1
                unknown_indexes.append(cube_index)
            break

        if first_sat is not None:
            break

    solver.delete()
    return {
        "worker_id": worker_id,
        "solver": actual_solver,
        "counts": dict(counts),
        "first_sat": first_sat,
        "unknown_indexes": unknown_indexes,
        "postcheck_rejections": postcheck_rejections,
        "elapsed": time.monotonic() - started,
    }


def model_to_coloring(model, edges, r):
    model_set = set(model)
    return {edge: literal_is_true(model_set, r(*edge)) for edge in edges}


def print_sat_model_summary(args, model, edges, r):
    coloring = model_to_coloring(model, edges, r)
    actual_bad = bad_vertices(coloring, args.m)
    profile = antipodal_pair_profile(coloring, args.m)
    print(f"Actual bad vertices: {len(actual_bad)}", flush=True)
    print(f"Actual good vertices: {2 ** args.m - len(actual_bad)}", flush=True)
    print(
        "Antipodal pair profile: "
        f"both_good={profile['both_good']}, "
        f"one_good={profile['one_good']}, "
        f"both_bad={profile['both_bad']}",
        flush=True,
    )
    print(f"Bad vertices hit every antipodal pair: {bad_vertices_hit_every_antipodal_pair(coloring, args.m)}", flush=True)
    print(f"Cell antipodal pairs: {len(cell_antipodal_pairs(coloring, args.m))}", flush=True)
    print(f"Perfect inherited splits: {format_dimension_list(perfect_inherited_splits(coloring, args.m))}", flush=True)
    print(f"Frontier branch: {format_frontier_branch_summary(frontier_branch_summary(coloring, args.m))}", flush=True)
    print(f"Bicross witness: {bicross_witness(coloring, args.m)}", flush=True)


def run(args):
    solver, vpool, r, _, _, clauses = encode_pair_hit_bound(
        args.m,
        args.hit_bound,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
        forbid_cell_pairs=args.forbid_cell_pairs,
        complete_bad=args.complete_bad,
        forbid_perfect_inherited_splits=args.forbid_perfect_inherited_splits or args.forbid_frontier_branches,
    )
    solver.delete()

    _, _, edges = all_edges(args.m)
    cube_edges = choose_cube_edges(edges, args.cube_depth, args.cube_mode, args.seed, offset=args.cube_offset)
    cube_literals = tuple(r(*edge) for edge in cube_edges)
    edge_literals = tuple((edge, r(*edge)) for edge in edges)
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
    print(f"Pair-hit lower bound: {args.hit_bound}", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Solver: {solver_name}", flush=True)
    if args.forbid_cell_pairs:
        print("Restriction: no antipodal pair may share both red and blue components", flush=True)
    if args.complete_bad or args.forbid_perfect_inherited_splits or args.forbid_frontier_branches:
        print("Restriction: complete bad variables using SAT reachability meets", flush=True)
    if args.forbid_perfect_inherited_splits:
        print("Restriction: reject concrete models with perfect inherited splits", flush=True)
    if args.forbid_frontier_branches:
        print("Restriction: reject concrete models unless branch=neither", flush=True)
    print(f"Workers: {jobs} (available cores: {effective_cpu_count()})", flush=True)
    print(f"Cube depth: {args.cube_depth}", flush=True)
    print(f"Cubes selected: {len(indexed_cubes)}/{len(cubes)}", flush=True)
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
                edge_literals,
                args.m,
                args.forbid_perfect_inherited_splits,
                args.forbid_frontier_branches,
                args.postcheck_limit_per_cube,
            )
            for worker_id, batch in enumerate(batches)
        ]
        for future in as_completed(futures):
            result = future.result()
            totals.update(result["counts"])
            unknown_indexes.extend(result["unknown_indexes"])
            print(
                f"batch={result['worker_id']} solver={result['solver']} "
                f"counts={result['counts']} postcheck_rejections={result['postcheck_rejections']} "
                f"elapsed={result['elapsed']:.2f}s",
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
    print(f"Elapsed: {elapsed:.2f}s", flush=True)
    print(f"Selected cubes solved: {solved}/{len(indexed_cubes)}", flush=True)
    print(f"Total cube space: {len(cubes)}", flush=True)
    print(f"SAT cubes: {totals['sat']}", flush=True)
    print(f"UNSAT cubes: {totals['unsat']}", flush=True)
    print(f"UNKNOWN cubes: {totals['unknown']}", flush=True)
    if unknown_indexes:
        print("UNKNOWN cube indexes: " + ",".join(str(index) for index in sorted(unknown_indexes)), flush=True)

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


def parse_index_set(raw):
    if not raw:
        return None
    indexes = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            indexes.update(range(int(start), int(end) + 1))
        else:
            indexes.add(int(part))
    return indexes


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of ordinary cube Q_m")
    parser.add_argument("--hit-bound", type=int, required=True, help="Pair-hit lower bound")
    parser.add_argument("--cube-depth", type=int, default=8, help="Number of edge variables to cube on")
    parser.add_argument(
        "--cube-mode",
        choices=("prefix", "spread", "random", "window", "zero-pattern-tail"),
        default="spread",
        help="How to choose edge variables for cubes",
    )
    parser.add_argument("--cube-offset", type=int, default=0, help="Start offset into edge list for prefix/window/random/spread")
    parser.add_argument("--seed", type=int, default=20260425, help="Random seed for cube selection/shuffle")
    parser.add_argument("--jobs", type=int, default=0, help="Parallel workers; default uses all available cores")
    parser.add_argument("--batch-size", type=int, default=0, help="Cubes per solver batch; default keeps one batch per worker")
    parser.add_argument("--solver", default=None, help=solver_help(require_assumptions=True))
    parser.add_argument("--conflict-budget", type=int, default=0, help="Optional conflict budget per cube")
    parser.add_argument("--shuffle-cubes", action="store_true", help="Shuffle cube order before assigning workers")
    parser.add_argument("--only-cube-indexes", help="Comma-separated cube indexes/ranges to run after cube ordering")
    parser.add_argument("--stop-on-sat", action="store_true", help="Return as soon as any cube is SAT")
    parser.add_argument("--sort-zero-edges", action="store_true", help="Sort colors incident to 00...0")
    parser.add_argument("--zero-red-degree-at-most-half", action="store_true", help="Bound red degree at 00...0")
    parser.add_argument("--partial-sym-break", type=int, default=0, help="Coordinate/bit-flip lex comparison cap")
    parser.add_argument("--forbid-cell-pairs", action="store_true", help="Forbid antipodal pairs inside one red/blue incidence cell")
    parser.add_argument(
        "--complete-bad",
        action="store_true",
        help="Complete bad variables using SAT reachability meets before cubing",
    )
    parser.add_argument(
        "--forbid-perfect-inherited-splits",
        action="store_true",
        help="Reject concrete SAT cube models with a perfect inherited split; implies --complete-bad in the encoder",
    )
    parser.add_argument(
        "--forbid-frontier-branches",
        action="store_true",
        help="Reject concrete SAT cube models unless branch=neither; implies symbolic no-perfect-split pruning",
    )
    parser.add_argument(
        "--postcheck-limit-per-cube",
        type=int,
        default=1,
        help="Maximum rejected SAT models to block inside one cube before marking it UNKNOWN; 0 means no limit",
    )
    return parser.parse_args()


def main():
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
