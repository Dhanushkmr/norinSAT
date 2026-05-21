import unittest

from bicross_cube_search import build_cubes, choose_cube_edges
from induction_probe import all_edges
from two_color_cross_cube_search import solve_cube_chunk
from two_color_cross_probe import encode_cross_cover_negation


class OptionalSatTwoColorCrossCubeSearchTests(unittest.TestCase):
    def test_q4_prefix_cubes_unsat(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        solver, _vpool, r, _bad, clauses = encode_cross_cover_negation(
            4,
            sort_zero_edges=True,
            zero_red_degree_at_most_half=True,
            partial_sym_break=8,
        )
        solver.delete()

        _vertices, _graph, edges = all_edges(4)
        cube_edges = choose_cube_edges(edges, depth=4, mode="prefix", seed=20260521)
        cube_literals = tuple(r(0, *edge) for edge in cube_edges)
        cubes = list(enumerate(build_cubes(cube_literals)))

        result = solve_cube_chunk(0, clauses, cubes, None, 0)

        self.assertEqual(result["counts"].get("sat", 0), 0)
        self.assertEqual(result["counts"].get("unknown", 0), 0)
        self.assertEqual(result["counts"].get("unsat", 0), 16)


if __name__ == "__main__":
    unittest.main()
