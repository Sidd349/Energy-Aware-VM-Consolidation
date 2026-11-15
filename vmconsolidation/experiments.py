from __future__ import annotations

import csv
import json
import statistics
from dataclasses import asdict, replace
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from .models import ExperimentRow, FailureRow, SimulationConfig
from .simulator import VMSimulator
from .workloads import SCENARIOS, generate_workload


def _run(config: SimulationConfig, scenario: str, seed: int, experiment: str) -> ExperimentRow:
    workload = generate_workload(scenario, config.vms, config.steps, seed)
    result = VMSimulator(config, workload, scenario, seed).run()
    return ExperimentRow(
        experiment=experiment, scenario=scenario, mode=result.mode, seed=seed,
        underload_threshold=config.underload_threshold,
        upper_threshold=config.upper_threshold, vm_selection=config.vm_selection,
        migration_energy_wh_per_vm=config.migration_energy_wh,
        energy_wh=result.total_energy_wh, host_energy_wh=result.host_energy_wh,
        migration_energy_wh=result.migration_energy_wh, migrations=result.migrations,
        sla_host_steps=result.sla_host_steps,
        sla_host_step_rate_pct=result.sla_host_step_rate_pct,
        sla_cpu_shortfall=result.sla_cpu_shortfall,
        active_host_steps=result.active_host_steps,
        powered_off_host_steps=result.powered_off_host_steps,
        peak_active_hosts=result.peak_active_hosts,
    )


