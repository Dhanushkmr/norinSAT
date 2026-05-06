"""Lift a high pair-hit coloring and locally improve it.

Random edge-colorings of larger cubes usually have very few bad vertices, so a
plain random local search starts far from the bicross frontier.  This helper
starts from a SAT-found high-hit coloring in Q_{m-1}, doubles it into Q_m, and
then searches by edge flips from that lifted near-obstruction.
"""

from __future__ import annotations

import argparse
import math
import random

from bicross_probe import (
    BLUE,
    RED,
    antipodal_pair_profile,
    bad_vertices,
    bad_vertices_hit_every_antipodal_pair,
    bicross_witness,
    color_name,
    doubled_coloring,
    encode_pair_hit_bound,
    format_bicross_witness,
    format_slice_analysis,
    literal_is_true,
    local_search_score,
    local_search_score_value,
    summarize_coloring,
)
from induction_probe import all_edges
from sat_utils import best_pysat_solver_name, solver_help


def model_to_coloring(model, edges, r):
    model_set = set(model)
    return {edge: literal_is_true(model_set, r(*edge)) for edge in edges}


def solve_seed_coloring(args):
    solver, _, r, _, _, _ = encode_pair_hit_bound(
        args.seed_dimension,
        args.seed_hit_bound,
        args.solver,
        sort_zero_edges=args.sort_zero_edges,
        zero_red_degree_at_most_half=args.zero_red_degree_at_most_half,
        partial_sym_break=args.partial_sym_break,
    )
    print(
        f"Solving seed: Q_{args.seed_dimension}, pair-hit >= {args.seed_hit_bound}, "
        f"solver={best_pysat_solver_name(args.solver)}",
        flush=True,
    )
    is_sat = solver.solve()
    if not is_sat:
        solver.delete()
        raise SystemExit("Seed formula is UNSAT; choose a lower seed hit bound.")

    _, _, edges = all_edges(args.seed_dimension)
    coloring = model_to_coloring(solver.get_model(), edges, r)
    solver.delete()
    return coloring


def pair_hits_from_profile(profile):
    return profile["one_good"] + profile["both_bad"]


def format_profile(prefix, coloring, m):
    profile = antipodal_pair_profile(coloring, m)
    actual_bad = bad_vertices(coloring, m)
    return (
        f"{prefix}: pairs_hit={pair_hits_from_profile(profile)}, "
        f"bad={len(actual_bad)}, "
        f"both_good={profile['both_good']}, "
        f"one_good={profile['one_good']}, "
        f"both_bad={profile['both_bad']}"
    )


def lift_variants(seed_coloring, seed_dimension):
    for dimension in range(seed_dimension + 1):
        for connector_color in (BLUE, RED):
            yield dimension, connector_color, doubled_coloring(seed_coloring, seed_dimension, connector_color, dimension)


def locally_improve(start_coloring, m, args, rng):
    _, _, edges = all_edges(m)
    coloring = dict(start_coloring)
    score = local_search_score(coloring, m, args.objective)
    best_coloring = dict(coloring)
    best_score = score
    accepted = 0
    temperature = max(0.001, args.temperature)

    for _ in range(args.kick_flips):
        edge = edges[rng.randrange(len(edges))]
        coloring[edge] = not coloring[edge]
    if args.kick_flips:
        score = local_search_score(coloring, m, args.objective)

    for step in range(args.steps):
        edge = edges[rng.randrange(len(edges))]
        coloring[edge] = not coloring[edge]
        next_score = local_search_score(coloring, m, args.objective)
        delta = local_search_score_value(next_score, m) - local_search_score_value(score, m)
        accept = next_score >= score or rng.random() < math.exp(delta / temperature)
        if accept:
            score = next_score
            accepted += 1
        else:
            coloring[edge] = not coloring[edge]

        temperature *= args.cooling

        if score > best_score:
            best_score = score
            best_coloring = dict(coloring)
            print(f"  improved at step={step + 1}: score={best_score}", flush=True)

    return best_coloring, best_score, accepted


def best_one_flip(coloring, m, objective):
    _, _, edges = all_edges(m)
    current_score = local_search_score(coloring, m, objective)
    best_score = current_score
    best_edges = []
    equal_edges = 0
    improving_edges = 0

    for edge in edges:
        coloring[edge] = not coloring[edge]
        score = local_search_score(coloring, m, objective)
        coloring[edge] = not coloring[edge]
        if score > current_score:
            improving_edges += 1
        elif score == current_score:
            equal_edges += 1
        if score > best_score:
            best_score = score
            best_edges = [edge]
        elif score == best_score and score > current_score:
            best_edges.append(edge)

    return current_score, best_score, best_edges, improving_edges, equal_edges


def greedy_improve(start_coloring, m, args):
    coloring = dict(start_coloring)
    for pass_index in range(args.greedy_passes):
        current_score, best_score, best_edges, improving_edges, equal_edges = best_one_flip(
            coloring,
            m,
            args.objective,
        )
        print(
            f"greedy_pass={pass_index + 1}; current={current_score}; best_one_flip={best_score}; "
            f"improving_edges={improving_edges}; equal_edges={equal_edges}",
            flush=True,
        )
        if not best_edges:
            break
        edge = best_edges[0]
        coloring[edge] = not coloring[edge]
    return coloring, local_search_score(coloring, m, args.objective)


