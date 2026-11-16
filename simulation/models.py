from dataclasses import dataclass, field
from typing import List


@dataclass
class VM:
    vm_id: str
    cpu_demand: float
    memory_gb: float = 2.0
    host_id: str | None = None
    history: List[float] = field(default_factory=list)

    def update_demand(self, demand: float) -> None:
        self.cpu_demand = max(0.0, float(demand))
        self.history.append(self.cpu_demand)


@dataclass
class Host:
    host_id: str
    capacity: float
    idle_power_w: float
    max_power_w: float
    vms: List[VM] = field(default_factory=list)
    active: bool = True
    migration_overhead: float = 0.0

    @property
    def cpu_demand(self) -> float:
        return sum(vm.cpu_demand for vm in self.vms) + self.migration_overhead

    @property
    def utilization(self) -> float:
        if not self.active or self.capacity <= 0:
            return 0.0
        return self.cpu_demand / self.capacity

    @property
    def utilization_pct(self) -> float:
        return self.utilization * 100.0

    def can_fit(self, vm: VM, safety_threshold: float = 0.90) -> bool:
        if not self.active:
            return False
        return (self.cpu_demand + vm.cpu_demand) <= self.capacity * safety_threshold

    def add_vm(self, vm: VM) -> None:
        if vm not in self.vms:
            self.vms.append(vm)
            vm.host_id = self.host_id

    def remove_vm(self, vm: VM) -> None:
        if vm in self.vms:
            self.vms.remove(vm)
            vm.host_id = None

    def power_w(self) -> float:
        if not self.active:
            return 0.0
        utilization = min(1.0, max(0.0, self.utilization))
        return self.idle_power_w + (self.max_power_w - self.idle_power_w) * utilization

    def shutdown(self) -> None:
        if self.vms:
            raise ValueError("Cannot shut down a host that still contains VMs.")
        self.active = False

    def start(self) -> None:
        self.active = True
