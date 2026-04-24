"""
SAT search for antipodal colorings with no one-connector component-chain witness.

A one-connector witness for coordinate i, color c, and antipodal pair
v, anti(v) consists of a connector edge x--flip_i(x) of color c such that:

- v is connected to x by color c inside one i-slice, and
- flip_i(x) is connected to anti(v) by color c inside the opposite i-slice.

Such a witness immediately reconstructs a monochromatic antipodal path.  This
script encodes the negation: an antipodal coloring with no such witness.
"""

import argparse
import itertools

from component_chain_classifier import classify_coloring, format_witness
from encoding_context import anti, build_encoding_context, build_hypercube_graph, flip_i, swap
from induction_probe import edge_key, monochromatic_antipodal_path
from lex import lex_smaller_eq
from sat_utils import make_pysat_solver, solver_help


def log(message):
    print(message, flush=True)


def color_name(color):
    return "red" if color else "blue"


def insert_coordinate(v, dimension, side):
    return v[:dimension] + (side,) + v[dimension:]


def projected_slice_vertices(n, dimension, side):
    small_vertices, _ = build_hypercube_graph(n - 1)
    return [insert_coordinate(v, dimension, side) for v in small_vertices]


def encode_slice_reachability(ctx, dimension, side, target_color, root_small):
    color = color_name(target_color)
    p = lambda v: ctx.vpool.id(f"one_connector_p_{dimension}_{side}_{color}_{root_small}_{v}")

    root = insert_coordinate(root_small, dimension, side)
    slice_vertices = projected_slice_vertices(ctx.n, dimension, side)
    slice_vertex_set = set(slice_vertices)

    ctx.enc.append([p(root)])

    for u in slice_vertices:
        for v in ctx.graph[u]:
            if v not in slice_vertex_set:
                continue

            edge_lit = ctx.r(u, v)
            if target_color:
                ctx.enc.append([-p(u), -edge_lit, p(v)])
            else:
                ctx.enc.append([-p(u), edge_lit, p(v)])

    return p


def connector_color_clause(p0_lit, connector_lit, p1_lit, target_color):
    if target_color:
        return [-p0_lit, -connector_lit, -p1_lit]
    return [-p0_lit, connector_lit, -p1_lit]


def encode_no_one_connector_witness(ctx):
    small_vertices, _ = build_hypercube_graph(ctx.n - 1)

    for dimension in range(ctx.n):
        for target_color in (False, True):
            reach = {}

            for side in (0, 1):
                for root_small in small_vertices:
                    reach[(side, root_small)] = encode_slice_reachability(
                        ctx,
                        dimension,
                        side,
                        target_color,
                        root_small,
                    )

            for start_small in small_vertices:
                end_small = anti(start_small)
                p0 = reach[(0, start_small)]
                p1 = reach[(1, end_small)]

                for connector_small in small_vertices:
                    connector0 = insert_coordinate(connector_small, dimension, 0)
                    connector1 = insert_coordinate(connector_small, dimension, 1)
                    connector_lit = ctx.r(connector0, connector1)
                    ctx.enc.append(
                        connector_color_clause(
                            p0(connector0),
                            connector_lit,
                            p1(connector1),
                            target_color,
                        )
                    )


def add_partial_symmetry_breaking(ctx, max_comparisons):
    original_signed_edges = [(1, (u, v)) for u in ctx.vertices for v in ctx.graph[u] if u < v]

    for i in range(ctx.n):
        permuted_edges = [(s, (flip_i(u, i), flip_i(v, i))) for s, (u, v) in original_signed_edges]
        ctx.enc = lex_smaller_eq(
            ctx.enc,
            ctx.vpool,
            [s * ctx.r(u, v) for s, (u, v) in original_signed_edges],
            [s * ctx.r(u, v) for s, (u, v) in permuted_edges],
        )

    for i, j in itertools.combinations(range(ctx.n), 2):
        permuted_edges = [(s, (swap(i, j, u), swap(i, j, v))) for s, (u, v) in original_signed_edges]
        ctx.enc = lex_smaller_eq(
            ctx.enc,
            ctx.vpool,
            [s * ctx.r(u, v) for s, (u, v) in original_signed_edges],
            [s * ctx.r(u, v) for s, (u, v) in permuted_edges],
            maxcomparisons=max_comparisons,
        )

    for i, j in itertools.combinations(range(ctx.n), 2):
        for k in range(ctx.n):
            permuted_edges = [
                (s, (swap(i, j, flip_i(u, k)), swap(i, j, flip_i(v, k))))
                for s, (u, v) in original_signed_edges
            ]
            ctx.enc = lex_smaller_eq(
                ctx.enc,
                ctx.vpool,
                [s * ctx.r(u, v) for s, (u, v) in original_signed_edges],
                [s * ctx.r(u, v) for s, (u, v) in permuted_edges],
                maxcomparisons=max_comparisons,
            )


