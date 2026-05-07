import unittest

from bicross_adaptive_cube_search import choose_ordered_cube_edges, cube_from_index, expand_indexes, format_index_ranges


class BicrossAdaptiveCubeSearchTests(unittest.TestCase):
    def test_cube_from_index_matches_binary_order(self):
        literals = (10, 20, 30, 40)

        self.assertEqual(cube_from_index(literals, 4, 0), (-10, -20, -30, -40))
        self.assertEqual(cube_from_index(literals, 4, 1), (-10, -20, -30, 40))
        self.assertEqual(cube_from_index(literals, 4, 6), (-10, 20, 30, -40))
        self.assertEqual(cube_from_index(literals, 4, 15), (10, 20, 30, 40))

    def test_expand_indexes_descends_to_children(self):
        self.assertEqual(expand_indexes([3], 2, 4), [12, 13, 14, 15])
        self.assertEqual(expand_indexes([1, 4], 3, 5), [4, 5, 6, 7, 16, 17, 18, 19])

    def test_format_index_ranges_compacts_sorted_ranges(self):
        self.assertEqual(format_index_ranges([5, 3, 4, 9, 11, 10]), "3-5,9-11")
        self.assertEqual(format_index_ranges([]), "")

    def test_choose_ordered_cube_edges_keeps_prefix_before_spread_tail(self):
        edges = tuple(range(20))
        selected = choose_ordered_cube_edges(edges, max_depth=8, tail_start_depth=4, tail_mode="spread")

        self.assertEqual(selected[:4], (0, 1, 2, 3))
        self.assertEqual(len(selected), 8)
        self.assertEqual(len(set(selected)), 8)
        self.assertNotEqual(selected[4:], (4, 5, 6, 7))


if __name__ == "__main__":
    unittest.main()
