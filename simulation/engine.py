from simulation.models import Host, VM
from simulation.workload import generate_workloads
from algorithms.policies import run_policy


def create_initial_hosts(num_hosts: int, num_vms: int, host_capacity: float,
                         idle_power_w: float, max_power_w: float, seed: int = 42):
    hosts = [
        Host(
            host_id=f"Host{i+1}",
            capacity=host_capacity,
            idle_power_w=idle_power_w,
            max_power_w=max_power_w,
        )
        for i in range(num_hosts)
    ]

    # Deterministic round-robin initial placement creates a spread of workloads.
    for i in range(num_vms):
        vm = VM(vm_id=f"VM{i+1}", cpu_demand=12.0, memory_gb=2.0 + (i % 3))
        hosts[i % num_hosts].add_vm(vm)
    return hosts


def run_simulation(config: dict, vm_selection: str = "Minimum CPU first"):
    hosts = create_initial_hosts(
        config["num_hosts"], config["num_vms"], config["host_capacity"],
        config["idle_power_w"], config["max_power_w"], config["seed"]
    )
    workloads = generate_workloads(config["num_vms"], config["simulation_steps"], config["seed"])

    policies = ["No Consolidation", "Threshold-Based", "Best-Fit Consolidation"]
    results = {}
    for policy in policies:
        # The policy engine uses best-fit placement for both consolidation
        # policies; threshold-based and best-fit differ in source selection.
        threshold = config["underload_threshold"]
        result = run_policy(
            name=policy,
            initial_hosts=hosts,
            workload_matrix=workloads,
            step_minutes=config["step_minutes"],
            underload_threshold=threshold,
            safety_threshold=config["safety_threshold"],
            migration_energy_wh=config["migration_energy_wh"],
            migration_overhead=config["migration_overhead"],
            vm_selection=vm_selection,
        )
        results[policy] = result

    # A separate Best-Fit policy uses the same safe placement but considers
    # the lowest-utilization source at each decision. Threshold-Based uses
    # the configured threshold; both are intentionally transparent variants.
    return results
