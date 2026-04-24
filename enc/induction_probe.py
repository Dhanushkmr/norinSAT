"""
Small-dimension probes for induction-style strengthenings of Norine's conjecture.

This script is deliberately independent of SAT solving.  It enumerates or samples
antipodal edge-colorings of Q_n, checks whether they contain a monochromatic path
between antipodal vertices, and checks whether they have a coordinate slice that
is itself an antipodal coloring of Q_{n-1}.
"""

import argparse
import itertools
import random
from collections import Counter, deque
from functools import lru_cache


Coloring = dict[tuple[tuple[int, ...], tuple[int, ...]], bool]


def anti(v):
    return tuple(1 - x for x in v)


@lru_cache(maxsize=None)
def build_hypercube_graph(n):
    vertices = list(itertools.product([0, 1], repeat=n))
    vertices = [v[::-1] for v in vertices]
    graph = {}
    for v in vertices:
        graph[v] = []
        for i in range(n):
            neighbor = tuple((1 - x) if i == j else x for j, x in enumerate(v))
            graph[v].append(neighbor)
    return vertices, graph


def edge_key(u, v):
    return (u, v) if u < v else (v, u)


def edge_name(edge):
    u, v = edge
    return f"{''.join(map(str, u))}-{''.join(map(str, v))}"


@lru_cache(maxsize=None)
def all_edges(n):
    vertices, graph = build_hypercube_graph(n)
    edges = []
    for u in vertices:
        for v in graph[u]:
            if u < v:
                edges.append((u, v))
    return vertices, graph, edges


def anti_edge(edge):
    u, v = edge
    return edge_key(anti(u), anti(v))


def is_antipodal_coloring(coloring):
    for edge, color in coloring.items():
        if coloring[anti_edge(edge)] == color:
            return False
    return True


def antipodal_edge_representatives(edges):
    reps = []
    seen = set()
    for edge in edges:
        if edge in seen:
            continue
        opposite = anti_edge(edge)
        reps.append(min(edge, opposite))
        seen.add(edge)
        seen.add(opposite)
    return sorted(set(reps))


def cube_automorphisms(n):
    for perm in itertools.permutations(range(n)):
        for mask in itertools.product((0, 1), repeat=n):
            yield perm, mask


def transform_vertex(v, perm, mask):
    return tuple(v[perm[i]] ^ mask[i] for i in range(len(v)))


def transform_edge(edge, perm, mask):
    u, v = edge
    return edge_key(transform_vertex(u, perm, mask), transform_vertex(v, perm, mask))


def canonical_coloring(coloring, n, allow_color_swap=True):
    _, _, edges = all_edges(n)
    forms = []
    for perm, mask in cube_automorphisms(n):
        transformed = {}
        for edge, color in coloring.items():
            transformed[transform_edge(edge, perm, mask)] = color
        color_swaps = (False, True) if allow_color_swap else (False,)
        for swap_colors in color_swaps:
            forms.append("".join("1" if transformed[edge] ^ swap_colors else "0" for edge in edges))
    return min(forms)


def coloring_from_bits(representatives, bits):
    coloring = {}
    for edge, bit in zip(representatives, bits):
        opposite = anti_edge(edge)
        color = bool(bit)
        coloring[edge] = color
        coloring[opposite] = not color
    return coloring


def random_antipodal_coloring(representatives, rng):
    return coloring_from_bits(representatives, [rng.randrange(2) for _ in representatives])


def slice_anti(v, dimension):
    return tuple(x if i == dimension else 1 - x for i, x in enumerate(v))


@lru_cache(maxsize=None)
def slice_antipodal_edge_pairs(n, dimension, side):
    _, _, edges = all_edges(n)
    pairs = []
    for edge in edges:
        u, v = edge
        if u[dimension] != side or v[dimension] != side:
            continue
        opposite = edge_key(slice_anti(u, dimension), slice_anti(v, dimension))
        if edge <= opposite:
            pairs.append((edge, opposite))
    return tuple(pairs)


def is_slice_antipodal(coloring, n, dimension, side=0):
    for edge, opposite in slice_antipodal_edge_pairs(n, dimension, side):
        if coloring[edge] == coloring[opposite]:
            return False
    return True


def reducible_slices(coloring, n):
    slices = []
    for dimension in range(n):
        if is_slice_antipodal(coloring, n, dimension, side=0):
            assert slices_are_identical(coloring, n, dimension)
            slices.append(dimension)
    return slices


def insert_coordinate(v, dimension, side):
    return v[:dimension] + (side,) + v[dimension:]


