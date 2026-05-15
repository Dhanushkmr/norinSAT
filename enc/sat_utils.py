"""Small SAT-solver helpers shared by the experimental scripts."""

from __future__ import annotations

import os


PREFERRED_PYSAT_SOLVERS = (
    "cadical195",
    "kissat404",
    "cadical153",
    "cadical103",
    "glucose4",
    "glucose42",
    "maplechrono",
    "gluecard4",
    "gluecard3",
    "maplesat",
    "maplecm",
    "mergesat3",
    "minicard",
    "minisat22",
    "minisatgh",
    "lingeling",
    "cryptosat",
)

ASSUMPTION_PYSAT_SOLVERS = tuple(
    name for name in PREFERRED_PYSAT_SOLVERS if name not in {"kissat404"}
)


def effective_cpu_count(default=1):
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except AttributeError:
        return os.cpu_count() or default


def available_pysat_solvers(candidates=PREFERRED_PYSAT_SOLVERS):
    try:
        from pysat.solvers import Solver
    except ModuleNotFoundError as exc:
        raise SystemExit(f"python-sat is required for SAT solver discovery: {exc}") from exc

    available = []
    for name in candidates:
        solver = None
        try:
            solver = Solver(name=name)
        except Exception:
            continue
        finally:
            if solver is not None:
                solver.delete()
        available.append(name)
    return tuple(available)


def best_pysat_solver_name(explicit=None, require_assumptions=False):
    candidates = ASSUMPTION_PYSAT_SOLVERS if require_assumptions else PREFERRED_PYSAT_SOLVERS
    if explicit:
        if require_assumptions and explicit not in candidates:
            allowed = ", ".join(candidates)
            raise SystemExit(
                f"PySAT solver {explicit!r} is not supported for assumption-based cube solving. "
                f"Choose one of: {allowed}"
            )
        return explicit
    available = available_pysat_solvers(candidates)
    return available[0] if available else None


def make_pysat_solver(name=None, require_assumptions=False):
    try:
        from pysat.solvers import Solver
    except ModuleNotFoundError as exc:
        raise SystemExit(f"python-sat is required for SAT solving: {exc}") from exc

    chosen = best_pysat_solver_name(name, require_assumptions=require_assumptions)
    if chosen is None:
        return Solver(), "pysat-default"
    return Solver(name=chosen), chosen


def solver_help(require_assumptions=False):
    suffix = ""
    if require_assumptions:
        suffix = " Assumption-based cube runners exclude solvers without assumption support, such as kissat404."
    return (
        "Optional PySAT solver name. If omitted, the fastest preferred "
        "available solver is selected automatically."
        + suffix
    )
