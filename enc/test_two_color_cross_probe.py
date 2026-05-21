import unittest

from bicross_frontier_construction import paired_coordinate_coloring
from two_color_cross_probe import (
    cross_bicross_witness,
    encode_cross_cover_negation,
    encode_target_bad_subset,
    enumerate_badset_counterexample,
    paired_left_cross_target,
    product_target,
)


class TwoColorCrossProbeTests(unittest.TestCase):
    def test_paired_construction_crosses_itself(self):
        coloring = paired_coordinate_coloring(4)
        self.assertIsNotNone(cross_bicross_witness(coloring, coloring, 4))

    def test_exact_badset_enumeration_through_q3_has_no_cross_cover(self):
        for m in (1, 2, 3):
            bad_c, bad_d, _bad_sets = enumerate_badset_counterexample(m)
            self.assertIsNone(bad_c)
            self.assertIsNone(bad_d)


class OptionalSatTwoColorCrossTests(unittest.TestCase):
    def test_sat_cross_cover_negation_unsat_for_q4(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        solver, *_ = encode_cross_cover_negation(
            4,
            sort_zero_edges=True,
            zero_red_degree_at_most_half=True,
            partial_sym_break=8,
        )
        try:
            self.assertFalse(solver.solve(), "Q_4 should have no two-color cross-cover obstruction")
        finally:
            solver.delete()

    def test_paired_left_target_unsat_for_q4(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        solver, *_ = encode_target_bad_subset(4, paired_left_cross_target(4))
        try:
            self.assertFalse(solver.solve(), "No Q_4 coloring should cover the paired-left target")
        finally:
            solver.delete()

    def test_product_targets_unsat_for_q4(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        states = ((0, 0), (0, 1), (1, 0), (1, 1))
        for left in states:
            for right in states:
                with self.subTest(left=left, right=right):
                    solver, *_ = encode_target_bad_subset(4, product_target(4, (left, right)))
                    try:
                        self.assertFalse(solver.solve())
                    finally:
                        solver.delete()


if __name__ == "__main__":
    unittest.main()
