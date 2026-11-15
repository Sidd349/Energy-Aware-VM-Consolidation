# Energy-Aware VM Consolidation

**CSN349 Cloud Computing Mini Project**

School of Computing, DIT University, Dehradun

Team members: complete in the contribution statement.

---
## Abstract

This mini project implements a local simulator for energy-aware virtual machine (VM) consolidation. It models CPU demand from 40 VMs on 10 physical hosts over a 24-hour day. A consolidation policy moves VMs away from hosts that remain underloaded, packs them onto other hosts within a CPU safety cap, and switches off hosts that become empty. A no-consolidation baseline uses the same workload traces.

Across 10 paired runs per workload, the default policy reduced modeled energy by 22.5% for steady demand, 38.2% for diurnal demand, and 25.2% for spiky demand. It made an average of 14.4, 22.0, and 15.5 migrations respectively. The host-time SLA violation rate was 0.00%, 0.14%, and 2.08%. A separate one-interval host crash experiment measured unavailable VM-time and a 15-minute modeled recovery.

These are simulation results, not physical electricity readings. Workloads and wattage values are synthetic or illustrative assumptions. The project includes source code, raw and summarized CSV data, SVG figures, an architecture diagram, a repeatable command, a demo outline, and this report.

Keywords: cloud computing, virtual machines, consolidation, energy model, migration, SLA, simulation.

## 1. Introduction and Problem Statement

Cloud data centres host many virtual machines on physical servers. Workloads change through the day, so some servers may operate at low utilization while others have spare capacity. Consolidating VMs can concentrate work on fewer hosts and allow empty hosts to be switched off. The trade-off is that migrations consume resources and excessive packing can cause CPU overload and service-level agreement (SLA) violations.

Energy-aware allocation research treats energy and performance as connected goals: resource placement should reduce power while preserving service quality [2]. This project studies that trade-off with a small simulator that can be reproduced on a student laptop. The chosen scope follows Project 15 in the CSN349 Advanced Project Handout [1].

Problem statement: Given a fixed set of hosts and VMs whose CPU demand changes over time, how much modeled energy can be saved by migrating VMs from underloaded hosts, and how do the underload threshold, destination utilization cap, migration cost, and workload shape affect energy use and SLA violations?

The simulator is intentionally CPU-only. It does not claim to model the full complexity of production hypervisors, storage, network traffic, temperature, cooling, or live migration.

## 2. Objectives and Scope

Objectives: (1) implement a discrete-time host/VM simulator; (2) generate changing CPU demands for multiple workload shapes; (3) implement underloaded-host detection and VM migration; (4) apply a host power model; (5) compare energy use with and without consolidation; (6) measure migrations and SLA violations; (7) repeat the experiments; and (8) inject a host failure and record unavailable VM-time and recovery.

Research questions: RQ1, does consolidation reduce modeled energy compared with static placement? RQ2, how does the maximum destination utilization affect the energy/SLA trade-off? RQ3, how do VM selection order and migration energy change results? RQ4, what service impact appears when a host fails for one interval?

The simulator uses 10 homogeneous hosts with 100 CPU units each and 40 VMs. Time advances in 96 intervals of 15 minutes. There is no external dataset, paid service, cloud account, or real VM migration. Workloads use deterministic pseudo-random seeds so another person can reproduce the included results.

The minimum requirements from the handout are directly mapped to working code: changing VM load, a consolidation policy for underloaded hosts, and the linear power model. Measurements include energy with/without consolidation, migration count, and SLA violations. Stretch work compares VM selection policies and includes an explicit migration-cost sweep.

## 3. Architecture

The system has five components. The synthetic workload generator creates one CPU demand value per VM per interval. The simulator keeps host state, VM placement, host utilization, and power state. The consolidation policy identifies underloaded hosts, chooses VM migration order, and finds a best-fit destination under a utilization cap. The accounting component calculates host energy, migration energy, SLA events, and failure impact. The experiment runner repeats paired scenarios and writes CSV summaries; the chart generator writes SVG figures.

The data flow is: workload traces to simulator state to consolidation and placement to power/migration/SLA accounting to CSV and charts. `docs/architecture.mmd` contains the editable diagram. The code is separated into `workloads.py`, `simulator.py`, `models.py`, `experiments.py`, and `charts.py` so each concern can be reviewed independently.

The control loop is centralized and has complete knowledge of the simulated state. This is a deliberate small-project simplification. A real production controller would need distributed monitoring, migration APIs, resource reservations, failure handling, and a more detailed performance model.

## 4. System Model and Assumptions

Each host has CPU capacity C = 100 units, idle power P_idle = 90 W, and maximum power P_max = 180 W. For a host with CPU demand D, utilization u = min(1, max(0, D/C)). The host power is P = P_idle + (P_max - P_idle) x u. Host energy for an interval of length deltat hours is E_host = P x deltat. The total host energy is the sum over active hosts and all intervals.

