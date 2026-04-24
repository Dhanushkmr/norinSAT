import unittest

from component_chain_classifier import (
    classify_coloring,
    compare_with_full_path_checker,
    validate_path,
)
from induction_probe import (
    all_edges,
    anti,
    antipodal_edge_representatives,
    iter_colorings,
    paired_slice_lift_witness,
    random_antipodal_coloring,
)


def assert_valid_one_connector_witness(test_case, coloring, n, witness):
    test_case.assertIsNotNone(witness)
    test_case.assertEqual(witness.end, anti(witness.start))
    test_case.assertEqual(witness.connector_crossings, 1)
    test_case.assertEqual(len(witness.connectors), 1)
    compare_with_full_path_checker(coloring, n, witness)

    connector_start, connector_end = witness.connectors[0]
    test_case.assertNotEqual(
        connector_start[witness.dimension],
        connector_end[witness.dimension],
    )
    test_case.assertEqual(
        coloring[min(connector_start, connector_end), max(connector_start, connector_end)],
        witness.color,
    )

    if witness.path is not None:
        test_case.assertTrue(validate_path(coloring, witness.path, n, witness.color))


class ComponentChainClassifierTests(unittest.TestCase):
    def test_exact_q3_all_colorings_have_one_connector_witness(self):
        checked = 0
        for _, coloring in iter_colorings(3, max_free_vars=24):
            checked += 1
            witness = classify_coloring(coloring, 3, include_path=True)
            assert_valid_one_connector_witness(self, coloring, 3, witness)
        self.assertEqual(checked, 64)

    def test_exact_q4_all_colorings_have_one_connector_witness(self):
        checked = 0
        for _, coloring in iter_colorings(4, max_free_vars=24):
            checked += 1
            witness = classify_coloring(coloring, 4)
            assert_valid_one_connector_witness(self, coloring, 4, witness)
        self.assertEqual(checked, 65536)

    def test_sampled_q5_witness_paths_reconstruct(self):
        _, _, edges = all_edges(5)
        representatives = antipodal_edge_representatives(edges)
        rng_seed = 20260424

        import random

        rng = random.Random(rng_seed)
        for _ in range(200):
            coloring = random_antipodal_coloring(representatives, rng)
            witness = classify_coloring(coloring, 5, include_path=True)
            assert_valid_one_connector_witness(self, coloring, 5, witness)

    def test_paired_slice_witness_implies_one_connector_witness(self):
        checked_with_paired_witness = 0
        for _, coloring in iter_colorings(4, max_free_vars=24):
            if paired_slice_lift_witness(coloring, 4) is None:
                continue
            checked_with_paired_witness += 1
            witness = classify_coloring(coloring, 4)
            assert_valid_one_connector_witness(self, coloring, 4, witness)

        self.assertEqual(checked_with_paired_witness, 64288)


class OptionalSatEncodingTests(unittest.TestCase):
    def import_sat_helpers(self):
        try:
            from pysat.solvers import Solver

            import one_connector_witness_sat
            import paired_slice_witness_sat
        except ModuleNotFoundError as exc:
            self.skipTest(f"optional python-sat dependency unavailable: {exc}")

        return Solver, one_connector_witness_sat, paired_slice_witness_sat

    def test_one_connector_negation_unsat_for_q3_q4(self):
        Solver, one_connector_witness_sat, _ = self.import_sat_helpers()

        for n in (3, 4):
            ctx = one_connector_witness_sat.build_encoding_context(n, antipodal=True)
            one_connector_witness_sat.encode_no_one_connector_witness(ctx)

            with Solver() as solver:
                for clause in ctx.enc:
                    solver.add_clause(clause)
                self.assertFalse(solver.solve(), f"Q_{n} should have no witness-free coloring")

    def test_no_paired_slice_model_still_has_one_connector_witness(self):
        Solver, _, paired_slice_witness_sat = self.import_sat_helpers()

        ctx = paired_slice_witness_sat.build_encoding_context(4, antipodal=True)
        paired_slice_witness_sat.encode_no_paired_slice_lift_witness(ctx)

        with Solver() as solver:
            for clause in ctx.enc:
                solver.add_clause(clause)
            self.assertTrue(solver.solve())
            coloring = paired_slice_witness_sat.model_to_coloring(ctx, solver.get_model())

        self.assertIsNone(paired_slice_lift_witness(coloring, 4))
        witness = classify_coloring(coloring, 4, include_path=True)
        assert_valid_one_connector_witness(self, coloring, 4, witness)


if __name__ == "__main__":
    unittest.main()
