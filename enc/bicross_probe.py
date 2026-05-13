"""
Probe the reduced bicross component lemma for ordinary cube edge-colorings.

The bicross lemma is the current clean proof target behind the one-connector
lemma.  It no longer uses antipodal edge-colorings of Q_n.  Instead it says:

    In every red/blue edge-coloring of Q_m, some antipodal pair x, anti(x)
    satisfies both

        C_red(x)  intersects C_blue(anti(x))
        C_blue(x) intersects C_red(anti(x)).

Here C_color(v) is the monochromatic component of v in the ordinary Q_m.
If this lemma holds for Q_{n-1}, it implies the fixed-slice lemma and then the
one-connector lemma for Q_n.
"""

import argparse
import itertools
import random
from collections import Counter, deque
from dataclasses import dataclass

from induction_probe import all_edges, anti, build_hypercube_graph, color_components, edge_key, summarize_coloring
from lex import lex_smaller_eq
from sat_utils import best_pysat_solver_name, make_pysat_solver, solver_help


BLUE = False
RED = True


@dataclass(frozen=True)
class BicrossWitness:
    start: tuple[int, ...]
    end: tuple[int, ...]
    red_to_blue_intersection: tuple[int, ...]
    blue_to_red_intersection: tuple[int, ...]


@dataclass(frozen=True)
class FixedSliceWitness:
    connector_vertex: tuple[int, ...]
    connector_color: bool
    intersection_vertex: tuple[int, ...]
    connector_color_path: tuple[tuple[int, ...], ...] | None = None
    opposite_color_path: tuple[tuple[int, ...], ...] | None = None


@dataclass(frozen=True)
class SliceSummary:
    dimension: int
    full_bad_side0: int
    full_bad_side1: int
    slice_bad_side0: int
    slice_bad_side1: int
    full_vs_slice_side0: tuple[tuple[int, int, int], ...]
    full_vs_slice_side1: tuple[tuple[int, int, int], ...]
    connector_red: int
    connector_blue: int
    identical_slices: bool
    uniform_connectors: bool
    antipodal_pair_patterns: tuple[tuple[str, int], ...]


def color_name(color):
    return "red" if color else "blue"


def vertex_name(v):
    return "".join(map(str, v))


def antipodal_vertex_representatives(vertices):
    for v in vertices:
        if v <= anti(v):
            yield v


def arbitrary_coloring_from_bits(edges, bits):
    return {edge: bool(bit) for edge, bit in zip(edges, bits)}


def coloring_blocking_clause(coloring, r):
    return [(-r(*edge) if color else r(*edge)) for edge, color in coloring.items()]


def random_edge_coloring(edges, rng):
    return {edge: bool(rng.randrange(2)) for edge in edges}


def insert_coordinate(v, dimension, side):
    return v[:dimension] + (side,) + v[dimension:]


def remove_coordinate(v, dimension):
    return v[:dimension] + v[dimension + 1 :]


def flip_coordinate(v, dimension):
    return tuple((1 - value) if index == dimension else value for index, value in enumerate(v))


def swap_coordinates(v, left, right):
    values = list(v)
    values[left], values[right] = values[right], values[left]
    return tuple(values)


def component_data(coloring, m):
    vertices, graph = build_hypercube_graph(m)
    return {
        BLUE: color_components(coloring, vertices, graph, BLUE),
        RED: color_components(coloring, vertices, graph, RED),
    }


def component_sets(component_map):
    grouped = {}
    for vertex, component_id in component_map.items():
        grouped.setdefault(component_id, []).append(vertex)
    return tuple(tuple(sorted(vertices)) for _, vertices in sorted(grouped.items()))


def first_intersection_vertex(vertices, component_a, id_a, component_b, id_b):
    for v in vertices:
        if component_a[v] == id_a and component_b[v] == id_b:
            return v
    return None


def bicross_witness(coloring, m):
    vertices, _ = build_hypercube_graph(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]

    for start in antipodal_vertex_representatives(vertices):
        end = anti(start)
        red_to_blue = first_intersection_vertex(
            vertices,
            red,
            red[start],
            blue,
            blue[end],
        )
        blue_to_red = first_intersection_vertex(
            vertices,
            blue,
            blue[start],
            red,
            red[end],
        )
        if red_to_blue is not None and blue_to_red is not None:
            return BicrossWitness(
                start=start,
                end=end,
                red_to_blue_intersection=red_to_blue,
                blue_to_red_intersection=blue_to_red,
            )

    return None


def good_vertices(coloring, m):
    """Vertices x where R(x) intersects B(anti(x))."""
    vertices, _ = build_hypercube_graph(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]
    good = []

    for start in vertices:
        end = anti(start)
        intersection = first_intersection_vertex(
            vertices,
            red,
            red[start],
            blue,
            blue[end],
        )
        if intersection is not None:
            good.append(start)

    return tuple(good)


def bad_vertices(coloring, m):
    good = set(good_vertices(coloring, m))
    vertices, _ = build_hypercube_graph(m)
    return tuple(v for v in vertices if v not in good)


def antipodal_pair_profile(coloring, m):
    good = set(good_vertices(coloring, m))
    vertices, _ = build_hypercube_graph(m)
    profile = Counter()

    for start in antipodal_vertex_representatives(vertices):
        end = anti(start)
        good_count = int(start in good) + int(end in good)
        if good_count == 2:
            profile["both_good"] += 1
        elif good_count == 1:
            profile["one_good"] += 1
        else:
            profile["both_bad"] += 1

    return profile


def bad_vertices_hit_every_antipodal_pair(coloring, m):
    profile = antipodal_pair_profile(coloring, m)
    return profile["both_good"] == 0


def cell_antipodal_pairs(coloring, m):
    """Antipodal pairs whose endpoints share both red and blue components."""
    vertices, _ = build_hypercube_graph(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]
    pairs = []

    for start in antipodal_vertex_representatives(vertices):
        end = anti(start)
        if red[start] == red[end] and blue[start] == blue[end]:
            pairs.append((start, end))

    return tuple(pairs)


def slice_coloring(coloring, m, dimension, side):
    vertices, graph = build_hypercube_graph(m)
    sliced = {}
    for u in vertices:
        if u[dimension] != side:
            continue
        for v in graph[u]:
            if v[dimension] != side or u >= v:
                continue
            sliced[edge_key(remove_coordinate(u, dimension), remove_coordinate(v, dimension))] = coloring[
                edge_key(u, v)
            ]
    return sliced


def doubled_coloring(coloring, m, connector_color=BLUE, dimension=None):
    """Duplicate a Q_m coloring into two Q_m slices of Q_{m+1}.

    The two slices are identical copies of the input coloring, and every edge in
    the new coordinate direction has the same connector color.
    """
    if dimension is None:
        dimension = m
    if not 0 <= dimension <= m:
        raise ValueError(f"dimension must be between 0 and {m}, got {dimension}")

    _, _, edges = all_edges(m + 1)
    doubled = {}
    for u, v in edges:
        if u[dimension] != v[dimension]:
            doubled[edge_key(u, v)] = connector_color
        else:
            small_edge = edge_key(
                remove_coordinate(u, dimension),
                remove_coordinate(v, dimension),
            )
            doubled[edge_key(u, v)] = coloring[small_edge]
    return doubled


