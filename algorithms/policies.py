
from dataclasses import dataclass, field
from typing import Dict, List
import copy

from simulation.models import Host, VM
from metrics.sla import count_sla_violations


# ==========================================================
# RESULT MODEL
# ==========================================================

@dataclass
class PolicyResult:
    name: str
    step_rows: List[dict]
    migration_rows: List[dict]
    host_rows: List[dict]
    total_energy_wh: float
    operational_energy_wh: float
    migration_energy_wh: float
    migrations: int
    sla_violations: int
    hosts_shutdown: int

    # New break-even analysis fields
    break_even_rows: List[dict] = field(default_factory=list)
    migrations_skipped_not_worthwhile: int = 0


# ==========================================================
# VM SELECTION
# ==========================================================

def _choose_vm(vms: List[VM], strategy: str):

    if not vms:
        return None

    if strategy == "Maximum CPU first":
        return max(vms, key=lambda vm: vm.cpu_demand)

    if strategy == "Minimum migration time":
        return min(vms, key=lambda vm: vm.memory_gb)

    return min(vms, key=lambda vm: vm.cpu_demand)


# ==========================================================
# DESTINATION HOST SELECTION
# ==========================================================

def _find_destination(
    vm: VM,
    source: Host,
    hosts: List[Host],
    safety_threshold: float,
    placement_mode: str,
    migration_overhead: float
):

    candidates = []

    for host in hosts:

        if host.host_id == source.host_id or not host.active:
            continue

        additional_load = vm.cpu_demand * (1 + migration_overhead)

        projected_load = host.cpu_demand + additional_load

        if projected_load <= host.capacity * safety_threshold:
            candidates.append(host)

    if not candidates:
        return None

    if placement_mode == "first-fit":
        return sorted(candidates, key=lambda h: h.host_id)[0]

    if placement_mode == "least-loaded":
        return min(candidates, key=lambda h: h.utilization)

    # Best-fit: pack VMs while leaving the least unused capacity.
    return min(
        candidates,
        key=lambda h: (
            h.capacity * safety_threshold
            - h.cpu_demand
            - vm.cpu_demand * (1 + migration_overhead)
        )
    )


def _find_or_activate_destination(
    vm: VM,
    source: Host,
    hosts: List[Host],
    safety_threshold: float,
    placement_mode: str,
    migration_overhead: float
):

    destination = _find_destination(
        vm,
        source,
        hosts,
        safety_threshold,
        placement_mode,
        migration_overhead
    )

    if destination is not None:
        return destination

    # Activate an inactive host if no active host can fit the VM.
    inactive_hosts = sorted(
        [h for h in hosts if not h.active],
        key=lambda h: h.host_id
    )

    for host in inactive_hosts:

        host.start()

        required_load = vm.cpu_demand * (1 + migration_overhead)

        if required_load <= host.capacity * safety_threshold:
            return host

        host.shutdown()

    return None


# ==========================================================
# PERFORM AND RECORD MIGRATION
# ==========================================================

def _record_migration(
    vm: VM,
    source: Host,
    destination: Host,
    step: int,
    step_minutes: int,
    migration_overhead: float,
    migration_rows: List[dict],
    vm_selection: str
):

    source.remove_vm(vm)
    destination.add_vm(vm)

    # Temporary CPU overhead during migration.
    destination.migration_overhead += (
        vm.cpu_demand * migration_overhead
    )

    migration_rows.append({
        "step": step + 1,
        "time_minutes": (step + 1) * step_minutes,
        "vm_id": vm.vm_id,
        "source": source.host_id,
        "destination": destination.host_id,
        "cpu_demand": round(vm.cpu_demand, 2),
        "selection_strategy": vm_selection
    })


# ==========================================================
# BUILD A HYPOTHETICAL CONSOLIDATION PLAN
# ==========================================================

