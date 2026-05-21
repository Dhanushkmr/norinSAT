"""Probe the two-color cross-bicross descent invariant.

For an ordinary red/blue edge-coloring C of Q_m, write

    G(C) = {x : R_C(x) intersects B_C(anti(x))}.

The quotient/descent proof attempt for the bicross lemma naturally asks for
the stronger two-color statement:

    For every pair of colorings C,D of Q_m,
    G(C) intersects anti(G(D)).

Equivalently, there should be no pair C,D whose bad sets cross-cover Q_m:

    Bad(C) union anti(Bad(D)) = Q_m.

This script supports exact tiny-cube bad-set enumeration and a SAT encoding of
the cross-cover negation.
"""

from __future__ import annotations

import argparse
import itertools
import time
from collections import Counter
from dataclasses import dataclass

from bicross_probe import (
    BLUE,
    RED,
    add_edge_coloring_symmetry_breaking,
    arbitrary_coloring_from_bits,
    bad_vertices,
    color_name,
    component_data,
    first_intersection_vertex,
    good_vertices,
    vertex_name,
)
from bicross_frontier_construction import paired_coordinate_coloring
from induction_probe import all_edges, anti, edge_key
from sat_utils import best_pysat_solver_name, make_pysat_solver, solver_help


@dataclass(frozen=True)
class CrossBicrossWitness:
    vertex: tuple[int, ...]
    c_meet: tuple[int, ...]
    d_meet: tuple[int, ...]


def model_to_coloring(model, edges, r):
    model_set = set(model)
    return {edge_key(u, v): r(u, v) in model_set for u, v in edges}


def cross_bicross_witness(coloring_c, coloring_d, m):
    """Return x with x in G(C) and anti(x) in G(D), or None."""
    vertices, _graph, _edges = all_edges(m)
    components_c = component_data(coloring_c, m)
    components_d = component_data(coloring_d, m)
    red_c = components_c[RED]
    blue_c = components_c[BLUE]
    red_d = components_d[RED]
    blue_d = components_d[BLUE]

    for vertex in vertices:
        antipode = anti(vertex)
        c_meet = first_intersection_vertex(
            vertices,
            red_c,
            red_c[vertex],
            blue_c,
            blue_c[antipode],
        )
        if c_meet is None:
            continue
        d_meet = first_intersection_vertex(
            vertices,
            red_d,
            red_d[antipode],
            blue_d,
            blue_d[vertex],
        )
        if d_meet is not None:
            return CrossBicrossWitness(vertex=vertex, c_meet=c_meet, d_meet=d_meet)

    return None


def distinct_bad_sets(m):
    """Enumerate all distinct bad sets realized by colorings of Q_m.

    This is intended only for tiny dimensions.  Q_3 has 12 edges and is still
    very cheap; Q_4 has 32 edges and should use SAT instead.
    """
    _vertices, _graph, edges = all_edges(m)
    if len(edges) > 20:
        raise ValueError(f"Refusing to enumerate 2^{len(edges)} colorings; use SAT for Q_{m}.")

    seen = {}
    for bits in itertools.product((0, 1), repeat=len(edges)):
        coloring = arbitrary_coloring_from_bits(edges, bits)
        bad = frozenset(bad_vertices(coloring, m))
        seen.setdefault(bad, 0)
        seen[bad] += 1
    return seen


def bad_sets_cross_cover(bad_c, bad_d, vertices):
    bad_c = set(bad_c)
    anti_bad_d = {anti(vertex) for vertex in bad_d}
    return bad_c | anti_bad_d == set(vertices)


def enumerate_badset_counterexample(m):
    vertices, _graph, _edges = all_edges(m)
    bad_sets = distinct_bad_sets(m)

    for bad_c in bad_sets:
        for bad_d in bad_sets:
            if bad_sets_cross_cover(bad_c, bad_d, vertices):
                return bad_c, bad_d, bad_sets

    return None, None, bad_sets


