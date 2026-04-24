"""
SAT search for antipodal colorings with no paired-slice lift witness.

A paired-slice lift witness is a coordinate split, a color, and a projected
antipodal pair x, anti(x) such that x and anti(x) are connected by that color in
both Q_{n-1} slices.  Such a witness forces a full monochromatic antipodal path
in Q_n for every legal connector coloring.

This script asks whether an antipodal coloring exists with no such witness.
"""

import argparse

from component_chain_classifier import classify_coloring, format_witness
from encoding_context import anti, antipodal_representatives, build_encoding_context, build_hypercube_graph
from induction_probe import edge_key, monochromatic_antipodal_path, paired_slice_lift_witness
from sat_utils import make_pysat_solver, solver_help


def insert_coordinate(v, dimension, side):
    return v[:dimension] + (side,) + v[dimension:]


def projected_slice_vertices(n, dimension, side):
    small_vertices, _ = build_hypercube_graph(n - 1)
    return [insert_coordinate(v, dimension, side) for v in small_vertices]


def encode_slice_reachability(ctx, dimension, side, target_color, root_small):
    color_name = "red" if target_color else "blue"
    p = lambda v: ctx.vpool.id(f"slice_p_{dimension}_{side}_{color_name}_{root_small}_{v}")

    root = insert_coordinate(root_small, dimension, side)
    slice_vertices = projected_slice_vertices(ctx.n, dimension, side)
    slice_vertex_set = set(slice_vertices)

    for v in ctx.graph[root]:
        if v not in slice_vertex_set:
            continue
        edge_lit = ctx.r(root, v)
        if target_color:
            ctx.enc.append([-edge_lit, p(v)])
        else:
            ctx.enc.append([edge_lit, p(v)])

    for w in slice_vertices:
        if w == root:
            continue
        for v in ctx.graph[w]:
            if v not in slice_vertex_set or v == root:
                continue
            edge_lit = ctx.r(v, w)
            if target_color:
                ctx.enc.append([-p(v), -edge_lit, p(w)])
            else:
                ctx.enc.append([-p(v), edge_lit, p(w)])

    return p


def encode_no_paired_slice_lift_witness(ctx):
    small_vertices, _ = build_hypercube_graph(ctx.n - 1)
    roots = list(antipodal_representatives(small_vertices))

    for dimension in range(ctx.n):
        for root_small in roots:
            target_small = anti(root_small)
            for target_color in (False, True):
                p0 = encode_slice_reachability(ctx, dimension, 0, target_color, root_small)
                p1 = encode_slice_reachability(ctx, dimension, 1, target_color, root_small)

                target0 = insert_coordinate(target_small, dimension, 0)
                target1 = insert_coordinate(target_small, dimension, 1)
                ctx.enc.append([-p0(target0), -p1(target1)])


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
    encode_no_paired_slice_lift_witness(ctx)

    print(f"Dimension: Q_{args.n}")
    print(f"Top variable: {ctx.vpool.top}")
    print(f"Clauses: {len(ctx.enc.clauses)}")

    if args.no_solve:
        ctx.enc.to_file(args.tmp_file)
        print(f"Wrote CNF to {args.tmp_file}")
        return

    solver, solver_name = make_pysat_solver(args.solver)
    print(f"Solver: {solver_name}")
    for clause in ctx.enc:
        solver.add_clause(clause)

    result = solver.solve()
    print(f"SAT: {result}")
    if result:
        model = solver.get_model()
        coloring = model_to_coloring(ctx, model)
        print(f"Verified paired-slice lift witness: {paired_slice_lift_witness(coloring, args.n)}")
        print(f"Verified monochromatic antipodal path: {monochromatic_antipodal_path(coloring, args.n)}")
        if args.analyze_model:
            witness = classify_coloring(coloring, args.n, include_path=args.show_path)
            print(f"Component-chain witness: {format_witness(witness, show_path=args.show_path)}")
        if args.model_out:
            write_coloring(args.model_out, coloring)
            print(f"Wrote model coloring to {args.model_out}")

    if result and args.print_model_edges:
        model = set(model)
        edge_vars = sorted(ctx.var_to_edge)
        for var in edge_vars:
            if var in model:
                u, v = ctx.var_to_edge[var]
                print(f"{''.join(map(str, u))}-{''.join(map(str, v))} R")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-n", type=int, required=True, help="Hypercube dimension")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--no-solve", action="store_true", help="Only write the CNF")
    parser.add_argument("--tmp-file", default="paired_slice_witness.cnf", help="CNF path for --no-solve")
    parser.add_argument("--print-model-edges", action="store_true", help="Print red edges when SAT")
    parser.add_argument("--analyze-model", action="store_true", help="Classify the SAT model by component-chain crossings")
    parser.add_argument("--show-path", action="store_true", help="Include the reconstructed path in --analyze-model output")
    parser.add_argument("--model-out", help="Write the SAT model coloring as an edge list")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.n < 3:
        raise ValueError("Use n >= 3 so slices have nontrivial antipodal pairs.")
    solve(args)


if __name__ == "__main__":
    main()
