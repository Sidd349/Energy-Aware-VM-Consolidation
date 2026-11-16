def calculate_step_energy(hosts, step_minutes: int) -> float:
    """Energy in Wh for one simulation interval."""
    hours = step_minutes / 60.0
    return sum(host.power_w() for host in hosts) * hours


def calculate_total_energy(step_energies, migration_count: int, migration_energy_wh: float):
    operational = float(sum(step_energies))
    migration = migration_count * migration_energy_wh
    return operational + migration, operational, migration