The interval length is 15 minutes, or 0.25 hours. An empty host is switched off and is modeled at 0 W. A VM migration adds 1 Wh in the default configuration. Thus E_total = (P_host x deltat) + N_migrations x E_migration. Migration energy is an explicit assumed penalty, not measured hypervisor power.

A host-time SLA violation occurs when demand exceeds host capacity. The violation count is recorded by interval and host; the simulator also totals CPU demand above capacity. In the failure experiment, a host outage makes its resident VM demand unavailable and is counted as an SLA violation. Workload scenarios are steady, diurnal, and spiky; they are generated in code and are not real trace data.

Initial placement distributes VMs round-robin across hosts. Workload seeds are fixed and paired between baseline and consolidation comparisons. The report does not claim emissions or carbon savings because no regional grid-intensity factor is modeled.

## 5. Consolidation Policy

The default policy uses a 40% underload threshold, a 60% upper utilization cap for destinations, and a two-interval underload window. A host must remain below the underload threshold for two consecutive intervals before migration is attempted. This hysteresis-like window reduces decisions caused by a single low-load sample.

The policy inspects VMs on an eligible source host in ascending current CPU demand order (smallest first). For each VM, it considers active destination hosts that would remain under the utilization cap after placement. It chooses the feasible host with the least remaining CPU headroom, a best-fit rule. When the source host becomes empty, it is switched off. If a VM cannot fit elsewhere, it remains on the source host.

The alternative selection policy sorts VMs largest first. The destination cap is a safeguard: an empty host saves modeled idle power, but packing active hosts too tightly can cause dynamic load spikes to exceed capacity. A sensitivity sweep tests caps of 55%, 60%, 65%, and 70%.

Policy pseudocode: for each interval, update demand; calculate host loads; find hosts below the lower threshold for the required window; move each VM to a feasible best-fit host; turn off emptied sources; calculate power, migration penalty, and SLA results.

## 6. Implementation and Reproducibility

The simulator is implemented in Python and uses only the standard library at runtime. `SimulationConfig` holds host count, VM count, time resolution, thresholds, migration penalty, and selection order. `generate_workload` builds deterministic traces. `VMSimulator` runs one trace. The experiment runner applies paired seeds and aggregates means and sample standard deviations. Charts are written as SVG without a charting dependency.

Run the complete experiment from the project root with `python run_project.py all --runs 10`. The command refuses fewer than 10 repetitions. It creates `results/raw_runs.csv`, `results/summary.csv`, `results/experiment_metadata.json`, `results/failure_injection.csv`, `results/failure_summary.csv`, and the figures directory. Raw rows allow the summary figures to be recomputed independently.

The included run contains 420 policy experiments (42 conditions x 10 runs) plus 30 failure experiments (3 workload patterns x 10 runs). A seed is shared within paired comparisons, so baseline and consolidation see the same synthetic demand for that run. `docs/build_report.py` regenerates the PDF and Markdown report from the CSV summaries; the PDF is also included for immediate review.

The project has no external workload dataset, so there are no dataset terms to reproduce. Python and optional ReportLab are listed with versions and licenses in `docs/tools_and_licenses.csv`.

## 7. Experimental Design

The baseline leaves every host powered on and never migrates VMs. The consolidation run uses the same workload seed, starting VM placement, host power assumptions, and time interval. This paired design isolates the change caused by the policy. Each condition is repeated 10 times with fixed but varied seeds; the report shows means and the CSV includes standard deviations.

The default baseline comparison covers 3 scenarios x 2 modes x 10 seeds = 60 runs. Underload-threshold sensitivity tests 30%, 40%, and 50%. Destination-cap sensitivity tests 55%, 60%, 65%, and 70%. The VM-selection stretch goal compares smallest-first and largest-first. Migration cost is tested at 0, 1, and 5 Wh per migration. Each sensitivity condition uses 10 runs per workload.

The failure-injection experiment uses the consolidated configuration. At interval 48 (12 hours), the busiest active host is switched off for one interval. VMs on that host are unavailable for that interval; the host returns on the next interval. The experiment records the affected VM-steps, lost CPU demand, SLA host-steps, energy, migrations, and recovery time.

Main measures: total modeled Wh per simulated day; percentage energy reduction versus paired baseline; number of migrations; SLA host-time count/rate; powered-off host-time; and failure recovery time. The project reports model outputs honestly and does not extrapolate them to real electricity bills.

## 8. Results: Baseline and Consolidation

The following table reports means over 10 runs per condition. Baseline and consolidated runs use the same workload seeds. Consolidated energy includes the default 1 Wh per VM migration.

