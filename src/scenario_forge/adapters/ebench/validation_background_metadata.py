"""SDK-free planning for GenManip validation metadata.

Particle-coordinate transforms and native checks remain adapter responsibilities.
"""

def resample_xy_groups(metadata: dict, *, seed: int, limit_m: float) -> tuple[dict, dict]:
    """Resample declared source groups, retaining height and rigid attachments.

    ``limit_m`` is a caller-owned task bound, not a global physics default.
    Returned shifts are increments from the supplied source layout, not absolute
    jitter values. Particle-coordinate updates belong to the runtime adapter.
    """
    import copy
    import math
    import random

    if not math.isfinite(limit_m) or limit_m <= 0:
        raise ValueError('A finite positive task-specific jitter limit is required')
    declared = metadata.get('validation_provenance', {}).get('xy_jitter_m', {})
    layout = metadata.get('task_data', {}).get('initial_layout', {})
    if not declared:
        raise ValueError('No source-owned layout groups declared')
    groups: dict[tuple, list[str]] = {}
    for name, offset in declared.items():
        if name not in layout or len(layout[name].get('position', [])) != 3:
            raise ValueError(f'Missing layout position for {name}')
        if len(offset) != 3 or not all(math.isfinite(float(v)) for v in offset):
            raise ValueError(f'Invalid source jitter for {name}')
        if offset[2] != 0 or any(abs(v) > limit_m for v in offset):
            raise ValueError(f'Source jitter outside the declared XY scope: {name}')
        groups.setdefault(tuple(offset), []).append(name)
    rng = random.Random(seed)
    result = copy.deepcopy(metadata)
    shifts = {}
    for old, names in groups.items():
        for _ in range(100):
            target = [rng.uniform(-limit_m, limit_m), rng.uniform(-limit_m, limit_m), 0.0]
            delta = [target[i] - old[i] for i in range(3)]
            if max(abs(v) for v in delta) >= limit_m * 0.3:
                break
        else:
            raise ValueError('Could not obtain a meaningfully distinct group offset')
        for name in names:
            shifts[name] = list(delta)
            result['validation_provenance']['xy_jitter_m'][name] = list(target)
            position = layout[name]['position']
            result['task_data']['initial_layout'][name]['position'] = [
                float(position[i]) + delta[i] for i in range(3)
            ]
    return result, shifts
