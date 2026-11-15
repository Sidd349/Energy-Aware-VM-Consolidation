from __future__ import annotations

import argparse
from pathlib import Path

from vmconsolidation.charts import generate_charts
from vmconsolidation.experiments import run_all, run_failure_injection


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the VM consolidation simulator and experiments.")
    parser.add_argument("command", nargs="?", choices=("all", "experiments", "failure"), default="all")
    parser.add_argument("--runs", type=int, default=10, help="Repeated runs per condition (minimum 10).")
    args = parser.parse_args()
    if args.runs < 10:
        parser.error("--runs must be at least 10 to meet the project handout's repeated-run requirement")

    if args.command in ("all", "experiments"):
        rows, failures = run_all(args.runs, RESULTS)
        generate_charts(RESULTS)
        print(f"Completed {len(rows)} policy experiment runs and {len(failures)} host-failure runs.")
        print(f"Results: {RESULTS}")
    else:
        failures = run_failure_injection(args.runs, RESULTS)
        print(f"Completed {len(failures)} host-failure runs. Results: {RESULTS / 'failure_summary.csv'}")


if __name__ == "__main__":
    main()
