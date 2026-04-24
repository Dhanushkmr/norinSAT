"""
Script for checking various conjectures related to Norine's conjecture and improving asymptotic bounds.
"""

import argparse
import itertools
import os
import random

from lex import lex_smaller_eq, checkLexMin

from pysat.card import CardEnc

from conjecture_encodings import (
    encode_conjecture1,
    encode_conjecture2,
    encode_conjecture3,
    encode_conjecture4,
)
from encoding_context import build_encoding_context, flip_i, swap
from f_encoding import encode_f_family
from sat_utils import make_pysat_solver, solver_help


DEFAULT_CARDINALITY_ENCODING = 7  # selected pysat encoding for cardinality constraints


def encode(
    n,
    sum_upper_bound,
    antipodal=False,
    fprime=False,
    deg_constraint=None,
    partial_sym_break=None,
    maximum_degree=None,
    conjecture1=False,
    conjecture2=False,
    conjecture3=False,
    conjecture4=False,
    conjecture6=False,
    card_type=1,
    path_version=False,
    b2=None,
    b3=None,
    first_vertex_min_degree=False,
):
    print(f"Card type: {card_type}")

    ctx = build_encoding_context(n, antipodal=antipodal)
    enc = ctx.enc
    vpool = ctx.vpool
    vertices = ctx.vertices
    graph = ctx.graph
    r = ctx.r

    has_target_encoding = False

    if conjecture1:
        encode_conjecture1(ctx)
        has_target_encoding = True

    if conjecture2:
        encode_conjecture2(ctx)
        has_target_encoding = True

    if conjecture3:
        encode_conjecture3(ctx)
        has_target_encoding = True

    if conjecture4:
        encode_conjecture4(ctx)
        has_target_encoding = True

    uses_f_family = sum_upper_bound is not None or b2 is not None or b3 is not None or conjecture6
    if uses_f_family:
        encode_f_family(
            ctx,
            sum_upper_bound=sum_upper_bound,
            fprime=fprime,
            card_type=card_type,
            path_version=path_version,
            b2=b2,
            b3=b3,
            conjecture6=conjecture6,
        )
        has_target_encoding = True

    assert has_target_encoding, "No encoding target selected. Use conjecture flags or one of -b/-b2/-b3/--conjecture6."

    print(f"Top variable: {vpool.top}")
    print(f"number of clauses: {len(enc.clauses)}")

    ## Symmetry breaking

    if partial_sym_break:
        max_comparisons = partial_sym_break

        original_signed_edges = [(1, (u, v)) for u in vertices for v in graph[u] if u < v]
        for i in range(n):
            permuted_edges = [(s, (flip_i(u, i), flip_i(v, i))) for s, (u, v) in original_signed_edges]
            enc = lex_smaller_eq(
                enc,
                vpool,
                [s * r(u, v) for s, (u, v) in original_signed_edges],
                [s * r(u, v) for s, (u, v) in permuted_edges],
            )

        for i, j in itertools.combinations(range(n), 2):
            permuted_edges = [(s, (swap(i, j, u), swap(i, j, v))) for s, (u, v) in original_signed_edges]
            enc = lex_smaller_eq(
                enc,
                vpool,
                [s * r(u, v) for s, (u, v) in original_signed_edges],
                [s * r(u, v) for s, (u, v) in permuted_edges],
                maxcomparisons=max_comparisons,
            )

        for i, j in itertools.combinations(range(n), 2):
            for k in range(n):
                permuted_edges = [(s, (swap(i, j, flip_i(u, k)), swap(i, j, flip_i(v, k)))) for s, (u, v) in original_signed_edges]
                enc = lex_smaller_eq(
                    enc,
                    vpool,
                    [s * r(u, v) for s, (u, v) in original_signed_edges],
                    [s * r(u, v) for s, (u, v) in permuted_edges],
                    maxcomparisons=max_comparisons,
                )

        print(f"Number of clauses after adding symmetry breaking: {len(enc.clauses)}")

    if maximum_degree is not None:
        # Just for the first vertex, rest by symmetry
        enc.extend(
            CardEnc.atmost(
                [r(vertices[0], v) for v in graph[vertices[0]]],
                bound=maximum_degree,
                vpool=vpool,
                encoding=card_type,
            )
        )

    if first_vertex_min_degree:
        from counter import counterFunction

        count_up_to = n
        count_vars0 = counterFunction(
            [r(vertices[0], v) for v in graph[vertices[0]]],
            countUpto=count_up_to,
            vPool=vpool,
            clauses=enc.clauses,
        )

        # each vertex doesn't have less edges
        for v in vertices[1:]:
            count_vars = counterFunction(
                [r(v, u) for u in graph[v]],
                countUpto=count_up_to,
                vPool=vpool,
                clauses=enc.clauses,
            )

            for i in range(count_up_to):
                enc.append([-count_vars0[i], count_vars[i]])

    print(f"Total number of clauses: {len(enc.clauses)}")

    return enc, ctx.var_to_edge