Measured main results:

**Baseline versus consolidation (mean of 10 paired runs)**

| Workload | Baseline Wh | Consolidated Wh | Saved | Migrations | SLA rate |
|---|---|---|---|---|---|
| Steady | 29,427.3 | 22,815.5 | 22.5% | 14.4 | 0.00% |
| Diurnal | 28,486.4 | 17,607.1 | 38.2% | 22.0 | 0.14% |
| Spiky | 29,678.1 | 22,208.0 | 25.2% | 15.5 | 2.08% |

## 9. Results: Sensitivity and Stretch Goal

Destination cap sensitivity shows the central trade-off: tighter caps use more hosts and more energy but suppress overload events; higher caps save more energy while raising SLA violations under diurnal and bursty demand. At 55%, mean host-time violations were 0 for diurnal and 0.6 host-steps for spiky demand; at 70%, they rose to 81.4 and 39.7 respectively.

Underload threshold sensitivity and VM selection results are shown below. For the spiky workload, moving the underload trigger from 30% to 40% reduced mean energy from 27,496.5 Wh to 23,391.5 Wh, while mean SLA host-steps rose from 1.6 to 9.8. The steady workload also saved more energy at 40% than at 30%, with no observed overloads.

Largest-first selection used slightly less energy than smallest-first in all three workload patterns in these runs. Differences were small, so the data does not establish a universal winner. The migration-energy sweep changed total energy in proportion to the assumed migration cost while leaving migration counts nearly unchanged; placement decisions do not currently optimize against migration cost.

**Destination cap sensitivity (10 runs per workload and cap)**

| Workload | Cap | Energy Wh | SLA host-steps |
|---|---|---|---|
| Steady | 55% | 24,325.5 | 0.0 |
| Steady | 60% | 22,730.5 | 0.0 |
| Steady | 65% | 21,533.1 | 0.0 |
| Steady | 70% | 20,650.2 | 0.0 |
| Diurnal | 55% | 18,138.1 | 0.0 |
| Diurnal | 60% | 17,506.6 | 1.1 |
| Diurnal | 65% | 16,413.9 | 30.1 |
| Diurnal | 70% | 15,694.7 | 81.4 |
| Spiky | 55% | 23,875.2 | 0.6 |
| Spiky | 60% | 22,813.5 | 13.7 |
| Spiky | 65% | 21,425.2 | 27.3 |
| Spiky | 70% | 20,805.1 | 39.7 |

## 10. Detailed Sensitivity Results

The tables on this page contain the sensitivity outputs for the 10-run experiment set. Energy is total modeled Wh per simulated day. SLA steps are the average count of host-time intervals that violate the modeled CPU service limit.

In the destination-cap sweep, the 60% cap reduces energy relative to a 55% cap but exposes a small number of SLA events under time-varying workloads. A cap of 70% reduces modeled energy further, with a much larger increase in violations. This supports treating the cap as a service-quality control, not merely an energy optimization knob.

The lower-threshold and selection sweeps show that results depend on workload shape. No single policy wins every metric. A provider would need to select a point on the energy/service trade-off that matches its SLA target.

**Underload threshold sensitivity (10 runs per workload and threshold)**

| Workload | Trigger | Energy Wh | Migrations | SLA steps |
|---|---|---|---|---|
| Steady | 30% | 27,986.4 | 4.2 | 0.0 |
| Steady | 40% | 23,266.4 | 13.7 | 0.0 |
| Steady | 50% | 23,266.6 | 13.9 | 0.0 |
| Diurnal | 30% | 18,030.8 | 20.9 | 1.2 |
| Diurnal | 40% | 18,031.1 | 21.2 | 1.2 |
| Diurnal | 50% | 18,031.1 | 21.2 | 1.2 |
| Spiky | 30% | 27,496.5 | 5.5 | 1.6 |
| Spiky | 40% | 23,391.5 | 14.5 | 9.8 |
| Spiky | 50% | 23,392.2 | 15.2 | 9.8 |

**VM-selection policy comparison**

| Workload | Policy | Energy Wh | Migrations | SLA steps |
|---|---|---|---|---|
| Steady | smallest | 21,997.4 | 14.9 | 0.0 |
| Steady | largest | 21,853.5 | 15.0 | 0.0 |
| Diurnal | smallest | 17,519.8 | 22.4 | 0.4 |
| Diurnal | largest | 17,297.2 | 22.5 | 0.1 |
| Spiky | smallest | 21,752.2 | 15.6 | 9.5 |
| Spiky | largest | 21,734.1 | 15.7 | 12.1 |

**Migration-cost sensitivity (Wh per migrated VM)**

