"""Analyze high pair-hit bicross colorings.

The reduced bicross problem is about ordinary red/blue edge-colorings of Q_m.
For a coloring, let G be the vertices x such that the red component of x
intersects the blue component of anti(x).  This script generates SAT models near
the pair-hit frontier and extracts component/incidence signatures that are more
useful for proof discovery than raw edge lists.
"""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter, defaultdict

from bicross_probe import (
    BLUE,
    RED,
    antipodal_pair_profile,
    antipodal_vertex_representatives,
    bad_vertices,
    color_name,
    component_data,
    component_sets,
    encode_pair_hit_bound,
    first_intersection_vertex,
    good_vertices,
    literal_is_true,
    slice_recursion_score,
    slice_summaries,
    vertex_name,
)
from induction_probe import all_edges, anti, canonical_coloring, edge_key
from sat_utils import best_pysat_solver_name, solver_help


def pair_hits_from_profile(profile):
    return profile["one_good"] + profile["both_bad"]


def model_to_coloring(model, edges, r):
    model_set = set(model)
    return {edge: literal_is_true(model_set, r(*edge)) for edge in edges}


def blocking_clause(coloring, r):
    clause = []
    for edge, color in coloring.items():
        lit = r(*edge)
        clause.append(-lit if color else lit)
    return clause


def hamming_weight(vertex):
    return sum(vertex)


def vertex_histogram(vertices):
    return dict(sorted(Counter(hamming_weight(vertex) for vertex in vertices).items()))


def parity_histogram(vertices):
    return dict(sorted(Counter(hamming_weight(vertex) % 2 for vertex in vertices).items()))


def component_size_signature(coloring, m):
    components = component_data(coloring, m)
    return {
        "red": sorted(len(component) for component in component_sets(components[RED])),
        "blue": sorted(len(component) for component in component_sets(components[BLUE])),
    }


def edge_boundary_profile(coloring, m, selected_vertices):
    selected = set(selected_vertices)
    _, _, edges = all_edges(m)
    profile = Counter()
    for u, v in edges:
        relation = "inside" if (u in selected) == (v in selected) else "cross"
        side = "selected" if u in selected and v in selected else "outside" if u not in selected and v not in selected else "boundary"
        profile[(relation, side, coloring[edge_key(u, v)])] += 1
    return dict(sorted((f"{relation}:{side}:{color_name(color)}", count) for (relation, side, color), count in profile.items()))


def all_bicross_pairs(coloring, m):
    vertices, _graph, _edges = all_edges(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]
    pairs = []

    for start in antipodal_vertex_representatives(vertices):
        end = anti(start)
        red_to_blue = first_intersection_vertex(vertices, red, red[start], blue, blue[end])
        blue_to_red = first_intersection_vertex(vertices, blue, blue[start], red, red[end])
        if red_to_blue is not None and blue_to_red is not None:
            pairs.append((start, end, red_to_blue, blue_to_red))

    return pairs


def component_incidence_analysis(coloring, m):
    vertices, _graph, _edges = all_edges(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]

    occupied = defaultdict(list)
    for vertex in vertices:
        occupied[(red[vertex], blue[vertex])].append(vertex)

    target_cells = Counter()
    missing_targets = Counter()
    good = set(good_vertices(coloring, m))

    for vertex in vertices:
        target = (red[vertex], blue[anti(vertex)])
        target_cells[target] += 1
        if vertex not in good:
            missing_targets[target] += 1

    occupied_sizes = sorted(len(values) for values in occupied.values())
    missing_multiplicities = sorted(missing_targets.values())
    repeated_missing = {cell: count for cell, count in missing_targets.items() if count > 1}

    return {
        "red_components": len(set(red.values())),
        "blue_components": len(set(blue.values())),
        "occupied_cells": len(occupied),
        "occupied_cell_sizes": occupied_sizes,
        "target_cells": len(target_cells),
        "missing_target_cells": len(missing_targets),
        "missing_target_multiplicities": missing_multiplicities,
        "repeated_missing_target_cells": dict(sorted(repeated_missing.items())),
    }


def cell_antipodal_pair_analysis(coloring, m):
    vertices, _graph, _edges = all_edges(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]
    cell_pair_counts = Counter()

    for start in antipodal_vertex_representatives(vertices):
        end = anti(start)
        start_cell = (red[start], blue[start])
        if start_cell == (red[end], blue[end]):
            cell_pair_counts[start_cell] += 1

    return {
        "pair_count": sum(cell_pair_counts.values()),
        "cells_with_pairs": len(cell_pair_counts),
        "cell_pair_multiplicities": sorted(cell_pair_counts.values()),
    }


