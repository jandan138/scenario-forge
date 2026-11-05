"""Simulator-neutral allocation for the second scientific validation batch.

This schedules cases only; it does not generate assets or grant qualification.
"""

from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True)
class BackgroundCase:
    task: str
    category: str
    index: int
    background: str


def allocate_cases(
    regular_tasks: Sequence[str],
    zero_shot_tasks: Sequence[str],
    backgrounds: Sequence[str],
) -> tuple[BackgroundCase, ...]:
    """Keep 14x8 + 6x4 cases, allocating the five rooms 28/27/27/27/27."""
    if len(regular_tasks) != 14 or len(zero_shot_tasks) != 6:
        raise ValueError('Expected fourteen regular and six zero-shot tasks')
    if len(backgrounds) != 5 or len(set(backgrounds)) != 5:
        raise ValueError('Expected five distinct backgrounds')
    tasks = [*regular_tasks, *zero_shot_tasks]
    if len(set(tasks)) != 20 or not all(tasks) or not all(backgrounds):
        raise ValueError('Task and background identifiers must be nonempty and unique')
    categories = ('mixed', 'unseen_instruction', 'unseen_prospect', 'unseen_background')
    result = []
    for offset, task in enumerate(regular_tasks):
        slots = [(i + offset) % 5 for i in range(8)]
        # Redistribute two surplus room assignments while retaining all five
        # rooms per task and distinct rooms within every two-case group.
        if offset in (0, 1):
            slots[-1] = 0
        for i, room in enumerate(slots):
            result.append(BackgroundCase(task, categories[i // 2], i % 2 + 1, backgrounds[room]))
    for offset, task in enumerate(zero_shot_tasks):
        slots = [room for room in range(5) if room != offset % 5]
        for i, room in enumerate(slots):
            result.append(BackgroundCase(task, 'mixed', i + 1, backgrounds[room]))
    return tuple(result)