def slices_are_identical(coloring, m, dimension):
    vertices, graph = build_hypercube_graph(m)
    for u in vertices:
        if u[dimension] != 0:
            continue
        for v in graph[u]:
            if v[dimension] != 0 or u >= v:
                continue
            u1 = insert_coordinate(remove_coordinate(u, dimension), dimension, 1)
            v1 = insert_coordinate(remove_coordinate(v, dimension), dimension, 1)
            if coloring[edge_key(u, v)] != coloring[edge_key(u1, v1)]:
                return False
    return True


def connector_color_counts(coloring, m, dimension):
    vertices, _ = build_hypercube_graph(m)
    counts = Counter()
    for u in vertices:
        if u[dimension] != 0:
            continue
        v = insert_coordinate(remove_coordinate(u, dimension), dimension, 1)
        counts[coloring[edge_key(u, v)]] += 1
    return counts


def full_vs_slice_profile(universe, full_bad_projected, slice_bad_projected):
    profile = Counter()
    for vertex in universe:
        profile[(int(vertex in full_bad_projected), int(vertex in slice_bad_projected))] += 1
    return tuple((key[0], key[1], count) for key, count in sorted(profile.items()))


def full_vs_slice_count(profile, full_bad, slice_bad):
    for full, sliced, count in profile:
        if full == full_bad and sliced == slice_bad:
            return count
    return 0


def slice_recursion_score(summary):
    """Return (overlap, extra_full_bad, slice_only_bad) across both sides."""
    overlap = full_vs_slice_count(summary.full_vs_slice_side0, 1, 1) + full_vs_slice_count(
        summary.full_vs_slice_side1, 1, 1
    )
    extra_full_bad = full_vs_slice_count(summary.full_vs_slice_side0, 1, 0) + full_vs_slice_count(
        summary.full_vs_slice_side1, 1, 0
    )
    slice_only_bad = full_vs_slice_count(summary.full_vs_slice_side0, 0, 1) + full_vs_slice_count(
        summary.full_vs_slice_side1, 0, 1
    )
    return overlap, extra_full_bad, slice_only_bad


def antipodal_pair_patterns_for_split(coloring, m, dimension):
    small_vertices, _ = build_hypercube_graph(m - 1)
    full_bad = set(bad_vertices(coloring, m))
    patterns = Counter()

    for small in antipodal_vertex_representatives(small_vertices):
        small_anti = anti(small)
        vertices = (
            insert_coordinate(small, dimension, 0),
            insert_coordinate(small, dimension, 1),
            insert_coordinate(small_anti, dimension, 0),
            insert_coordinate(small_anti, dimension, 1),
        )
        pattern = "".join("B" if vertex in full_bad else "G" for vertex in vertices)
        patterns[pattern] += 1

    return tuple(sorted(patterns.items()))


def slice_summary(coloring, m, dimension):
    if m < 2:
        raise ValueError("Slice summaries require m >= 2.")

    full_bad = set(bad_vertices(coloring, m))
    side_bad = {}
    slice_bad = {}
    small_vertices, _ = build_hypercube_graph(m - 1)

    for side in (0, 1):
        side_bad[side] = {
            remove_coordinate(vertex, dimension)
            for vertex in full_bad
            if vertex[dimension] == side
        }
        sliced = slice_coloring(coloring, m, dimension, side)
        slice_bad[side] = set(bad_vertices(sliced, m - 1))

    connector_counts = connector_color_counts(coloring, m, dimension)
    return SliceSummary(
        dimension=dimension,
        full_bad_side0=len(side_bad[0]),
        full_bad_side1=len(side_bad[1]),
        slice_bad_side0=len(slice_bad[0]),
        slice_bad_side1=len(slice_bad[1]),
        full_vs_slice_side0=full_vs_slice_profile(small_vertices, side_bad[0], slice_bad[0]),
        full_vs_slice_side1=full_vs_slice_profile(small_vertices, side_bad[1], slice_bad[1]),
        connector_red=connector_counts[RED],
        connector_blue=connector_counts[BLUE],
        identical_slices=slices_are_identical(coloring, m, dimension),
        uniform_connectors=connector_counts[RED] == 0 or connector_counts[BLUE] == 0,
        antipodal_pair_patterns=antipodal_pair_patterns_for_split(coloring, m, dimension),
    )


def slice_summaries(coloring, m):
    return tuple(slice_summary(coloring, m, dimension) for dimension in range(m))


def perfect_inherited_splits(coloring, m):
    """Coordinates where full bad vertices match slice bad vertices exactly."""
    return tuple(
        summary.dimension
        for summary in slice_summaries(coloring, m)
        if slice_recursion_score(summary)[1:] == (0, 0)
    )


def uniform_perfect_inherited_splits(coloring, m):
    """Perfect inherited coordinates whose connector edges all have one color."""
    return tuple(
        summary.dimension
        for summary in slice_summaries(coloring, m)
        if summary.uniform_connectors and slice_recursion_score(summary)[1:] == (0, 0)
    )


def path_for_coordinate_order(start, order):
    current = start
    path = [current]
    for dimension in order:
        current = tuple((1 - x) if i == dimension else x for i, x in enumerate(current))
        path.append(current)
    return tuple(path)


def is_red_then_blue_path(coloring, path):
    seen_blue = False
    for u, v in zip(path, path[1:]):
        if coloring[edge_key(u, v)] == BLUE:
            seen_blue = True
        elif seen_blue:
            return False
    return True


def monotone_geodesic_vertices(coloring, m):
    vertices, _ = build_hypercube_graph(m)
    monotone = set()
    for order in itertools.permutations(range(m)):
        for start in vertices:
            path = path_for_coordinate_order(start, order)
            if is_red_then_blue_path(coloring, path):
                monotone.add(start)
    return tuple(sorted(monotone))


def construct_bad_antipodal_labeling(coloring, m):
    """Return a witness-free antipodal labeling, if the bicross lemma fails."""
    vertices, _ = build_hypercube_graph(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]
    labels = {}

    for start in antipodal_vertex_representatives(vertices):
        end = anti(start)
        red_to_blue = first_intersection_vertex(
            vertices,
            red,
            red[start],
            blue,
            blue[end],
        )
        blue_to_red = first_intersection_vertex(
            vertices,
            blue,
            blue[start],
            red,
            red[end],
        )

        if red_to_blue is None:
            labels[start] = RED
            labels[end] = BLUE
        elif blue_to_red is None:
            labels[start] = BLUE
            labels[end] = RED
        else:
            return None

    return labels


def iter_antipodal_labelings(m, max_label_vars):
    vertices, _ = build_hypercube_graph(m)
    representatives = list(antipodal_vertex_representatives(vertices))
    if len(representatives) > max_label_vars:
        raise ValueError(
            f"Q_{m} has {len(representatives)} antipodal vertex-label variables; "
            f"raise --max-label-vars to enumerate them explicitly."
        )

    for bits in itertools.product((0, 1), repeat=len(representatives)):
        labels = {}
        for vertex, bit in zip(representatives, bits):
            labels[vertex] = bool(bit)
            labels[anti(vertex)] = not bool(bit)
        yield labels