def slice_signature(coloring, m):
    rows = []
    for summary in slice_summaries(coloring, m):
        rows.append(
            {
                "dimension": summary.dimension,
                "full_bad": (summary.full_bad_side0, summary.full_bad_side1),
                "slice_bad": (summary.slice_bad_side0, summary.slice_bad_side1),
                "recursion_score": slice_recursion_score(summary),
                "connectors": (summary.connector_red, summary.connector_blue),
                "identical_slices": summary.identical_slices,
                "uniform_connectors": summary.uniform_connectors,
                "pair_patterns": summary.antipodal_pair_patterns,
            }
        )
    return rows


def analyze_coloring(coloring, m, canonical=False):
    good = tuple(good_vertices(coloring, m))
    bad = tuple(bad_vertices(coloring, m))
    profile = antipodal_pair_profile(coloring, m)
    bicross_pairs = all_bicross_pairs(coloring, m)
    component_sizes = component_size_signature(coloring, m)
    incidence = component_incidence_analysis(coloring, m)
    cell_pairs = cell_antipodal_pair_analysis(coloring, m)
    slices = slice_signature(coloring, m)
    canonical_key = canonical_coloring(coloring, m) if canonical else None

    return {
        "pair_profile": dict(profile),
        "pairs_hit": pair_hits_from_profile(profile),
        "good_count": len(good),
        "bad_count": len(bad),
        "bicross_pair_count": len(bicross_pairs),
        "bicross_pairs": bicross_pairs,
        "bad_weight_histogram": vertex_histogram(bad),
        "good_weight_histogram": vertex_histogram(good),
        "bad_parity_histogram": parity_histogram(bad),
        "good_parity_histogram": parity_histogram(good),
        "component_sizes": component_sizes,
        "incidence": incidence,
        "cell_antipodal_pairs": cell_pairs,
        "bad_boundary_profile": edge_boundary_profile(coloring, m, bad),
        "slice_signature": slices,
        "canonical_key": canonical_key,
    }


def freeze(value):
    """Convert nested summaries into hashable values for aggregate counters."""
    if isinstance(value, dict):
        items = [(freeze(key), freeze(item_value)) for key, item_value in value.items()]
        return tuple(sorted(items, key=lambda item: repr(item[0])))
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return value


def bicross_shape(analysis):
    meet_vertices = []
    same_meet_count = 0
    pair_distance_histogram = Counter()

    for start, end, red_to_blue, blue_to_red in analysis["bicross_pairs"]:
        meet_vertices.extend((red_to_blue, blue_to_red))
        if red_to_blue == blue_to_red:
            same_meet_count += 1
        pair_distance_histogram[hamming_weight(tuple(a ^ b for a, b in zip(start, red_to_blue)))] += 1
        pair_distance_histogram[hamming_weight(tuple(a ^ b for a, b in zip(end, blue_to_red)))] += 1

    meet_counts = Counter(meet_vertices)
    return {
        "pair_count": analysis["bicross_pair_count"],
        "same_meet_count": same_meet_count,
        "distinct_meet_vertices": len(meet_counts),
        "meet_multiplicities": sorted(meet_counts.values()),
        "endpoint_to_meet_distance_histogram": dict(sorted(pair_distance_histogram.items())),
    }


def incidence_shape(analysis):
    incidence = analysis["incidence"]
    return {
        "red_components": incidence["red_components"],
        "blue_components": incidence["blue_components"],
        "occupied_cells": incidence["occupied_cells"],
        "occupied_cell_sizes": incidence["occupied_cell_sizes"],
        "target_cells": incidence["target_cells"],
        "missing_target_cells": incidence["missing_target_cells"],
        "missing_target_multiplicities": incidence["missing_target_multiplicities"],
    }


def inheritance_shape(analysis):
    scores = [row["recursion_score"] for row in analysis["slice_signature"]]
    perfect_splits = sum(1 for _overlap, extra_full, slice_only in scores if extra_full == 0 and slice_only == 0)
    no_slice_only_splits = sum(1 for _overlap, _extra_full, slice_only in scores if slice_only == 0)
    uniform_perfect_splits = sum(
        1
        for row in analysis["slice_signature"]
        if row["uniform_connectors"] and row["recursion_score"][1:] == (0, 0)
    )
    return {
        "perfect_splits": perfect_splits,
        "no_slice_only_splits": no_slice_only_splits,
        "uniform_perfect_splits": uniform_perfect_splits,
        "score_multiset": sorted(scores),
    }