def run_all(runs: int, out_dir: Path) -> Tuple[List[ExperimentRow], List[FailureRow]]:
    if runs < 10:
        raise ValueError("The handout requires repeated experiments; use at least 10 runs.")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: List[ExperimentRow] = []
    base = SimulationConfig()

    # Required baseline comparison: paired seeds keep workload inputs identical.
    for scenario in SCENARIOS:
        for run_id in range(runs):
            seed = 20261114 + run_id
            rows.append(_run(replace(base, consolidate=False), scenario, seed, "baseline_comparison"))
            rows.append(_run(replace(base, consolidate=True), scenario, seed, "baseline_comparison"))

    # Threshold sensitivity (same workload seeds for every threshold).
    for scenario in SCENARIOS:
        for threshold in (0.30, 0.40, 0.50):
            cfg = replace(base, consolidate=True, underload_threshold=threshold)
            for run_id in range(runs):
                rows.append(_run(cfg, scenario, 20262114 + run_id, "threshold_sweep"))

    # Safety-cap sensitivity shows the energy/SLA trade-off when hosts are packed more tightly.
    for scenario in SCENARIOS:
        for threshold in (0.55, 0.60, 0.65, 0.70):
            cfg = replace(base, consolidate=True, upper_threshold=threshold)
            for run_id in range(runs):
                rows.append(_run(cfg, scenario, 20262614 + run_id, "upper_threshold_sweep"))

    # VM selection stretch goal.
    for scenario in SCENARIOS:
        for selection in ("smallest", "largest"):
            cfg = replace(base, consolidate=True, vm_selection=selection)
            for run_id in range(runs):
                rows.append(_run(cfg, scenario, 20263114 + run_id, "vm_selection_comparison"))

    # Explicit migration-cost sensitivity, with the same VM policy and workloads.
    for scenario in SCENARIOS:
        for migration_cost in (0.0, 1.0, 5.0):
            cfg = replace(base, consolidate=True, migration_energy_wh=migration_cost)
            for run_id in range(runs):
                rows.append(_run(cfg, scenario, 20264114 + run_id, "migration_cost_sweep"))

    _write_csv(out_dir / "raw_runs.csv", [asdict(row) for row in rows])
    summary = summarize(rows)
    _write_csv(out_dir / "summary.csv", summary)
    _write_csv(out_dir / "break_even_summary.csv", break_even_summary(rows))
    metadata = {
        "runs_per_condition": runs,
        "scenarios": list(SCENARIOS),
        "steps": base.steps,
        "step_minutes": base.step_minutes,
        "hours_simulated": base.steps * base.step_minutes / 60,
        "hosts": base.hosts,
        "vms": base.vms,
        "host_capacity_cpu_units": 100,
        "host_idle_power_w": 90,
        "host_max_power_w": 180,
        "default_underload_threshold": base.underload_threshold,
        "default_upper_threshold": base.upper_threshold,
        "migration_energy_wh_per_vm": base.migration_energy_wh,
        "seed_policy": "fixed paired seeds within each experiment condition",
        "note": "Synthetic CPU workloads and illustrative host power values; not measured hardware energy.",
    }
    (out_dir / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    failures = run_failure_injection(runs, out_dir)
    return rows, failures


def run_failure_injection(runs: int, out_dir: Path) -> List[FailureRow]:
    failure_rows: List[FailureRow] = []
    base = SimulationConfig(consolidate=True)
    failure_step = base.steps // 2
    for scenario in SCENARIOS:
        for run_id in range(runs):
            seed = 20265114 + run_id
            workload = generate_workload(scenario, base.vms, base.steps, seed)
            result = VMSimulator(base, workload, scenario, seed,
                                 failure_step=failure_step,
                                 failure_duration_steps=1).run()
            failure_rows.append(FailureRow(
                scenario=scenario, seed=seed, failure_step=failure_step,
                failure_host_id=result.failure_host_id or "not-selected",
                failure_vm_steps_lost=result.failure_vm_steps_lost,
                failure_cpu_demand_lost=result.failure_cpu_demand_lost,
                recovery_time_minutes=result.recovery_time_minutes,
                total_energy_wh=result.total_energy_wh, migrations=result.migrations,
                sla_host_steps=result.sla_host_steps,
            ))
    _write_csv(out_dir / "failure_injection.csv", [asdict(row) for row in failure_rows])
    _write_csv(out_dir / "failure_summary.csv", _summarize_failure(failure_rows))
    return failure_rows


def _write_csv(path: Path, records: Sequence[dict]) -> None:
    if not records:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def _mean_std(values: Iterable[float]) -> Tuple[float, float]:
    values = list(values)
    if not values:
        return 0.0, 0.0
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def summarize(rows: List[ExperimentRow]) -> List[dict]:
    keys = sorted({(r.experiment, r.scenario, r.mode, r.underload_threshold,
                    r.upper_threshold, r.vm_selection, r.migration_energy_wh_per_vm) for r in rows})
    output = []
    for key in keys:
        selected = [r for r in rows if (r.experiment, r.scenario, r.mode, r.underload_threshold,
                   r.upper_threshold, r.vm_selection, r.migration_energy_wh_per_vm) == key]
        group = dict(zip(("experiment", "scenario", "mode", "underload_threshold",
                          "upper_threshold", "vm_selection", "migration_energy_wh_per_vm"), key))
        group["runs"] = len(selected)
        for label, attr in (("energy_wh", "energy_wh"), ("host_energy_wh", "host_energy_wh"),
                            ("migration_energy_wh", "migration_energy_wh"),
                            ("migrations", "migrations"), ("sla_host_steps", "sla_host_steps"),
                            ("sla_host_step_rate_pct", "sla_host_step_rate_pct"),
                            ("sla_cpu_shortfall", "sla_cpu_shortfall"),
                            ("active_host_steps", "active_host_steps"),
                            ("powered_off_host_steps", "powered_off_host_steps"),
                            ("peak_active_hosts", "peak_active_hosts")):
            mean, std = _mean_std(getattr(r, attr) for r in selected)
            group[f"mean_{label}"] = round(mean, 4)
            group[f"std_{label}"] = round(std, 4)
        output.append(group)
    return output


def break_even_summary(rows: List[ExperimentRow]) -> List[dict]:
    """Find the per-migration energy penalty that cancels baseline savings.

    This is calculated for each paired seed as:
      (baseline total energy - consolidated host energy) / VM migrations.
    At or above this penalty, the unchanged consolidation plan no longer saves
    energy versus the baseline. It is an analytical break-even boundary, not a
    dynamic stop rule inside the placement policy.
    """
    paired: Dict[Tuple[str, int], Dict[str, ExperimentRow]] = {}
    for row in rows:
        if row.experiment != "baseline_comparison":
            continue
        paired.setdefault((row.scenario, row.seed), {})[row.mode] = row

    output: List[dict] = []
    for scenario in SCENARIOS:
        values = []
        baseline_energy = []
        host_energy = []
        migrations = []
        for (case, _seed), modes in paired.items():
            if case != scenario or "baseline" not in modes or "consolidated" not in modes:
                continue
            base = modes["baseline"]
            consolidated = modes["consolidated"]
            if consolidated.migrations <= 0:
                continue
            values.append((base.energy_wh - consolidated.host_energy_wh) / consolidated.migrations)
            baseline_energy.append(base.energy_wh)
            host_energy.append(consolidated.host_energy_wh)
            migrations.append(consolidated.migrations)
        mean, std = _mean_std(values)
        output.append({
            "scenario": scenario,
            "runs": len(values),
            "mean_baseline_energy_wh": round(statistics.mean(baseline_energy), 4) if baseline_energy else 0.0,
            "mean_consolidated_host_energy_wh": round(statistics.mean(host_energy), 4) if host_energy else 0.0,
            "mean_migrations": round(statistics.mean(migrations), 4) if migrations else 0.0,
            "mean_break_even_migration_energy_wh": round(mean, 4),
            "std_break_even_migration_energy_wh": round(std, 4),
        })
    return output


def _summarize_failure(rows: List[FailureRow]) -> List[dict]:
    output = []
    for scenario in SCENARIOS:
        group = [r for r in rows if r.scenario == scenario]
        record = {"scenario": scenario, "runs": len(group)}
        for label in ("failure_vm_steps_lost", "failure_cpu_demand_lost", "recovery_time_minutes",
                      "total_energy_wh", "migrations", "sla_host_steps"):
            mean, std = _mean_std(getattr(r, label) for r in group)
            record[f"mean_{label}"] = round(mean, 4)
            record[f"std_{label}"] = round(std, 4)
        output.append(record)
    return output