def shortest_color_path(coloring, m, target_color, start, end):
    if start == end:
        return (start,)

    _, graph = build_hypercube_graph(m)
    queue = deque([start])
    parent = {start: None}

    while queue:
        u = queue.popleft()
        for v in graph[u]:
            if v in parent:
                continue
            if coloring[edge_key(u, v)] != target_color:
                continue
            parent[v] = u
            if v == end:
                queue.clear()
                break
            queue.append(v)

    if end not in parent:
        raise ValueError(f"No {color_name(target_color)} path from {start} to {end}")

    path = []
    v = end
    while v is not None:
        path.append(v)
        v = parent[v]
    path.reverse()
    return tuple(path)


def fixed_slice_witness(coloring, m, labels, include_paths=False):
    vertices, _ = build_hypercube_graph(m)
    components = component_data(coloring, m)

    for connector_vertex in vertices:
        connector_color = labels[connector_vertex]
        opposite_color = not connector_color
        antipode = anti(connector_vertex)
        intersection = first_intersection_vertex(
            vertices,
            components[connector_color],
            components[connector_color][connector_vertex],
            components[opposite_color],
            components[opposite_color][antipode],
        )
        if intersection is None:
            continue

        if not include_paths:
            return FixedSliceWitness(
                connector_vertex=connector_vertex,
                connector_color=connector_color,
                intersection_vertex=intersection,
            )

        return FixedSliceWitness(
            connector_vertex=connector_vertex,
            connector_color=connector_color,
            intersection_vertex=intersection,
            connector_color_path=shortest_color_path(
                coloring,
                m,
                connector_color,
                intersection,
                connector_vertex,
            ),
            opposite_color_path=shortest_color_path(
                coloring,
                m,
                opposite_color,
                intersection,
                antipode,
            ),
        )

    return None


def validate_bad_labeling(coloring, m, labels):
    vertices, _ = build_hypercube_graph(m)
    for v in vertices:
        if labels[anti(v)] == labels[v]:
            return False
    return fixed_slice_witness(coloring, m, labels) is None


def format_bicross_witness(witness):
    if witness is None:
        return "none"
    return (
        f"pair={vertex_name(witness.start)}-{vertex_name(witness.end)}; "
        f"red_to_blue_intersection={vertex_name(witness.red_to_blue_intersection)}; "
        f"blue_to_red_intersection={vertex_name(witness.blue_to_red_intersection)}"
    )


def format_path(path):
    return " -> ".join(vertex_name(v) for v in path)


def format_dimension_list(dimensions):
    return ", ".join(map(str, dimensions)) if dimensions else "none"


def format_fixed_slice_witness(witness):
    if witness is None:
        return "none"

    parts = [
        f"connector={vertex_name(witness.connector_vertex)}",
        f"connector_color={color_name(witness.connector_color)}",
        f"intersection={vertex_name(witness.intersection_vertex)}",
    ]
    if witness.connector_color_path is not None:
        parts.append(f"connector_color_path={format_path(witness.connector_color_path)}")
    if witness.opposite_color_path is not None:
        parts.append(f"opposite_color_path={format_path(witness.opposite_color_path)}")
    return "; ".join(parts)


def format_labeling(labels):
    return ", ".join(f"{vertex_name(v)}={color_name(labels[v])}" for v in sorted(labels))


def format_component_sets(name, components):
    lines = [f"{name} components:"]
    for component_id, vertices in enumerate(components):
        lines.append(f"  {component_id}: " + ", ".join(vertex_name(v) for v in vertices))
    return "\n".join(lines)


def format_incidence_matrix(coloring, m):
    vertices, _ = build_hypercube_graph(m)
    components = component_data(coloring, m)
    red = components[RED]
    blue = components[BLUE]
    red_ids = sorted(set(red.values()))
    blue_ids = sorted(set(blue.values()))
    cells = {(r, b): [] for r in red_ids for b in blue_ids}

    for vertex in vertices:
        cells[(red[vertex], blue[vertex])].append(vertex)

    header = "Component incidence matrix (red rows, blue columns):"
    labels = "      " + "  ".join(f"B{blue_id}" for blue_id in blue_ids)
    lines = [header, labels]
    for red_id in red_ids:
        entries = []
        for blue_id in blue_ids:
            entry_vertices = cells[(red_id, blue_id)]
            if entry_vertices:
                entries.append("{" + ",".join(vertex_name(v) for v in sorted(entry_vertices)) + "}")
            else:
                entries.append(".")
        lines.append(f"  R{red_id}: " + "  ".join(entries))
    return "\n".join(lines)


def format_coloring_structure(coloring, m):
    components = component_data(coloring, m)
    good = good_vertices(coloring, m)
    bad = bad_vertices(coloring, m)
    lines = [
        format_component_sets("Red", component_sets(components[RED])),
        format_component_sets("Blue", component_sets(components[BLUE])),
        format_incidence_matrix(coloring, m),
        "Good vertices: " + ", ".join(vertex_name(v) for v in good),
        "Bad vertices: " + ", ".join(vertex_name(v) for v in bad),
    ]
    return "\n".join(lines)


def format_full_vs_slice(profile):
    if not profile:
        return "none"
    return ", ".join(f"full_bad={full}, slice_bad={sliced}: {count}" for full, sliced, count in profile)


def format_slice_summary(summary):
    patterns = ", ".join(f"{pattern}:{count}" for pattern, count in summary.antipodal_pair_patterns)
    overlap, extra_full_bad, slice_only_bad = slice_recursion_score(summary)
    return (
        f"dimension={summary.dimension}; "
        f"full_bad=({summary.full_bad_side0},{summary.full_bad_side1}); "
        f"slice_bad=({summary.slice_bad_side0},{summary.slice_bad_side1}); "
        f"recursion_score=(overlap={overlap}, extra_full={extra_full_bad}, slice_only={slice_only_bad}); "
        f"connectors red/blue=({summary.connector_red},{summary.connector_blue}); "
        f"identical_slices={summary.identical_slices}; "
        f"uniform_connectors={summary.uniform_connectors}; "
        f"side0 full-vs-slice=[{format_full_vs_slice(summary.full_vs_slice_side0)}]; "
        f"side1 full-vs-slice=[{format_full_vs_slice(summary.full_vs_slice_side1)}]; "
        f"pair_patterns=[{patterns}]"
    )


def format_slice_analysis(coloring, m):
    return "\n".join(format_slice_summary(summary) for summary in slice_summaries(coloring, m))


def coloring_source(args):
    _, _, edges = all_edges(args.m)

    if args.samples:
        rng = random.Random(args.seed)
        for _ in range(args.samples):
            yield random_edge_coloring(edges, rng)
        return

    if len(edges) > args.max_edges:
        raise ValueError(
            f"Q_{args.m} has {len(edges)} edge variables; "
            f"raise --max-edges to enumerate it explicitly."
        )

    for bits in itertools.product((0, 1), repeat=len(edges)):
        yield arbitrary_coloring_from_bits(edges, bits)


