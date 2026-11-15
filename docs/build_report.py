from __future__ import annotations

import csv
import html
import statistics
import sys
import unicodedata
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT_PDF = Path(__file__).resolve().parent / "report.pdf"
OUT_MD = Path(__file__).resolve().parent / "report.md"


def read_csv(name: str) -> list[dict]:
    with (RESULTS / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summary_row(rows: list[dict], experiment: str, scenario: str, mode: str | None = None,
                **filters: str) -> dict:
    for row in rows:
        if row["experiment"] != experiment or row["scenario"] != scenario:
            continue
        if mode is not None and row["mode"] != mode:
            continue
        if all(row[key] == value for key, value in filters.items()):
            return row
    raise KeyError((experiment, scenario, mode, filters))


def fmt(value: float, digits: int = 1) -> str:
    return f"{float(value):,.{digits}f}"


def ascii_text(value: str) -> str:
    value = value.translate(str.maketrans({
        "×": "x", "−": "-", "–": "-", "—": "-", "’": "'", "‘": "'",
        "“": '"', "”": '"', "·": "-", "Δ": "delta", "→": "to",
    }))
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def saved(baseline: dict, consolidated: dict) -> str:
    b = float(baseline["mean_energy_wh"])
    c = float(consolidated["mean_energy_wh"])
    return f"{100 * (b-c) / b:.1f}%"


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    line = "| " + " | ".join(headers) + " |"
    sep = "|" + "|".join("---" for _ in headers) + "|"
    return "\n".join([line, sep] + ["| " + " | ".join(row) + " |" for row in rows])


def make_energy_chart(main: list[dict]) -> Drawing:
    scenarios = ["steady", "diurnal", "spiky"]
    baseline = [float(summary_row(main, "baseline_comparison", s, "baseline")["mean_energy_wh"]) for s in scenarios]
    consolidated = [float(summary_row(main, "baseline_comparison", s, "consolidated")["mean_energy_wh"]) for s in scenarios]
    d = Drawing(475, 205)
    d.add(String(237, 190, "Energy use in Wh per simulated day (10 paired runs)", textAnchor="middle",
                 fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor("#0f172a")))
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 34
    chart.width = 375
    chart.height = 135
    chart.data = [baseline, consolidated]
    chart.categoryAxis.categoryNames = scenarios
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.boxAnchor = "n"
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = 35000
    chart.valueAxis.valueStep = 5000
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = "%.0f"
    chart.bars[0].fillColor = colors.HexColor("#64748b")
    chart.bars[1].fillColor = colors.HexColor("#0f766e")
    chart.groupSpacing = 14
    chart.barSpacing = 2
    chart.strokeColor = colors.white
    d.add(chart)
    d.add(Rect(155, 174, 8, 8, fillColor=colors.HexColor("#64748b"), strokeColor=None))
    d.add(String(168, 175, "Baseline", fontName="Helvetica", fontSize=8,
                 fillColor=colors.HexColor("#475569")))
    d.add(Rect(230, 174, 8, 8, fillColor=colors.HexColor("#0f766e"), strokeColor=None))
    d.add(String(243, 175, "Consolidated", fontName="Helvetica", fontSize=8,
                 fillColor=colors.HexColor("#475569")))
    return d


def make_architecture_diagram() -> Drawing:
    d = Drawing(475, 70)
    labels = [("Workload", "generator"), ("Host and VM", "simulator"),
              ("Consolidation", "policy"), ("Power and SLA", "accounting"),
              ("CSV and SVG", "results")]
    box_w, box_h, gap, y = 82, 42, 12, 18
    for i, (first, second) in enumerate(labels):
        x = i * (box_w + gap)
        d.add(Rect(x, y, box_w, box_h, rx=5, ry=5, fillColor=colors.HexColor("#ecfdf5"),
                   strokeColor=colors.HexColor("#0f766e"), strokeWidth=1.2))
        d.add(String(x + box_w/2, y + 24, first, textAnchor="middle", fontName="Helvetica-Bold",
                     fontSize=7, fillColor=colors.HexColor("#0f172a")))
        d.add(String(x + box_w/2, y + 11, second, textAnchor="middle", fontName="Helvetica",
                     fontSize=7, fillColor=colors.HexColor("#0f172a")))
        if i < len(labels) - 1:
            start_x, end_x, center_y = x + box_w, x + box_w + gap - 2, y + box_h/2
            d.add(Line(start_x, center_y, end_x, center_y, strokeColor=colors.HexColor("#475569"), strokeWidth=1.2))
            d.add(Polygon([end_x, center_y, end_x-4, center_y+2.5, end_x-4, center_y-2.5],
                          fillColor=colors.HexColor("#475569"), strokeColor=colors.HexColor("#475569")))
    return d


def build() -> None:
    rows = read_csv("summary.csv")
    fail_rows = read_csv("failure_summary.csv")
    break_even_rows = read_csv("break_even_summary.csv")
    scenarios = ["steady", "diurnal", "spiky"]
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    main_table = []
    for scenario in scenarios:
        b = summary_row(rows, "baseline_comparison", scenario, "baseline")
        c = summary_row(rows, "baseline_comparison", scenario, "consolidated")
        main_table.append([scenario.title(), fmt(b["mean_energy_wh"]), fmt(c["mean_energy_wh"]),
                           saved(b, c), fmt(c["mean_migrations"]),
                           fmt(c["mean_sla_host_step_rate_pct"], 2) + "%"])

    upper_table = []
    for scenario in scenarios:
        for cap in (0.55, 0.60, 0.65, 0.70):
            r = summary_row(rows, "upper_threshold_sweep", scenario, None, upper_threshold=str(cap))
            upper_table.append([scenario.title(), f"{cap:.0%}", fmt(r["mean_energy_wh"]),
                                fmt(r["mean_sla_host_steps"], 1)])

    low_table = []
    for scenario in scenarios:
        for threshold in (0.30, 0.40, 0.50):
            r = summary_row(rows, "threshold_sweep", scenario, None,
                            underload_threshold=str(threshold))
            low_table.append([scenario.title(), f"{threshold:.0%}", fmt(r["mean_energy_wh"]),
                              fmt(r["mean_migrations"]), fmt(r["mean_sla_host_steps"], 1)])

    policy_table = []
    for scenario in scenarios:
        for policy in ("smallest", "largest"):
            r = summary_row(rows, "vm_selection_comparison", scenario, None, vm_selection=policy)
            policy_table.append([scenario.title(), policy, fmt(r["mean_energy_wh"]),
                                 fmt(r["mean_migrations"]), fmt(r["mean_sla_host_steps"], 1)])

    migration_table = []
    for scenario in scenarios:
        for cost in (0.0, 1.0, 5.0):
            r = summary_row(rows, "migration_cost_sweep", scenario, None,
                             migration_energy_wh_per_vm=str(cost))
            migration_table.append([scenario.title(), fmt(cost, 0), fmt(r["mean_energy_wh"]),
                                    fmt(r["mean_migrations"])])

    failure_table = []
    for scenario in scenarios:
        r = next(x for x in fail_rows if x["scenario"] == scenario)
        failure_table.append([scenario.title(), fmt(r["mean_failure_vm_steps_lost"], 1),
                              fmt(r["mean_recovery_time_minutes"], 0),
                              fmt(r["mean_sla_host_steps"], 1), fmt(r["mean_migrations"], 1)])

    break_even_table = []
    for scenario in scenarios:
        r = next(x for x in break_even_rows if x["scenario"] == scenario)
        break_even_table.append([scenario.title(), fmt(r["mean_migrations"]),
                                 fmt(r["mean_break_even_migration_energy_wh"], 1),
                                 fmt(r["std_break_even_migration_energy_wh"], 1)])

    # Report source is deliberately split into 14 sections/pages for direct editing.
    sections: list[tuple[str, list[str]]] = []
    sections.append(("Abstract", [
        "This mini project implements a local simulator for energy-aware virtual machine (VM) consolidation. It models CPU demand from 40 VMs on 10 physical hosts over a 24-hour day. A consolidation policy moves VMs away from hosts that remain underloaded, packs them onto other hosts within a CPU safety cap, and switches off hosts that become empty. A no-consolidation baseline uses the same workload traces.",
        "Across 10 paired runs per workload, the default policy reduced modeled energy by 22.5% for steady demand, 38.2% for diurnal demand, and 25.2% for spiky demand. It made an average of 14.4, 22.0, and 15.5 migrations respectively. The host-time SLA violation rate was 0.00%, 0.14%, and 2.08%. A separate one-interval host crash experiment measured unavailable VM-time and a 15-minute modeled recovery.",
        "These are simulation results, not physical electricity readings. Workloads and wattage values are synthetic or illustrative assumptions. The project includes source code, raw and summarized CSV data, SVG figures, an architecture diagram, a repeatable command, a demo outline, and this report.",
        "Keywords: cloud computing, virtual machines, consolidation, energy model, migration, SLA, simulation."
    ]))
    sections.append(("1. Introduction and Problem Statement", [
        "Cloud data centres host many virtual machines on physical servers. Workloads change through the day, so some servers may operate at low utilization while others have spare capacity. Consolidating VMs can concentrate work on fewer hosts and allow empty hosts to be switched off. The trade-off is that migrations consume resources and excessive packing can cause CPU overload and service-level agreement (SLA) violations.",
        "Energy-aware allocation research treats energy and performance as connected goals: resource placement should reduce power while preserving service quality [2]. This project studies that trade-off with a small simulator that can be reproduced on a student laptop. The chosen scope follows Project 15 in the CSN349 Advanced Project Handout [1].",
        "Problem statement: Given a fixed set of hosts and VMs whose CPU demand changes over time, how much modeled energy can be saved by migrating VMs from underloaded hosts, and how do the underload threshold, destination utilization cap, migration cost, and workload shape affect energy use and SLA violations?",
        "The simulator is intentionally CPU-only. It does not claim to model the full complexity of production hypervisors, storage, network traffic, temperature, cooling, or live migration."
    ]))
    sections.append(("2. Objectives and Scope", [
        "Objectives: (1) implement a discrete-time host/VM simulator; (2) generate changing CPU demands for multiple workload shapes; (3) implement underloaded-host detection and VM migration; (4) apply a host power model; (5) compare energy use with and without consolidation; (6) measure migrations and SLA violations; (7) repeat the experiments; and (8) inject a host failure and record unavailable VM-time and recovery.",
        "Research questions: RQ1, does consolidation reduce modeled energy compared with static placement? RQ2, how does the maximum destination utilization affect the energy/SLA trade-off? RQ3, how do VM selection order and migration energy change results? RQ4, what service impact appears when a host fails for one interval?",
        "The simulator uses 10 homogeneous hosts with 100 CPU units each and 40 VMs. Time advances in 96 intervals of 15 minutes. There is no external dataset, paid service, cloud account, or real VM migration. Workloads use deterministic pseudo-random seeds so another person can reproduce the included results.",
        "The minimum requirements from the handout are directly mapped to working code: changing VM load, a consolidation policy for underloaded hosts, and the linear power model. Measurements include energy with/without consolidation, migration count, and SLA violations. Stretch work compares VM selection policies and includes an explicit migration-cost sweep."
    ]))
    sections.append(("3. Architecture", [
        "The system has five components. The synthetic workload generator creates one CPU demand value per VM per interval. The simulator keeps host state, VM placement, host utilization, and power state. The consolidation policy identifies underloaded hosts, chooses VM migration order, and finds a best-fit destination under a utilization cap. The accounting component calculates host energy, migration energy, SLA events, and failure impact. The experiment runner repeats paired scenarios and writes CSV summaries; the chart generator writes SVG figures.",
        "The data flow is: workload traces → simulator state → consolidation and placement → power/migration/SLA accounting → CSV and charts. `docs/architecture.mmd` contains the editable diagram. The code is separated into `workloads.py`, `simulator.py`, `models.py`, `experiments.py`, and `charts.py` so each concern can be reviewed independently.",
        "The control loop is centralized and has complete knowledge of the simulated state. This is a deliberate small-project simplification. A real production controller would need distributed monitoring, migration APIs, resource reservations, failure handling, and a more detailed performance model."
    ]))
    sections.append(("4. System Model and Assumptions", [
        "Each host has CPU capacity C = 100 units, idle power P_idle = 90 W, and maximum power P_max = 180 W. For a host with CPU demand D, utilization u = min(1, max(0, D/C)). The host power is P = P_idle + (P_max − P_idle) × u. Host energy for an interval of length Δt hours is E_host = P × Δt. The total host energy is the sum over active hosts and all intervals.",
        "The interval length is 15 minutes, or 0.25 hours. An empty host is switched off and is modeled at 0 W. A VM migration adds 1 Wh in the default configuration. Thus E_total = Σ(P_host × Δt) + N_migrations × E_migration. Migration energy is an explicit assumed penalty, not measured hypervisor power.",
        "A host-time SLA violation occurs when demand exceeds host capacity. The violation count is recorded by interval and host; the simulator also totals CPU demand above capacity. In the failure experiment, a host outage makes its resident VM demand unavailable and is counted as an SLA violation. Workload scenarios are steady, diurnal, and spiky; they are generated in code and are not real trace data.",
        "Initial placement distributes VMs round-robin across hosts. Workload seeds are fixed and paired between baseline and consolidation comparisons. The report does not claim emissions or carbon savings because no regional grid-intensity factor is modeled."
    ]))
    sections.append(("5. Consolidation Policy", [
        "The default policy uses a 40% underload threshold, a 60% upper utilization cap for destinations, and a two-interval underload window. A host must remain below the underload threshold for two consecutive intervals before migration is attempted. This hysteresis-like window reduces decisions caused by a single low-load sample.",
        "The policy inspects VMs on an eligible source host in ascending current CPU demand order (smallest first). For each VM, it considers active destination hosts that would remain under the utilization cap after placement. It chooses the feasible host with the least remaining CPU headroom, a best-fit rule. When the source host becomes empty, it is switched off. If a VM cannot fit elsewhere, it remains on the source host.",
        "The alternative selection policy sorts VMs largest first. The destination cap is a safeguard: an empty host saves modeled idle power, but packing active hosts too tightly can cause dynamic load spikes to exceed capacity. A sensitivity sweep tests caps of 55%, 60%, 65%, and 70%.",
        "Policy pseudocode: for each interval, update demand; calculate host loads; find hosts below the lower threshold for the required window; move each VM to a feasible best-fit host; turn off emptied sources; calculate power, migration penalty, and SLA results."
    ]))
    sections.append(("6. Implementation and Reproducibility", [
        "The simulator is implemented in Python and uses only the standard library at runtime. `SimulationConfig` holds host count, VM count, time resolution, thresholds, migration penalty, and selection order. `generate_workload` builds deterministic traces. `VMSimulator` runs one trace. The experiment runner applies paired seeds and aggregates means and sample standard deviations. Charts are written as SVG without a charting dependency.",
        "Run the complete experiment from the project root with `python run_project.py all --runs 10`. The command refuses fewer than 10 repetitions. It creates `results/raw_runs.csv`, `results/summary.csv`, `results/experiment_metadata.json`, `results/failure_injection.csv`, `results/failure_summary.csv`, and the figures directory. Raw rows allow the summary figures to be recomputed independently.",
        "The included run contains 420 policy experiments (42 conditions × 10 runs) plus 30 failure experiments (3 workload patterns × 10 runs). A seed is shared within paired comparisons, so baseline and consolidation see the same synthetic demand for that run. `docs/build_report.py` regenerates the PDF and Markdown report from the CSV summaries; the PDF is also included for immediate review.",
        "The project has no external workload dataset, so there are no dataset terms to reproduce. Python and optional ReportLab are listed with versions and licenses in `docs/tools_and_licenses.csv`."
    ]))
    sections.append(("7. Experimental Design", [
        "The baseline leaves every host powered on and never migrates VMs. The consolidation run uses the same workload seed, starting VM placement, host power assumptions, and time interval. This paired design isolates the change caused by the policy. Each condition is repeated 10 times with fixed but varied seeds; the report shows means and the CSV includes standard deviations.",
        "The default baseline comparison covers 3 scenarios × 2 modes × 10 seeds = 60 runs. Underload-threshold sensitivity tests 30%, 40%, and 50%. Destination-cap sensitivity tests 55%, 60%, 65%, and 70%. The VM-selection stretch goal compares smallest-first and largest-first. Migration cost is tested at 0, 1, and 5 Wh per migration. Each sensitivity condition uses 10 runs per workload.",
        "The failure-injection experiment uses the consolidated configuration. At interval 48 (12 hours), the busiest active host is switched off for one interval. VMs on that host are unavailable for that interval; the host returns on the next interval. The experiment records the affected VM-steps, lost CPU demand, SLA host-steps, energy, migrations, and recovery time.",
        "Main measures: total modeled Wh per simulated day; percentage energy reduction versus paired baseline; number of migrations; SLA host-time count/rate; powered-off host-time; and failure recovery time. The project reports model outputs honestly and does not extrapolate them to real electricity bills."
    ]))
    sections.append(("8. Results: Baseline and Consolidation", [
        "The following table reports means over 10 runs per condition. Baseline and consolidated runs use the same workload seeds. Consolidated energy includes the default 1 Wh per VM migration.",
        "Measured main results:",
        "The break-even migration penalty is (baseline energy - consolidated host energy) divided by the number of migrations. At or above this cost per migrated VM, the same consolidation plan no longer saves energy compared with the baseline. This is a measured cost boundary; the policy does not dynamically cancel individual migrations."
    ]))
    sections.append(("9. Results: Sensitivity and Stretch Goal", [
        "Destination cap sensitivity shows the central trade-off: tighter caps use more hosts and more energy but suppress overload events; higher caps save more energy while raising SLA violations under diurnal and bursty demand. At 55%, mean host-time violations were 0 for diurnal and 0.6 host-steps for spiky demand; at 70%, they rose to 81.4 and 39.7 respectively.",
        "Underload threshold sensitivity and VM selection results are shown below. For the spiky workload, moving the underload trigger from 30% to 40% reduced mean energy from 27,496.5 Wh to 23,391.5 Wh, while mean SLA host-steps rose from 1.6 to 9.8. The steady workload also saved more energy at 40% than at 30%, with no observed overloads.",
        "Largest-first selection used slightly less energy than smallest-first in all three workload patterns in these runs. Differences were small, so the data does not establish a universal winner. The migration-energy sweep changed total energy in proportion to the assumed migration cost while leaving migration counts nearly unchanged; placement decisions do not currently optimize against migration cost."
    ]))
    sections.append(("10. Detailed Sensitivity Results", [
        "The tables on this page contain the sensitivity outputs for the 10-run experiment set. Energy is total modeled Wh per simulated day. SLA steps are the average count of host-time intervals that violate the modeled CPU service limit.",
        "In the destination-cap sweep, the 60% cap reduces energy relative to a 55% cap but exposes a small number of SLA events under time-varying workloads. A cap of 70% reduces modeled energy further, with a much larger increase in violations. This supports treating the cap as a service-quality control, not merely an energy optimization knob.",
        "The lower-threshold and selection sweeps show that results depend on workload shape. No single policy wins every metric. A provider would need to select a point on the energy/service trade-off that matches its SLA target."
    ]))
    sections.append(("11. Failure Injection", [
        "The failure experiment is a controlled one-interval host crash. At the 12-hour point, the simulator selects the active host with the largest current CPU load, turns it off for one 15-minute interval, and restores it at the following interval. Resident VM demand is counted as unavailable during the outage. This tests whether the model records a service impact and recovery point; it is not a high-availability implementation.",
        "Failure results below are means over 10 runs per workload. The average recovery time is one interval (15 minutes). Mean VM-steps lost vary with how many VMs occupy the selected host. Spiky runs also include ordinary consolidation overload events, which is why their SLA host-step mean is higher than one.",
        "The injected failure is repeatable and has an observable outcome in `results/failure_injection.csv`. A useful demo is to show the event in the report, then inspect the CSV row values. The project does not claim zero data loss or automatic VM recovery; it models service restoration when the host returns."
    ]))
    sections.append(("12. Analysis, Limitations and Conclusion", [
        "The simulator supports the conclusion that consolidation can reduce modeled energy when the initial placement leaves underused hosts. In the included configuration, savings range from 22.5% to 38.2% across workload patterns. The destination cap controls the energy/SLA trade-off: packing more tightly can reduce energy, but dynamic peaks create more host-time violations. The 60% cap provides a more conservative result than the 65-70% caps tested, while still reducing modeled energy.",
        "Limitations: CPU is the only resource; wattage values are illustrative; VM CPU traces are synthetic; there is no boot/sleep delay; a switched-off host is assumed to consume zero power; migration cost is a fixed per-VM penalty; workload demands are treated as known at each interval; no memory, disk, network, cooling, carbon intensity, or real hypervisor overhead is modeled. Failure recovery is a one-interval host restart rather than redundant replication or rescheduling to other hosts.",
        "Next improvements could use a public workload trace with its terms cited, add memory/network constraints, model transition energy and migration downtime, compare threshold controllers with predictive placement, and add recovery by relocating VMs after a permanent host failure.",
        "Conclusion: The project implements the handout's simulator, changing-load, underloaded-host migration, power-model, energy comparison, migration count, SLA, repeatability, stretch-policy, break-even, and failure-injection goals. The team still needs to produce its live or recorded demo and complete the signed contribution statement. The main lesson is that energy savings must be evaluated alongside service violations and migration overhead, not in isolation."
    ]))
    sections.append(("13. Tools, References and Team Contributions", [
        f"Tools used: Python {py_version} with the Python Software Foundation License 2.0 for the simulator and standard library; ReportLab 4.4.9 under its BSD license for optional PDF generation; Git 2.52.0 under GNU GPL version 2 for version control. No paid tools, cloud accounts, or external datasets are used. The runtime has no third-party dependencies.",
        "References: [1] CSF349/CSN349 Cloud Computing, Advanced Project Handout, School of Computing, DIT University, Project 15: Energy-Aware VM Consolidation. [2] A. Beloglazov, J. Abawajy, and R. Buyya, ‘Energy-aware resource allocation heuristics for efficient management of data centers for Cloud computing,’ Future Generation Computer Systems, vol. 28, no. 5, pp. 755–768, 2012, doi:10.1016/j.future.2011.04.017.",
        "Contribution statement: The handout requires a signed statement from each team member. Complete `docs/contributions.md` with the actual names, student IDs, contributions, and signatures. This template is intentionally blank because team identities and work allocations must be supplied by the team.",
        "Submission checklist: repository/source code; one-command run instructions; architecture diagram; 12–15 page report; repeated experiments and tables/figures; tool/license table; demo with failure injection; and signed individual contribution statements. The code, report draft, results, chart files, demo outline, and contribution template are included in this project package."
    ]))

    # Include explicit Markdown tables on the pages where results are presented.
    page_extra: dict[int, list[tuple[str, list[list[str]]]]] = {
        9: [("Baseline versus consolidation (mean of 10 paired runs)",
             [["Workload", "Baseline Wh", "Consolidated Wh", "Saved", "Migrations", "SLA rate"]] + main_table),
            ("Break-even migration penalty (Wh per migrated VM)",
             [["Workload", "Migrations", "Break-even penalty", "SD"]] + break_even_table)],
        10: [("Destination cap sensitivity (10 runs per workload and cap)",
             [["Workload", "Cap", "Energy Wh", "SLA host-steps"]] + upper_table)],
        11: [("Underload threshold sensitivity (10 runs per workload and threshold)",
             [["Workload", "Trigger", "Energy Wh", "Migrations", "SLA steps"]] + low_table),
            ("VM-selection policy comparison", [["Workload", "Policy", "Energy Wh", "Migrations", "SLA steps"]] + policy_table),
            ("Migration-cost sensitivity (Wh per migrated VM)", [["Workload", "Penalty", "Energy Wh", "Migrations"]] + migration_table)],
        12: [("Host crash: mean values across 10 runs per workload", [["Workload", "VM-steps lost", "Recovery min", "SLA steps", "Migrations"]] + failure_table)],
        14: [("Project tools and licenses", [["Tool", "Version", "License", "Use"],
              ["Python", py_version, "PSF License 2.0", "Simulator and standard library"],
              ["ReportLab", "4.4.9", "BSD license", "Optional report PDF generation"],
              ["Git", "2.52.0", "GNU GPL v2", "Version control repository"]])]
    }

    # PDF sections: cover plus 14 topic pages = 15 pages, within the required range.
    md_parts = ["# Energy-Aware VM Consolidation\n\n**CSN349 Cloud Computing Mini Project**\n\nSchool of Computing, DIT University, Dehradun\n\nTeam members: complete in the contribution statement.\n\n---\n"]
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontName="Helvetica-Bold",
                                 fontSize=25, leading=31, alignment=TA_CENTER,
                                 textColor=colors.HexColor("#0f172a"), spaceAfter=20)
    subtitle_style = ParagraphStyle("SubtitleCustom", parent=styles["Normal"], fontName="Helvetica",
                                    fontSize=13, leading=19, alignment=TA_CENTER,
                                    textColor=colors.HexColor("#334155"), spaceAfter=10)
    heading_style = ParagraphStyle("PageHeading", parent=styles["Heading1"], fontName="Helvetica-Bold",
                                   fontSize=16, leading=19, textColor=colors.HexColor("#0f766e"),
                                   spaceAfter=9)
    body_style = ParagraphStyle("BodyCustom", parent=styles["BodyText"], fontName="Helvetica",
                                fontSize=9.1, leading=12.4, alignment=TA_LEFT,
                                textColor=colors.HexColor("#1e293b"), spaceAfter=7)
    small_style = ParagraphStyle("SmallCustom", parent=body_style, fontSize=7.6, leading=9.2, spaceAfter=2)
    cover = [Spacer(1, 31*mm), Paragraph("Energy-Aware<br/>VM Consolidation", title_style),
             Paragraph("Dynamic workload simulation with VM migration, a host power model, repeated measurements, and failure injection", subtitle_style),
             Spacer(1, 20*mm), Paragraph("CSN349 Cloud Computing Mini Project", subtitle_style),
             Paragraph("CSF349 Advanced Project Handout · Project 15", subtitle_style),
             Paragraph("School of Computing<br/>DIT University, Dehradun", subtitle_style),
             Spacer(1, 30*mm), Paragraph("Team members and signatures: see the included contribution statement template.", subtitle_style),
             Paragraph("Results shown in this report were generated by the included simulator.", subtitle_style), PageBreak()]
    story.extend(cover)

    # Map the 12 report sections to human-readable headings and page numbers.
    headings = [
        "Abstract", "1. Introduction and Problem Statement", "2. Objectives and Scope",
        "3. Architecture", "4. System Model and Assumptions", "5. Consolidation Policy",
        "6. Implementation and Reproducibility", "7. Experimental Design",
        "8. Results: Baseline and Consolidation", "9. Results: Sensitivity and Stretch Goal",
        "10. Detailed Sensitivity Results", "11. Failure Injection",
        "12. Analysis, Limitations and Conclusion",
        "13. Tools, References and Team Contributions"
    ]
    for idx, ((_, paragraphs), heading) in enumerate(zip(sections, headings), start=1):
        if idx > 1:
            story.append(PageBreak())
        heading = ascii_text(heading)
        story.append(Paragraph(html.escape(heading), heading_style))
        md_parts.append(f"## {heading}\n\n")
        for para in paragraphs:
            para = ascii_text(para)
            story.append(Paragraph(html.escape(para), body_style))
            md_parts.append(para + "\n\n")
        if idx == 4:
            story.extend([make_architecture_diagram(), Spacer(1, 5)])
        for table_title, data in page_extra.get(idx, []):
            table_title = ascii_text(table_title)
            story.append(Paragraph(html.escape(table_title), ParagraphStyle("TableTitle", parent=body_style,
                                fontName="Helvetica-Bold", fontSize=8.5, leading=10, spaceBefore=3, spaceAfter=4)))
            table_data = [[Paragraph(html.escape(ascii_text(str(cell))), small_style) for cell in row] for row in data]
            available = A4[0] - 34*mm
            widths = [available / len(data[0])] * len(data[0])
            table = Table(table_data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("LEFTPADDING", (0,0), (-1,-1), 4), ("RIGHTPADDING", (0,0), (-1,-1), 4),
                ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ]))
            story.extend([table, Spacer(1, 5)])
            md_parts.append(f"**{table_title}**\n\n")
            md_parts.append(markdown_table(data[0], data[1:]) + "\n\n")
        if idx == 9:
            story.append(make_energy_chart(rows))

    md_parts.append("\n---\n\n**Submission note:** add team names and signatures in `contributions.md`; confirm these results with a fresh run before final submission.\n")
    OUT_MD.write_text("".join(md_parts), encoding="utf-8")

    def draw_page(canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        if page_num > 1:
            canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
            canvas.line(17*mm, 14*mm, A4[0]-17*mm, 14*mm)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.drawString(17*mm, 9*mm, "CSN349 · Energy-Aware VM Consolidation")
            canvas.drawRightString(A4[0]-17*mm, 9*mm, f"Page {page_num}")
        canvas.restoreState()

    doc = BaseDocTemplate(str(OUT_PDF), pagesize=A4, leftMargin=17*mm, rightMargin=17*mm,
                          topMargin=17*mm, bottomMargin=19*mm, title="Energy-Aware VM Consolidation",
                          author="CSN349 project team")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=draw_page)])
    doc.build(story)
    print(f"Wrote {OUT_PDF} and {OUT_MD}")


if __name__ == "__main__":
    build()
