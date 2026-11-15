# Energy-Aware VM Consolidation

Mini project for **CSN349 Cloud Computing**. This is a local, deterministic Python simulator: it models VM CPU loads on physical hosts, migrates VMs off underloaded hosts, switches empty hosts off, and compares modeled energy and SLA outcomes with a no-consolidation baseline.

## Start the project

Requires Python 3.10 or newer. The simulator uses only the Python standard library; no cloud account, paid service, dataset, Docker, or third-party runtime package is needed.

```bash
python run_project.py all --runs 10
```

This single command runs all core experiments and the host-crash injection, writing reproducible CSV and SVG outputs under `results/`. It requires at least 10 runs per condition, matching the project's repeated-measurement requirement. To rebuild the report PDF after changing results, install the optional report dependency listed in `requirements-report.txt` and run `python docs/build_report.py`.

## What is implemented

- 10 hosts, 40 VMs, 24 simulated hours, and 96 fifteen-minute intervals.
- Three deterministic synthetic workload patterns: steady, diurnal, and spiky.
- Baseline with static placement and no consolidation.
- Consolidation of underloaded hosts, a 60% destination utilization cap, best-fit placement, and a two-interval underload window.
- Linear host power model: `idle power + (maximum power - idle power) × CPU utilization`.
- Explicit migration energy cost, migration count, powered-off host-time, CPU overload/SLA accounting, and paired workload seeds.
- Sensitivity experiments for underload threshold, destination safety cap, VM selection order, and migration cost, plus a per-migration break-even analysis.
- A one-interval host crash and recovery injection in each workload pattern.

## Project map

| Path | Purpose |
|---|---|
| `run_project.py` | One-command experiment entry point |
| `vmconsolidation/` | Workload generator, simulator, policies, experiment aggregation, chart generation |
| `results/raw_runs.csv` | Individual runs; use this for re-analysis |
| `results/summary.csv` | Mean and standard deviation by experiment condition |
| `results/break_even_summary.csv` | Migration-energy penalty at which consolidation's modeled savings equal the baseline |
| `results/failure_injection.csv` | Individual failure-injection runs |
| `results/figures/` | SVG charts generated from the summary data |
| `docs/architecture.svg` | Ready-to-view architecture diagram |
| `docs/architecture.mmd` | Editable Mermaid architecture source |
| `docs/project_proposal.md` | One-page project proposal |
| `docs/report.md` and `docs/report.pdf` | Editable report source and 14-page report |
| `docs/demo_script.md` | Ten-minute demonstration outline |
| `docs/contributions.md` | Team contribution statement template |

## Reproduce or extend

```bash
python run_project.py all --runs 10
```

Increase `--runs` to reduce sampling noise. Workloads use fixed seeds so paired baseline/consolidated runs receive the same demand trace. Edit `SimulationConfig` in `vmconsolidation/models.py` to change hosts, VMs, interval length, or thresholds. Adjust the experiment sets in `vmconsolidation/experiments.py` to add scenarios. The report's results are generated from the included 10-run CSV files; regenerate the report after changing experiment settings.

## Commit to your team's remote repository

The project folder is initialized as a Git repository. After filling in the team members and contribution statement, make the team's first commit and add the remote created by your team:

```bash
git add .
git commit -m "Build energy-aware VM consolidation simulator"
git remote add origin <your-team-repository-url>
git push -u origin main
```

## Interpret the numbers correctly

All workloads are synthetic and all host power values are illustrative assumptions. The outputs are **modeled Wh**, not readings from a physical server. A VM's CPU demand is treated as known to the simulator; the simulator does not boot real VMs or perform live migration. The default migration energy is an assumed 1 Wh per migrated VM. The failure experiment removes the busiest active host for one interval, counts unavailable VM-time as an SLA violation, and restores it on the next interval.

The included report discusses model limitations, assumptions, results, and reproducibility. Replace the blank team names and contribution signatures before submission, and make sure every team member can explain the code and actual experiment output.

## Tools and licenses

See `docs/tools_and_licenses.csv`. The runtime simulator needs only Python and its standard library. Report generation uses optional ReportLab; the PDF is already included.