def analyze_colorings(args):
    _, _, edges = all_edges(args.m)
    checked = 0
    with_bicross = 0
    without_bicross = 0
    bad_labelings = 0
    all_labelings_checked = 0
    witness_pair_histogram = Counter()
    good_count_histogram = Counter()
    monotone_count_histogram = Counter()
    pair_profile_histogram = Counter()
    min_good_count = None
    min_monotone_count = None
    good_with_no_monotone_geodesic = 0
    first_witness = None
    first_obstruction = None
    first_min_good = None
    first_good_with_no_monotone = None

    for coloring in coloring_source(args):
        checked += 1
        witness = bicross_witness(coloring, args.m)
        good = set(good_vertices(coloring, args.m))
        good_count = len(good)
        good_count_histogram[good_count] += 1
        pair_profile = antipodal_pair_profile(coloring, args.m)
        pair_profile_histogram[
            (
                pair_profile["both_good"],
                pair_profile["one_good"],
                pair_profile["both_bad"],
            )
        ] += 1
        if min_good_count is None or good_count < min_good_count:
            min_good_count = good_count
            first_min_good = coloring

        if args.analyze_monotone:
            monotone = set(monotone_geodesic_vertices(coloring, args.m))
            monotone_count_histogram[len(monotone)] += 1
            if min_monotone_count is None or len(monotone) < min_monotone_count:
                min_monotone_count = len(monotone)
            if good - monotone:
                good_with_no_monotone_geodesic += 1
                if first_good_with_no_monotone is None:
                    first_good_with_no_monotone = coloring
            if not monotone <= good:
                raise AssertionError("A red-then-blue geodesic start was not a good vertex")

        if witness is not None:
            with_bicross += 1
            witness_pair_histogram[(witness.start, witness.end)] += 1
            if first_witness is None:
                first_witness = (coloring, witness)
        else:
            without_bicross += 1
            labels = construct_bad_antipodal_labeling(coloring, args.m)
            if labels is None or not validate_bad_labeling(coloring, args.m, labels):
                raise AssertionError("Bicross failed but no valid bad labeling was constructed")
            bad_labelings += 1
            if first_obstruction is None:
                first_obstruction = (coloring, labels)

        if args.check_all_labelings:
            for labels in iter_antipodal_labelings(args.m, args.max_label_vars):
                all_labelings_checked += 1
                fixed_witness = fixed_slice_witness(coloring, args.m, labels)
                if fixed_witness is None:
                    if witness is not None:
                        raise AssertionError("Bicross witness exists but a labeling has no fixed-slice witness")
                    break

    print(f"Dimension: Q_{args.m}")
    print(f"Edge variables: {len(edges)}")
    print(f"Edge colorings checked: {checked}")
    print(f"With bicross witness: {with_bicross}")
    print(f"Without bicross witness: {without_bicross}")
    print(f"Constructed bad fixed-slice labelings: {bad_labelings}")
    if args.check_all_labelings:
        print(f"Fixed-slice labelings checked: {all_labelings_checked}")
    if min_good_count is not None:
        print(f"Minimum |{{x: R(x) intersects B(anti(x))}}|: {min_good_count}")
        print("Good-count histogram:")
        for count in sorted(good_count_histogram):
            print(f"  {count}: {good_count_histogram[count]}")
        print("Antipodal pair profile histogram:")
        for profile, count in sorted(pair_profile_histogram.items(), key=lambda item: (item[0], item[1]))[:12]:
            both_good, one_good, both_bad = profile
            print(f"  both_good={both_good}, one_good={one_good}, both_bad={both_bad}: {count}")
    if args.analyze_monotone:
        print(f"Minimum red-then-blue geodesic starts: {min_monotone_count}")
        print(f"Colorings with good vertices needing non-geodesic component paths: {good_with_no_monotone_geodesic}")
        print("Monotone-geodesic count histogram:")
        for count in sorted(monotone_count_histogram):
            print(f"  {count}: {monotone_count_histogram[count]}")

    if witness_pair_histogram:
        print("First-witness antipodal pair histogram:")
        for pair, count in sorted(witness_pair_histogram.items(), key=lambda item: (-item[1], item[0]))[:8]:
            start, end = pair
            print(f"  {vertex_name(start)}-{vertex_name(end)}: {count}")

    print("First representatives:")
    if first_witness is not None:
        coloring, witness = first_witness
        print(f"  bicross: {format_bicross_witness(witness)}")
        if args.show_examples:
            print(summarize_coloring(coloring))
            if args.show_components:
                print(format_coloring_structure(coloring, args.m))
            if args.show_slices:
                print(format_slice_analysis(coloring, args.m))
    if first_obstruction is not None:
        coloring, labels = first_obstruction
        print("  obstruction: found")
        print(f"  labels: {format_labeling(labels)}")
        if args.show_examples:
            print(summarize_coloring(coloring))
            if args.show_components:
                print(format_coloring_structure(coloring, args.m))
            if args.show_slices:
                print(format_slice_analysis(coloring, args.m))
    if args.show_examples and first_min_good is not None:
        print("  minimum-good-count coloring:")
        print(summarize_coloring(first_min_good))
        if args.show_components:
            print(format_coloring_structure(first_min_good, args.m))
        if args.show_slices:
            print(format_slice_analysis(first_min_good, args.m))
    if args.show_examples and first_good_with_no_monotone is not None:
        print("  first coloring with non-geodesic good vertices:")
        print(summarize_coloring(first_good_with_no_monotone))
        if args.show_components:
            print(format_coloring_structure(first_good_with_no_monotone, args.m))
        if args.show_slices:
            print(format_slice_analysis(first_good_with_no_monotone, args.m))


def zero_vertex(m):
    return (0,) * m


def unit_vertex(m, dimension):
    return tuple(1 if i == dimension else 0 for i in range(m))


def add_fixed_slice_symmetry_breaking(clauses, m, r, h, fix_zero_label=False, sort_zero_edges=False):
    if fix_zero_label:
        clauses.append([h(zero_vertex(m))])

    if sort_zero_edges:
        zero = zero_vertex(m)
        incident = [r(zero, unit_vertex(m, dimension)) for dimension in range(m)]
        for left, right in zip(incident, incident[1:]):
            clauses.append([-left, right])


def encode_fixed_slice_negation(
    m,
    solver_name=None,
    fix_zero_label=False,
    sort_zero_edges=False,
):
    try:
        from pysat.formula import IDPool
    except ModuleNotFoundError as exc:
        raise SystemExit(f"python-sat is required for --sat-fixed-slice: {exc}") from exc

    vertices, graph = build_hypercube_graph(m)
    _, _, edges = all_edges(m)
    vpool = IDPool()

    def r(u, v):
        return vpool.id(("r", edge_key(u, v)))

    def h(v):
        return vpool.id(("h", v))

    def reachable(target_color, root, v):
        return vpool.id(("p", target_color, root, v))

    clauses = []

    for start in antipodal_vertex_representatives(vertices):
        end = anti(start)
        clauses.append([-h(start), -h(end)])
        clauses.append([h(start), h(end)])

    for target_color in (BLUE, RED):
        for root in vertices:
            clauses.append([reachable(target_color, root, root)])
            for u, v in edges:
                edge_lit = r(u, v)
                if target_color:
                    clauses.append([-reachable(target_color, root, u), -edge_lit, reachable(target_color, root, v)])
                    clauses.append([-reachable(target_color, root, v), -edge_lit, reachable(target_color, root, u)])
                else:
                    clauses.append([-reachable(target_color, root, u), edge_lit, reachable(target_color, root, v)])
                    clauses.append([-reachable(target_color, root, v), edge_lit, reachable(target_color, root, u)])

    for connector_vertex in vertices:
        antipode = anti(connector_vertex)
        for intersection in vertices:
            clauses.append(
                [
                    -h(connector_vertex),
                    -reachable(RED, connector_vertex, intersection),
                    -reachable(BLUE, antipode, intersection),
                ]
            )
            clauses.append(
                [
                    h(connector_vertex),
                    -reachable(BLUE, connector_vertex, intersection),
                    -reachable(RED, antipode, intersection),
                ]
            )

    add_fixed_slice_symmetry_breaking(
        clauses,
        m,
        r,
        h,
        fix_zero_label=fix_zero_label,
        sort_zero_edges=sort_zero_edges,
    )

    solver, _ = make_pysat_solver(solver_name)
    for clause in clauses:
        solver.add_clause(clause)

    return solver, vpool, r, h, clauses