def slice_shape(analysis):
    rows = []
    for row in analysis["slice_signature"]:
        rows.append(
            (
                tuple(sorted(row["full_bad"])),
                tuple(sorted(row["slice_bad"])),
                row["recursion_score"],
                row["connectors"],
                row["identical_slices"],
                row["uniform_connectors"],
                row["pair_patterns"],
            )
        )
    return tuple(sorted(rows))


def structural_signature(analysis):
    return {
        "pair_profile": analysis["pair_profile"],
        "bad_weight_histogram": analysis["bad_weight_histogram"],
        "good_weight_histogram": analysis["good_weight_histogram"],
        "bad_parity_histogram": analysis["bad_parity_histogram"],
        "component_sizes": analysis["component_sizes"],
        "incidence_shape": incidence_shape(analysis),
        "cell_antipodal_pairs": analysis["cell_antipodal_pairs"],
        "inheritance_shape": inheritance_shape(analysis),
        "bicross_shape": bicross_shape(analysis),
        "slice_shape": slice_shape(analysis),
    }


def update_aggregate_counts(analysis, aggregate_counts, structural_counts, representatives):
    sections = {
        "pair_profile": analysis["pair_profile"],
        "bad_weight_histogram": analysis["bad_weight_histogram"],
        "component_sizes": analysis["component_sizes"],
        "incidence_shape": incidence_shape(analysis),
        "cell_antipodal_pairs": analysis["cell_antipodal_pairs"],
        "inheritance_shape": inheritance_shape(analysis),
        "bicross_shape": bicross_shape(analysis),
        "slice_shape": slice_shape(analysis),
        "bad_boundary_profile": analysis["bad_boundary_profile"],
    }

    for name, value in sections.items():
        aggregate_counts[name][freeze(value)] += 1

    signature_key = freeze(structural_signature(analysis))
    structural_counts[signature_key] += 1
    representatives.setdefault(signature_key, analysis)


def format_pair(pair):
    start, end, red_to_blue, blue_to_red = pair
    return (
        f"{vertex_name(start)}-{vertex_name(end)} "
        f"(R/B meet {vertex_name(red_to_blue)}, B/R meet {vertex_name(blue_to_red)})"
    )


def format_analysis(index, analysis, show_slices=False):
    lines = [
        f"Model {index}: pairs_hit={analysis['pairs_hit']}; "
        f"bad={analysis['bad_count']}; good={analysis['good_count']}; "
        f"bicross_pairs={analysis['bicross_pair_count']}",
        "  pair_profile="
        + ", ".join(f"{key}={analysis['pair_profile'].get(key, 0)}" for key in ("both_good", "one_good", "both_bad")),
        f"  bad_weight_histogram={analysis['bad_weight_histogram']}",
        f"  good_weight_histogram={analysis['good_weight_histogram']}",
        f"  bad_parity_histogram={analysis['bad_parity_histogram']}",
        f"  component_sizes red={analysis['component_sizes']['red']} blue={analysis['component_sizes']['blue']}",
        f"  incidence={analysis['incidence']}",
        f"  cell_antipodal_pairs={analysis['cell_antipodal_pairs']}",
        f"  inheritance_shape={inheritance_shape(analysis)}",
        f"  bad_boundary_profile={analysis['bad_boundary_profile']}",
        "  bicross_pairs:",
    ]
    lines.extend(f"    {format_pair(pair)}" for pair in analysis["bicross_pairs"])
    if analysis["canonical_key"] is not None:
        lines.append(f"  canonical_key={analysis['canonical_key']}")
    if show_slices:
        lines.append("  slices:")
        for row in analysis["slice_signature"]:
            lines.append(f"    {row}")
    return "\n".join(lines)


def short_repr(value, width):
    text = repr(value)
    if len(text) <= width:
        return text
    return text[: width - 3] + "..."


def fingerprint(value):
    return hashlib.sha1(repr(value).encode("utf-8")).hexdigest()[:12]


def format_counter(title, counter, limit, width):
    lines = [f"  {title}: {len(counter)} distinct"]
    for index, (key, count) in enumerate(counter.most_common(limit), start=1):
        lines.append(f"    {index}. count={count} id={fingerprint(key)}: {short_repr(key, width)}")
    if len(counter) > limit:
        lines.append(f"    ... {len(counter) - limit} more")
    return "\n".join(lines)


