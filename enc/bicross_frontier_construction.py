"""Sharp candidate constructions for the quantitative bicross frontier.

The paired-coordinate construction colors Q_m by grouping coordinates into
blocks (0,1), (2,3), ... .  In each two-coordinate block, an edge is colored by
the value of the other coordinate in that block:

    color(edge in coordinate 2j)     = vertex[2j + 1]
    color(edge in coordinate 2j + 1) = vertex[2j]

If m is odd, the final unpaired coordinate edges are colored blue.

For this construction, a vertex is good iff no paired block is 00.  Hence an
antipodal pair is bicross iff every paired block is 01 or 10.  This realizes
the conjectural sharp value 2^floor((m - 1) / 2) bicross pairs.
"""

from __future__ import annotations

import argparse
from collections import Counter

from bicross_probe import (
    BLUE,
    RED,
    antipodal_pair_profile,
    bad_vertices,
    color_name,
    component_data,
    good_vertices,
    vertex_name,
)
from induction_probe import all_edges, anti, edge_key, summarize_coloring


def predicted_min_bicross(m):
    if m < 1:
        raise ValueError("Use m >= 1.")
    return 2 ** ((m - 1) // 2)


def predicted_max_hit(m):
    return 2 ** (m - 1) - predicted_min_bicross(m)


def paired_coordinate_coloring(m):
    if m < 1:
        raise ValueError("Use m >= 1.")

    _, _, edges = all_edges(m)
    coloring = {}
    for u, v in edges:
        dimension = next(index for index, (a, b) in enumerate(zip(u, v)) if a != b)
        base = u if u[dimension] == 0 else v
        if dimension % 2 == 0:
            color = BLUE if dimension + 1 == m else bool(base[dimension + 1])
        else:
            color = bool(base[dimension - 1])
        coloring[edge_key(u, v)] = color
    return coloring


def paired_blocks(vertex):
    return tuple(vertex[index : index + 2] for index in range(0, len(vertex) - 1, 2))


def has_zero_block(vertex):
    return any(block == (0, 0) for block in paired_blocks(vertex))


def predicted_good_vertices(m):
    vertices, _, _ = all_edges(m)
    return tuple(vertex for vertex in vertices if not has_zero_block(vertex))


def predicted_pair_profile(m):
    paired_blocks_count = m // 2
    good_count = (2 if m % 2 else 1) * (3**paired_blocks_count)
    both_good = predicted_min_bicross(m)
    one_good = good_count - 2 * both_good
    both_bad = 2 ** (m - 1) - both_good - one_good
    return Counter({"both_good": both_good, "one_good": one_good, "both_bad": both_bad})


def profile_tuple(profile):
    return tuple(profile[key] for key in ("both_good", "one_good", "both_bad"))


def validate_paired_construction(m):
    coloring = paired_coordinate_coloring(m)
    actual_good = tuple(good_vertices(coloring, m))
    expected_good = predicted_good_vertices(m)
    actual_profile = antipodal_pair_profile(coloring, m)
    expected_profile = predicted_pair_profile(m)
    return {
        "good_matches": set(actual_good) == set(expected_good),
        "actual_good": len(actual_good),
        "expected_good": len(expected_good),
        "actual_profile": actual_profile,
        "expected_profile": expected_profile,
        "bicross_pairs": actual_profile["both_good"],
        "predicted_bicross_pairs": predicted_min_bicross(m),
        "hit_pairs": actual_profile["one_good"] + actual_profile["both_bad"],
        "predicted_hit_pairs": predicted_max_hit(m),
    }


def format_profile(profile):
    return ", ".join(f"{key}={profile[key]}" for key in ("both_good", "one_good", "both_bad"))


def format_block(vertex):
    parts = ["".join(map(str, block)) for block in paired_blocks(vertex)]
    if len(vertex) % 2:
        parts.append(str(vertex[-1]))
    return ".".join(parts)


def print_component_summary(coloring, m):
    components = component_data(coloring, m)
    for color in (BLUE, RED):
        sizes = sorted(Counter(components[color].values()).values())
        print(f"{color_name(color)} component sizes: {sizes}")


def run(args):
    coloring = paired_coordinate_coloring(args.m)
    validation = validate_paired_construction(args.m)
    profile = validation["actual_profile"]
    bad = bad_vertices(coloring, args.m)
    good = good_vertices(coloring, args.m)

    print(f"Dimension: Q_{args.m}")
    print("Construction: paired-coordinate")
    print(f"Good-set rule verified: {validation['good_matches']}")
    print(f"Good vertices: {len(good)}")
    print(f"Bad vertices: {len(bad)}")
    print(f"Pair profile: {format_profile(profile)}")
    print(f"Bicross pairs: {validation['bicross_pairs']}")
    print(f"Predicted bicross pairs: {validation['predicted_bicross_pairs']}")
    print(f"Hit pairs: {validation['hit_pairs']}")
    print(f"Predicted max-hit pairs: {validation['predicted_hit_pairs']}")

    if args.show_vertices:
        print("Bad vertices: " + ", ".join(format_block(vertex) for vertex in bad))
        bicross_reps = [
            vertex
            for vertex in good
            if vertex <= anti(vertex) and anti(vertex) in set(good)
        ]
        print(
            "Bicross pair representatives: "
            + ", ".join(f"{format_block(vertex)}-{format_block(anti(vertex))}" for vertex in bicross_reps)
        )
    if args.show_components:
        print_component_summary(coloring, args.m)
    if args.show_coloring:
        print(summarize_coloring(coloring))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of ordinary cube Q_m")
    parser.add_argument("--show-vertices", action="store_true", help="Print bad vertices and bicross pairs")
    parser.add_argument("--show-components", action="store_true", help="Print red/blue component size summaries")
    parser.add_argument("--show-coloring", action="store_true", help="Print the edge coloring")
    return parser.parse_args()


def main():
    run(parse_args())


if __name__ == "__main__":
    main()
