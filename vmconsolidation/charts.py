from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


COLORS = {"baseline": "#64748b", "consolidated": "#0f766e", "smallest": "#2563eb", "largest": "#d97706"}


def _read_rows(path: Path) -> List[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _svg_bar_chart(path: Path, title: str, categories: List[str], series: Dict[str, List[float]], ylabel: str) -> None:
    width, height = 900, 500
    left, right, top, bottom = 90, 40, 70, 100
    plot_w, plot_h = width - left - right, height - top - bottom
    all_values = [v for values in series.values() for v in values]
    ymax = max(all_values or [1]) * 1.18
    if ymax <= 0:
        ymax = 1
    y_ticks = 5
    group_n = max(1, len(categories))
    bar_series = max(1, len(series))
    group_w = plot_w / group_n
    bar_w = min(48, group_w / (bar_series + 1))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#ffffff"/>',
             f'<text x="{width/2}" y="35" text-anchor="middle" font-family="Arial" font-size="22" font-weight="bold" fill="#0f172a">{title}</text>']
    for i in range(y_ticks + 1):
        val = ymax * i / y_ticks
        y = top + plot_h - plot_h * i / y_ticks
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" stroke="#e2e8f0"/>')
        parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#475569">{val:.1f}</text>')
    parts.append(f'<text x="20" y="{top+plot_h/2}" transform="rotate(-90 20 {top+plot_h/2})" text-anchor="middle" font-family="Arial" font-size="14" fill="#334155">{ylabel}</text>')
    names = list(series)
    for ci, category in enumerate(categories):
        center = left + group_w * (ci + 0.5)
        offset = -((len(names) - 1) * bar_w) / 2
        for si, name in enumerate(names):
            val = series[name][ci]
            bh = plot_h * val / ymax
            x = center + offset + si * bar_w - bar_w * 0.42
            y = top + plot_h - bh
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w*0.84:.1f}" height="{bh:.1f}" rx="4" fill="{COLORS.get(name, "#7c3aed")}"/>')
            parts.append(f'<text x="{x+bar_w*0.42:.1f}" y="{y-5:.1f}" text-anchor="middle" font-family="Arial" font-size="10" fill="#334155">{val:.1f}</text>')
        parts.append(f'<text x="{center:.1f}" y="{top+plot_h+24}" text-anchor="middle" font-family="Arial" font-size="13" fill="#334155">{category}</text>')
    legend_x = left + 10
    for i, name in enumerate(names):
        x = legend_x + i * 170
        parts.append(f'<rect x="{x}" y="{height-35}" width="14" height="14" fill="{COLORS.get(name, "#7c3aed")}"/>')
        parts.append(f'<text x="{x+20}" y="{height-23}" font-family="Arial" font-size="12" fill="#334155">{name}</text>')
    parts.append('</svg>')
    path.write_text("\n".join(parts), encoding="utf-8")


def generate_charts(results_dir: Path) -> None:
    rows = _read_rows(results_dir / "summary.csv")
    plots = results_dir / "figures"
    plots.mkdir(exist_ok=True)
    scenarios = ["steady", "diurnal", "spiky"]

    baseline = defaultdict(dict)
    for row in rows:
        if row["experiment"] == "baseline_comparison":
            baseline[row["mode"]][row["scenario"]] = float(row["mean_energy_wh"])
    _svg_bar_chart(plots / "energy_baseline_vs_consolidated.svg", "Energy by workload: baseline vs consolidation",
                   scenarios, {mode: [baseline[mode][s] for s in scenarios] for mode in ("baseline", "consolidated")}, "Energy (Wh / simulated day)")

    threshold_rows = [r for r in rows if r["experiment"] == "threshold_sweep"]
    thresholds = [0.30, 0.40, 0.50]
    _svg_bar_chart(plots / "energy_by_threshold.svg", "Energy by underload threshold (all workloads)",
                   ["30%", "40%", "50%"], {"consolidated": [
                       sum(float(r["mean_energy_wh"]) for r in threshold_rows if float(r["underload_threshold"]) == t) / len(scenarios)
                       for t in thresholds]}, "Energy (Wh / simulated day)")

    upper_rows = [r for r in rows if r["experiment"] == "upper_threshold_sweep"]
    upper_thresholds = [0.55, 0.60, 0.65, 0.70]
    _svg_bar_chart(plots / "energy_by_safety_cap.svg", "Energy by host utilization safety cap",
                   ["55%", "60%", "65%", "70%"], {"consolidated": [
                       sum(float(r["mean_energy_wh"]) for r in upper_rows if float(r["upper_threshold"]) == t) / len(scenarios)
                       for t in upper_thresholds]}, "Energy (Wh / simulated day)")

    sel_rows = [r for r in rows if r["experiment"] == "vm_selection_comparison"]
    sel = defaultdict(dict)
    for row in sel_rows:
        sel[row["vm_selection"]][row["scenario"]] = float(row["mean_energy_wh"])
    _svg_bar_chart(plots / "energy_by_vm_selection.svg", "VM selection policy comparison",
                   scenarios, {mode: [sel[mode][s] for s in scenarios] for mode in ("smallest", "largest")}, "Energy (Wh / simulated day)")