def format_aggregate_summary(aggregate_counts, structural_counts, representatives, args):
    lines = [
        format_counter("structural_signatures", structural_counts, args.signature_limit, args.signature_width),
    ]

    for name in (
        "pair_profile",
        "bad_weight_histogram",
        "component_sizes",
        "incidence_shape",
        "cell_antipodal_pairs",
        "inheritance_shape",
        "bicross_shape",
        "slice_shape",
        "bad_boundary_profile",
    ):
        lines.append(format_counter(name, aggregate_counts[name], args.signature_limit, args.signature_width))

    if args.representatives:
        lines.append("  representatives:")
        for index, (signature_key, count) in enumerate(structural_counts.most_common(args.representatives), start=1):
            lines.append(f"    structural_signature {index}: count={count}")
            lines.append(format_analysis(index, representatives[signature_key], show_slices=args.show_slices))

    return "\n".join(lines)


def run(args):
    solver, _vpool, r, _bad, _pair_hit, _clauses = encode_pair_hit_bound(
        args.m,
        args.hit_bound,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
        forbid_cell_pairs=args.forbid_cell_pairs,
    )
    _vertices, _graph, edges = all_edges(args.m)

    print(f"Dimension: Q_{args.m}", flush=True)
    print(f"Pair-hit lower bound: {args.hit_bound}", flush=True)
    print(f"Solver: {best_pysat_solver_name(args.solver) or 'pysat-default'}", flush=True)
    if args.forbid_cell_pairs:
        print("Restriction: no antipodal pair may share both red and blue components", flush=True)
    print(f"Model limit: {args.models}", flush=True)

    analyses = []
    canonical_counts = Counter()
    aggregate_counts = defaultdict(Counter)
    structural_counts = Counter()
    representatives = {}
    raw_models_checked = 0
    solved = 0

    while solved < args.models and solver.solve():
        raw_models_checked += 1
        coloring = model_to_coloring(solver.get_model(), edges, r)
        analysis = analyze_coloring(coloring, args.m, canonical=args.canonical)
        if not args.exact_hit or analysis["pairs_hit"] == args.hit_bound:
            analyses.append(analysis)
            solved += 1
            update_aggregate_counts(analysis, aggregate_counts, structural_counts, representatives)
            if analysis["canonical_key"] is not None:
                canonical_counts[analysis["canonical_key"]] += 1
            if args.summary_only:
                if args.progress_every and solved % args.progress_every == 0:
                    print(f"  reported {solved} models...", flush=True)
            else:
                print(format_analysis(solved, analysis, show_slices=args.show_slices), flush=True)
        solver.add_clause(blocking_clause(coloring, r))

    print("Summary:", flush=True)
    print(f"  reported_models={len(analyses)}", flush=True)
    print(f"  raw_models_checked={raw_models_checked}", flush=True)
    print(f"  canonical_orbits={len(canonical_counts) if args.canonical else 'not-computed'}", flush=True)
    if args.canonical:
        for orbit_index, (_key, count) in enumerate(canonical_counts.most_common(), start=1):
            print(f"  orbit {orbit_index}: models={count}", flush=True)
    if analyses:
        print(format_aggregate_summary(aggregate_counts, structural_counts, representatives, args), flush=True)

    solver.delete()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of ordinary cube Q_m")
    parser.add_argument("--hit-bound", type=int, required=True, help="Pair-hit lower bound")
    parser.add_argument("--models", type=int, default=1, help="Number of SAT models to analyze")
    parser.add_argument("--exact-hit", action="store_true", help="Only report models whose actual pair-hit count equals bound")
    parser.add_argument("--canonical", action="store_true", help="Compute cube-automorphism/global-color canonical keys")
    parser.add_argument("--show-slices", action="store_true", help="Print coordinate-slice summaries")
    parser.add_argument("--summary-only", action="store_true", help="Print aggregate signatures instead of every model")
    parser.add_argument("--signature-limit", type=int, default=6, help="Rows to show per aggregate signature table")
    parser.add_argument("--signature-width", type=int, default=240, help="Maximum characters per aggregate signature row")
    parser.add_argument("--representatives", type=int, default=0, help="Print representative models for the top structural signatures")
    parser.add_argument("--progress-every", type=int, default=10, help="Progress interval for --summary-only; 0 disables")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--sort-zero-edges", action="store_true", help="Sort colors incident to 00...0")
    parser.add_argument("--zero-red-degree-at-most-half", action="store_true", help="Bound red degree at 00...0")
    parser.add_argument("--partial-sym-break", type=int, default=0, help="Coordinate/bit-flip lex comparison cap")
    parser.add_argument("--forbid-cell-pairs", action="store_true", help="Forbid antipodal pairs inside one red/blue incidence cell")
    return parser.parse_args()


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
