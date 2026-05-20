"""Group- and category-inspired structure probes for bicross colorings.

The main experimental target is the affine survivor question from
docs/GROUP_CATEGORY_DIRECTIONS.md:

    Does the set of bicross antipodal pairs contain an affine subspace of
    dimension floor((m - 1) / 2) in F_2^m / <omega>?

The quotient F_2^m / <omega> is represented by the map

    (x_0, ..., x_{m-1}) -> (x_0 + x_{m-1}, ..., x_{m-2} + x_{m-1}).

This identifies antipodal vertices and gives coordinates in F_2^(m-1).
"""

from __future__ import annotations

import argparse
import itertools
import math
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

from bicross_cube_search import batches_for_cubes, build_cubes, choose_cube_edges, parse_index_set, solve_cube_chunk
from bicross_frontier_construction import paired_coordinate_coloring, predicted_min_bicross
from bicross_probe import (
    all_bicross_pairs,
    antipodal_pair_profile,
    arbitrary_coloring_from_bits,
    coloring_blocking_clause,
    encode_pair_hit_bound,
    frontier_branch_summary,
    literal_is_true,
    random_edge_coloring,
)
from induction_probe import all_edges, anti, edge_key
from sat_utils import best_pysat_solver_name, effective_cpu_count, solver_help


def vertex_to_int(vertex):
    value = 0
    for index, bit in enumerate(vertex):
        if bit:
            value |= 1 << index
    return value


def int_to_vertex(value, m):
    return tuple((value >> index) & 1 for index in range(m))


def quotient_dimension(m):
    if m < 1:
        raise ValueError("Use m >= 1.")
    return m - 1


def quotient_point(vertex):
    """Map a vertex to F_2^m / <omega>, encoded as an integer."""
    if len(vertex) == 1:
        return 0
    last = vertex[-1]
    value = 0
    for index, bit in enumerate(vertex[:-1]):
        if bit ^ last:
            value |= 1 << index
    return value


def quotient_point_name(point, dimension):
    if dimension == 0:
        return "0"
    return format(point, f"0{dimension}b")[::-1]


def quotient_representative(point, m):
    return tuple((point >> index) & 1 for index in range(m - 1)) + (0,)


def bicross_quotient_set(coloring, m):
    return frozenset(quotient_point(witness.start) for witness in all_bicross_pairs(coloring, m))


def gf2_rank(rows):
    rows = [row for row in rows if row]
    rank = 0
    while rows:
        pivot = max(rows)
        bit = pivot.bit_length() - 1
        rank += 1
        next_rows = []
        for row in rows:
            if row == pivot:
                continue
            if (row >> bit) & 1:
                row ^= pivot
            if row:
                next_rows.append(row)
        rows = next_rows
    return rank


def span_from_basis(basis):
    values = {0}
    for vector in basis:
        values |= {value ^ vector for value in tuple(values)}
    return frozenset(values)


def iter_rref_bases(n, d):
    """Yield one reduced-row-echelon basis for each d-subspace of F_2^n."""
    if d < 0 or d > n:
        return
    if d == 0:
        yield ()
        return

    for pivots in itertools.combinations(range(n), d):
        choices = []
        for pivot in pivots:
            choices.append(tuple(col for col in range(pivot + 1, n) if col not in pivots))

        total_free = sum(len(cols) for cols in choices)
        for mask in range(1 << total_free):
            rows = []
            offset = 0
            for pivot, cols in zip(pivots, choices):
                row = 1 << pivot
                for col in cols:
                    if (mask >> offset) & 1:
                        row |= 1 << col
                    offset += 1
                rows.append(row)
            yield tuple(rows)


def iter_linear_subspaces(n, d):
    for basis in iter_rref_bases(n, d):
        yield span_from_basis(basis), basis


def iter_affine_subspaces(n, d):
    for linear, basis in iter_linear_subspaces(n, d):
        seen_cosets = set()
        for point in range(1 << n):
            coset = frozenset(point ^ value for value in linear)
            representative = min(coset)
            if representative in seen_cosets:
                continue
            seen_cosets.add(representative)
            yield coset, basis


def find_affine_subspace(points, n, d):
    """Return one affine d-subspace contained in points, or None."""
    points = frozenset(points)
    if d < 0 or d > n:
        return None
    if d == 0:
        if not points:
            return None
        point = min(points)
        return (point,), ()

    for linear, basis in iter_linear_subspaces(n, d):
        seen_cosets = set()
        for point in points:
            coset = frozenset(point ^ value for value in linear)
            representative = min(coset)
            if representative in seen_cosets:
                continue
            seen_cosets.add(representative)
            if coset <= points:
                return tuple(sorted(coset)), basis
    return None