def encode_cross_cover_negation(
    m,
    solver_name=None,
    sort_zero_edges=False,
    zero_red_degree_at_most_half=False,
    partial_sym_break=0,
):
    try:
        from pysat.formula import IDPool
    except ModuleNotFoundError as exc:
        raise SystemExit(f"python-sat is required for --sat-negation: {exc}") from exc

    vertices, _graph, edges = all_edges(m)
    vpool = IDPool()

    def r(coloring_index, u, v):
        return vpool.id(("r", coloring_index, edge_key(u, v)))

    def reachable(coloring_index, target_color, root, vertex):
        return vpool.id(("p", coloring_index, target_color, root, vertex))

    def bad(coloring_index, vertex):
        return vpool.id(("bad", coloring_index, vertex))

    clauses = []

    for coloring_index in (0, 1):
        for target_color in (BLUE, RED):
            for root in vertices:
                clauses.append([reachable(coloring_index, target_color, root, root)])
                for u, v in edges:
                    edge_lit = r(coloring_index, u, v)
                    u_reachable = reachable(coloring_index, target_color, root, u)
                    v_reachable = reachable(coloring_index, target_color, root, v)
                    if target_color:
                        clauses.append([-u_reachable, -edge_lit, v_reachable])
                        clauses.append([-v_reachable, -edge_lit, u_reachable])
                    else:
                        clauses.append([-u_reachable, edge_lit, v_reachable])
                        clauses.append([-v_reachable, edge_lit, u_reachable])

        for start in vertices:
            end = anti(start)
            for intersection in vertices:
                clauses.append(
                    [
                        -bad(coloring_index, start),
                        -reachable(coloring_index, RED, start, intersection),
                        -reachable(coloring_index, BLUE, end, intersection),
                    ]
                )

    # Cross-cover negation of the two-color theorem:
    # for every x, either x notin G(C) or anti(x) notin G(D).
    for vertex in vertices:
        clauses.append([bad(0, vertex), bad(1, anti(vertex))])

    # Simultaneous cube automorphisms and simultaneous global color swap allow
    # us to normalize the first coloring.
    add_edge_coloring_symmetry_breaking(
        clauses,
        m,
        lambda u, v: r(0, u, v),
        vpool,
        sort_zero_edges=sort_zero_edges,
        zero_red_degree_at_most_half=zero_red_degree_at_most_half,
        partial_sym_break=partial_sym_break,
    )

    solver, _chosen = make_pysat_solver(solver_name)
    for clause in clauses:
        solver.add_clause(clause)

    return solver, vpool, r, bad, clauses


def paired_left_cross_target(m):
    """Target vertices that D would need bad to cross-cover paired C."""
    left = paired_coordinate_coloring(m)
    return frozenset(anti(vertex) for vertex in good_vertices(left, m))


def product_target(m, forbidden_blocks):
    """Vertices whose paired two-coordinate blocks avoid the given states."""
    vertices, _graph, _edges = all_edges(m)
    forbidden_blocks = tuple(tuple(block) for block in forbidden_blocks)
    if len(forbidden_blocks) != m // 2:
        raise ValueError(f"Expected {m // 2} forbidden blocks for Q_{m}, got {len(forbidden_blocks)}")
    for block in forbidden_blocks:
        if block not in ((0, 0), (0, 1), (1, 0), (1, 1)):
            raise ValueError(f"Invalid forbidden block: {block}")

    target = []
    for vertex in vertices:
        if all(vertex[2 * index : 2 * index + 2] != block for index, block in enumerate(forbidden_blocks)):
            target.append(vertex)
    return frozenset(target)


