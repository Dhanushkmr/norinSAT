import itertools
import unittest

from bicross_frontier_construction import paired_coordinate_coloring
from bicross_probe import arbitrary_coloring_from_bits
from group_structure_probe import (
    bicross_quotient_set,
    count_affine_subspaces,
    find_affine_subspace,
    gf2_rank,
    geometry_baseline_summary,
    is_affine_subspace,
    iter_linear_subspaces,
    max_affine_dimension,
    no_affine_survivor_clauses,
    quotient_dimension,
    quotient_point,
    quotient_cube_stabilizer_size,
    square_curvature_rows,
    analyze_coloring,
    translation_stabilizer_size,
)
from induction_probe import all_edges, anti


class GroupStructureProbeTests(unittest.TestCase):
    def test_quotient_identifies_antipodes(self):
        vertices, _, _ = all_edges(5)
        for vertex in vertices:
            self.assertEqual(quotient_point(vertex), quotient_point(anti(vertex)))
        self.assertEqual(quotient_dimension(5), 4)

    def test_linear_subspace_counts_for_f2_3(self):
        self.assertEqual(len(list(iter_linear_subspaces(3, 0))), 1)
        self.assertEqual(len(list(iter_linear_subspaces(3, 1))), 7)
        self.assertEqual(len(list(iter_linear_subspaces(3, 2))), 7)
        self.assertEqual(len(list(iter_linear_subspaces(3, 3))), 1)

    def test_affine_subspace_detector_finds_plane(self):
        plane = frozenset({1, 3, 5, 7})
        witness = find_affine_subspace(plane, n=3, d=2)

        self.assertIsNotNone(witness)
        self.assertTrue(is_affine_subspace(plane))
        self.assertEqual(count_affine_subspaces(plane, n=3, d=2), 1)
        self.assertEqual(max_affine_dimension(plane, n=3), (2, 1))
        self.assertEqual(gf2_rank([1, 2, 3]), 2)

    def test_stabilizers_for_affine_plane(self):
        plane = frozenset({1, 3, 5, 7})

        self.assertEqual(translation_stabilizer_size(plane, 3), 4)
        self.assertGreaterEqual(quotient_cube_stabilizer_size(plane, 4), 4)

    def test_no_affine_clause_counts(self):
        def fake_bad(vertex):
            return hash(vertex) or 1

        self.assertEqual(len(no_affine_survivor_clauses(3, fake_bad)), 6)
        self.assertEqual(len(no_affine_survivor_clauses(4, fake_bad)), 28)
        self.assertEqual(len(no_affine_survivor_clauses(5, fake_bad)), 140)
        self.assertEqual(len(no_affine_survivor_clauses(6, fake_bad)), 1240)

    def test_geometry_baseline_q4_four_point_subsets(self):
        summary = geometry_baseline_summary(4, subset_size=2)

        self.assertEqual(summary["checked"], 28)
        self.assertEqual(summary["target_count_distribution"][1], 28)

    def test_paired_construction_has_exact_affine_survivor(self):
        for m in range(1, 9):
            with self.subTest(m=m):
                coloring = paired_coordinate_coloring(m)
                analysis = analyze_coloring(coloring, m)

                self.assertTrue(analysis["contains_target_affine"])
                self.assertTrue(analysis["bicross_set_is_affine"])
                self.assertEqual(analysis["max_affine_dimension"], analysis["target_affine_dimension"])
                self.assertEqual(analysis["target_affine_count"], 1)
                self.assertEqual(analysis["bicross_pair_count"], analysis["predicted_min_bicross"])

    def test_exact_q3_all_colorings_have_affine_survivor(self):
        _, _, edges = all_edges(3)

        for bits in itertools.product((0, 1), repeat=len(edges)):
            coloring = arbitrary_coloring_from_bits(edges, bits)
            analysis = analyze_coloring(coloring, 3)
            self.assertTrue(analysis["contains_target_affine"])

    def test_paired_construction_has_zero_square_curvature_but_affine_edges(self):
        coloring = paired_coordinate_coloring(4)
        rows = square_curvature_rows(coloring, 4)
        analysis = analyze_coloring(coloring, 4)

        self.assertEqual(gf2_rank(rows), 0)
        self.assertTrue(analysis["affine_directions"]["all_directions_affine"])
        self.assertEqual(len(bicross_quotient_set(coloring, 4)), 2)


if __name__ == "__main__":
    unittest.main()