def run(args):
    if args.seed_dimension != args.m - 1:
        raise SystemExit("V1 expects --seed-dimension to be exactly m-1.")

    seed = solve_seed_coloring(args)
    print(format_profile(f"Seed Q_{args.seed_dimension}", seed, args.seed_dimension), flush=True)

    variants = list(lift_variants(seed, args.seed_dimension))
    scored_variants = []
    for dimension, connector_color, coloring in variants:
        score = local_search_score(coloring, args.m, args.objective)
        scored_variants.append((score, dimension, connector_color, coloring))
        print(
            f"Lift dimension={dimension} connector={color_name(connector_color)} score={score}; "
            + format_profile(f"Q_{args.m}", coloring, args.m),
            flush=True,
        )

    scored_variants.sort(key=lambda item: item[0], reverse=True)
    best_score, best_dimension, best_connector, best_coloring = scored_variants[0]
    rng = random.Random(args.seed)
    total_accepted = 0

    if args.scan_neighborhood:
        current_score, one_flip_score, best_edges, improving_edges, equal_edges = best_one_flip(
            best_coloring,
            args.m,
            args.objective,
        )
        print(
            f"Initial best one-flip scan: current={current_score}; best_one_flip={one_flip_score}; "
            f"improving_edges={improving_edges}; equal_edges={equal_edges}",
            flush=True,
        )
        if best_edges:
            print(
                "Initial improving edges: "
                + ", ".join(f"{edge[0]}-{edge[1]}" for edge in best_edges[: args.max_report_edges]),
                flush=True,
            )

    if args.greedy_passes:
        candidate, score = greedy_improve(best_coloring, args.m, args)
        if score > best_score:
            best_score = score
            best_coloring = candidate

    for restart in range(args.restarts):
        _, dimension, connector_color, start = scored_variants[restart % len(scored_variants)]
        print(
            f"restart={restart + 1}; start_dimension={dimension}; "
            f"connector={color_name(connector_color)}; best_score={best_score}",
            flush=True,
        )
        candidate, score, accepted = locally_improve(start, args.m, args, rng)
        total_accepted += accepted
        if score > best_score:
            best_score = score
            best_dimension = dimension
            best_connector = connector_color
            best_coloring = candidate

    print(f"Dimension: Q_{args.m}")
    print(f"Seed dimension: Q_{args.seed_dimension}")
    print(f"Seed pair-hit lower bound: {args.seed_hit_bound}")
    print(f"Objective: {args.objective}")
    print(f"Restarts: {args.restarts}")
    print(f"Steps per restart: {args.steps}")
    print(f"Kick flips per restart: {args.kick_flips}")
    print(f"Accepted moves: {total_accepted}")
    print(f"Best lift dimension: {best_dimension}")
    print(f"Best connector color: {color_name(best_connector)}")
    print(f"Best score: {best_score}")
    print(format_profile("Best", best_coloring, args.m))
    print(f"Bad vertices hit every antipodal pair: {bad_vertices_hit_every_antipodal_pair(best_coloring, args.m)}")
    print(f"Bicross witness: {format_bicross_witness(bicross_witness(best_coloring, args.m))}")
    if args.show_examples:
        print(summarize_coloring(best_coloring))
    if args.show_slices:
        print(format_slice_analysis(best_coloring, args.m))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-m", type=int, required=True, help="Target ordinary cube dimension")
    parser.add_argument("--seed-dimension", type=int, help="Seed dimension; defaults to m-1")
    parser.add_argument("--seed-hit-bound", type=int, required=True, help="Pair-hit lower bound for the seed SAT solve")
    parser.add_argument("--steps", type=int, default=5000, help="Local-search edge flips per restart")
    parser.add_argument("--restarts", type=int, default=10, help="Local-search restarts from lift variants")
    parser.add_argument("--kick-flips", type=int, default=0, help="Random flips before each restart")
    parser.add_argument("--scan-neighborhood", action="store_true", help="Scan all one-edge flips of the best lift")
    parser.add_argument("--greedy-passes", type=int, default=0, help="Apply up to N best improving one-edge flips")
    parser.add_argument("--max-report-edges", type=int, default=12, help="Maximum improving edges to print")
    parser.add_argument(
        "--objective",
        choices=("bad", "pairs-hit"),
        default="pairs-hit",
        help="Local-search objective",
    )
    parser.add_argument("--temperature", type=float, default=5000.0, help="Initial local-search temperature")
    parser.add_argument("--cooling", type=float, default=0.9995, help="Local-search cooling multiplier")
    parser.add_argument("--seed", type=int, default=20260507, help="Random seed")
    parser.add_argument("--solver", default=None, help=solver_help())
    parser.add_argument("--sort-zero-edges", action="store_true", help="Sort colors incident to 00...0 in the seed solve")
    parser.add_argument("--zero-red-degree-at-most-half", action="store_true", help="Bound red degree at 00...0 in seed solve")
    parser.add_argument("--partial-sym-break", type=int, default=0, help="Coordinate/bit-flip lex comparison cap")
    parser.add_argument("--show-examples", action="store_true", help="Print best coloring edge list")
    parser.add_argument("--show-slices", action="store_true", help="Print best coloring slice diagnostics")
    args = parser.parse_args()
    if args.seed_dimension is None:
        args.seed_dimension = args.m - 1
    return args


def main():
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
