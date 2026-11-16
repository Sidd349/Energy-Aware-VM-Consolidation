
def count_sla_violations(hosts, threshold: float = 0.90) -> int:
    """
    Count active hosts exceeding the configured safe CPU threshold.

    Default threshold is 90%.
    """

    return sum(
        1 for host in hosts
        if host.active and host.utilization > threshold
    )


def count_capacity_violations(hosts) -> int:
    """
    Count active hosts whose CPU demand exceeds physical capacity.

    A utilization greater than 100% indicates an actual CPU overload.
    """

    return sum(
        1 for host in hosts
        if host.active and host.utilization > 1.0
    )
