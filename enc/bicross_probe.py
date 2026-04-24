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


def random_edge_coloring(edges, rng):
    return {edge: bool(rng.randrange(2)) for edge in edges}


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
    if first_obstruction is not None:
        coloring, labels = first_obstruction
        print("  obstruction: found")
        print(f"  labels: {format_labeling(labels)}")
        if args.show_examples:
            print(summarize_coloring(coloring))
            if args.show_components:
                print(format_coloring_structure(coloring, args.m))
    if args.show_examples and first_min_good is not None:
        print("  minimum-good-count coloring:")
        print(summarize_coloring(first_min_good))
        if args.show_components:
            print(format_coloring_structure(first_min_good, args.m))
    if args.show_examples and first_good_with_no_monotone is not None:
        print("  first coloring with non-geodesic good vertices:")
        print(summarize_coloring(first_good_with_no_monotone))
        if args.show_components:
            print(format_coloring_structure(first_good_with_no_monotone, args.m))


def encode_fixed_slice_negation(m, solver_name=None):
    try:
        from pysat.formula import IDPool
        from pysat.solvers import Solver
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

    solver = Solver(name=solver_name) if solver_name else Solver()
    for clause in clauses:
        solver.add_clause(clause)

    return solver, vpool, r, h, clauses


def encode_bad_count_bound(m, bad_bound, solver_name=None):
    try:
        from pysat.card import CardEnc, EncType
        from pysat.formula import IDPool
        from pysat.solvers import Solver
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

    solver = Solver(name=solver_name) if solver_name else Solver()
    for clause in clauses:
        solver.add_clause(clause)

    return solver, vpool, r, bad, clauses


def literal_is_true(model_set, lit):
    return lit in model_set if lit > 0 else -lit not in model_set


def solve_fixed_slice_negation(args):
    solver, vpool, r, h, clauses = encode_fixed_slice_negation(args.m, args.solver)
    vertices, _, edges = all_edges(args.m)

    print(f"Dimension: Q_{args.m}")
    print(f"Edge variables: {len(edges)}")
    print(f"Top variable: {vpool.top}")
    print(f"Clauses: {len(clauses)}")

    result = solver.solve()
    print(f"SAT: {result}")

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

    solver.delete()


def solve_bad_count_bound(args):
    solver, vpool, r, bad, clauses = encode_bad_count_bound(args.m, args.sat_bad_at_least, args.solver)
    vertices, _, edges = all_edges(args.m)

    print(f"Dimension: Q_{args.m}")
    print(f"Edge variables: {len(edges)}")
    print(f"Bad-vertex lower bound: {args.sat_bad_at_least}")
    print(f"Top variable: {vpool.top}")
    print(f"Clauses: {len(clauses)}")

    result = solver.solve()
    print(f"SAT: {result}")

    if result:
        model_set = set(solver.get_model())
        coloring = {edge: literal_is_true(model_set, r(*edge)) for edge in edges}
        actual_bad = bad_vertices(coloring, args.m)
        encoded_bad = tuple(v for v in vertices if literal_is_true(model_set, bad(v)))
        print(f"Encoded bad vertices: {len(encoded_bad)}")
        print(f"Actual bad vertices: {len(actual_bad)}")
        print(f"Actual good vertices: {len(vertices) - len(actual_bad)}")
        print("Actual bad vertex list: " + ", ".join(vertex_name(v) for v in actual_bad))
        print(f"Bicross witness: {format_bicross_witness(bicross_witness(coloring, args.m))}")
        if args.show_examples:
            print(summarize_coloring(coloring))
            if args.show_components:
                print(format_coloring_structure(coloring, args.m))

    solver.delete()


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Dimension of the ordinary cube Q_m")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enumerate", action="store_true", help="Enumerate all edge-colorings")
    mode.add_argument("--samples", type=int, default=0, help="Sample random edge-colorings")
    mode.add_argument("--sat-fixed-slice", action="store_true", help="SAT-encode the fixed-slice negation")
    mode.add_argument("--sat-bad-at-least", type=int, help="SAT-search for a coloring with at least K bad vertices")
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
    parser.add_argument("--solver", default=None, help="Optional PySAT solver name for --sat-fixed-slice")
    parser.add_argument("--show-examples", action="store_true", help="Print first coloring or SAT model")
    parser.add_argument("--show-components", action="store_true", help="Print red/blue components for shown examples")
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
    else:
        analyze_colorings(args)


if __name__ == "__main__":
    main()
