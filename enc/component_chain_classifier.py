"""
Classify monochromatic antipodal paths by their slice-component connector chain.

For each coordinate split and color, this script compresses the two Q_{n-1}
slices into monochromatic connected components.  Connector edges of the same
color become edges in a quotient graph.  A quotient path from the component of
v to the component of anti(v) reconstructs a full monochromatic antipodal path;
the quotient path length is the number of connector crossings in that split.
"""

import argparse
import random
from collections import Counter, defaultdict, deque
from dataclasses import dataclass

from induction_probe import (
    all_edges,
    anti,
    antipodal_edge_representatives,
    build_hypercube_graph,
    color_components,
    edge_key,
    iter_colorings,
    monochromatic_antipodal_path,
    paired_slice_lift_witness,
    random_antipodal_coloring,
    reducible_slices,
    summarize_coloring,
)


BLUE = False
RED = True


@dataclass(frozen=True)
class ChainWitness:
    color: bool
    dimension: int
    start: tuple[int, ...]
    end: tuple[int, ...]
    connector_crossings: int
    quotient_nodes: tuple[tuple[int, int], ...]
    connectors: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    path: tuple[tuple[int, ...], ...] | None = None


def color_name(color):
    return "red" if color else "blue"


def vertex_name(v):
    return "".join(map(str, v))


def flip_coordinate(v, dimension):
    return tuple((1 - x) if i == dimension else x for i, x in enumerate(v))


def antipodal_vertex_representatives(vertices):
    for v in vertices:
        if v <= anti(v):
            yield v


def quotient_for_split(coloring, n, dimension, target_color):
    vertices, graph = build_hypercube_graph(n)
    vertex_to_node = {}
    quotient_adj = defaultdict(list)

    for side in (0, 1):
        components = color_components(
            coloring,
            vertices,
            graph,
            target_color,
            vertex_filter=lambda v, d=dimension, s=side: v[d] == s,
        )
        for v, component_id in components.items():
            node = (side, component_id)
            vertex_to_node[v] = node
            quotient_adj[node]

    for u in vertices:
        if u[dimension] != 0:
            continue
        v = flip_coordinate(u, dimension)
        if coloring[edge_key(u, v)] != target_color:
            continue

        node_u = vertex_to_node[u]
        node_v = vertex_to_node[v]
        quotient_adj[node_u].append((node_v, (u, v)))
        quotient_adj[node_v].append((node_u, (v, u)))

    return vertex_to_node, quotient_adj


def shortest_quotient_route(quotient_adj, start_node, end_node):
    queue = deque([start_node])
    parent = {start_node: (None, None)}

    while queue:
        node = queue.popleft()
        if node == end_node:
            break
        for next_node, connector in quotient_adj[node]:
            if next_node in parent:
                continue
            parent[next_node] = (node, connector)
            queue.append(next_node)

    if end_node not in parent:
        return None

    nodes = []
    connectors = []
    node = end_node
    while node is not None:
        nodes.append(node)
        prev, connector = parent[node]
        if connector is not None:
            connectors.append(connector)
        node = prev

    nodes.reverse()
    connectors.reverse()
    return tuple(nodes), tuple(connectors)


def shortest_in_slice_path(coloring, n, dimension, target_color, start, end):
    if start == end:
        return [start]

    _, graph = build_hypercube_graph(n)
    side = start[dimension]
    queue = deque([start])
    parent = {start: None}

    while queue:
        u = queue.popleft()
        for v in graph[u]:
            if v[dimension] != side or v in parent:
                continue
            if coloring[edge_key(u, v)] != target_color:
                continue
            parent[v] = u
            if v == end:
                queue.clear()
                break
            queue.append(v)

    if end not in parent:
        raise ValueError(f"No in-slice path from {start} to {end}")

    path = []
    v = end
    while v is not None:
        path.append(v)
        v = parent[v]
    path.reverse()
    return path


def reconstruct_path(coloring, n, witness):
    path = [witness.start]
    current = witness.start

    for connector_start, connector_end in witness.connectors:
        segment = shortest_in_slice_path(
            coloring,
            n,
            witness.dimension,
            witness.color,
            current,
            connector_start,
        )
        path.extend(segment[1:])
        path.append(connector_end)
        current = connector_end

    tail = shortest_in_slice_path(
        coloring,
        n,
        witness.dimension,
        witness.color,
        current,
        witness.end,
    )
    path.extend(tail[1:])
    return tuple(path)


def validate_path(coloring, path, n, target_color):
    if not path or path[-1] != anti(path[0]):
        return False
    _, graph = build_hypercube_graph(n)
    for u, v in zip(path, path[1:]):
        if v not in graph[u] or coloring[edge_key(u, v)] != target_color:
            return False
    return True