def cube_and_conquer(n, enc, var_to_edge, cubing_depth=10):
    """
    Manual cubing. (Automatic cubing turned out to be superior over this cubing)
    """

    random.seed(42)  # for shuffling the cubes

    cubes = []
    edges = []
    vertices = list(itertools.product([0, 1], repeat=n))
    graph = {}
    for v in vertices:
        graph[v] = []
        for i in range(n):
            neighbor = [v[j] if i != j else (1 - v[j]) for j in range(n)]
            graph[v].append(tuple(neighbor))

    edge_to_var = {v: k for k, v in var_to_edge.items()}

    for v in vertices:
        assert len(graph[v]) == n, f"Graph is not a hypercube: {v} has {len(graph[v])} neighbors"

    for u in vertices[30:35]:
        for v in graph[u]:
            if u < v:
                edges.append((u, v))
    random.shuffle(edges)
    edges = edges[:cubing_depth]

    edges_lits = []
    for u, v in edges:
        elit = edge_to_var[(u, v)] if (u, v) in edge_to_var else edge_to_var[(v, u)]
        if -elit in edges_lits:
            continue
        edges_lits.append(elit)

    for edge_vals in itertools.product([0, 1], repeat=len(edges_lits)):
        cube = []
        for i, edge_lit in enumerate(edges_lits):
            if edge_vals[i] == 1:
                cube.append(edge_lit)
            else:
                cube.append(-edge_lit)
        cubes.append(cube)
    random.shuffle(cubes)
    return cubes


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Norine's conjecture")
    argparser.add_argument("-n", type=int, help="Order of the hypercube graph", required=True)
    argparser.add_argument("--tmp-file", type=str, help="Temporary file to store the encoding", default="norine_tmp.cnf")
    argparser.add_argument("--no-solve", action="store_true", help="Do not use solver, just create the encoding and save it to the temp file")
    argparser.add_argument(
        "--nauty", action="store_true", help="Use nauty for checking final solutions for isomorphic copies(only if pysat solver is used)"
    )
    argparser.add_argument(
        "--use-pysat-solver", action="store_true", help="Use pysat solver instead of custom SMS version and check for isomorphic copies at the end"
    )
    argparser.add_argument("-a", "--all", action="store_true", help="Enumerate all models")
    argparser.add_argument("--partial-sym-break", type=int, help="Max comparisons for partial symbreak", default=20)
    argparser.add_argument("--antipodal-coloring", action="store_true", help="Enforce that the coloring is antipodal")

    # argparser.add_argument("--path", action="store_true", help="Allow general paths not only geodesics")

    argparser.add_argument("-b", type=int, help="Upper bound on f function or f'")
    argparser.add_argument("-p", "--fprime", action="store_true", help="Use f' instead of f, i.e., primed version")
    argparser.add_argument("-b2", type=int, help="Upperbound on bad antipodal pairs, i.e., strictly more than one swap")
    argparser.add_argument("-b3", type=int, help="Upperbound on slightly bad antipodal pairs, i.e., more than zero swaps")

    argparser.add_argument("--conjecture1", action="store_true", help="(Antipodal coloring) Antipodal vertex pair with monochromatic path")
    argparser.add_argument("--conjecture2", action="store_true", help="(Antipodal coloring) Antipodal vertex pair with monochromatic geodesic")
    argparser.add_argument(
        "--conjecture3",
        action="store_true",
        help="(General coloring) Antipodal vertex pair with path having at most one color change",
    )
    argparser.add_argument(
        "--conjecture4",
        action="store_true",
        help="(General coloring) Antipodal vertex pair with geodesic having at most one color change",
    )
    argparser.add_argument(
        "--conjecture6",
        action="store_true",
        help="For each geodesic there is a vertex on the path such that is not blocked. (not compatable with symmetry breaking)",
    )

    argparser.add_argument(
        "--cardinality-contraint",
        type=int,
        help="Type of cardinality constraint to use in pysat (1 is sequential)",
        default=DEFAULT_CARDINALITY_ENCODING,
    )

    argparser.add_argument("--cnc", type=int, help="Cubing depth for cube and conquer", default=None)

    argparser.add_argument("--maximum-degree", type=int, help="Ensure that the first vertex has at most the given degree")
    argparser.add_argument("--first-vertex-min-degree", action="store_true", help="Ensure that the first vertex has the lowest red degree")
    argparser.add_argument("--solver", default=None, help=solver_help())

    args = argparser.parse_args()

    print(f"Arguments: {args}")
    n = args.n

    encoding, var_to_edge = encode(
        n,
        args.b,
        antipodal=args.antipodal_coloring,
        fprime=args.fprime,
        partial_sym_break=args.partial_sym_break,
        maximum_degree=args.maximum_degree,
        conjecture1=args.conjecture1,
        conjecture2=args.conjecture2,
        conjecture3=args.conjecture3,
        conjecture4=args.conjecture4,
        conjecture6=args.conjecture6,
        card_type=args.cardinality_contraint,
        b2=args.b2,
        b3=args.b3,
        first_vertex_min_degree=args.first_vertex_min_degree,
    )

    tmp_file = args.tmp_file

    if args.cnc is not None:
        print(f"Using cube and conquer with cubing depth {args.cnc}")
        cubes = cube_and_conquer(n, encoding, var_to_edge, cubing_depth=args.cnc)
        print(f"Generated {len(cubes)} cubes for cubing depth {args.cnc}")
        with open(f"n{n}_{args.cnc}.cubes", "w") as f:
            f.write("p inccnf\n")
            for cls in encoding.clauses:
                f.write(" ".join(str(lit) for lit in cls) + " 0\n")
            for cube in cubes:
                f.write("a " + " ".join(str(lit) for lit in cube) + " 0\n")
        print(f"Wrote cubes to n{n}_{args.cnc}.cubes")

    if args.no_solve:
        encoding.to_file(tmp_file)
        raise SystemExit(0)

    if not args.use_pysat_solver:
        # use SMS for solving
        frequency = 30
        cmd = f"time ./dynamic/build/src/norine {n} {frequency} {1 if args.all else 0} {tmp_file}"

        encoding.to_file(tmp_file)
        print("Execute command:", cmd)
        os.system(cmd)
        os.remove(tmp_file)

    else:
        solver, solver_name = make_pysat_solver(args.solver)
        print(f"Solver: {solver_name}")
        for clause in encoding:
            solver.add_clause(clause)
        r = True

        num_edge_vars = 2 ** (n - 1) * n

        num_models = 0
        num_minimal_models = 0

        path_for_graphs = f"graphs_{n}.g6"
        path_for_filtered_graphs = f"graphs_filtered_{n}.g6"

        os.remove(path_for_graphs) if os.path.exists(path_for_graphs) else None

        print("Start solving...")
        while r:
            r = solver.solve()

            if r:
                num_models += 1
                model = solver.get_model()
                red_edges = [var_to_edge[abs(lit)] for lit in model[:num_edge_vars] if lit > 0]

                if checkLexMin(red_edges, n):
                    num_minimal_models += 1

                if args.nauty:
                    # we used nauty to check the correctness/completeness of our symmetry breaking
                    from graph6 import graph6

                    with open(path_for_graphs, "a") as f:
                        f.write(graph6(red_edges, n) + "\n")

                # block model on edge variables
                solver.add_clause([-model[i] for i in range(num_edge_vars)])

        print(f"Number of models: {num_models}")
        print(f"Number of minimal models: {num_minimal_models}")

        if args.nauty:
            os.system(f"shortg {path_for_graphs} {path_for_filtered_graphs}")
