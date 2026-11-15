from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .models import HostSpec, SimulationConfig, SimulationResult


class VMSimulator:
    """Discrete-time VM placement and host power simulator.

    It models CPU only. Migration energy is an explicit scenario parameter;
    it is not a measurement of a real hypervisor or physical server.
    """

    def __init__(self, config: SimulationConfig, workload: Dict[str, List[float]],
                 scenario: str, seed: int, failure_step: Optional[int] = None,
                 failure_duration_steps: int = 1):
        self.cfg = config
        self.workload = workload
        self.scenario = scenario
        self.seed = seed
        self.specs = [HostSpec(f"host-{i:02d}") for i in range(config.hosts)]
        self.vms = sorted(workload)
        self.placement: Dict[str, str] = {
            vm_id: self.specs[i % len(self.specs)].host_id
            for i, vm_id in enumerate(self.vms)
        }
        self.active = {h.host_id: True for h in self.specs}
        self.underloaded_intervals = defaultdict(int)
        self.failure_step = failure_step
        self.failure_duration_steps = max(1, failure_duration_steps)
        self.failure_host_id: Optional[str] = None
        self.failed_until = -1
        self.failure_vm_steps_lost = 0
        self.failure_cpu_demand_lost = 0.0
        self.recovery_time_minutes = 0

    def _vm_demand(self, vm_id: str, t: int) -> float:
        return self.workload[vm_id][t]

    def _loads(self, t: int) -> Dict[str, float]:
        loads = {h.host_id: 0.0 for h in self.specs}
        for vm_id, host_id in self.placement.items():
            loads[host_id] += self._vm_demand(vm_id, t)
        return loads

    def _vms_on(self, host_id: str) -> List[str]:
        return [vm_id for vm_id in self.vms if self.placement[vm_id] == host_id]

    def _choose_destination(self, source: str, vm_id: str, loads: Dict[str, float]) -> Optional[str]:
        demand = self._vm_demand(vm_id, self._current_step)
        candidates: List[Tuple[float, str]] = []
        for spec in self.specs:
            target = spec.host_id
            if target == source or not self.active[target]:
                continue
            post_util = (loads[target] + demand) / spec.cpu_capacity
            if post_util <= self.cfg.upper_threshold + 1e-12:
                # Best fit: use the feasible host with the least remaining headroom.
                candidates.append((spec.cpu_capacity - loads[target] - demand, target))
        return min(candidates)[1] if candidates else None

    def _consolidate(self, t: int) -> int:
        if not self.cfg.consolidate:
            return 0
        loads = self._loads(t)
        moved = 0
        host_by_id = {h.host_id: h for h in self.specs}
        for spec in sorted(self.specs, key=lambda h: loads[h.host_id] / h.cpu_capacity):
            source = spec.host_id
            if not self.active[source] or not self._vms_on(source):
                continue
            util = loads[source] / spec.cpu_capacity
            if util < self.cfg.underload_threshold:
                self.underloaded_intervals[source] += 1
            else:
                self.underloaded_intervals[source] = 0
            if self.underloaded_intervals[source] < self.cfg.underload_window:
                continue

            resident = self._vms_on(source)
            if self.cfg.vm_selection == "largest":
                resident.sort(key=lambda vm: (-self._vm_demand(vm, t), vm))
            else:
                resident.sort(key=lambda vm: (self._vm_demand(vm, t), vm))
            moved_from_source = 0
            for vm_id in resident:
                target = self._choose_destination(source, vm_id, loads)
                if target is None:
                    continue
                demand = self._vm_demand(vm_id, t)
                self.placement[vm_id] = target
                loads[source] -= demand
                loads[target] += demand
                moved += 1
                moved_from_source += 1
            if not self._vms_on(source):
                self.active[source] = False
            if moved_from_source == 0:
                # Avoid repeated futile scans; try again after the next interval.
                self.underloaded_intervals[source] = max(0, self.cfg.underload_window - 1)
        return moved

    def run(self) -> SimulationResult:
        steps = min(self.cfg.steps, min(len(v) for v in self.workload.values()))
        step_hours = self.cfg.step_minutes / 60.0
        host_energy = migration_energy = 0.0
        migrations = sla_host_steps = 0
        sla_cpu_shortfall = 0.0
        active_host_steps = powered_off_host_steps = 0
        peak_active_hosts = 0
        energy_by_step: List[float] = []
        migrations_by_step: List[int] = []

        for t in range(steps):
            self._current_step = t
            if self.failure_host_id is not None and t >= self.failed_until and not self.active[self.failure_host_id]:
                self.active[self.failure_host_id] = True
                self.recovery_time_minutes = (t - int(self.failure_step)) * self.cfg.step_minutes

            if self.failure_step is not None and t == self.failure_step:
                loads_before = self._loads(t)
                candidates = [h.host_id for h in self.specs if self.active[h.host_id] and self._vms_on(h.host_id)]
                if candidates:
                    self.failure_host_id = max(candidates, key=lambda hid: (loads_before[hid], hid))
                    self.failed_until = t + self.failure_duration_steps
                    self.active[self.failure_host_id] = False

            loads = self._loads(t)
            unavailable_load = 0.0
            unavailable_vms = 0
            if self.failure_host_id is not None and not self.active[self.failure_host_id]:
                unavailable_load = loads[self.failure_host_id]
                unavailable_vms = len(self._vms_on(self.failure_host_id))
                self.failure_vm_steps_lost += unavailable_vms
                self.failure_cpu_demand_lost += unavailable_load

            # SLA is defined as a host-time interval with demand above capacity,
            # or a host-time interval during which a crashed host's VMs are unavailable.
            for spec in self.specs:
                hid = spec.host_id
                if hid == self.failure_host_id and not self.active[hid]:
                    sla_host_steps += 1
                    sla_cpu_shortfall += unavailable_load
                elif self.active[hid] and loads[hid] > spec.cpu_capacity:
                    sla_host_steps += 1
                    sla_cpu_shortfall += loads[hid] - spec.cpu_capacity

            moved = self._consolidate(t)
            migrations += moved
            migration_cost = moved * self.cfg.migration_energy_wh
            migration_energy += migration_cost

            # Energy is based on the post-consolidation placement for this interval.
            loads = self._loads(t)
            step_power = 0.0
            active_now = 0
            for spec in self.specs:
                hid = spec.host_id
                if not self.active[hid]:
                    continue
                active_now += 1
                util = min(1.0, max(0.0, loads[hid] / spec.cpu_capacity))
                power_w = spec.idle_power_w + (spec.max_power_w - spec.idle_power_w) * util
                step_power += power_w * step_hours
            host_energy += step_power
            energy_by_step.append(step_power + migration_cost)
            migrations_by_step.append(moved)
            active_host_steps += active_now
            powered_off_host_steps += self.cfg.hosts - active_now
            peak_active_hosts = max(peak_active_hosts, active_now)

        return SimulationResult(
            scenario=self.scenario,
            seed=self.seed,
            mode="consolidated" if self.cfg.consolidate else "baseline",
            total_energy_wh=host_energy + migration_energy,
            host_energy_wh=host_energy,
            migration_energy_wh=migration_energy,
            migrations=migrations,
            sla_host_steps=sla_host_steps,
            sla_cpu_shortfall=sla_cpu_shortfall,
            active_host_steps=active_host_steps,
            powered_off_host_steps=powered_off_host_steps,
            peak_active_hosts=peak_active_hosts,
            energy_by_step_wh=energy_by_step,
            migrations_by_step=migrations_by_step,
            failure_host_id=self.failure_host_id,
            failure_vm_steps_lost=self.failure_vm_steps_lost,
            failure_cpu_demand_lost=self.failure_cpu_demand_lost,
            recovery_time_minutes=self.recovery_time_minutes,
        )
