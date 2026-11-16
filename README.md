# Energy-Aware VM Consolidation

A Python + Streamlit simulation of energy-aware virtual machine (VM) consolidation in a data centre.

## Features
- Simulates physical hosts and VMs with changing CPU demand.
- Compares No Consolidation, Threshold-Based, and Best-Fit Consolidation policies.
- Migrates VMs from underutilized hosts when a safe destination is available.
- Powers off empty hosts.
- Calculates host power using the assignment's linear power model:
  `P = P_idle + (P_max - P_idle) * CPU_utilization`
- Adds a configurable energy cost per migration.
- Reports migrations, powered-off hosts, and SLA violations.
- Provides an interactive Streamlit dashboard and CSV exports.

## Requirements
- Python 3.10+
- Windows, Linux, or macOS
- VS Code (recommended)

## Run on Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
streamlit run main.py
```

If PowerShell blocks activation, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## Run on Ubuntu

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run main.py
```

## How to use
1. Start the app with `streamlit run main.py`.
2. Adjust hosts, VMs, simulation steps, thresholds, and power values in the sidebar.
3. Click **Run simulation**.
4. Compare energy, migration count, powered-off hosts, and SLA violations.
5. Download CSV results from the Raw data tab.

## Model assumptions and limitations
- This is a discrete-time simulator, not a hypervisor or live migration implementation.
- CPU demand is expressed in normalized capacity units.
- Each host has one CPU capacity value; RAM, storage, network bandwidth, and heterogeneous hardware are not modelled.
- Migration energy is represented by a configurable fixed Wh cost per VM migration.
- Migration time is approximated by VM memory size divided by a conceptual fixed bandwidth; the simplified policy selector uses memory size as a proxy.
- The power model is linear between idle and maximum power.
- SLA violations count active hosts whose demand exceeds their CPU capacity. Safe placement is intended to avoid overload.
- Workload traces are synthetic and seeded for reproducibility.
- Threshold-Based uses first-fit destination placement, while Best-Fit Consolidation selects the eligible destination with the least remaining capacity after placement.
- Both consolidation policies use the configured underload threshold to identify candidate source hosts.

## Suggested report measurements
- Total energy without consolidation vs. with consolidation.
- Migration count and migration energy.
- Number of hosts switched off.
- SLA violations.
- Energy savings percentage:
  `(baseline_energy - consolidated_energy) / baseline_energy * 100`
- Net savings after migration cost.

## Project structure
```text
Energy-Aware-VM-Consolidation/
├── main.py
├── config.py
├── simulation/
│   ├── __init__.py
│   ├── models.py
│   ├── workload.py
│   └── engine.py
├── algorithms/
│   ├── __init__.py
│   └── policies.py
├── metrics/
│   ├── __init__.py
│   ├── energy.py
│   └── sla.py
├── dashboard/
├── results/
└── requirements.txt
```
