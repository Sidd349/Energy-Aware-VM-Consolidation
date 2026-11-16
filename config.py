"""Default simulation configuration. Values can also be changed in the dashboard."""

DEFAULT_CONFIG = {
    "num_hosts": 8,
    "num_vms": 16,
    "host_capacity": 100.0,       # normalized CPU capacity units
    "simulation_steps": 48,
    "step_minutes": 15,
    "underload_threshold": 0.40,
    "overload_threshold": 0.85,
    "safety_threshold": 0.90,
    "idle_power_w": 120.0,
    "max_power_w": 250.0,
    "migration_energy_wh": 8.0,   # simplified energy cost per migration
    "migration_overhead": 0.05,   # temporary 5% CPU overhead on destination
    "seed": 42,
}
