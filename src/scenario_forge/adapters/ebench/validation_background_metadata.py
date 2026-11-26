"""SDK-free planning for GenManip validation metadata.

Particle-coordinate transforms and native checks remain adapter responsibilities.
"""

from collections.abc import Sequence


def _collect_group_offsets(
    metadata: dict,
    layout: dict,
    limit_m: float,
    groups: Sequence[Sequence[str]] | None,
) -> list[tuple[tuple[float, float, float], list[str]]]:
    import math

    if groups is not None:
        if not groups:
            raise ValueError('Explicit layout groups must be nonempty')
        seen: set[str] = set()
        grouped: list[tuple[tuple[float, float, float], list[str]]] = []
        for group in groups:
            names = list(group)
            if not names:
                raise ValueError('Each layout group must contain at least one object')
            for name in names:
                if name in seen:
                    raise ValueError(f'Duplicate object across layout groups: {name}')
                seen.add(name)
                if name not in layout or len(layout[name].get('position', [])) != 3:
                    raise ValueError(f'Missing layout position for {name}')
            grouped.append(((0.0, 0.0, 0.0), names))
        return grouped

    declared = metadata.get('validation_provenance', {}).get('xy_jitter_m', {})
    if not declared:
        raise ValueError('No source-owned layout groups declared')
    by_offset: dict[tuple[float, float, float], list[str]] = {}
    for name, offset in declared.items():
        if name not in layout or len(layout[name].get('position', [])) != 3:
            raise ValueError(f'Missing layout position for {name}')
        if len(offset) != 3 or not all(math.isfinite(float(v)) for v in offset):
            raise ValueError(f'Invalid source jitter for {name}')
        if offset[2] != 0 or any(abs(v) > limit_m for v in offset):
            raise ValueError(f'Source jitter outside the declared XY scope: {name}')
        key = (float(offset[0]), float(offset[1]), float(offset[2]))
        by_offset.setdefault(key, []).append(name)
    return list(by_offset.items())


def resample_xy_groups(
    metadata: dict,
    *,
    seed: int,
    limit_m: float,
    groups: Sequence[Sequence[str]] | None = None,
) -> tuple[dict, dict]:
    """Resample declared or explicit source groups, retaining height and rigid attachments.

    ``limit_m`` is a caller-owned task bound, not a global physics default.
    Returned shifts are increments from the supplied source layout, not absolute
    jitter values. Explicit ``groups`` support un-jittered source metadata that
    lacks ``validation_provenance`` (treating baseline offset as zero).
    Particle-coordinate updates belong to the runtime adapter.
    """
    import copy
    import math
    import random

    if not math.isfinite(limit_m) or limit_m <= 0:
        raise ValueError('A finite positive task-specific jitter limit is required')
    layout = metadata.get('task_data', {}).get('initial_layout', {})
    grouped = _collect_group_offsets(metadata, layout, limit_m, groups)
    rng = random.Random(seed)
    result = copy.deepcopy(metadata)
    prov = result.setdefault('validation_provenance', {})
    prov_jitter = prov.setdefault('xy_jitter_m', {})
    shifts = {}
    for old, names in grouped:
        for _ in range(100):
            target = [rng.uniform(-limit_m, limit_m), rng.uniform(-limit_m, limit_m), 0.0]
            delta = [target[i] - old[i] for i in range(3)]
            if max(abs(v) for v in delta) >= limit_m * 0.3:
                break
        else:
            raise ValueError('Could not obtain a meaningfully distinct group offset')
        for name in names:
            shifts[name] = list(delta)
            prov_jitter[name] = list(target)
            position = layout[name]['position']
            result['task_data']['initial_layout'][name]['position'] = [
                float(position[i]) + delta[i] for i in range(3)
            ]
    return result, shifts
