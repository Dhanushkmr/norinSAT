"""Run a SAT command as a parallel solver portfolio.

Examples:

    uv run --python 3.12 --with python-sat python enc/sat_portfolio.py \
      --timeout 180 \
      -- python enc/bicross_probe.py -m 7 --sat-pairs-hit-at-least 64

    python3 enc/sat_portfolio.py \
      --solvers kissat,cadical \
      -- {solver} formula.cnf

If the command contains ``{solver}``, the placeholder is replaced directly.
Otherwise ``--solver <name>`` is appended, which matches the PySAT-backed
scripts in this repository.
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from sat_utils import available_pysat_solvers, effective_cpu_count


SAT_RE = re.compile(r"\bSAT:\s*(True|False)\b")


@dataclass
class RunningJob:
    solver: str
    command: list[str]
    proc: subprocess.Popen
    started: float
    stdout_path: Path
    stdout_file: object


@dataclass
class FinishedJob:
    solver: str
    command: list[str]
    status: str
    returncode: int | None
    elapsed: float
    output: str


def parse_solver_list(value):
    if value == "auto":
        solvers = available_pysat_solvers()
        if not solvers:
            raise SystemExit("No preferred PySAT solvers are available.")
        return list(solvers)
    solvers = [item.strip() for item in value.split(",") if item.strip()]
    if not solvers:
        raise SystemExit("--solvers must be 'auto' or a comma-separated list")
    return solvers


def command_for_solver(command_template, solver):
    if any("{solver}" in arg for arg in command_template):
        return [arg.replace("{solver}", solver) for arg in command_template]
    return command_template + ["--solver", solver]


def parse_status(output, returncode):
    match = SAT_RE.search(output)
    if match:
        return f"SAT:{match.group(1)}"
    if returncode == 10:
        return "SAT:True"
    if returncode == 20:
        return "SAT:False"
    if returncode == 0:
        return "DONE"
    return "ERROR"


def launch_job(solver, command_template, cwd):
    command = command_for_solver(command_template, solver)
    stdout_file = tempfile.NamedTemporaryFile(prefix=f"sat-{solver}-", suffix=".log", delete=False)
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=stdout_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=False,
    )
    return RunningJob(
        solver=solver,
        command=command,
        proc=proc,
        started=time.monotonic(),
        stdout_path=Path(stdout_file.name),
        stdout_file=stdout_file,
    )


def kill_job(job):
    try:
        os.killpg(job.proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def finish_job(job, status_override=None):
    job.stdout_file.close()
    elapsed = time.monotonic() - job.started
    returncode = job.proc.poll()
    output = job.stdout_path.read_text(errors="replace")
    try:
        job.stdout_path.unlink()
    except FileNotFoundError:
        pass
    status = status_override or parse_status(output, returncode)
    return FinishedJob(
        solver=job.solver,
        command=job.command,
        status=status,
        returncode=returncode,
        elapsed=elapsed,
        output=output,
    )


def print_finished(job, show_output):
    print(
        f"[{job.solver}] status={job.status} returncode={job.returncode} "
        f"elapsed={job.elapsed:.2f}s",
        flush=True,
    )
    if show_output:
        print(f"--- output: {job.solver} ---")
        print(job.output, end="" if job.output.endswith("\n") else "\n")


def run_portfolio(args):
    solvers = parse_solver_list(args.solvers)
    jobs = max(1, min(args.jobs or effective_cpu_count(), len(solvers)))
    pending = list(solvers)
    running = []
    finished = []
    first_result = None
    cwd = Path(args.cwd).resolve()

    print(f"Solvers: {', '.join(solvers)}", flush=True)
    print(f"Workers: {jobs} (available cores: {effective_cpu_count()})", flush=True)
    if args.timeout:
        print(f"Timeout per solver: {args.timeout}s", flush=True)
    print("Command template: " + " ".join(args.command), flush=True)

    while pending or running:
        while pending and len(running) < jobs:
            solver = pending.pop(0)
            job = launch_job(solver, args.command, cwd)
            running.append(job)
            print(f"[{solver}] started pid={job.proc.pid}", flush=True)

        time.sleep(args.poll_interval)
        now = time.monotonic()

        still_running = []
        for job in running:
            returncode = job.proc.poll()
            if returncode is not None:
                done = finish_job(job)
                finished.append(done)
                print_finished(done, args.show_output)
                if done.status in ("SAT:True", "SAT:False") and first_result is None:
                    first_result = done
                continue

            if args.timeout and now - job.started > args.timeout:
                kill_job(job)
                job.proc.wait()
                done = finish_job(job, status_override="TIMEOUT")
                finished.append(done)
                print_finished(done, args.show_output)
                continue

            still_running.append(job)

        running = still_running

        if first_result is not None and args.stop_on_result:
            pending.clear()
            for job in running:
                kill_job(job)
                job.proc.wait()
                done = finish_job(job, status_override="KILLED")
                finished.append(done)
                print_finished(done, args.show_output)
            running.clear()

    print("Summary:", flush=True)
    for job in finished:
        print(f"  {job.solver}: {job.status} in {job.elapsed:.2f}s", flush=True)

    if first_result is not None:
        print(f"First decisive result: {first_result.solver} {first_result.status}", flush=True)
        return 0

    if any(job.status == "ERROR" for job in finished):
        return 2
    return 124 if any(job.status == "TIMEOUT" for job in finished) else 0


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--solvers",
        default="auto",
        help="Comma-separated solver names, or 'auto' for the preferred available PySAT portfolio",
    )
    parser.add_argument("--jobs", type=int, default=0, help="Parallel workers; default uses all available cores")
    parser.add_argument("--timeout", type=float, default=0, help="Timeout per solver in seconds")
    parser.add_argument("--cwd", default=".", help="Working directory for launched commands")
    parser.add_argument("--poll-interval", type=float, default=0.2, help="Polling interval in seconds")
    parser.add_argument("--keep-going", dest="stop_on_result", action="store_false", help="Do not stop after first SAT/UNSAT result")
    parser.add_argument("--show-output", action="store_true", help="Print each solver's captured output")
    parser.add_argument("--list-solvers", action="store_true", help="List preferred available PySAT solvers and exit")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command template after --")
    parser.set_defaults(stop_on_result=True)
    args = parser.parse_args()

    if args.list_solvers:
        print("\n".join(parse_solver_list(args.solvers)))
        raise SystemExit(0)

    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("provide a command after --, or use --list-solvers")
    return args


def main():
    raise SystemExit(run_portfolio(parse_args()))


if __name__ == "__main__":
    main()