def classify_coloring(coloring, n, include_path=False):
    vertices, _ = build_hypercube_graph(n)
    best = None

    for dimension in range(n):
        for target_color in (BLUE, RED):
            vertex_to_node, quotient_adj = quotient_for_split(coloring, n, dimension, target_color)
            for start in antipodal_vertex_representatives(vertices):
                end = anti(start)
                route = shortest_quotient_route(quotient_adj, vertex_to_node[start], vertex_to_node[end])
                if route is None:
                    continue

                quotient_nodes, connectors = route
                witness = ChainWitness(
                    color=target_color,
                    dimension=dimension,
                    start=start,
                    end=end,
                    connector_crossings=len(connectors),
                    quotient_nodes=quotient_nodes,
                    connectors=connectors,
                )

                if include_path:
                    path = reconstruct_path(coloring, n, witness)
                    witness = ChainWitness(
                        color=witness.color,
                        dimension=witness.dimension,
                        start=witness.start,
                        end=witness.end,
                        connector_crossings=witness.connector_crossings,
                        quotient_nodes=witness.quotient_nodes,
                        connectors=witness.connectors,
                        path=path,
                    )
                    if not validate_path(coloring, path, n, target_color):
                        raise AssertionError("Reconstructed path failed validation")

                if best is None or witness.connector_crossings < best.connector_crossings:
                    best = witness
                    if best.connector_crossings == 1:
                        return best

    return best


def format_witness(witness, show_path=False):
    if witness is None:
        return "none"

    parts = [
        f"color={color_name(witness.color)}",
        f"dimension={witness.dimension}",
        f"pair={vertex_name(witness.start)}-{vertex_name(witness.end)}",
        f"connector_crossings={witness.connector_crossings}",
    ]
    if witness.connectors:
        parts.append(
            "connectors="
            + ",".join(f"{vertex_name(u)}-{vertex_name(v)}" for u, v in witness.connectors)
        )
    if show_path and witness.path is not None:
        parts.append("path=" + " -> ".join(vertex_name(v) for v in witness.path))
    return "; ".join(parts)


def compare_with_full_path_checker(coloring, n, witness):
    full_witness = monochromatic_antipodal_path(coloring, n)
    if (full_witness is None) != (witness is None):
        raise AssertionError(
            f"Classifier disagrees with full path checker: classifier={witness}, full={full_witness}"
        )


def coloring_source(args):
    if args.samples:
        _, _, edges = all_edges(args.n)
        representatives = antipodal_edge_representatives(edges)
        rng = random.Random(args.seed)
        for _ in range(args.samples):
            yield random_antipodal_coloring(representatives, rng)
        return

    for _, coloring in iter_colorings(args.n, args.max_free_vars):
        yield coloring


def analyze_colorings(args):
    checked = 0
    no_path = 0
    reducible = 0
    paired = 0
    longer = 0
    crossing_histogram = Counter()
    first_by_crossing = {}
    first_no_path = None

    for coloring in coloring_source(args):
        checked += 1
        witness = classify_coloring(coloring, args.n, include_path=args.show_paths)
        compare_with_full_path_checker(coloring, args.n, witness)

        if reducible_slices(coloring, args.n):
            reducible += 1
        if paired_slice_lift_witness(coloring, args.n) is not None:
            paired += 1

        if witness is None:
            no_path += 1
            if first_no_path is None:
                first_no_path = coloring
            continue

        crossing_histogram[witness.connector_crossings] += 1
        first_by_crossing.setdefault(witness.connector_crossings, (coloring, witness))
        if witness.connector_crossings > 1:
            longer += 1

    print(f"Dimension: Q_{args.n}")
    print(f"Colorings checked: {checked}")
    print(f"Without monochromatic antipodal path: {no_path}")
    print(f"With at least one reducible slice: {reducible}")
    print(f"With a paired-slice lift witness: {paired}")
    print(f"Requiring longer component chains (>1 connector): {longer}")
    print("Minimum connector-crossing histogram:")
    for crossings in sorted(crossing_histogram):
        print(f"  {crossings}: {crossing_histogram[crossings]}")

    print("First representatives:")
    for crossings in sorted(first_by_crossing):
        coloring, witness = first_by_crossing[crossings]
        print(f"  crossings={crossings}: {format_witness(witness, show_path=args.show_paths)}")
        if args.show_examples:
            print(summarize_coloring(coloring))
    if first_no_path is not None:
        print("  no-path: found")
        if args.show_examples:
            print(summarize_coloring(first_no_path))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", type=int, required=True, help="Hypercube dimension")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--enumerate", action="store_true", help="Enumerate all antipodal colorings")
    mode.add_argument("--samples", type=int, default=0, help="Sample random antipodal colorings")
    parser.add_argument(
        "--max-free-vars",
        type=int,
        default=24,
        help="Maximum free antipodal edge variables to enumerate exactly",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for --samples")
    parser.add_argument("--show-examples", action="store_true", help="Print first coloring in each class")
    parser.add_argument("--show-paths", action="store_true", help="Reconstruct and print witness paths")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.n < 2:
        raise ValueError("Use n >= 2.")
    analyze_colorings(args)


if __name__ == "__main__":
    main()