@lru_cache(maxsize=None)
def identical_slice_edge_pairs(n, dimension):
    vertices, graph = build_hypercube_graph(n - 1)
    pairs = []
    for u_small in vertices:
        for v_small in graph[u_small]:
            if u_small < v_small:
                u0 = insert_coordinate(u_small, dimension, 0)
                v0 = insert_coordinate(v_small, dimension, 0)
                u1 = insert_coordinate(u_small, dimension, 1)
                v1 = insert_coordinate(v_small, dimension, 1)
                pairs.append((edge_key(u0, v0), edge_key(u1, v1)))
    return tuple(pairs)


def slices_are_identical(coloring, n, dimension):
    for edge0, edge1 in identical_slice_edge_pairs(n, dimension):
        if coloring[edge0] != coloring[edge1]:
            return False
    return True


def connector_representatives(m):
    vertices, _ = build_hypercube_graph(m)
    return [v for v in vertices if v <= anti(v)]


def lift_from_base_coloring(base_coloring, m, connector_bits, dimension=0):
    n = m + 1
    coloring = {}

    for edge, color in base_coloring.items():
        u_small, v_small = edge
        for side in (0, 1):
            u = insert_coordinate(u_small, dimension, side)
            v = insert_coordinate(v_small, dimension, side)
            coloring[edge_key(u, v)] = color

    reps = connector_representatives(m)
    for u_small, bit in zip(reps, connector_bits):
        color = bool(bit)
        opposite_small = anti(u_small)

        u0 = insert_coordinate(u_small, dimension, 0)
        u1 = insert_coordinate(u_small, dimension, 1)
        coloring[edge_key(u0, u1)] = color

        v0 = insert_coordinate(opposite_small, dimension, 0)
        v1 = insert_coordinate(opposite_small, dimension, 1)
        coloring[edge_key(v0, v1)] = not color

    assert len(coloring) == n * (2 ** (n - 1))
    assert is_antipodal_coloring(coloring)
    assert is_slice_antipodal(coloring, n, dimension, side=0)
    return coloring


def monochromatic_antipodal_path(coloring, n):
    vertices, graph = build_hypercube_graph(n)

    for target_color in (False, True):
        component = {}
        next_component = 0

        for start in vertices:
            if start in component:
                continue

            queue = deque([start])
            component[start] = next_component

            while queue:
                u = queue.popleft()
                for v in graph[u]:
                    if coloring[edge_key(u, v)] != target_color or v in component:
                        continue
                    component[v] = next_component
                    queue.append(v)

            next_component += 1

        for u in vertices:
            if u <= anti(u) and component[u] == component[anti(u)]:
                return target_color, u, anti(u)

    return None


def color_components(coloring, vertices, graph, target_color, vertex_filter=None):
    allowed = set(vertices) if vertex_filter is None else {v for v in vertices if vertex_filter(v)}
    component = {}
    next_component = 0

    for start in vertices:
        if start not in allowed or start in component:
            continue

        queue = deque([start])
        component[start] = next_component

        while queue:
            u = queue.popleft()
            for v in graph[u]:
                if v not in allowed or v in component:
                    continue
                if coloring[edge_key(u, v)] != target_color:
                    continue
                component[v] = next_component
                queue.append(v)

        next_component += 1

    return component


def paired_slice_lift_witness(coloring, n):
    vertices, graph = build_hypercube_graph(n)
    small_vertices, _ = build_hypercube_graph(n - 1)

    for dimension in range(n):
        for target_color in (False, True):
            side0 = color_components(
                coloring,
                vertices,
                graph,
                target_color,
                vertex_filter=lambda v, d=dimension: v[d] == 0,
            )
            side1 = color_components(
                coloring,
                vertices,
                graph,
                target_color,
                vertex_filter=lambda v, d=dimension: v[d] == 1,
            )

            for u_small in small_vertices:
                if u_small > anti(u_small):
                    continue
                a_small = anti(u_small)
                u0 = insert_coordinate(u_small, dimension, 0)
                a0 = insert_coordinate(a_small, dimension, 0)
                u1 = insert_coordinate(u_small, dimension, 1)
                a1 = insert_coordinate(a_small, dimension, 1)

                if side0[u0] == side0[a0] and side1[u1] == side1[a1]:
                    return target_color, dimension, u_small

    return None


def summarize_coloring(coloring):
    lines = []
    for edge in sorted(coloring):
        color = "R" if coloring[edge] else "B"
        lines.append(f"  {edge_name(edge)} {color}")
    return "\n".join(lines)


def iter_colorings(n, max_free_vars):
    _, _, edges = all_edges(n)
    representatives = antipodal_edge_representatives(edges)
    if len(representatives) > max_free_vars:
        raise ValueError(
            f"Q_{n} has {len(representatives)} free antipodal edge variables; "
            f"raise --max-free-vars to enumerate it explicitly."
        )

    for bits in itertools.product((0, 1), repeat=len(representatives)):
        yield representatives, coloring_from_bits(representatives, bits)


