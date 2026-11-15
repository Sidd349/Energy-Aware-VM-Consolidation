# Mini Project Proposal: Energy-Aware VM Consolidation

**Course:** CSN349 Cloud Computing  
**Project:** Energy-Aware VM Consolidation (Project 15)  
**Team:** Add the four team members' names and student IDs before submission.

## Problem

Cloud data-centre workloads change over time. Some physical hosts can remain lightly utilized while carrying an idle-power cost. Consolidating virtual machines (VMs) onto fewer active hosts may reduce modeled energy, but migrations add overhead and tightly packed hosts can exceed capacity and cause SLA violations.

## Aim

Build a local Python simulator that models hosts, VMs, changing CPU demand, VM migration, host power, and SLA outcomes. Compare energy use with and without consolidation and identify how workload shape and policy thresholds affect the trade-off.

## Method

The simulator will model 10 hosts and 40 VMs over 24 hours using 96 fifteen-minute intervals. It will generate three synthetic workload patterns: steady, diurnal, and spiky. The policy will identify a host that stays below a utilization threshold, move its VMs to feasible destinations without exceeding a destination utilization cap, and switch the source host off when empty. A linear power model will estimate host power. A static-placement baseline will use the same VM workload traces.

## Measurements and experiments

For each condition, run at least 10 fixed-seed repetitions. Report modeled energy in Wh, percentage energy change relative to baseline, migrations, CPU overload/SLA host-steps, and powered-off host-time. Sweep the underload threshold and destination cap. Compare smallest-first and largest-first VM selection. Vary the assumed migration-energy penalty. Inject a one-interval host crash at the midpoint and record unavailable VM-steps and recovery time.

## Tools, limits, and expected deliverables

Use Python 3 and its standard library; no cloud account, paid service, or external dataset is required. All CPU loads and power values are simulation inputs, so report results as modeled estimates, not physical energy measurements. Deliver source code, a one-command run script, architecture diagram, CSV results, charts, a 12-15 page report, tool/license table, demo, and signed team contribution statement.
