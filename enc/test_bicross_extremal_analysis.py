import unittest

from bicross_extremal_analysis import (
    analyze_coloring,
    bicross_shape,
    cell_antipodal_pair_analysis,
    component_incidence_analysis,
    freeze,
    frontier_branch,
    inheritance_shape,
    pair_coverage_summary,
    pair_hits_from_profile,
    structural_signature,
    vertex_histogram,
)
from bicross_probe import arbitrary_coloring_from_bits
from induction_probe import all_edges


class BicrossExtremalAnalysisTests(unittest.TestCase):
    def test_pair_hits_from_profile(self):
        self.assertEqual(pair_hits_from_profile({"one_good": 3, "both_bad": 2}), 5)

    def test_pair_coverage_summary_tracks_overcovered_pairs(self):
        summary = pair_coverage_summary({"both_good": 4, "one_good": 18, "both_bad": 10})

        self.assertEqual(summary["pairs_hit"], 28)
        self.assertEqual(summary["bad_vertices_counted_by_pairs"], 38)
        self.assertEqual(summary["extra_bad_vertices_over_pair_hits"], 10)

    def test_vertex_histogram_counts_hamming_weights(self):
        self.assertEqual(vertex_histogram([(0, 0), (1, 0), (1, 1)]), {0: 1, 1: 1, 2: 1})

    def test_component_incidence_for_monochromatic_q2(self):
        _, _, edges = all_edges(2)
        coloring = arbitrary_coloring_from_bits(edges, [0] * len(edges))
        incidence = component_incidence_analysis(coloring, 2)

        self.assertEqual(incidence["red_components"], 4)
        self.assertEqual(incidence["blue_components"], 1)
        self.assertEqual(incidence["occupied_cells"], 4)
        self.assertEqual(incidence["missing_target_cells"], 0)

    def test_bicross_shape_for_monochromatic_q2(self):
        _, _, edges = all_edges(2)
        coloring = arbitrary_coloring_from_bits(edges, [0] * len(edges))
        analysis = analyze_coloring(coloring, 2)
        shape = bicross_shape(analysis)

        self.assertEqual(shape["pair_count"], 2)
        self.assertEqual(shape["same_meet_count"], 0)
        self.assertEqual(shape["distinct_meet_vertices"], 4)
        self.assertEqual(shape["meet_multiplicities"], [1, 1, 1, 1])

    def test_cell_antipodal_pairs_for_monochromatic_q2(self):
        _, _, edges = all_edges(2)
        coloring = arbitrary_coloring_from_bits(edges, [0] * len(edges))
        cell_pairs = cell_antipodal_pair_analysis(coloring, 2)

        self.assertEqual(cell_pairs["pair_count"], 0)
        self.assertEqual(cell_pairs["cells_with_pairs"], 0)

    def test_structural_signature_is_hashable(self):
        _, _, edges = all_edges(2)
        coloring = arbitrary_coloring_from_bits(edges, [0] * len(edges))
        analysis = analyze_coloring(coloring, 2)

        hash(freeze(structural_signature(analysis)))

    def test_inheritance_shape_for_monochromatic_q2(self):
        _, _, edges = all_edges(2)
        coloring = arbitrary_coloring_from_bits(edges, [0] * len(edges))
        analysis = analyze_coloring(coloring, 2)
        shape = inheritance_shape(analysis)

        self.assertEqual(shape["perfect_splits"], 2)
        self.assertEqual(shape["uniform_perfect_splits"], 2)

    def test_frontier_branch_detects_both_branch(self):
        analysis = {
            "bicross_pair_count": 4,
            "cell_antipodal_pairs": {"pair_count": 4, "cells_with_pairs": 1},
            "slice_signature": [{"recursion_score": (8, 0, 0), "uniform_connectors": False}],
        }
        branch = frontier_branch(analysis)

        self.assertTrue(branch["cell_star"])
        self.assertTrue(branch["perfect_inherited"])
        self.assertEqual(branch["branch"], "both")


if __name__ == "__main__":
    unittest.main()
