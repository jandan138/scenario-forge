"""Pure supported-mass accounting for the task09 fixture, in grams."""
import math


def supported_inventory(masses, supports, pan, excluded=()):
    """Count only loads wholly supported by the pan, rejecting external support.

    Edges point from a load to its upward supporting body. Cycles without a
    rooted support are not loads; masses are never inferred from task targets.
    """
    if any(not math.isfinite(m) or m <= 0 for m in masses.values()):
        raise ValueError('mass must be finite and positive')
    excluded = set(excluded)
    accepted = {pan}
    for _ in masses:
        added = {p for p in masses if p not in excluded and supports.get(p)
                 and set(supports[p]) <= accepted}
        if added <= accepted:
            break
        accepted |= added
    accepted.discard(pan)
    return accepted, sum(masses[p] for p in accepted)