def _build_consolidation_plan(
    source: Host,
    hosts: List[Host],
    safety_threshold: float,
    placement_mode: str,
    migration_overhead: float,
    vm_selection: str
):
    """
    Simulate moving every VM from a source host.

    The real simulation is not modified.
    Returns a hypothetical placement and migration plan.
    """

    trial_hosts = copy.deepcopy(hosts)

    trial_source = next(
        h for h in trial_hosts
        if h.host_id == source.host_id
    )

    migration_plan = []

    while trial_source.vms:

        vm = _choose_vm(
            trial_source.vms,
            vm_selection
        )

        destination = _find_destination(
            vm,
            trial_source,
            trial_hosts,
            safety_threshold,
            placement_mode,
            migration_overhead
        )

        if destination is None:
            # Cannot empty this source safely.
            return None, []

        migration_plan.append({
            "vm_id": vm.vm_id,
            "source": trial_source.host_id,
            "destination": destination.host_id,
            "cpu_demand": round(vm.cpu_demand, 2)
        })

        trial_source.remove_vm(vm)
        destination.add_vm(vm)

        destination.migration_overhead += (
            vm.cpu_demand * migration_overhead
        )

    # The hypothetical source host is now empty.
    trial_source.shutdown()

    return trial_hosts, migration_plan


# ==========================================================
# APPLY FUTURE WORKLOAD
# ==========================================================

def _apply_workload(hosts: List[Host], demands):

    vm_lookup = {
        vm.vm_id: vm
        for host in hosts
        for vm in host.vms
    }

    for i, demand in enumerate(demands):

        vm_id = f"VM{i + 1}"

        if vm_id in vm_lookup:
            vm_lookup[vm_id].update_demand(demand)


def _total_power(hosts: List[Host]) -> float:

    return sum(host.power_w() for host in hosts)


# ==========================================================
# MIGRATION BREAK-EVEN ANALYSIS
# ==========================================================

def _evaluate_break_even(
    hosts: List[Host],
    trial_hosts: List[Host],
    migration_plan: List[dict],
    workload_matrix,
    current_step: int,
    step_minutes: int,
    migration_energy_wh: float,
    safety_threshold: float
):
    """
    Compare the expected energy without consolidation
    against the expected energy after consolidation.

    Uses the remaining known workload as a simulation forecast.

    Migration is worthwhile only when:
        Expected operational energy savings > migration energy cost

    Also verifies that the hypothetical placement remains
    within the configured safety threshold.
    """

    baseline_hosts = copy.deepcopy(hosts)

    remaining_steps = len(workload_matrix) - current_step

    step_hours = step_minutes / 60.0

    migration_count = len(migration_plan)

    total_migration_cost = (
        migration_count * migration_energy_wh
    )

    baseline_energy = 0.0
    consolidated_energy = 0.0

    future_safe = True

    for future_step in range(current_step, len(workload_matrix)):

        if future_step > current_step:

            # Migration overhead is temporary.
            for host in baseline_hosts:
                host.migration_overhead = 0.0

            for host in trial_hosts:
                host.migration_overhead = 0.0

            demands = workload_matrix[future_step]

            _apply_workload(baseline_hosts, demands)
            _apply_workload(trial_hosts, demands)

        # Ensure the proposed consolidated placement
        # can handle the remaining forecast workloads.
        overloaded = any(
            host.active and host.utilization > safety_threshold
            for host in trial_hosts
        )

        if overloaded:
            future_safe = False
            break

        baseline_energy += (
            _total_power(baseline_hosts) * step_hours
        )

        consolidated_energy += (
            _total_power(trial_hosts) * step_hours
        )

    expected_operational_savings = (
        baseline_energy - consolidated_energy
        if future_safe else 0.0
    )

    net_energy_savings = (
        expected_operational_savings - total_migration_cost
    )

    average_savings_per_step = (
        expected_operational_savings / remaining_steps
        if remaining_steps > 0 else 0.0
    )

    if average_savings_per_step > 0:

        payback_steps = (
            total_migration_cost / average_savings_per_step
        )

    else:
        payback_steps = None

    worthwhile = (
        future_safe
        and expected_operational_savings > total_migration_cost
    )

    if not future_safe:
        decision = "Rejected: future CPU safety limit exceeded"

    elif worthwhile:
        decision = "Approved: migration is energy-efficient"

    else:
        decision = "Rejected: migration cost exceeds expected savings"

    return {
        "expected_operational_savings_wh": round(
            expected_operational_savings, 2
        ),
        "migration_cost_wh": round(
            total_migration_cost, 2
        ),
        "net_energy_savings_wh": round(
            net_energy_savings, 2
        ),
        "remaining_steps": remaining_steps,
        "estimated_payback_steps": (
            round(payback_steps, 2)
            if payback_steps is not None else None
        ),
        "future_placement_safe": future_safe,
        "worthwhile": worthwhile,
        "decision": decision
    }