def probe_enumeration(args):
    checked = 0
    with_path = 0
    without_path = 0
    reducible = 0
    irreducible = 0
    paired_lift = 0
    reducible_histogram = Counter()
    first_irreducible = None
    first_irreducible_without_path = None
    first_without_paired_lift = None

    representatives = None
    for representatives, coloring in iter_colorings(args.n, args.max_free_vars):
        checked += 1
        witness = monochromatic_antipodal_path(coloring, args.n)
        slices = reducible_slices(coloring, args.n)
        paired_witness = paired_slice_lift_witness(coloring, args.n)

        if witness is None:
            without_path += 1
        else:
            with_path += 1

        if paired_witness is None:
            if first_without_paired_lift is None:
                first_without_paired_lift = coloring
        else:
            paired_lift += 1

        reducible_histogram[len(slices)] += 1
        if slices:
            reducible += 1
        else:
            irreducible += 1
            if first_irreducible is None:
                first_irreducible = coloring
            if witness is None and first_irreducible_without_path is None:
                first_irreducible_without_path = coloring

    print_summary(
        n=args.n,
        free_vars=len(representatives) if representatives is not None else 0,
        checked=checked,
        with_path=with_path,
        without_path=without_path,
        reducible=reducible,
        irreducible=irreducible,
        paired_lift=paired_lift,
        reducible_histogram=reducible_histogram,
        first_irreducible=first_irreducible,
        first_irreducible_without_path=first_irreducible_without_path,
        first_without_paired_lift=first_without_paired_lift,
        show_counterexample=args.show_counterexample,
    )


def probe_samples(args):
    _, _, edges = all_edges(args.n)
    representatives = antipodal_edge_representatives(edges)
    rng = random.Random(args.seed)

    checked = args.samples
    with_path = 0
    without_path = 0
    reducible = 0
    irreducible = 0
    paired_lift = 0
    reducible_histogram = Counter()
    first_irreducible = None
    first_irreducible_without_path = None
    first_without_paired_lift = None

    for _ in range(args.samples):
        coloring = random_antipodal_coloring(representatives, rng)
        witness = monochromatic_antipodal_path(coloring, args.n)
        slices = reducible_slices(coloring, args.n)
        paired_witness = paired_slice_lift_witness(coloring, args.n)

        if witness is None:
            without_path += 1
        else:
            with_path += 1

        if paired_witness is None:
            if first_without_paired_lift is None:
                first_without_paired_lift = coloring
        else:
            paired_lift += 1

        reducible_histogram[len(slices)] += 1
        if slices:
            reducible += 1
        else:
            irreducible += 1
            if first_irreducible is None:
                first_irreducible = coloring
            if witness is None and first_irreducible_without_path is None:
                first_irreducible_without_path = coloring

    print_summary(
        n=args.n,
        free_vars=len(representatives),
        checked=checked,
        with_path=with_path,
        without_path=without_path,
        reducible=reducible,
        irreducible=irreducible,
        paired_lift=paired_lift,
        reducible_histogram=reducible_histogram,
        first_irreducible=first_irreducible,
        first_irreducible_without_path=first_irreducible_without_path,
        first_without_paired_lift=first_without_paired_lift,
        show_counterexample=args.show_counterexample,
    )


def summarize_orbits(args):
    orbit_data = {}
    for _, coloring in iter_colorings(args.n, args.max_free_vars):
        key = canonical_coloring(coloring, args.n, allow_color_swap=not args.no_color_swap)
        slices = reducible_slices(coloring, args.n)
        has_path = monochromatic_antipodal_path(coloring, args.n) is not None

        if key not in orbit_data:
            orbit_data[key] = {
                "count": 0,
                "reducible": bool(slices),
                "slice_count": len(slices),
                "has_path": has_path,
                "paired_lift": paired_slice_lift_witness(coloring, args.n) is not None,
            }
        else:
            # These are invariance checks for the properties we care about.
            assert orbit_data[key]["reducible"] == bool(slices)
            assert orbit_data[key]["slice_count"] == len(slices)
            assert orbit_data[key]["has_path"] == has_path
            assert orbit_data[key]["paired_lift"] == (
                paired_slice_lift_witness(coloring, args.n) is not None
            )

        orbit_data[key]["count"] += 1

    orbit_histogram = Counter(data["slice_count"] for data in orbit_data.values())
    reducible_orbits = sum(1 for data in orbit_data.values() if data["reducible"])
    irreducible_orbits = len(orbit_data) - reducible_orbits
    paired_lift_orbits = sum(1 for data in orbit_data.values() if data["paired_lift"])

    print(f"Orbit summary: Q_{args.n}")
    print(f"Orbits checked: {len(orbit_data)}")
    print(f"Orbits with at least one reducible slice: {reducible_orbits}")
    print(f"Orbits with no reducible slice: {irreducible_orbits}")
    print(f"Orbits with a paired-slice lift witness: {paired_lift_orbits}")
    print("Orbit reducible-slice histogram:")
    for slice_count in sorted(orbit_histogram):
        print(f"  {slice_count}: {orbit_histogram[slice_count]}")