def affine_span(points):
    points = tuple(sorted(points))
    if not points:
        return frozenset(), ()
    base = points[0]
    differences = [point ^ base for point in points[1:]]
    basis = row_basis(differences)
    span = frozenset(base ^ value for value in span_from_basis(basis))
    return span, basis


def row_basis(rows):
    basis_by_bit = {}
    for row in rows:
        value = row
        while value:
            bit = value.bit_length() - 1
            if bit not in basis_by_bit:
                basis_by_bit[bit] = value
                break
            value ^= basis_by_bit[bit]
    return tuple(basis_by_bit[bit] for bit in sorted(basis_by_bit, reverse=True))


def is_affine_subspace(points):
    points = frozenset(points)
    if not points:
        return False
    span, _basis = affine_span(points)
    return span == points


def edge_color_in_direction(coloring, m, vertex_int, dimension):
    u = int_to_vertex(vertex_int, m)
    v = int_to_vertex(vertex_int ^ (1 << dimension), m)
    return coloring[edge_key(u, v)]


def square_curvature_rows(coloring, m):
    rows = []
    for left, right in itertools.combinations(range(m), 2):
        row = 0
        for vertex_int in range(1 << m):
            value = (
                edge_color_in_direction(coloring, m, vertex_int, left)
                ^ edge_color_in_direction(coloring, m, vertex_int ^ (1 << right), left)
                ^ edge_color_in_direction(coloring, m, vertex_int, right)
                ^ edge_color_in_direction(coloring, m, vertex_int ^ (1 << left), right)
            )
            if value:
                row |= 1 << vertex_int
        rows.append(row)
    return tuple(rows)


def curvature_summary(coloring, m):
    rows = square_curvature_rows(coloring, m)
    weights = [row.bit_count() for row in rows]
    return {
        "rank": gf2_rank(rows),
        "nonzero": sum(1 for row in rows if row),
        "weight_histogram": dict(sorted(Counter(weights).items())),
    }


def affine_direction_summary(coloring, m):
    """Check whether each direction's edge color is affine-linear in position."""
    summaries = []
    for direction in range(m):
        other = [index for index in range(m) if index != direction]
        zero = tuple(0 for _ in range(m))
        constant = coloring[edge_key(zero, tuple(1 if i == direction else 0 for i in range(m)))]
        coefficients = {}
        for index in other:
            base = tuple(1 if i == index else 0 for i in range(m))
            flipped = tuple(1 if i in (index, direction) else 0 for i in range(m))
            coefficients[index] = coloring[edge_key(base, flipped)] ^ constant

        affine = True
        for bits in itertools.product((0, 1), repeat=len(other)):
            base = [0] * m
            for index, bit in zip(other, bits):
                base[index] = bit
            flipped = list(base)
            flipped[direction] = 1
            expected = constant
            for index, bit in zip(other, bits):
                if bit:
                    expected ^= coefficients[index]
            if coloring[edge_key(tuple(base), tuple(flipped))] != expected:
                affine = False
                break

        summaries.append(
            {
                "direction": direction,
                "affine": affine,
                "constant": constant,
                "coefficients": tuple(index for index in other if coefficients[index]),
            }
        )
    return {
        "affine_directions": sum(1 for item in summaries if item["affine"]),
        "all_directions_affine": all(item["affine"] for item in summaries),
        "directions": tuple(summaries),
    }


def analyze_coloring(coloring, m):
    qdim = quotient_dimension(m)
    target_dim = (m - 1) // 2
    bicross_points = bicross_quotient_set(coloring, m)
    affine_witness = find_affine_subspace(bicross_points, qdim, target_dim)
    span, span_basis = affine_span(bicross_points)
    profile = antipodal_pair_profile(coloring, m)
    if m >= 2:
        branch = frontier_branch_summary(coloring, m)
    else:
        branch = {"branch": "base", "cell_star": False, "perfect_inherited": False}
    return {
        "m": m,
        "quotient_dimension": qdim,
        "target_affine_dimension": target_dim,
        "bicross_pair_count": len(bicross_points),
        "predicted_min_bicross": predicted_min_bicross(m),
        "contains_target_affine": affine_witness is not None,
        "target_affine_witness": affine_witness,
        "bicross_set_is_affine": is_affine_subspace(bicross_points),
        "bicross_affine_span_size": len(span),
        "bicross_affine_span_rank": len(span_basis),
        "pair_profile": dict(profile),
        "frontier_branch": branch,
        "curvature": curvature_summary(coloring, m),
        "affine_directions": affine_direction_summary(coloring, m),
    }


