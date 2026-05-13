import unittest
from types import SimpleNamespace
from unittest.mock import patch

import sat_portfolio


class FakeProcess:
    pid = 12345

    def __init__(self):
        self.killed = False

    def kill(self):
        self.killed = True


class SatPortfolioTests(unittest.TestCase):
    def test_command_template_replaces_solver_placeholder(self):
        command = sat_portfolio.command_for_solver(["solver={solver}", "formula.cnf"], "cadical195")

        self.assertEqual(command, ["solver=cadical195", "formula.cnf"])

    def test_command_template_appends_pysat_solver_argument(self):
        command = sat_portfolio.command_for_solver(["python", "enc/bicross_probe.py"], "cadical195")

        self.assertEqual(command, ["python", "enc/bicross_probe.py", "--solver", "cadical195"])

    def test_kill_job_falls_back_to_child_process_when_process_group_is_denied(self):
        proc = FakeProcess()
        job = SimpleNamespace(proc=proc)

        with patch.object(sat_portfolio.os, "killpg", side_effect=PermissionError):
            sat_portfolio.kill_job(job)

        self.assertTrue(proc.killed)


if __name__ == "__main__":
    unittest.main()
