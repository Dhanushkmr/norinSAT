import unittest

from induction_probe import anti
from two_color_product_hole_analysis import analyze_hole_orbits, hole_orbits


class TwoColorProductHoleAnalysisTests(unittest.TestCase):
    def test_q4_two_hole_orbit_count(self):
        orbits = hole_orbits(4, 2)

        self.assertEqual(len(orbits), 8)
        self.assertEqual(sum(len(members) for members in orbits.values()), 36)


class OptionalSatTwoColorProductHoleAnalysisTests(unittest.TestCase):
    def test_q4_two_hole_sat_orbit_is_antipodal(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        results = analyze_hole_orbits(4, 2)
        sat_results = [result for result in results if result.result is True]

        self.assertEqual(len(sat_results), 1)
        self.assertTrue(sat_results[0].antipodal_pair)
        left, right = sat_results[0].representative
        self.assertEqual(anti(left), right)

        for result in results:
            if result.result is False:
                self.assertFalse(result.antipodal_pair)


if __name__ == "__main__":
    unittest.main()