def iter_product_targets(m):
    states = ((0, 0), (0, 1), (1, 0), (1, 1))
    for forbidden_blocks in itertools.product(states, repeat=m // 2):
        yield forbidden_blocks, product_target(m, forbidden_blocks)


def encode_target_bad_subset(m, target_vertices, solver_name=None):
    try:
        from pysat.formula import IDPool
    except ModuleNotFoundError as exc:
        raise SystemExit(f"python-sat is required for target bad-set solving: {exc}") from exc

    vertices, _graph, edges = all_edges(m)
    target_vertices = frozenset(target_vertices)
    unknown = target_vertices - set(vertices)
    if unknown:
        raise ValueError(f"Target contains vertices outside Q_{m}: {sorted(unknown)}")

    vpool = IDPool()

    def r(u, v):
        return vpool.id(("r", edge_key(u, v)))

    def reachable(target_color, root, vertex):
        return vpool.id(("p", target_color, root, vertex))

    def bad(vertex):
        return vpool.id(("bad", vertex))

    clauses = []
    for target_color in (BLUE, RED):
        for root in vertices:
            clauses.append([reachable(target_color, root, root)])
            for u, v in edges:
                edge_lit = r(u, v)
                u_reachable = reachable(target_color, root, u)
                v_reachable = reachable(target_color, root, v)
                if target_color:
                    clauses.append([-u_reachable, -edge_lit, v_reachable])
                    clauses.append([-v_reachable, -edge_lit, u_reachable])
                else:
                    clauses.append([-u_reachable, edge_lit, v_reachable])
                    clauses.append([-v_reachable, edge_lit, u_reachable])

    for start in vertices:
        end = anti(start)
        for intersection in vertices:
            clauses.append(
                [
                    -bad(start),
                    -reachable(RED, start, intersection),
                    -reachable(BLUE, end, intersection),
                ]
            )

    for vertex in target_vertices:
        clauses.append([bad(vertex)])

    solver, _chosen = make_pysat_solver(solver_name)
    for clause in clauses:
        solver.add_clause(clause)

    return solver, vpool, r, bad, clauses


def format_vertices(vertices):
    if not vertices:
        return "none"
    return ", ".join(vertex_name(vertex) for vertex in sorted(vertices))


def run_enumeration(args):
    bad_c, bad_d, bad_sets = enumerate_badset_counterexample(args.m)
    print(f"Dimension: Q_{args.m}")
    print("Mode: exact distinct bad-set enumeration")
    print(f"Distinct bad sets: {len(bad_sets)}")
    print(f"Total colorings represented: {sum(bad_sets.values())}")
    if bad_c is None:
        print("Cross-cover counterexample: none")
        return
    print("Cross-cover counterexample: FOUND")
    print(f"Bad(C): {format_vertices(bad_c)}")
    print(f"Bad(D): {format_vertices(bad_d)}")


def run_sat(args):
    solver, vpool, r, _bad, clauses = encode_cross_cover_negation(
        args.m,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
    )
    vertices, _graph, edges = all_edges(args.m)
    print(f"Dimension: Q_{args.m}")
    print("Mode: SAT cross-cover negation")
    print(f"Top variable: {vpool.top}")
    print(f"Clauses: {len(clauses)}")
    print(f"Solver: {best_pysat_solver_name(args.solver) or 'pysat-default'}")
    if args.sort_zero_edges:
        print("Symmetry: first coloring has sorted zero-incident colors")
    if args.zero_red_degree_at_most_half:
        print("Symmetry: first coloring has zero red degree at most half")
    if args.partial_sym_break:
        print(f"Symmetry: first coloring lex comparisons up to {args.partial_sym_break}")

    if args.conflict_budget:
        solver.conf_budget(args.conflict_budget)
        result = solver.solve_limited()
    else:
        result = solver.solve()
    print(f"SAT: {result}")
    if result is not True:
        solver.delete()
        return

    model = solver.get_model()
    coloring_c = model_to_coloring(model, edges, lambda u, v: r(0, u, v))
    coloring_d = model_to_coloring(model, edges, lambda u, v: r(1, u, v))
    witness = cross_bicross_witness(coloring_c, coloring_d, args.m)
    bad_c = set(bad_vertices(coloring_c, args.m))
    bad_d = set(bad_vertices(coloring_d, args.m))
    print(f"Postcheck cross witness: {witness}")
    print(f"Postcheck cross-cover: {bad_sets_cross_cover(bad_c, bad_d, vertices)}")
    print(f"Bad sizes: C={len(bad_c)}, D={len(bad_d)}")
    print(f"Good sizes: C={len(good_vertices(coloring_c, args.m))}, D={len(good_vertices(coloring_d, args.m))}")
    if args.show_model:
        print(f"Bad(C): {format_vertices(bad_c)}")
        print(f"Bad(D): {format_vertices(bad_d)}")
        print("Coloring C:")
        for u, v in edges:
            print(f"  {vertex_name(u)}-{vertex_name(v)} {color_name(coloring_c[edge_key(u, v)])}")
        print("Coloring D:")
        for u, v in edges:
            print(f"  {vertex_name(u)}-{vertex_name(v)} {color_name(coloring_d[edge_key(u, v)])}")
    solver.delete()


def run_cover_paired_left(args):
    target = paired_left_cross_target(args.m)
    solver, vpool, r, _bad, clauses = encode_target_bad_subset(args.m, target, args.solver)
    vertices, _graph, edges = all_edges(args.m)
    print(f"Dimension: Q_{args.m}")
    print("Mode: fixed paired-left cross-cover target")
    print(f"Target vertices forced bad: {len(target)}")
    print(f"Top variable: {vpool.top}")
    print(f"Clauses: {len(clauses)}")
    print(f"Solver: {best_pysat_solver_name(args.solver) or 'pysat-default'}")

    if args.conflict_budget:
        solver.conf_budget(args.conflict_budget)
        result = solver.solve_limited()
    else:
        result = solver.solve()
    print(f"SAT: {result}")
    if result is not True:
        solver.delete()
        return

    model = solver.get_model()
    coloring = model_to_coloring(model, edges, r)
    actual_bad = set(bad_vertices(coloring, args.m))
    print(f"Postcheck target subset: {target <= actual_bad}")
    print(f"Bad size: {len(actual_bad)}")
    if args.show_model:
        print(f"Target: {format_vertices(target)}")
        print(f"Bad(D): {format_vertices(actual_bad)}")
    solver.delete()


def format_blocks(blocks):
    if not blocks:
        return "none"
    return ",".join("".join(map(str, block)) for block in blocks)


def run_cover_product_targets(args):
    counts = Counter()
    hard = []
    started = time.monotonic()
    total = 4 ** (args.m // 2)

    print(f"Dimension: Q_{args.m}")
    print("Mode: product bad-target sweep")
    print(f"Targets: {total}")
    if args.conflict_budget:
        print(f"Conflict budget per target: {args.conflict_budget}")

    for index, (forbidden_blocks, target) in enumerate(iter_product_targets(args.m), start=1):
        solver, _vpool, _r, _bad, _clauses = encode_target_bad_subset(args.m, target, args.solver)
        if args.conflict_budget:
            solver.conf_budget(args.conflict_budget)
            result = solver.solve_limited()
        else:
            result = solver.solve()
        solver.delete()

        if result is False:
            counts["unsat"] += 1
        elif result is True:
            counts["sat"] += 1
            hard.append(("SAT", forbidden_blocks))
            if args.stop_on_hard:
                break
        else:
            counts["unknown"] += 1
            hard.append(("UNKNOWN", forbidden_blocks))
            if args.stop_on_hard:
                break

        if args.report_every and (index % args.report_every == 0 or index == total):
            print(f"checked={index}/{total} counts={dict(counts)} elapsed={time.monotonic() - started:.2f}s", flush=True)

    print(f"Elapsed: {time.monotonic() - started:.2f}s")
    print(f"UNSAT targets: {counts['unsat']}")
    print(f"SAT targets: {counts['sat']}")
    print(f"UNKNOWN targets: {counts['unknown']}")
    if hard:
        formatted = [f"{status}:{format_blocks(blocks)}" for status, blocks in hard[: args.hard_limit]]
        print("Hard targets: " + "; ".join(formatted))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of ordinary cube Q_m")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--enumerate-badsets", action="store_true", help="Exact tiny-cube bad-set enumeration")
    mode.add_argument("--sat-negation", action="store_true", help="SAT solve the two-color cross-cover negation")
    mode.add_argument(
        "--cover-paired-left",
        action="store_true",
        help="Fix C to the paired-coordinate construction and ask whether some D cross-covers it",
    )
    mode.add_argument(
        "--cover-product-targets",
        action="store_true",
        help="Sweep all targets that avoid one state in each paired coordinate block",
    )
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--sort-zero-edges", action="store_true", help="Normalize first coloring zero-incident colors")
    parser.add_argument(
        "--zero-red-degree-at-most-half",
        action="store_true",
        help="Use simultaneous color swap to bound first coloring red degree at zero",
    )
    parser.add_argument(
        "--partial-sym-break",
        type=int,
        default=0,
        help="Add coordinate/bit-flip lex symmetry breaking for the first coloring",
    )
    parser.add_argument("--show-model", action="store_true", help="Print SAT model details if the negation is SAT")
    parser.add_argument(
        "--conflict-budget",
        type=int,
        default=0,
        help="Use solve_limited with this conflict budget; SAT output may be None for UNKNOWN",
    )
    parser.add_argument("--report-every", type=int, default=0, help="Product-target mode: progress report interval")
    parser.add_argument("--stop-on-hard", action="store_true", help="Product-target mode: stop on first SAT or UNKNOWN target")
    parser.add_argument("--hard-limit", type=int, default=20, help="Product-target mode: max SAT/UNKNOWN targets to print")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.enumerate_badsets:
        run_enumeration(args)
    elif args.sat_negation:
        run_sat(args)
    elif args.cover_paired_left:
        run_cover_paired_left(args)
    elif args.cover_product_targets:
        run_cover_product_targets(args)


if __name__ == "__main__":
    main()