def format_point_set(points, qdim):
    return "{" + ", ".join(quotient_point_name(point, qdim) for point in sorted(points)) + "}"


def format_analysis(analysis):
    branch = analysis["frontier_branch"]
    lines = [
        f"Dimension: Q_{analysis['m']}",
        f"Target affine dimension: {analysis['target_affine_dimension']} in quotient dimension {analysis['quotient_dimension']}",
        f"Bicross pairs: {analysis['bicross_pair_count']}",
        f"Predicted minimum: {analysis['predicted_min_bicross']}",
        f"Contains target affine subspace: {analysis['contains_target_affine']}",
        f"Bicross set is affine: {analysis['bicross_set_is_affine']}",
        f"Bicross affine span rank: {analysis['bicross_affine_span_rank']}",
        f"Bicross affine span size: {analysis['bicross_affine_span_size']}",
        (
            "Pair profile: "
            f"both_good={analysis['pair_profile'].get('both_good', 0)}, "
            f"one_good={analysis['pair_profile'].get('one_good', 0)}, "
            f"both_bad={analysis['pair_profile'].get('both_bad', 0)}"
        ),
        (
            "Frontier branch: "
            f"{branch['branch']} "
            f"(cell_star={branch['cell_star']}, perfect_inherited={branch['perfect_inherited']})"
        ),
        (
            "Curvature: "
            f"rank={analysis['curvature']['rank']}, "
            f"nonzero={analysis['curvature']['nonzero']}, "
            f"weights={analysis['curvature']['weight_histogram']}"
        ),
        (
            "Affine edge directions: "
            f"{analysis['affine_directions']['affine_directions']}/"
            f"{analysis['m']}"
        ),
    ]
    if analysis["target_affine_witness"] is not None:
        points, basis = analysis["target_affine_witness"]
        lines.append("Affine witness points: " + format_point_set(points, analysis["quotient_dimension"]))
        lines.append("Affine witness basis: " + format_point_set(basis, analysis["quotient_dimension"]))
    return "\n".join(lines)


def aggregate_analyses(analyses):
    counter = Counter()
    curvature_ranks = Counter()
    span_ranks = Counter()
    affine_direction_counts = Counter()
    branches = Counter()
    failures = []
    for index, analysis in enumerate(analyses, start=1):
        counter["checked"] += 1
        if analysis["contains_target_affine"]:
            counter["contains_target_affine"] += 1
        else:
            counter["affine_failures"] += 1
            failures.append(index)
        if analysis["bicross_set_is_affine"]:
            counter["bicross_set_is_affine"] += 1
        curvature_ranks[analysis["curvature"]["rank"]] += 1
        span_ranks[analysis["bicross_affine_span_rank"]] += 1
        affine_direction_counts[analysis["affine_directions"]["affine_directions"]] += 1
        branches[analysis["frontier_branch"]["branch"]] += 1

    return {
        "counts": counter,
        "curvature_ranks": curvature_ranks,
        "span_ranks": span_ranks,
        "affine_direction_counts": affine_direction_counts,
        "branches": branches,
        "failure_indexes": failures,
    }


def print_aggregate(summary):
    counts = summary["counts"]
    print(f"Colorings checked: {counts['checked']}")
    print(f"With target affine survivor: {counts['contains_target_affine']}")
    print(f"Affine survivor failures: {counts['affine_failures']}")
    print(f"Bicross set itself affine: {counts['bicross_set_is_affine']}")
    print("Bicross affine span rank distribution:")
    for rank, count in sorted(summary["span_ranks"].items()):
        print(f"  {rank}: {count}")
    print("Curvature rank distribution:")
    for rank, count in sorted(summary["curvature_ranks"].items()):
        print(f"  {rank}: {count}")
    print("Affine edge-direction count distribution:")
    for count_value, count in sorted(summary["affine_direction_counts"].items()):
        print(f"  {count_value}: {count}")
    print("Frontier branch distribution:")
    for branch, count in sorted(summary["branches"].items()):
        print(f"  {branch}: {count}")
    if summary["failure_indexes"]:
        print("Failure model indexes: " + ",".join(map(str, summary["failure_indexes"][:20])))


def iter_enumerated_colorings(m, max_edges):
    _vertices, _graph, edges = all_edges(m)
    if len(edges) > max_edges:
        raise SystemExit(f"Q_{m} has {len(edges)} edges; use --max-edges to raise the enumeration limit")
    for bits in itertools.product((0, 1), repeat=len(edges)):
        yield arbitrary_coloring_from_bits(edges, bits)


