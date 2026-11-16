import numpy as np


def generate_workloads(num_vms: int, steps: int, seed: int = 42):
    """
    Return a deterministic [time_step][vm_index] workload matrix.
    Each VM has a baseline demand with daily-style variation and noise.
    """
    rng = np.random.default_rng(seed)
    baselines = rng.uniform(8.0, 24.0, size=num_vms)
    phases = rng.uniform(0, 2 * np.pi, size=num_vms)
    workloads = []

    for t in range(steps):
        row = []
        daily_wave = 0.75 + 0.25 * np.sin((2 * np.pi * t / max(steps, 1)) - np.pi / 2)
        for i in range(num_vms):
            variation = 0.72 + 0.28 * np.sin((2 * np.pi * t / max(steps, 1)) + phases[i])
            noise = rng.normal(1.0, 0.07)
            demand = baselines[i] * daily_wave * variation * noise
            # Add a few workload bursts to make consolidation decisions meaningful.
            if (t + i * 3) % 17 in (0, 1):
                demand *= 1.45
            row.append(float(max(2.0, demand)))
        workloads.append(row)
    return workloads
