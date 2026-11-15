from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class HostSpec:
    host_id: str
    cpu_capacity: float = 100.0
    idle_power_w: float = 90.0
    max_power_w: float = 180.0


@dataclass(frozen=True)
class SimulationConfig:
    hosts: int = 10
    vms: int = 40
    steps: int = 96
    step_minutes: int = 15
    underload_threshold: float = 0.40
    upper_threshold: float = 0.60
    underload_window: int = 2
    migration_energy_wh: float = 1.0
    vm_selection: str = "smallest"
    consolidate: bool = True


@dataclass
class SimulationResult:
    scenario: str
    seed: int
    mode: str
    total_energy_wh: float
    host_energy_wh: float
    migration_energy_wh: float
    migrations: int
    sla_host_steps: int
    sla_cpu_shortfall: float
    active_host_steps: int
    powered_off_host_steps: int
    peak_active_hosts: int
    energy_by_step_wh: List[float] = field(default_factory=list)
    migrations_by_step: List[int] = field(default_factory=list)
    failure_host_id: Optional[str] = None
    failure_vm_steps_lost: int = 0
    failure_cpu_demand_lost: float = 0.0
    recovery_time_minutes: int = 0

    @property
    def sla_host_step_rate_pct(self) -> float:
        if self.active_host_steps == 0:
            return 0.0
        return 100.0 * self.sla_host_steps / self.active_host_steps

    @property
    def energy_saved_pct(self) -> float:
        # Filled by paired-experiment aggregation; a single run has no baseline.
        return 0.0


@dataclass
class ExperimentRow:
    experiment: str
    scenario: str
    mode: str
    seed: int
    underload_threshold: float
    upper_threshold: float
    vm_selection: str
    migration_energy_wh_per_vm: float
    energy_wh: float
    host_energy_wh: float
    migration_energy_wh: float
    migrations: int
    sla_host_steps: int
    sla_host_step_rate_pct: float
    sla_cpu_shortfall: float
    active_host_steps: int
    powered_off_host_steps: int
    peak_active_hosts: int


@dataclass
class FailureRow:
    scenario: str
    seed: int
    failure_step: int
    failure_host_id: str
    failure_vm_steps_lost: int
    failure_cpu_demand_lost: float
    recovery_time_minutes: int
    total_energy_wh: float
    migrations: int
    sla_host_steps: int