def iter_sampled_colorings(m, samples, seed):
    _vertices, _graph, edges = all_edges(m)
    rng = random.Random(seed)
    for _ in range(samples):
        yield random_edge_coloring(edges, rng)


def model_to_coloring(model, edges, r):
    model_set = set(model)
    return {edge: literal_is_true(model_set, r(*edge)) for edge in edges}


def iter_sat_frontier_colorings(args):
    solver, _vpool, r, _bad, _pair_hit, _clauses = encode_pair_hit_bound(
        args.m,
        args.hit_bound,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
        forbid_cell_pairs=args.forbid_cell_pairs,
        complete_bad=args.complete_bad,
        forbid_perfect_inherited_splits=args.forbid_perfect_inherited_splits,
    )
    _vertices, _graph, edges = all_edges(args.m)
    accepted = 0
    attempts = 0
    try:
        while accepted < args.models and attempts < args.postcheck_limit:
            if not solver.solve():
                break
            attempts += 1
            coloring = model_to_coloring(solver.get_model(), edges, r)
            profile = antipodal_pair_profile(coloring, args.m)
            pairs_hit = profile["one_good"] + profile["both_bad"]
            if args.exact_hit and pairs_hit != args.hit_bound:
                solver.add_clause(coloring_blocking_clause(coloring, r))
                continue
            accepted += 1
            yield coloring
            solver.add_clause(coloring_blocking_clause(coloring, r))
    finally:
        solver.delete()


def no_affine_survivor_clauses(m, bad):
    qdim = quotient_dimension(m)
    target_dim = (m - 1) // 2
    clauses = []
    for affine_points, _basis in iter_affine_subspaces(qdim, target_dim):
        clause = []
        for point in affine_points:
            vertex = quotient_representative(point, m)
            clause.append(bad(vertex))
            clause.append(bad(anti(vertex)))
        clauses.append(clause)
    return clauses