| Workload | Penalty | Energy Wh | Migrations |
|---|---|---|---|
| Steady | 0 | 22,363.5 | 14.7 |
| Steady | 1 | 22,378.2 | 14.7 |
| Steady | 5 | 22,437.0 | 14.7 |
| Diurnal | 0 | 17,306.7 | 22.5 |
| Diurnal | 1 | 17,329.2 | 22.5 |
| Diurnal | 5 | 17,419.2 | 22.5 |
| Spiky | 0 | 22,009.0 | 15.5 |
| Spiky | 1 | 22,024.5 | 15.5 |
| Spiky | 5 | 22,086.5 | 15.5 |

## 11. Failure Injection

The failure experiment is a controlled one-interval host crash. At the 12-hour point, the simulator selects the active host with the largest current CPU load, turns it off for one 15-minute interval, and restores it at the following interval. Resident VM demand is counted as unavailable during the outage. This tests whether the model records a service impact and recovery point; it is not a high-availability implementation.

Failure results below are means over 10 runs per workload. The average recovery time is one interval (15 minutes). Mean VM-steps lost vary with how many VMs occupy the selected host. Spiky runs also include ordinary consolidation overload events, which is why their SLA host-step mean is higher than one.

The injected failure is repeatable and has an observable outcome in `results/failure_injection.csv`. A useful demo is to show the event in the report, then inspect the CSV row values. The project does not claim zero data loss or automatic VM recovery; it models service restoration when the host returns.

**Host crash: mean values across 10 runs per workload**

| Workload | VM-steps lost | Recovery min | SLA steps | Migrations |
|---|---|---|---|---|
| Steady | 6.6 | 15 | 1.0 | 14.4 |
| Diurnal | 9.7 | 15 | 1.1 | 21.7 |
| Spiky | 6.8 | 15 | 11.6 | 15.3 |

## 12. Analysis, Limitations and Conclusion

The simulator supports the conclusion that consolidation can reduce modeled energy when the initial placement leaves underused hosts. In the included configuration, savings range from 22.5% to 38.2% across workload patterns. The destination cap controls the energy/SLA trade-off: packing more tightly can reduce energy, but dynamic peaks create more host-time violations. The 60% cap provides a more conservative result than the 65-70% caps tested, while still reducing modeled energy.

Limitations: CPU is the only resource; wattage values are illustrative; VM CPU traces are synthetic; there is no boot/sleep delay; a switched-off host is assumed to consume zero power; migration cost is a fixed per-VM penalty; workload demands are treated as known at each interval; no memory, disk, network, cooling, carbon intensity, or real hypervisor overhead is modeled. Failure recovery is a one-interval host restart rather than redundant replication or rescheduling to other hosts.

Next improvements could use a public workload trace with its terms cited, add memory/network constraints, model transition energy and migration downtime, compare threshold controllers with predictive placement, and add recovery by relocating VMs after a permanent host failure.

Conclusion: The project satisfies the handout's simulator, changing-load, underloaded-host migration, power-model, energy comparison, migration count, SLA, repeatability, stretch-policy, and failure-injection goals. The main lesson is that energy savings must be evaluated alongside service violations and migration overhead, not in isolation.

## 13. Tools, References and Team Contributions

Tools used: Python 3.12.14 with the Python Software Foundation License 2.0 for the simulator and standard library; ReportLab 4.4.9 under its BSD license for optional PDF generation; Git 2.52.0 under GNU GPL version 2 for version control. No paid tools, cloud accounts, or external datasets are used. The runtime has no third-party dependencies.

References: [1] CSF349/CSN349 Cloud Computing, Advanced Project Handout, School of Computing, DIT University, Project 15: Energy-Aware VM Consolidation. [2] A. Beloglazov, J. Abawajy, and R. Buyya, 'Energy-aware resource allocation heuristics for efficient management of data centers for Cloud computing,' Future Generation Computer Systems, vol. 28, no. 5, pp. 755-768, 2012, doi:10.1016/j.future.2011.04.017.

Contribution statement: The handout requires a signed statement from each team member. Complete `docs/contributions.md` with the actual names, student IDs, contributions, and signatures. This template is intentionally blank because team identities and work allocations must be supplied by the team.

Submission checklist: repository/source code; one-command run instructions; architecture diagram; 12-15 page report; repeated experiments and tables/figures; tool/license table; demo with failure injection; and signed individual contribution statements. The code, report draft, results, chart files, demo outline, and contribution template are included in this project package.

**Project tools and licenses**

| Tool | Version | License | Use |
|---|---|---|---|
| Python | 3.12.14 | PSF License 2.0 | Simulator and standard library |
| ReportLab | 4.4.9 | BSD license | Optional report PDF generation |
| Git | 2.52.0 | GNU GPL v2 | Version control repository |


---

**Submission note:** add team names and signatures in `contributions.md`; confirm these results with a fresh run before final submission.