def encode_bad_count_bound(
    m,
    bad_bound,
    solver_name=None,
    sort_zero_edges=False,
    zero_red_degree_at_most_half=False,
    partial_sym_break=0,
):
    try:
        from pysat.card import CardEnc, EncType
        from pysat.formula import IDPool
    except ModuleNotFoundError as exc:
        raise SystemExit(f"python-sat is required for --sat-bad-at-least: {exc}") from exc

    vertices, _, edges = all_edges(m)
    vpool = IDPool()

    def r(u, v):
        return vpool.id(("r", edge_key(u, v)))

    def reachable(target_color, root, v):
        return vpool.id(("p", target_color, root, v))

    def bad(v):
        return vpool.id(("bad", v))

    clauses = []

    for target_color in (BLUE, RED):
        for root in vertices:
            clauses.append([reachable(target_color, root, root)])
            for u, v in edges:
                edge_lit = r(u, v)
                if target_color:
                    clauses.append([-reachable(target_color, root, u), -edge_lit, reachable(target_color, root, v)])
                    clauses.append([-reachable(target_color, root, v), -edge_lit, reachable(target_color, root, u)])
                else:
                    clauses.append([-reachable(target_color, root, u), edge_lit, reachable(target_color, root, v)])
                    clauses.append([-reachable(target_color, root, v), edge_lit, reachable(target_color, root, u)])

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

    cardinality = CardEnc.atleast(
        lits=[bad(v) for v in vertices],
        bound=bad_bound,
        vpool=vpool,
        encoding=EncType.seqcounter,
    )
    clauses.extend(cardinality.clauses)

    add_edge_coloring_symmetry_breaking(
        clauses,
        m,
        r,
        vpool,
        sort_zero_edges=sort_zero_edges,
        zero_red_degree_at_most_half=zero_red_degree_at_most_half,
        partial_sym_break=partial_sym_break,
    )

    solver, _ = make_pysat_solver(solver_name)
    for clause in clauses:
        solver.add_clause(clause)

    return solver, vpool, r, bad, clauses


def add_edge_coloring_symmetry_breaking(
    clauses,
    m,
    r,
    vpool,
    sort_zero_edges=False,
    zero_red_degree_at_most_half=False,
    partial_sym_break=0,
):
    zero = zero_vertex(m)
    incident = [r(zero, unit_vertex(m, dimension)) for dimension in range(m)]

    if sort_zero_edges:
        for left, right in zip(incident, incident[1:]):
            clauses.append([-left, right])

    if zero_red_degree_at_most_half:
        try:
            from pysat.card import CardEnc, EncType
        except ModuleNotFoundError as exc:
            raise SystemExit(f"python-sat is required for --zero-red-degree-at-most-half: {exc}") from exc

        cardinality = CardEnc.atmost(
            lits=incident,
            bound=m // 2,
            vpool=vpool,
            encoding=EncType.seqcounter,
        )
        clauses.extend(cardinality.clauses)

    if partial_sym_break:
        _, _, edges = all_edges(m)
        original = [r(u, v) for u, v in edges]

        for dimension in range(m):
            transformed = [r(flip_coordinate(u, dimension), flip_coordinate(v, dimension)) for u, v in edges]
            lex_smaller_eq(clauses, vpool, original, transformed, maxcomparisons=partial_sym_break)

        for left, right in itertools.combinations(range(m), 2):
            transformed = [r(swap_coordinates(u, left, right), swap_coordinates(v, left, right)) for u, v in edges]
            lex_smaller_eq(clauses, vpool, original, transformed, maxcomparisons=partial_sym_break)


def add_full_bad_clauses(clauses, vertices, reachable, bad):
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


def add_full_bad_completion_clauses(clauses, vertices, reachable, bad, vpool):
    """Force unmarked vertices to have a red-blue meet in the SAT reachability relation.

    The reachability relation is intentionally monotone: every genuinely
    reachable vertex must be marked reachable, but SAT models may mark extra
    vertices reachable.  Therefore these clauses are mainly useful for UNSAT
    falsification of structural lemmas.  Any SAT model is still post-checked
    against the concrete coloring.
    """

    def full_meet(start, intersection):
        return vpool.id(("full_meet", start, intersection))

    for start in vertices:
        end = anti(start)
        meet_lits = []
        for intersection in vertices:
            meet_lit = full_meet(start, intersection)
            red_reachable = reachable(RED, start, intersection)
            blue_reachable = reachable(BLUE, end, intersection)
            clauses.append([-meet_lit, red_reachable])
            clauses.append([-meet_lit, blue_reachable])
            clauses.append([-red_reachable, -blue_reachable, meet_lit])
            clauses.append([-bad(start), -meet_lit])
            meet_lits.append(meet_lit)

        clauses.append([bad(start)] + meet_lits)


def add_forbid_perfect_inherited_split_clauses(clauses, m, r, bad, vpool):
    if m < 2:
        raise ValueError("Perfect inherited split constraints require m >= 2.")

    small_vertices, _, small_edges = all_edges(m - 1)

    def slice_reachable(target_color, dimension, side, root, v):
        return vpool.id(("slice_reachable", target_color, dimension, side, root, v))

    def slice_meet(dimension, side, start, intersection):
        return vpool.id(("slice_meet", dimension, side, start, intersection))

    def slice_bad_var(dimension, side, v):
        return vpool.id(("slice_bad", dimension, side, v))

    def mismatch(dimension, side, v):
        return vpool.id(("slice_bad_mismatch", dimension, side, v))

    for dimension in range(m):
        for side in (0, 1):
            for target_color in (BLUE, RED):
                for root in small_vertices:
                    clauses.append([slice_reachable(target_color, dimension, side, root, root)])
                    for u, v in small_edges:
                        edge_lit = r(
                            insert_coordinate(u, dimension, side),
                            insert_coordinate(v, dimension, side),
                        )
                        u_reachable = slice_reachable(target_color, dimension, side, root, u)
                        v_reachable = slice_reachable(target_color, dimension, side, root, v)
                        if target_color:
                            clauses.append([-u_reachable, -edge_lit, v_reachable])
                            clauses.append([-v_reachable, -edge_lit, u_reachable])
                        else:
                            clauses.append([-u_reachable, edge_lit, v_reachable])
                            clauses.append([-v_reachable, edge_lit, u_reachable])

            for start in small_vertices:
                end = anti(start)
                meet_lits = []
                slice_bad_lit = slice_bad_var(dimension, side, start)
                for intersection in small_vertices:
                    meet_lit = slice_meet(dimension, side, start, intersection)
                    red_reachable = slice_reachable(RED, dimension, side, start, intersection)
                    blue_reachable = slice_reachable(BLUE, dimension, side, end, intersection)
                    clauses.append([-meet_lit, red_reachable])
                    clauses.append([-meet_lit, blue_reachable])
                    clauses.append([-red_reachable, -blue_reachable, meet_lit])
                    clauses.append([-slice_bad_lit, -meet_lit])
                    meet_lits.append(meet_lit)

                clauses.append([slice_bad_lit] + meet_lits)

    for dimension in range(m):
        mismatch_lits = []
        for side in (0, 1):
            for small_vertex in small_vertices:
                full_vertex = insert_coordinate(small_vertex, dimension, side)
                full_bad_lit = bad(full_vertex)
                slice_bad_lit = slice_bad_var(dimension, side, small_vertex)
                mismatch_lit = mismatch(dimension, side, small_vertex)
                clauses.append([-mismatch_lit, full_bad_lit, slice_bad_lit])
                clauses.append([-mismatch_lit, -full_bad_lit, -slice_bad_lit])
                clauses.append([-full_bad_lit, slice_bad_lit, mismatch_lit])
                clauses.append([full_bad_lit, -slice_bad_lit, mismatch_lit])
                mismatch_lits.append(mismatch_lit)

        clauses.append(mismatch_lits)


