import itertools
import random
import unittest

from bicross_probe import (
    arbitrary_coloring_from_bits,
    antipodal_pair_profile,
    bad_vertices,
    bad_vertices_hit_every_antipodal_pair,
    bicross_witness,
    cell_antipodal_pairs,
    construct_bad_antipodal_labeling,
    doubled_coloring,
    encode_bad_count_bound,
    good_vertices,
    encode_fixed_slice_negation,
    encode_pair_hit_bound,
    fixed_slice_witness,
    iter_antipodal_labelings,
    monotone_geodesic_vertices,
    perfect_inherited_splits,
    random_edge_coloring,
    slice_recursion_score,
    slice_summaries,
    uniform_perfect_inherited_splits,
    validate_bad_labeling,
)
from induction_probe import all_edges


class BicrossProbeTests(unittest.TestCase):
    def test_exact_q3_all_edge_colorings_have_bicross_witness(self):
        _, _, edges = all_edges(3)
        checked = 0
        min_good_count = 8

        for bits in itertools.product((0, 1), repeat=len(edges)):
            coloring = arbitrary_coloring_from_bits(edges, bits)
            checked += 1
            self.assertIsNotNone(bicross_witness(coloring, 3))
            self.assertIsNone(construct_bad_antipodal_labeling(coloring, 3))
            self.assertFalse(bad_vertices_hit_every_antipodal_pair(coloring, 3))
            self.assertGreater(antipodal_pair_profile(coloring, 3)["both_good"], 0)
            good = set(good_vertices(coloring, 3))
            monotone = set(monotone_geodesic_vertices(coloring, 3))
            self.assertEqual(good, monotone)
            min_good_count = min(min_good_count, len(good))

        self.assertEqual(checked, 4096)
        self.assertEqual(min_good_count, 6)

    def test_exact_q2_every_labeling_has_fixed_slice_witness(self):
        _, _, edges = all_edges(2)
        checked = 0

        for bits in itertools.product((0, 1), repeat=len(edges)):
            coloring = arbitrary_coloring_from_bits(edges, bits)
            for labels in iter_antipodal_labelings(2, max_label_vars=8):
                checked += 1
                self.assertIsNotNone(fixed_slice_witness(coloring, 2, labels))

        self.assertEqual(checked, 64)

    def test_sampled_q4_edge_colorings_have_bicross_witness(self):
        _, _, edges = all_edges(4)
        rng = random.Random(20260424)

        for _ in range(500):
            coloring = random_edge_coloring(edges, rng)
            self.assertIsNotNone(bicross_witness(coloring, 4))
            self.assertIsNone(construct_bad_antipodal_labeling(coloring, 4))

    def test_validate_bad_labeling_rejects_non_antipodal_labels(self):
        _, _, edges = all_edges(2)
        coloring = arbitrary_coloring_from_bits(edges, [0] * len(edges))
        labels = {vertex: False for vertex in all_edges(2)[0]}

        self.assertFalse(validate_bad_labeling(coloring, 2, labels))

    def test_slice_summary_for_monochromatic_q3(self):
        _, _, edges = all_edges(3)
        coloring = arbitrary_coloring_from_bits(edges, [0] * len(edges))

        for summary in slice_summaries(coloring, 3):
            self.assertEqual(summary.full_bad_side0, 0)
            self.assertEqual(summary.full_bad_side1, 0)
            self.assertEqual(summary.slice_bad_side0, 0)
            self.assertEqual(summary.slice_bad_side1, 0)
            self.assertEqual(slice_recursion_score(summary), (0, 0, 0))
            self.assertTrue(summary.identical_slices)
            self.assertTrue(summary.uniform_connectors)

    def test_cell_antipodal_pairs_for_monochromatic_q3(self):
        _, _, edges = all_edges(3)
        coloring = arbitrary_coloring_from_bits(edges, [0] * len(edges))

        self.assertEqual(cell_antipodal_pairs(coloring, 3), ())

    def test_doubling_preserves_bad_vertices_by_copy(self):
        _, _, edges = all_edges(2)
        for bits in itertools.product((0, 1), repeat=len(edges)):
            coloring = arbitrary_coloring_from_bits(edges, bits)
            original_bad_count = len(bad_vertices(coloring, 2))
            original_profile = antipodal_pair_profile(coloring, 2)

            for connector_color in (False, True):
                for dimension in range(3):
                    doubled = doubled_coloring(coloring, 2, connector_color, dimension)
                    doubled_profile = antipodal_pair_profile(doubled, 3)
                    self.assertEqual(len(bad_vertices(doubled, 3)), 2 * original_bad_count)
                    self.assertEqual(doubled_profile["both_good"], 2 * original_profile["both_good"])
                    self.assertEqual(doubled_profile["one_good"], 2 * original_profile["one_good"])
                    self.assertEqual(doubled_profile["both_bad"], 2 * original_profile["both_bad"])

    def test_doubling_has_expected_perfect_inherited_split(self):
        _, _, edges = all_edges(2)
        coloring = arbitrary_coloring_from_bits(edges, [0, 1, 1, 0])

        for dimension in range(3):
            doubled = doubled_coloring(coloring, 2, connector_color=False, dimension=dimension)
            self.assertIn(dimension, perfect_inherited_splits(doubled, 3))
            self.assertIn(dimension, uniform_perfect_inherited_splits(doubled, 3))