# ==========================================================
# MAIN CONSOLIDATION POLICY
# ==========================================================

def run_policy(
    name: str,
    initial_hosts: List[Host],
    workload_matrix,
    step_minutes: int,
    underload_threshold: float,
    safety_threshold: float,
    migration_energy_wh: float,
    migration_overhead: float,
    vm_selection: str = "Minimum CPU first",
):

    # Each policy receives its own independent data centre.
    hosts = copy.deepcopy(initial_hosts)

    vm_lookup: Dict[str, VM] = {
        vm.vm_id: vm
        for host in hosts
        for vm in host.vms
    }

    step_rows = []
    migration_rows = []
    host_rows = []
    break_even_rows = []
    step_energies = []

    migrations = 0
    sla_violations = 0
    shutdown_ids = set()

    migrations_skipped_not_worthwhile = 0

    placement_mode = (
        "first-fit"
        if name == "Threshold-Based"
        else "best-fit"
    )

    for t, demands in enumerate(workload_matrix):

        # --------------------------------------------------
        # 1. UPDATE VM WORKLOADS
        # --------------------------------------------------

        for i, demand in enumerate(demands):

            vm = vm_lookup[f"VM{i + 1}"]

            vm.update_demand(demand)

        # Reset temporary migration overhead each interval.
        for host in hosts:
            host.migration_overhead = 0.0

        if name != "No Consolidation":

            # --------------------------------------------------
            # 2. HANDLE OVERLOADED HOSTS
            # --------------------------------------------------

            overloaded_hosts = sorted(
                [
                    h for h in hosts
                    if h.active
                    and h.vms
                    and h.utilization > safety_threshold
                ],
                key=lambda h: h.utilization,
                reverse=True
            )

            for source in overloaded_hosts:

                while (
                    source.active
                    and source.vms
                    and source.utilization > safety_threshold
                ):

                    # Overload migrations are mandatory
                    # to protect CPU safety.
                    vm = _choose_vm(
                        source.vms,
                        vm_selection
                    )

                    destination = _find_or_activate_destination(
                        vm,
                        source,
                        hosts,
                        safety_threshold,
                        placement_mode,
                        migration_overhead
                    )

                    if destination is None:
                        break

                    _record_migration(
                        vm,
                        source,
                        destination,
                        t,
                        step_minutes,
                        migration_overhead,
                        migration_rows,
                        vm_selection
                    )

                    migrations += 1

                if source.active and not source.vms:

                    source.shutdown()
                    shutdown_ids.add(source.host_id)

            # --------------------------------------------------
            # 3. HANDLE UNDERUTILIZED HOSTS
            # --------------------------------------------------

            underloaded_hosts = sorted(
                [
                    h for h in hosts
                    if h.active
                    and h.vms
                    and h.utilization < underload_threshold
                ],
                key=lambda h: h.utilization
            )

            for source in underloaded_hosts:

                if not source.active or not source.vms:
                    continue

                # Build a hypothetical full-consolidation plan.
                trial_hosts, migration_plan = (
                    _build_consolidation_plan(
                        source,
                        hosts,
                        safety_threshold,
                        placement_mode,
                        migration_overhead,
                        vm_selection
                    )
                )

                # No safe destination for all VMs.
                if trial_hosts is None:

                    break_even_rows.append({
                        "step": t + 1,
                        "source_host": source.host_id,
                        "vms_to_migrate": len(source.vms),
                        "expected_operational_savings_wh": 0,
                        "migration_cost_wh": round(
                            len(source.vms) * migration_energy_wh, 2
                        ),
                        "net_energy_savings_wh": 0,
                        "remaining_steps": len(workload_matrix) - t,
                        "estimated_payback_steps": None,
                        "future_placement_safe": False,
                        "worthwhile": False,
                        "decision": "Rejected: insufficient safe destination capacity"
                    })

                    continue

                # Evaluate the energy economics of the plan.
                evaluation = _evaluate_break_even(
                    hosts,
                    trial_hosts,
                    migration_plan,
                    workload_matrix,
                    t,
                    step_minutes,
                    migration_energy_wh,
                    safety_threshold
                )

                break_even_rows.append({
                    "step": t + 1,
                    "source_host": source.host_id,
                    "vms_to_migrate": len(migration_plan),
                    **evaluation
                })

                # Do not perform energy-wasteful consolidation.
                if not evaluation["worthwhile"]:

                    migrations_skipped_not_worthwhile += 1
                    continue

                # --------------------------------------------------
                # 4. EXECUTE APPROVED MIGRATIONS
                # --------------------------------------------------

                for planned_migration in migration_plan:

                    vm = vm_lookup[planned_migration["vm_id"]]

                    destination = next(
                        h for h in hosts
                        if h.host_id == planned_migration["destination"]
                    )

                    _record_migration(
                        vm,
                        source,
                        destination,
                        t,
                        step_minutes,
                        migration_overhead,
                        migration_rows,
                        vm_selection
                    )

                    migrations += 1

                # Shut down the source only after it is empty.
                if source.active and not source.vms:

                    source.shutdown()
                    shutdown_ids.add(source.host_id)

        # --------------------------------------------------
        # 5. CALCULATE SLA VIOLATIONS
        # --------------------------------------------------

        current_sla = count_sla_violations(
            hosts,
            threshold=safety_threshold
        )

        sla_violations += current_sla

        # --------------------------------------------------
        # 6. CALCULATE ENERGY CONSUMPTION
        # --------------------------------------------------

        total_cpu = sum(
            vm.cpu_demand for vm in vm_lookup.values()
        )

        active_hosts = sum(
            1 for h in hosts if h.active
        )

        operational_wh = (
            sum(h.power_w() for h in hosts)
            * (step_minutes / 60.0)
        )

        step_energies.append(operational_wh)

        step_rows.append({
            "step": t + 1,
            "time_minutes": (t + 1) * step_minutes,
            "total_cpu_demand": round(total_cpu, 2),
            "active_hosts": active_hosts,
            "powered_off_hosts": len(hosts) - active_hosts,
            "operational_energy_wh": round(
                operational_wh, 3
            ),
            "migrations_so_far": migrations,
            "sla_violations_this_step": current_sla
        })

        # --------------------------------------------------
        # 7. RECORD HOST INFORMATION
        # --------------------------------------------------

        for host in hosts:

            host_rows.append({
                "step": t + 1,
                "host_id": host.host_id,
                "active": host.active,
                "cpu_demand": round(host.cpu_demand, 2),
                "utilization_pct": round(
                    host.utilization_pct, 2
                ),
                "vm_count": len(host.vms),
                "power_w": round(host.power_w(), 2)
            })

    # --------------------------------------------------
    # 8. FINAL ENERGY SUMMARY
    # --------------------------------------------------

    operational = float(sum(step_energies))

    migration_cost = (
        migrations * migration_energy_wh
    )

    total_energy = operational + migration_cost

    return PolicyResult(
        name=name,
        step_rows=step_rows,
        migration_rows=migration_rows,
        host_rows=host_rows,
        total_energy_wh=total_energy,
        operational_energy_wh=operational,
        migration_energy_wh=migration_cost,
        migrations=migrations,
        sla_violations=sla_violations,
        hosts_shutdown=len(shutdown_ids),
        break_even_rows=break_even_rows,
        migrations_skipped_not_worthwhile=(
            migrations_skipped_not_worthwhile
        )
    )