def encode_pair_hit_bound(
    m,
    hit_bound,
    solver_name=None,
    sort_zero_edges=False,
    zero_red_degree_at_most_half=False,
    partial_sym_break=0,
    forbid_cell_pairs=False,
    complete_bad=False,
    forbid_perfect_inherited_splits=False,
):
    try:
        from pysat.card import CardEnc, EncType
        from pysat.formula import IDPool
    except ModuleNotFoundError as exc:
        raise SystemExit(f"python-sat is required for --sat-pairs-hit-at-least: {exc}") from exc

    vertices, _, edges = all_edges(m)
    representatives = list(antipodal_vertex_representatives(vertices))
    vpool = IDPool()

    def r(u, v):
        return vpool.id(("r", edge_key(u, v)))

    def reachable(target_color, root, v):
        return vpool.id(("p", target_color, root, v))

    def bad(v):
        return vpool.id(("bad", v))

    def pair_hit(v):
        return vpool.id(("pair_hit", v))

    clauses = []
    complete_bad = complete_bad or forbid_perfect_inherited_splits

    for target_color in (BLUE, RED):
        for root in vertices:
            clauses.append([reachable(target_color, root, root)])
            for u, v in edges:
                edge_lit = r(u, v)
                if target_color:
                    clauses.append([-reachable(target_color, root, u), -edge_lit, reachable(target_color, root, v)])
                    clauses.append([-reachable(target_color, root, v), -edge_lit, reachable(target_color, root, u)])
                else:
                    clauses.append([-reachable(target_color, root, u), edge_lit, reachable(target_color, root, v)])
                    clauses.append([-reachable(target_color, root, v), edge_lit, reachable(target_color, root, u)])

    add_full_bad_clauses(clauses, vertices, reachable, bad)

    if complete_bad:
        add_full_bad_completion_clauses(clauses, vertices, reachable, bad, vpool)

    for start in representatives:
        end = anti(start)
        clauses.append([-pair_hit(start), bad(start), bad(end)])

    if forbid_cell_pairs:
        for start in representatives:
            end = anti(start)
            clauses.append([-reachable(RED, start, end), -reachable(BLUE, start, end)])

    if forbid_perfect_inherited_splits:
        add_forbid_perfect_inherited_split_clauses(clauses, m, r, bad, vpool)

    cardinality = CardEnc.atleast(
        lits=[pair_hit(v) for v in representatives],
        bound=hit_bound,
        vpool=vpool,
        encoding=EncType.seqcounter,
    )
    clauses.extend(cardinality.clauses)

    add_edge_coloring_symmetry_breaking(
        clauses,
        m,
        r,
        vpool,
        sort_zero_edges=sort_zero_edges,
        zero_red_degree_at_most_half=zero_red_degree_at_most_half,
        partial_sym_break=partial_sym_break,
    )

    solver, _ = make_pysat_solver(solver_name)
    for clause in clauses:
        solver.add_clause(clause)

    return solver, vpool, r, bad, pair_hit, clauses


def literal_is_true(model_set, lit):
    return lit in model_set if lit > 0 else -lit not in model_set


def write_dimacs(path, top_variable, clauses):
    with open(path, "w") as f:
        f.write(f"p cnf {top_variable} {len(clauses)}\n")
        for clause in clauses:
            f.write(" ".join(str(lit) for lit in clause) + " 0\n")


