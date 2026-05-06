import unittest

from bicross_cube_search import build_cubes, choose_cube_edges, parse_index_set
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


if __name__ == "__main__":
    unittest.main()