class OptionalSatBicrossTests(unittest.TestCase):
    def test_fixed_slice_negation_unsat_for_q3_q4(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        for m in (3, 4):
            solver, _, _, _, _ = encode_fixed_slice_negation(m)
            try:
                self.assertFalse(solver.solve(), f"Q_{m} fixed-slice negation should be UNSAT")
            finally:
                solver.delete()

    def test_bad_count_bound_for_q4(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        solver, _, _, _, _ = encode_bad_count_bound(
            4,
            bad_bound=8,
            sort_zero_edges=True,
            zero_red_degree_at_most_half=True,
            partial_sym_break=8,
        )
        try:
            self.assertFalse(solver.solve(), "Q_4 should not have 8 bad vertices")
        finally:
            solver.delete()

    def test_pair_hit_bound_for_q4(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        solver, _, _, _, _, _ = encode_pair_hit_bound(4, hit_bound=8)
        try:
            self.assertFalse(solver.solve(), "Q_4 bad vertices should not hit every antipodal pair")
        finally:
            solver.delete()

    def test_pair_hit_frontier_for_q3_q4(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        for m, hit_bound in ((3, 3), (4, 7)):
            solver, _, _, _, _, _ = encode_pair_hit_bound(m, hit_bound=hit_bound)
            try:
                self.assertFalse(
                    solver.solve(),
                    f"Q_{m} bad vertices should not hit {hit_bound} antipodal pairs",
                )
            finally:
                solver.delete()

    def test_cell_pair_restriction_separates_q3_q4_frontiers(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        q3_solver, *_ = encode_pair_hit_bound(3, hit_bound=2, forbid_cell_pairs=True)
        try:
            self.assertTrue(q3_solver.solve(), "Q_3 has exact-frontier colorings with no cell antipodal pair")
        finally:
            q3_solver.delete()

        q4_solver, *_ = encode_pair_hit_bound(4, hit_bound=6, forbid_cell_pairs=True)
        try:
            self.assertFalse(
                q4_solver.solve(),
                "Q_4 exact-frontier colorings should force a cell antipodal pair",
            )
        finally:
            q4_solver.delete()

    def test_forbid_perfect_inherited_splits_encoding_smoke(self):
        try:
            import pysat  # noqa: F401
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        solver, *_ = encode_pair_hit_bound(3, hit_bound=4, forbid_perfect_inherited_splits=True)
        try:
            self.assertFalse(solver.solve(), "Q_3 cannot hit all antipodal pairs, with or without slice restrictions")
        finally:
            solver.delete()


if __name__ == "__main__":
    unittest.main()
