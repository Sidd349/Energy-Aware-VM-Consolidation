from __future__ import annotations

import math
import random
from typing import Dict, List


SCENARIOS = ("steady", "diurnal", "spiky")


def generate_workload(scenario: str, vm_count: int, steps: int, seed: int) -> Dict[str, List[float]]:
    """Return deterministic, synthetic CPU demand (capacity units) for each VM."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown workload scenario: {scenario}")
    rng = random.Random(seed)
    bases = {f"vm-{i:02d}": rng.uniform(6.0, 13.0) for i in range(vm_count)}
    phases = {vm_id: rng.random() * 2 * math.pi for vm_id in bases}
    series: Dict[str, List[float]] = {vm_id: [] for vm_id in bases}

    for t in range(steps):
        daily = 0.88 + 0.20 * math.sin((2 * math.pi * t / steps) - math.pi / 2)
        # Two short, repeatable bursts in the spiky scenario.
        burst = 1.0
        if scenario == "spiky" and (steps // 3 <= t < steps // 3 + max(2, steps // 24) or
                                    2 * steps // 3 <= t < 2 * steps // 3 + max(2, steps // 24)):
            burst = 1.65

        for vm_id, base in bases.items():
            if scenario == "steady":
                factor = 0.96 + 0.08 * math.sin((2 * math.pi * t / steps) + phases[vm_id])
            elif scenario == "diurnal":
                factor = daily * (0.96 + 0.08 * math.sin((2 * math.pi * t / steps) + phases[vm_id]))
            else:
                factor = (0.94 + 0.10 * math.sin((2 * math.pi * t / steps) + phases[vm_id])) * burst
            noise = rng.uniform(0.94, 1.06)
            series[vm_id].append(round(max(1.0, base * factor * noise), 4))
    return series