def add_first_vertex_min_degree(ctx):
    from counter import counterFunction

    count_up_to = ctx.n
    first_vertex = ctx.vertices[0]
    count_vars0 = counterFunction(
        [ctx.r(first_vertex, v) for v in ctx.graph[first_vertex]],
        countUpto=count_up_to,
        vPool=ctx.vpool,
        clauses=ctx.enc.clauses,
    )

    for v in ctx.vertices[1:]:
        count_vars = counterFunction(
            [ctx.r(v, u) for u in ctx.graph[v]],
            countUpto=count_up_to,
            vPool=ctx.vpool,
            clauses=ctx.enc.clauses,
        )
        for i in range(count_up_to):
            ctx.enc.append([-count_vars0[i], count_vars[i]])


def literal_is_true(model, lit):
    return lit in model if lit > 0 else -lit not in model


def model_to_coloring(ctx, model):
    model_set = set(model)
    coloring = {}
    for u in ctx.vertices:
        for v in ctx.graph[u]:
            if u < v:
                coloring[edge_key(u, v)] = literal_is_true(model_set, ctx.r(u, v))
    return coloring


def write_coloring(path, coloring):
    with open(path, "w") as f:
        for edge in sorted(coloring):
            u, v = edge
            color = "R" if coloring[edge] else "B"
            f.write(f"{''.join(map(str, u))}-{''.join(map(str, v))} {color}\n")


def solve(args):
    ctx = build_encoding_context(args.n, antipodal=True)
    encode_no_one_connector_witness(ctx)

    log(f"Dimension: Q_{args.n}")
    log(f"Top variable: {ctx.vpool.top}")
    log(f"Clauses: {len(ctx.enc.clauses)}")

    if args.partial_sym_break:
        add_partial_symmetry_breaking(ctx, args.partial_sym_break)
        log(f"Clauses after symmetry breaking: {len(ctx.enc.clauses)}")

    if args.first_vertex_min_degree:
        add_first_vertex_min_degree(ctx)
        log(f"Clauses after first-vertex min-degree: {len(ctx.enc.clauses)}")

    if args.no_solve:
        ctx.enc.to_file(args.tmp_file)
        log(f"Wrote CNF to {args.tmp_file}")
        return

    solver, solver_name = make_pysat_solver(args.solver)
    log(f"Solver: {solver_name}")
    for clause in ctx.enc:
        solver.add_clause(clause)

    result = solver.solve()
    log(f"SAT: {result}")

    if result:
        model = solver.get_model()
        coloring = model_to_coloring(ctx, model)
        log(f"Verified monochromatic antipodal path: {monochromatic_antipodal_path(coloring, args.n)}")
        witness = classify_coloring(coloring, args.n, include_path=args.show_path)
        log(f"Component-chain witness: {format_witness(witness, show_path=args.show_path)}")
        if args.model_out:
            write_coloring(args.model_out, coloring)
            log(f"Wrote model coloring to {args.model_out}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", type=int, required=True, help="Hypercube dimension")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--no-solve", action="store_true", help="Only write the CNF")
    parser.add_argument("--tmp-file", default="one_connector_witness.cnf", help="CNF path for --no-solve")
    parser.add_argument("--partial-sym-break", type=int, default=0, help="Max comparisons for partial symmetry breaking")
    parser.add_argument("--first-vertex-min-degree", action="store_true", help="Symmetry-break by making vertex 0 min red degree")
    parser.add_argument("--show-path", action="store_true", help="Include a reconstructed path if SAT")
    parser.add_argument("--model-out", help="Write the SAT model coloring as an edge list")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.n < 2:
        raise ValueError("Use n >= 2.")
    solve(args)


if __name__ == "__main__":
    main()
