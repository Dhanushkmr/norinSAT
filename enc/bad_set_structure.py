"""Analyze the bad-set geometry of one bicross coloring.

This is a proof-discovery helper for the reduced bicross problem.  It can
analyze either the paired-coordinate sharpness construction or a SAT-produced
model, then prints the component, incidence, antipodal-pair, and slice
structure in the same format used by the extremal sampler.
"""

from __future__ import annotations

import argparse
from collections import defaultdict

from bicross_extremal_analysis import analyze_coloring, format_analysis, model_to_coloring
from bicross_frontier_construction import paired_coordinate_coloring
from bicross_probe import (
    RED,
    antipodal_vertex_representatives,
    component_data,
    encode_bad_count_bound,
    encode_pair_hit_bound,
    good_vertices,
    vertex_name,
)
from induction_probe import all_edges, anti
from sat_utils import best_pysat_solver_name, solver_help


def print_formula_header(args, mode, vpool, clauses):
    print(f"Dimension: Q_{args.m}")
    print(f"Source: {mode}")
    print(f"Top variable: {vpool.top}")
    print(f"Clauses: {len(clauses)}")
    print(f"Solver: {best_pysat_solver_name(args.solver) or 'pysat-default'}")
    if args.sort_zero_edges:
        print("Symmetry: incident colors at 00...0 sorted")
    if args.zero_red_degree_at_most_half:
        print("Symmetry: red degree at 00...0 at most half")
    if args.partial_sym_break:
        print(f"Symmetry: coordinate/flip lex comparisons up to {args.partial_sym_break}")


def solve_sat_bad_model(args):
    solver, vpool, r, _bad, clauses = encode_bad_count_bound(
        args.m,
        args.sat_bad_at_least,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
    )
    _vertices, _graph, edges = all_edges(args.m)
    print_formula_header(args, f"SAT bad >= {args.sat_bad_at_least}", vpool, clauses)
    result = solver.solve()
    print(f"SAT: {result}")
    if not result:
        solver.delete()
        return None
    coloring = model_to_coloring(solver.get_model(), edges, r)
    solver.delete()
    return coloring


def solve_sat_pair_hit_model(args):
    solver, vpool, r, _bad, _pair_hit, clauses = encode_pair_hit_bound(
        args.m,
        args.sat_pairs_hit_at_least,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
        forbid_cell_pairs=args.forbid_cell_pairs,
        complete_bad=args.complete_bad,
        forbid_perfect_inherited_splits=args.forbid_perfect_inherited_splits,
    )
    _vertices, _graph, edges = all_edges(args.m)
    print_formula_header(args, f"SAT pair-hit >= {args.sat_pairs_hit_at_least}", vpool, clauses)
    if args.forbid_cell_pairs:
        print("Restriction: no antipodal pair may share both red and blue components")
    if args.complete_bad or args.forbid_perfect_inherited_splits:
        print("Restriction: complete bad variables using SAT reachability meets")
    if args.forbid_perfect_inherited_splits:
        print("Restriction: every coordinate split must have a full/slice bad-set mismatch")
    result = solver.solve()
    print(f"SAT: {result}")
    if not result:
        solver.delete()
        return None
    coloring = model_to_coloring(solver.get_model(), edges, r)
    solver.delete()
    return coloring


def selected_coloring(args):
    if args.paired_construction:
        print(f"Dimension: Q_{args.m}")
        print("Source: paired-coordinate construction")
        return paired_coordinate_coloring(args.m)
    if args.sat_bad_at_least is not None:
        return solve_sat_bad_model(args)
    if args.sat_pairs_hit_at_least is not None:
        return solve_sat_pair_hit_model(args)
    raise ValueError("choose --paired-construction, --sat-bad-at-least, or --sat-pairs-hit-at-least")


def format_vertices(vertices):
    if not vertices:
        return "none"
    return ", ".join(vertex_name(vertex) for vertex in sorted(vertices))


