# Ten-Minute Demo Script

## Before the demo

From the project root, run `python run_project.py all --runs 10`. Keep the generated `results/` folder. Open `results/summary.csv` and `results/figures/energy_baseline_vs_consolidated.svg` so results can be shown quickly. No network connection is needed.

## Demo flow

| Time | What to show | What to explain |
|---|---|---|
| 0:00–1:00 | Project goal and architecture | We simulate hosts and VMs, consolidate VMs from underloaded hosts, then compare energy and SLA outcomes. |
| 1:00–2:00 | `SimulationConfig` and workload generator | 10 hosts, 40 VMs, 96 intervals, and three deterministic workloads. Demand is synthetic and uses fixed seeds. |
| 2:00–4:00 | Run `python run_project.py all --runs 10` | One command reproduces 420 policy runs and 30 host-failure runs; show output files. |
| 4:00–6:00 | Consolidation logic | Explain the 40% underload threshold, 60% destination cap, two-interval window, best-fit host placement, and switch-off when empty. |
| 6:00–7:30 | Energy and SLA formulas | Show the linear power model, convert W × hours to Wh, count migrations, and explain the CPU-overload SLA definition. |
| 7:30–8:30 | Baseline comparison chart/table | Show actual means across 10 seeds and explain energy savings as model estimates. |
| 8:30–9:15 | Failure injection | At the midpoint, the busiest active host is unavailable for one interval. Show lost VM-steps and 15-minute recovery time. |
| 9:15–10:00 | Limitations and next steps | Mention synthetic traces, illustrative watts, CPU-only modeling, and possible real workload traces or migration downtime modeling. |

## Live commands

```bash
python run_project.py all --runs 10
```

```bash
python - <<'PY'
import csv
with open("results/summary.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row["experiment"] == "baseline_comparison":
            print(row["scenario"], row["mode"], row["mean_energy_wh"],
                  row["mean_migrations"], row["mean_sla_host_steps"])
PY
```

## Questions to prepare for

1. Why is consolidation energy-aware? Empty hosts can be switched off, avoiding their idle-power draw.
2. Why use a destination cap? A host packed too tightly can overload when demand rises.
3. Why are results synthetic? The handout permits a Python simulator; no external trace was required for this project.
4. Are the Wh values actual electricity readings? No. They are outputs of the stated illustrative power model.
5. What does the host crash show? The simulator injects a one-interval outage and measures unavailable VM-time and recovery.
