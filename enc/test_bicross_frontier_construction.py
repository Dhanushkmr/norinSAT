import unittest

from bicross_frontier_construction import (
    paired_coordinate_coloring,
    predicted_good_vertices,
    predicted_max_hit,
    predicted_min_bicross,
    predicted_pair_profile,
    validate_paired_construction,
)
from bicross_probe import antipodal_pair_profile, bad_vertices, good_vertices


class BicrossFrontierConstructionTests(unittest.TestCase):
    def test_paired_coordinate_construction_matches_predicted_profiles(self):
        expected_bicross = {
            1: 1,
            2: 1,
            3: 2,
            4: 2,
            5: 4,
            6: 4,
            7: 8,
            8: 8,
            9: 16,
            10: 16,
        }

        for m, bicross_pairs in expected_bicross.items():
            with self.subTest(m=m):
                coloring = paired_coordinate_coloring(m)
                profile = antipodal_pair_profile(coloring, m)
                self.assertEqual(profile, predicted_pair_profile(m))
                self.assertEqual(profile["both_good"], bicross_pairs)
                self.assertEqual(predicted_min_bicross(m), bicross_pairs)
                self.assertEqual(profile["one_good"] + profile["both_bad"], predicted_max_hit(m))

    def test_good_vertices_are_exactly_vertices_with_no_zero_pair_block(self):
        for m in range(1, 9):
            with self.subTest(m=m):
                coloring = paired_coordinate_coloring(m)
                self.assertEqual(set(good_vertices(coloring, m)), set(predicted_good_vertices(m)))

    def test_validation_reports_exact_match(self):
        for m in range(1, 9):
            with self.subTest(m=m):
                validation = validate_paired_construction(m)
                self.assertTrue(validation["good_matches"])
                self.assertEqual(validation["bicross_pairs"], validation["predicted_bicross_pairs"])
                self.assertEqual(validation["hit_pairs"], validation["predicted_hit_pairs"])

    def test_bad_count_formula(self):
        for m in range(1, 9):
            with self.subTest(m=m):
                coloring = paired_coordinate_coloring(m)
                paired_blocks = m // 2
                expected_good = (2 if m % 2 else 1) * (3**paired_blocks)
                self.assertEqual(len(good_vertices(coloring, m)), expected_good)
                self.assertEqual(len(bad_vertices(coloring, m)), 2**m - expected_good)


if __name__ == "__main__":
    unittest.main()