def solve_fixed_slice_negation(args):
    solver, vpool, r, h, clauses = encode_fixed_slice_negation(
        args.m,
        args.solver,
        fix_zero_label=args.fix_zero_label,
        sort_zero_edges=args.sort_zero_edges,
    )
    vertices, _, edges = all_edges(args.m)

    print(f"Dimension: Q_{args.m}", flush=True)
    print(f"Edge variables: {len(edges)}", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Solver: {best_pysat_solver_name(args.solver) or 'pysat-default'}", flush=True)
    if args.fix_zero_label:
        print("Symmetry: h(00...0)=red", flush=True)
    if args.sort_zero_edges:
        print("Symmetry: incident colors at 00...0 sorted", flush=True)

    if args.no_solve:
        write_dimacs(args.tmp_file, vpool.top, clauses)
        print(f"Wrote CNF to {args.tmp_file}", flush=True)
        solver.delete()
        return

    result = solver.solve()
    print(f"SAT: {result}", flush=True)

    if result:
        model_set = set(solver.get_model())
        coloring = {edge: literal_is_true(model_set, r(*edge)) for edge in edges}
        labels = {v: literal_is_true(model_set, h(v)) for v in vertices}

        print(f"Bicross witness: {format_bicross_witness(bicross_witness(coloring, args.m))}")
        print(
            "Fixed-slice witness: "
            + format_fixed_slice_witness(
                fixed_slice_witness(coloring, args.m, labels, include_paths=args.show_paths)
            )
        )
        print(f"Labeling valid and witness-free: {validate_bad_labeling(coloring, args.m, labels)}")
        if args.show_examples:
            print("Labels:")
            print(format_labeling(labels))
            print("Coloring:")
            print(summarize_coloring(coloring))
        if args.show_components:
            print(format_coloring_structure(coloring, args.m))
        if args.show_slices:
            print(format_slice_analysis(coloring, args.m))

    solver.delete()


def solve_bad_count_bound(args):
    solver, vpool, r, bad, clauses = encode_bad_count_bound(
        args.m,
        args.sat_bad_at_least,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
    )
    vertices, _, edges = all_edges(args.m)

    print(f"Dimension: Q_{args.m}", flush=True)
    print(f"Edge variables: {len(edges)}", flush=True)
    print(f"Bad-vertex lower bound: {args.sat_bad_at_least}", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Solver: {best_pysat_solver_name(args.solver) or 'pysat-default'}", flush=True)
    if args.sort_zero_edges:
        print("Symmetry: incident colors at 00...0 sorted", flush=True)
    if args.zero_red_degree_at_most_half:
        print("Symmetry: red degree at 00...0 at most half", flush=True)
    if args.partial_sym_break:
        print(f"Symmetry: coordinate/flip lex comparisons up to {args.partial_sym_break}", flush=True)

    if args.no_solve:
        write_dimacs(args.tmp_file, vpool.top, clauses)
        print(f"Wrote CNF to {args.tmp_file}", flush=True)
        solver.delete()
        return

    result = solver.solve()
    print(f"SAT: {result}", flush=True)

    if result:
        model_set = set(solver.get_model())
        coloring = {edge: literal_is_true(model_set, r(*edge)) for edge in edges}
        actual_bad = bad_vertices(coloring, args.m)
        pair_profile = antipodal_pair_profile(coloring, args.m)
        encoded_bad = tuple(v for v in vertices if literal_is_true(model_set, bad(v)))
        print(f"Encoded bad vertices: {len(encoded_bad)}")
        print(f"Actual bad vertices: {len(actual_bad)}")
        print(f"Actual good vertices: {len(vertices) - len(actual_bad)}")
        print(
            "Antipodal pair profile: "
            f"both_good={pair_profile['both_good']}, "
            f"one_good={pair_profile['one_good']}, "
            f"both_bad={pair_profile['both_bad']}"
        )
        print(f"Bad vertices hit every antipodal pair: {bad_vertices_hit_every_antipodal_pair(coloring, args.m)}")
        print("Actual bad vertex list: " + ", ".join(vertex_name(v) for v in actual_bad))
        print(f"Bicross witness: {format_bicross_witness(bicross_witness(coloring, args.m))}")
        if args.show_examples:
            print(summarize_coloring(coloring))
        if args.show_components:
            print(format_coloring_structure(coloring, args.m))
        if args.show_slices:
            print(format_slice_analysis(coloring, args.m))

    solver.delete()


def solve_pair_hit_bound(args):
    solver, vpool, r, bad, pair_hit, clauses = encode_pair_hit_bound(
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
    vertices, _, edges = all_edges(args.m)
    representatives = list(antipodal_vertex_representatives(vertices))

    print(f"Dimension: Q_{args.m}", flush=True)
    print(f"Edge variables: {len(edges)}", flush=True)
    print(f"Pair-hit lower bound: {args.sat_pairs_hit_at_least}", flush=True)
    print(f"Antipodal pairs: {len(representatives)}", flush=True)
    print(f"Top variable: {vpool.top}", flush=True)
    print(f"Clauses: {len(clauses)}", flush=True)
    print(f"Solver: {best_pysat_solver_name(args.solver) or 'pysat-default'}", flush=True)
    if args.forbid_cell_pairs:
        print("Restriction: no antipodal pair may share both red and blue components", flush=True)
    if args.complete_bad or args.forbid_perfect_inherited_splits:
        print("Restriction: complete bad variables using SAT reachability meets", flush=True)
    if args.forbid_perfect_inherited_splits:
        print("Restriction: every coordinate split must have a full/slice bad-set mismatch", flush=True)
    if args.sort_zero_edges:
        print("Symmetry: incident colors at 00...0 sorted", flush=True)
    if args.zero_red_degree_at_most_half:
        print("Symmetry: red degree at 00...0 at most half", flush=True)
    if args.partial_sym_break:
        print(f"Symmetry: coordinate/flip lex comparisons up to {args.partial_sym_break}", flush=True)

    if args.no_solve:
        write_dimacs(args.tmp_file, vpool.top, clauses)
        print(f"Wrote CNF to {args.tmp_file}", flush=True)
        solver.delete()
        return

    attempts = 0
    result = False
    rejected_by_postcheck = 0

    while attempts < args.postcheck_limit:
        result = solver.solve()
        if not result:
            break

        attempts += 1
        model_set = set(solver.get_model())
        coloring = {edge: literal_is_true(model_set, r(*edge)) for edge in edges}
        actual_bad = bad_vertices(coloring, args.m)
        pair_profile = antipodal_pair_profile(coloring, args.m)
        encoded_bad = tuple(v for v in vertices if literal_is_true(model_set, bad(v)))
        encoded_hits = tuple(v for v in representatives if literal_is_true(model_set, pair_hit(v)))
        perfect_splits = perfect_inherited_splits(coloring, args.m)
        uniform_perfect_splits = uniform_perfect_inherited_splits(coloring, args.m)
        postcheck_errors = []
        if args.forbid_perfect_inherited_splits and perfect_splits:
            postcheck_errors.append(f"actual perfect inherited splits={format_dimension_list(perfect_splits)}")

        if postcheck_errors and attempts < args.postcheck_limit:
            rejected_by_postcheck += 1
            if attempts <= args.postcheck_report_first or (
                args.postcheck_report_every and attempts % args.postcheck_report_every == 0
            ):
                print(
                    f"Postcheck rejected model {attempts}: " + "; ".join(postcheck_errors),
                    flush=True,
                )
            solver.add_clause(coloring_blocking_clause(coloring, r))
            continue

        print(f"SAT: {result}", flush=True)
        if rejected_by_postcheck:
            print(f"Postcheck rejected colorings: {rejected_by_postcheck}", flush=True)
        if postcheck_errors:
            print("Postcheck status: failed after limit: " + "; ".join(postcheck_errors), flush=True)
        else:
            print("Postcheck status: passed", flush=True)
        print(f"Encoded bad vertices: {len(encoded_bad)}")
        print(f"Encoded hit pairs: {len(encoded_hits)}")
        print(f"Actual bad vertices: {len(actual_bad)}")
        print(f"Actual good vertices: {len(vertices) - len(actual_bad)}")
        print(
            "Antipodal pair profile: "
            f"both_good={pair_profile['both_good']}, "
            f"one_good={pair_profile['one_good']}, "
            f"both_bad={pair_profile['both_bad']}"
        )
        print(f"Bad vertices hit every antipodal pair: {bad_vertices_hit_every_antipodal_pair(coloring, args.m)}")
        print(f"Cell antipodal pairs: {len(cell_antipodal_pairs(coloring, args.m))}")
        print(f"Perfect inherited splits: {format_dimension_list(perfect_inherited_splits(coloring, args.m))}")
        print(
            "Uniform perfect inherited splits: "
            f"{format_dimension_list(uniform_perfect_inherited_splits(coloring, args.m))}"
        )
        print("Actual bad vertex list: " + ", ".join(vertex_name(v) for v in actual_bad))
        print(f"Bicross witness: {format_bicross_witness(bicross_witness(coloring, args.m))}")
        if args.show_examples:
            print(summarize_coloring(coloring))
        if args.show_components:
            print(format_coloring_structure(coloring, args.m))
        if args.show_slices:
            print(format_slice_analysis(coloring, args.m))
        break
    else:
        result = False

    if not result:
        print("SAT: False", flush=True)
        if rejected_by_postcheck:
            print(f"Postcheck rejected colorings: {rejected_by_postcheck}", flush=True)

    solver.delete()


def local_search_score(coloring, m, objective):
    actual_bad = bad_vertices(coloring, m)
    profile = antipodal_pair_profile(coloring, m)
    pairs_hit = profile["one_good"] + profile["both_bad"]
    if objective == "pairs-hit":
        return pairs_hit, len(actual_bad), profile["both_bad"]
    return len(actual_bad), pairs_hit, profile["both_bad"]


def local_search_score_value(score, m):
    scale = 2 ** m
    return score[0] * (scale + 1) * (scale + 1) + score[1] * (scale + 1) + score[2]


def local_search_bad(args):
    _, _, edges = all_edges(args.m)
    rng = random.Random(args.seed)
    best_coloring = None
    best_score = None
    accepted = 0

    for restart in range(args.restarts):
        coloring = random_edge_coloring(edges, rng)
        score = local_search_score(coloring, args.m, args.local_search_objective)
        temperature = max(0.001, args.temperature)

        for step in range(args.local_search_bad):
            edge = edges[rng.randrange(len(edges))]
            coloring[edge] = not coloring[edge]
            next_score = local_search_score(coloring, args.m, args.local_search_objective)
            delta = local_search_score_value(next_score, args.m) - local_search_score_value(score, args.m)
            accept = next_score >= score or rng.random() < pow(2.718281828, delta / temperature)
            if accept:
                score = next_score
                accepted += 1
            else:
                coloring[edge] = not coloring[edge]

            temperature *= args.cooling

            if best_score is None or score > best_score:
                best_score = score
                best_coloring = dict(coloring)

        print(f"restart={restart + 1}; current_score={score}; best_score={best_score}", flush=True)

    actual_bad = bad_vertices(best_coloring, args.m)
    profile = antipodal_pair_profile(best_coloring, args.m)
    print(f"Dimension: Q_{args.m}")
    print(f"Objective: {args.local_search_objective}")
    print(f"Restarts: {args.restarts}")
    print(f"Steps per restart: {args.local_search_bad}")
    print(f"Accepted moves: {accepted}")
    print(f"Best score: {best_score}")
    print(f"Actual bad vertices: {len(actual_bad)}")
    print(f"Actual good vertices: {2 ** args.m - len(actual_bad)}")
    print(
        "Antipodal pair profile: "
        f"both_good={profile['both_good']}, "
        f"one_good={profile['one_good']}, "
        f"both_bad={profile['both_bad']}"
    )
    print(f"Bad vertices hit every antipodal pair: {bad_vertices_hit_every_antipodal_pair(best_coloring, args.m)}")
    print(f"Bicross witness: {format_bicross_witness(bicross_witness(best_coloring, args.m))}")
    if args.show_examples:
        print(summarize_coloring(best_coloring))
    if args.show_components:
        print(format_coloring_structure(best_coloring, args.m))
    if args.show_slices:
        print(format_slice_analysis(best_coloring, args.m))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of the ordinary cube Q_m")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enumerate", action="store_true", help="Enumerate all edge-colorings")
    mode.add_argument("--samples", type=int, default=0, help="Sample random edge-colorings")
    mode.add_argument("--sat-fixed-slice", action="store_true", help="SAT-encode the fixed-slice negation")
    mode.add_argument("--sat-bad-at-least", type=int, help="SAT-search for a coloring with at least K bad vertices")
    mode.add_argument(
        "--sat-pairs-hit-at-least",
        type=int,
        help="SAT-search for a coloring whose bad vertices hit at least K antipodal pairs",
    )
    mode.add_argument("--local-search-bad", type=int, help="Run N local-search edge flips for near-obstructions")
    parser.add_argument("--max-edges", type=int, default=24, help="Maximum edge variables to enumerate exactly")
    parser.add_argument(
        "--check-all-labelings",
        action="store_true",
        help="Also enumerate antipodal vertex-labelings for each checked coloring",
    )
    parser.add_argument(
        "--analyze-monotone",
        action="store_true",
        help="Track starts with an antipodal geodesic whose colors are red-then-blue",
    )
    parser.add_argument(
        "--max-label-vars",
        type=int,
        default=16,
        help="Maximum antipodal vertex-label variables to enumerate exactly",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for --samples")
    parser.add_argument("--restarts", type=int, default=10, help="Restarts for --local-search-bad")
    parser.add_argument(
        "--local-search-objective",
        choices=("bad", "pairs-hit"),
        default="bad",
        help="Objective for --local-search-bad",
    )
    parser.add_argument("--temperature", type=float, default=25.0, help="Initial local-search temperature")
    parser.add_argument("--cooling", type=float, default=0.9995, help="Local-search cooling multiplier")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--no-solve", action="store_true", help="Write SAT-mode CNF and exit without solving")
    parser.add_argument("--tmp-file", default="bicross_probe.cnf", help="CNF path for --no-solve")
    parser.add_argument(
        "--postcheck-limit",
        type=int,
        default=1,
        help="Maximum SAT models to concretely post-check and block in pair-hit SAT mode",
    )
    parser.add_argument(
        "--postcheck-report-first",
        type=int,
        default=10,
        help="Report the first N postcheck rejections in pair-hit SAT mode",
    )
    parser.add_argument(
        "--postcheck-report-every",
        type=int,
        default=100,
        help="After the first reports, print every Nth postcheck rejection; use 0 to silence periodic reports",
    )
    parser.add_argument(
        "--fix-zero-label",
        action="store_true",
        help="In SAT fixed-slice mode, use color-swap symmetry to set h(00...0)=red",
    )
    parser.add_argument(
        "--sort-zero-edges",
        action="store_true",
        help="In SAT modes, use coordinate symmetry to sort colors incident to 00...0",
    )
    parser.add_argument(
        "--zero-red-degree-at-most-half",
        action="store_true",
        help="In bad-count and pair-hit SAT modes, use color-swap symmetry to bound red degree at 00...0",
    )
    parser.add_argument(
        "--partial-sym-break",
        type=int,
        default=0,
        help="In bad-count and pair-hit SAT modes, add coordinate/bit-flip lex symmetry breaking with this comparison cap",
    )
    parser.add_argument(
        "--forbid-cell-pairs",
        action="store_true",
        help="In pair-hit SAT mode, forbid antipodal pairs inside one red/blue incidence cell",
    )
    parser.add_argument(
        "--complete-bad",
        action="store_true",
        help=(
            "In pair-hit SAT mode, require every unmarked bad variable to have a SAT reachability meet. "
            "SAT models are still concrete-post-checked because reachability is monotone."
        ),
    )
    parser.add_argument(
        "--forbid-perfect-inherited-splits",
        action="store_true",
        help=(
            "In pair-hit SAT mode, require every coordinate split to have a mismatch between full bad vertices "
            "and induced-slice bad vertices. Implies --complete-bad."
        ),
    )
    parser.add_argument("--show-examples", action="store_true", help="Print first coloring or SAT model edge list")
    parser.add_argument("--show-components", action="store_true", help="Print red/blue components for shown examples")
    parser.add_argument("--show-slices", action="store_true", help="Print coordinate-slice bad-set summaries")
    parser.add_argument("--show-paths", action="store_true", help="Show reconstructed fixed-slice paths in SAT mode")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.m < 1:
        raise ValueError("Use m >= 1.")

    if args.sat_fixed_slice:
        solve_fixed_slice_negation(args)
    elif args.sat_bad_at_least is not None:
        solve_bad_count_bound(args)
    elif args.sat_pairs_hit_at_least is not None:
        solve_pair_hit_bound(args)
    elif args.local_search_bad is not None:
        local_search_bad(args)
    else:
        analyze_colorings(args)


if __name__ == "__main__":
    main()