def format_cell_details(coloring, m):
    vertices, _graph, _edges = all_edges(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]
    good = set(good_vertices(coloring, m))

    occupied_cells = defaultdict(list)
    for vertex in vertices:
        occupied_cells[(red[vertex], blue[vertex])].append(vertex)

    pair_cells = defaultdict(list)
    for start in antipodal_vertex_representatives(vertices):
        end = anti(start)
        cell = (red[start], blue[start])
        if cell == (red[end], blue[end]):
            pair_cells[cell].append((start, end))

    missing_targets = defaultdict(list)
    for vertex in vertices:
        if vertex not in good:
            missing_targets[(red[vertex], blue[anti(vertex)])].append(vertex)

    lines = ["Cell details:"]
    if pair_cells:
        lines.append("  antipodal-pair cells:")
        for cell, pairs in sorted(pair_cells.items(), key=lambda item: (-len(item[1]), item[0])):
            cell_vertices = sorted(occupied_cells[cell])
            good_in_cell = [vertex for vertex in cell_vertices if vertex in good]
            bad_in_cell = [vertex for vertex in cell_vertices if vertex not in good]
            pair_text = ", ".join(f"{vertex_name(start)}-{vertex_name(end)}" for start, end in pairs)
            lines.append(
                f"    cell={cell}; size={len(cell_vertices)}; pairs={len(pairs)}; "
                f"good={len(good_in_cell)}; bad={len(bad_in_cell)}"
            )
            lines.append(f"      pairs: {pair_text}")
            lines.append(f"      good vertices: {format_vertices(good_in_cell)}")
            if bad_in_cell:
                lines.append(f"      bad vertices: {format_vertices(bad_in_cell)}")
    else:
        lines.append("  antipodal-pair cells: none")

    lines.append("  missing target cells:")
    for cell, bad_starts in sorted(missing_targets.items(), key=lambda item: (-len(item[1]), item[0])):
        lines.append(
            f"    target={cell}; count={len(bad_starts)}; "
            f"occupied={cell in occupied_cells}: {format_vertices(bad_starts)}"
        )
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of the ordinary cube Q_m")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--paired-construction", action="store_true", help="Analyze the paired-coordinate construction")
    mode.add_argument("--sat-bad-at-least", type=int, help="Analyze one SAT model with at least K bad vertices")
    mode.add_argument("--sat-pairs-hit-at-least", type=int, help="Analyze one SAT model whose bad set hits at least K pairs")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--sort-zero-edges", action="store_true", help="Sort colors incident to 00...0")
    parser.add_argument(
        "--zero-red-degree-at-most-half",
        action="store_true",
        help="Use color-swap symmetry to bound red degree at 00...0",
    )
    parser.add_argument(
        "--partial-sym-break",
        type=int,
        default=0,
        help="Add coordinate/bit-flip lex symmetry breaking with this comparison cap",
    )
    parser.add_argument("--forbid-cell-pairs", action="store_true", help="Pair-hit SAT only: forbid cell antipodal pairs")
    parser.add_argument("--complete-bad", action="store_true", help="Pair-hit SAT only: complete bad variables")
    parser.add_argument(
        "--forbid-perfect-inherited-splits",
        action="store_true",
        help="Pair-hit SAT only: forbid perfect inherited splits",
    )
    parser.add_argument("--show-slices", action="store_true", help="Print per-coordinate slice summaries")
    parser.add_argument("--show-cell-details", action="store_true", help="Print antipodal-pair cells and missing target cells")
    parser.add_argument("--canonical", action="store_true", help="Compute a signed-coordinate canonical key")
    return parser.parse_args()


def main():
    args = parse_args()
    coloring = selected_coloring(args)
    if coloring is None:
        return
    analysis = analyze_coloring(coloring, args.m, canonical=args.canonical)
    print(format_analysis(1, analysis, show_slices=args.show_slices))
    if args.show_cell_details:
        print(format_cell_details(coloring, args.m))


if __name__ == "__main__":
    main()