def check_lift(args):
    n = args.n
    m = n - 1
    connectors = connector_representatives(m)
    if len(connectors) > args.max_connector_vars:
        raise ValueError(
            f"The lift check for Q_{n} has {len(connectors)} free connector variables; "
            f"raise --max-connector-vars to enumerate it explicitly."
        )

    base_checked = 0
    base_with_path = 0
    connector_cases = 0

    for _, base_coloring in iter_colorings(m, args.max_free_vars):
        base_checked += 1
        if monochromatic_antipodal_path(base_coloring, m) is None:
            continue

        base_with_path += 1
        for connector_bits in itertools.product((0, 1), repeat=len(connectors)):
            connector_cases += 1
            coloring = lift_from_base_coloring(base_coloring, m, connector_bits)
            if monochromatic_antipodal_path(coloring, n) is None:
                print("Lift violation found.")
                print("Base coloring:")
                print(summarize_coloring(base_coloring))
                print("Connector bits:", connector_bits)
                return

    print(f"Lift check: Q_{m} -> Q_{n}")
    print(f"Base colorings checked: {base_checked}")
    print(f"Base colorings with monochromatic antipodal path: {base_with_path}")
    print(f"Connector assignments checked: {connector_cases}")
    print("Lift violations: 0")


def print_summary(
    *,
    n,
    free_vars,
    checked,
    with_path,
    without_path,
    reducible,
    irreducible,
    paired_lift,
    reducible_histogram,
    first_irreducible,
    first_irreducible_without_path,
    first_without_paired_lift,
    show_counterexample,
):
    print(f"Dimension: Q_{n}")
    print(f"Free antipodal edge variables: {free_vars}")
    print(f"Colorings checked: {checked}")
    print(f"With monochromatic antipodal path: {with_path}")
    print(f"Without monochromatic antipodal path: {without_path}")
    print(f"With at least one reducible slice: {reducible}")
    print(f"With no reducible slice: {irreducible}")
    print(f"With a paired-slice lift witness: {paired_lift}")
    print("Reducible-slice histogram:")
    for slice_count in sorted(reducible_histogram):
        print(f"  {slice_count}: {reducible_histogram[slice_count]}")

    if first_irreducible is not None:
        print("First broad reducible-slice counterexample: found")
        if show_counterexample:
            print(summarize_coloring(first_irreducible))
    else:
        print("First broad reducible-slice counterexample: none")

    if first_irreducible_without_path is not None:
        print("First irreducible no-path counterexample candidate: found")
        if show_counterexample:
            print(summarize_coloring(first_irreducible_without_path))
    else:
        print("First irreducible no-path counterexample candidate: none")

    if first_without_paired_lift is not None:
        print("First coloring without paired-slice lift witness: found")
        if show_counterexample:
            print(summarize_coloring(first_without_paired_lift))
    else:
        print("First coloring without paired-slice lift witness: none")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", type=int, required=True, help="Hypercube dimension")
    parser.add_argument(
        "--max-free-vars",
        type=int,
        default=24,
        help="Maximum free antipodal edge variables to enumerate exactly",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=0,
        help="Use random sampling instead of exact enumeration",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for --samples")
    parser.add_argument(
        "--show-counterexample",
        action="store_true",
        help="Print the first coloring with no reducible slice, if one is found",
    )
    parser.add_argument(
        "--check-lift",
        action="store_true",
        help="Check that reducible Q_{n-1} slices lift through every connector coloring",
    )
    parser.add_argument(
        "--orbit-summary",
        action="store_true",
        help="Quotient exact enumeration by cube automorphisms and global color swap",
    )
    parser.add_argument(
        "--no-color-swap",
        action="store_true",
        help="In --orbit-summary, do not identify colorings under global color swap",
    )
    parser.add_argument(
        "--max-connector-vars",
        type=int,
        default=16,
        help="Maximum free connector variables to enumerate in --check-lift mode",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.n < 3:
        raise ValueError("Use n >= 3 so coordinate slices have nontrivial antipodal edge pairs.")

    if args.check_lift:
        check_lift(args)
    elif args.orbit_summary:
        summarize_orbits(args)
    elif args.samples:
        probe_samples(args)
    else:
        probe_enumeration(args)


if __name__ == "__main__":
    main()