def solve_no_affine_survivor(args):
    solver, vpool, r, _bad, clauses = build_no_affine_survivor_formula(args)

    print(f"Dimension: Q_{args.m}", flush=True)
    print(f"Target affine dimension: {(args.m - 1) // 2}", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Solver: {best_pysat_solver_name(args.solver) or 'pysat-default'}", flush=True)

    result = solver.solve()
    print(f"SAT: {result}", flush=True)
    if result:
        _vertices, _graph, edges = all_edges(args.m)
        coloring = model_to_coloring(solver.get_model(), edges, r)
        print(format_analysis(analyze_coloring(coloring, args.m)))
    solver.delete()


def build_no_affine_survivor_formula(args):
    solver, vpool, r, bad, _pair_hit, clauses = encode_pair_hit_bound(
        args.m,
        0,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
        complete_bad=True,
    )
    extra_clauses = no_affine_survivor_clauses(args.m, bad)
    for clause in extra_clauses:
        solver.add_clause(clause)
    clauses.extend(extra_clauses)
    return solver, vpool, r, bad, clauses


def solve_no_affine_survivor_cubes(args):
    solver, vpool, r, _bad, clauses = build_no_affine_survivor_formula(args)
    solver.delete()

    _vertices, _graph, edges = all_edges(args.m)
    cube_edges = choose_cube_edges(edges, args.cube_depth, args.cube_mode, args.seed, offset=args.cube_offset)
    cube_literals = tuple(r(*edge) for edge in cube_edges)
    cubes = list(build_cubes(cube_literals))
    selected_indexes = parse_index_set(args.only_cube_indexes)
    indexed_cubes = list(enumerate(cubes))
    if selected_indexes is not None:
        indexed_cubes = [(index, cube) for index, cube in indexed_cubes if index in selected_indexes]

    jobs = max(1, min(args.jobs or effective_cpu_count(), len(indexed_cubes) or 1))
    batches = batches_for_cubes(indexed_cubes, jobs, args.batch_size)
    solver_name = best_pysat_solver_name(args.solver, require_assumptions=True)
    started = time.monotonic()

    print(f"Dimension: Q_{args.m}", flush=True)
    print(f"Target affine dimension: {(args.m - 1) // 2}", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Solver: {solver_name}", flush=True)
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
        coloring = model_to_coloring(first_sat["model"], edges, r)
        print(format_analysis(analyze_coloring(coloring, args.m)))
        return

    if totals["unknown"]:
        print("SAT: Unknown", flush=True)
    elif totals["unsat"] == len(indexed_cubes):
        print("SAT: False" if selected_indexes is None else "Selected cubes SAT: False", flush=True)
    else:
        print("SAT: Incomplete", flush=True)


def run(args):
    if args.sat_no_affine_survivor:
        solve_no_affine_survivor(args)
        return
    if args.sat_no_affine_cubes:
        solve_no_affine_survivor_cubes(args)
        return

    if args.paired_construction:
        colorings = [paired_coordinate_coloring(args.m)]
    elif args.enumerate:
        colorings = iter_enumerated_colorings(args.m, args.max_edges)
    elif args.samples:
        colorings = iter_sampled_colorings(args.m, args.samples, args.seed)
    elif args.sat_frontier:
        colorings = iter_sat_frontier_colorings(args)
    else:
        raise SystemExit("Choose one mode: --paired-construction, --enumerate, --samples, or --sat-frontier")

    analyses = []
    for index, coloring in enumerate(colorings, start=1):
        analysis = analyze_coloring(coloring, args.m)
        analyses.append(analysis)
        if args.show_first or not analysis["contains_target_affine"]:
            print(f"Model {index}")
            print(format_analysis(analysis))
        if not analysis["contains_target_affine"] and args.stop_on_failure:
            break

    print_aggregate(aggregate_analyses(analyses))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of ordinary cube Q_m")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--paired-construction", action="store_true", help="Analyze the paired-coordinate construction")
    mode.add_argument("--enumerate", action="store_true", help="Enumerate all edge colorings up to --max-edges")
    mode.add_argument("--samples", type=int, default=0, help="Analyze random edge colorings")
    mode.add_argument("--sat-frontier", action="store_true", help="Sample SAT models at a pair-hit frontier")
    mode.add_argument(
        "--sat-no-affine-survivor",
        action="store_true",
        help="SAT-search for a coloring with no target-dimensional affine survivor",
    )
    mode.add_argument(
        "--sat-no-affine-cubes",
        action="store_true",
        help="Cube-and-conquer SAT search for a coloring with no target-dimensional affine survivor",
    )
    parser.add_argument("--max-edges", type=int, default=24, help="Maximum edge variables to enumerate exactly")
    parser.add_argument("--seed", type=int, default=20260520, help="Random seed")
    parser.add_argument("--show-first", action="store_true", help="Print every analyzed model")
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop after the first affine-survivor failure")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--hit-bound", type=int, help="Pair-hit lower bound for --sat-frontier")
    parser.add_argument("--models", type=int, default=20, help="SAT models to sample in --sat-frontier mode")
    parser.add_argument("--postcheck-limit", type=int, default=1000, help="Maximum SAT models to inspect in --sat-frontier mode")
    parser.add_argument("--exact-hit", action="store_true", help="Only accept SAT models whose actual pair-hit count equals --hit-bound")
    parser.add_argument("--sort-zero-edges", action="store_true", help="SAT symmetry: sort colors incident to 00...0")
    parser.add_argument("--zero-red-degree-at-most-half", action="store_true", help="SAT symmetry: bound red degree at 00...0")
    parser.add_argument("--partial-sym-break", type=int, default=0, help="SAT symmetry lex comparison cap")
    parser.add_argument("--forbid-cell-pairs", action="store_true", help="SAT restriction: no same-cell antipodal pairs")
    parser.add_argument("--complete-bad", action="store_true", help="SAT restriction: complete bad variables")
    parser.add_argument(
        "--forbid-perfect-inherited-splits",
        action="store_true",
        help="SAT restriction: symbolic no-perfect-inherited-split pruning",
    )
    parser.add_argument("--cube-depth", type=int, default=6, help="Number of edge variables to cube on")
    parser.add_argument(
        "--cube-mode",
        choices=("prefix", "spread", "random", "window", "zero-pattern-tail"),
        default="prefix",
        help="How to choose edge variables for cubes",
    )
    parser.add_argument("--cube-offset", type=int, default=0, help="Start offset into edge list for prefix/window/random/spread")
    parser.add_argument("--jobs", type=int, default=0, help="Parallel workers for cube mode; default uses all available cores")
    parser.add_argument("--batch-size", type=int, default=0, help="Cubes per solver batch in cube mode")
    parser.add_argument("--conflict-budget", type=int, default=0, help="Optional conflict budget per cube")
    parser.add_argument("--only-cube-indexes", help="Comma-separated cube indexes/ranges to run after cube ordering")
    parser.add_argument("--stop-on-sat", action="store_true", help="Return as soon as any cube is SAT")
    args = parser.parse_args()
    if args.sat_frontier and args.hit_bound is None:
        parser.error("--sat-frontier requires --hit-bound")
    return args


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
