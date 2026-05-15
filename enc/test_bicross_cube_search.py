import unittest

from bicross_cube_search import build_cubes, choose_cube_edges, parse_index_set, solve_cube_chunk
from induction_probe import all_edges


class BicrossCubeSearchTests(unittest.TestCase):
    def test_parse_index_set_accepts_ranges_and_singletons(self):
        self.assertEqual(parse_index_set("0,2,4-6,9"), {0, 2, 4, 5, 6, 9})
        self.assertIsNone(parse_index_set(None))
        self.assertIsNone(parse_index_set(""))

    def test_build_cubes_keeps_binary_index_order(self):
        cubes = list(build_cubes((10, 20, 30)))

        self.assertEqual(cubes[0], (-10, -20, -30))
        self.assertEqual(cubes[1], (-10, -20, 30))
        self.assertEqual(cubes[6], (10, 20, -30))
        self.assertEqual(cubes[7], (10, 20, 30))

    def test_zero_pattern_tail_uses_cube_dimension(self):
        _, _, edges = all_edges(3)
        selected = choose_cube_edges(edges, depth=5, mode="zero-pattern-tail", seed=1, offset=0)

        self.assertEqual(selected[:3], tuple(edges[:3]))
        self.assertEqual(selected[3:], tuple(edges[3:5]))
        self.assertEqual(len(set(selected)), 5)

    def test_window_respects_offset(self):
        _, _, edges = all_edges(4)

        self.assertEqual(
            choose_cube_edges(edges, depth=4, mode="window", seed=1, offset=3),
            tuple(edges[3:7]),
        )


class OptionalSatBicrossCubeSearchTests(unittest.TestCase):
    def test_forbid_frontier_branches_q4_prefix_cubes_unsat(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        from bicross_probe import encode_pair_hit_bound

        solver, _, r, _, _, clauses = encode_pair_hit_bound(
            4,
            hit_bound=6,
            sort_zero_edges=True,
            zero_red_degree_at_most_half=True,
            partial_sym_break=12,
            forbid_perfect_inherited_splits=True,
        )
        solver.delete()

        _, _, edges = all_edges(4)
        cube_edges = choose_cube_edges(edges, depth=4, mode="prefix", seed=20260425)
        cube_literals = tuple(r(*edge) for edge in cube_edges)
        edge_literals = tuple((edge, r(*edge)) for edge in edges)
        cubes = list(enumerate(build_cubes(cube_literals)))

        result = solve_cube_chunk(
            0,
            clauses,
            cubes,
            None,
            0,
            edge_literals,
            4,
            False,
            True,
            0,
        )

        self.assertEqual(result["counts"].get("sat", 0), 0)
        self.assertEqual(result["counts"].get("unknown", 0), 0)
        self.assertEqual(result["counts"].get("unsat", 0), 16)
        self.assertGreater(result["postcheck_rejections"], 0)


if __name__ == "__main__":
    unittest.main()
