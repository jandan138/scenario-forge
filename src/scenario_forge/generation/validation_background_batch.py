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


def allocate_cases_340(
    regular_tasks: Sequence[str],
    zero_shot_tasks: Sequence[str],
    backgrounds: Sequence[str],
) -> tuple[BackgroundCase, ...]:
    """Expand the 136-case allocation to 340 cases while freezing the 136 prefix.

    Each regular task receives indices 3..5 in each category with the remaining
    three rooms rotated deterministically (1/1/1/1/1 per category), and each
    zero-shot task receives mixed_5..10 (2/2/2/2/2 across the five rooms).
    """
    base_136 = allocate_cases(regular_tasks, zero_shot_tasks, backgrounds)
    base_map = {(case.task, case.category, case.index): case for case in base_136}
    categories = ('mixed', 'unseen_instruction', 'unseen_prospect', 'unseen_background')
    result: list[BackgroundCase] = []
    for offset, task in enumerate(regular_tasks):
        for cat_idx, category in enumerate(categories):
            c1 = base_map[(task, category, 1)]
            c2 = base_map[(task, category, 2)]
            result.extend((c1, c2))
            used = {c1.background, c2.background}
            rem = [bg for bg in backgrounds if bg not in used]
            rot = (offset + cat_idx) % 3
            rem = rem[rot:] + rem[:rot]
            for k, bg in enumerate(rem):
                result.append(BackgroundCase(task, category, 3 + k, bg))
    for offset, task in enumerate(zero_shot_tasks):
        prefix = [base_map[(task, 'mixed', idx)] for idx in range(1, 5)]
        result.extend(prefix)
        used = {case.background for case in prefix}
        missing = [bg for bg in backgrounds if bg not in used]
        result.append(BackgroundCase(task, 'mixed', 5, missing[0]))
        for k in range(5):
            result.append(BackgroundCase(task, 'mixed', 6 + k, backgrounds[(offset + 1 + k) % 5]))
    return tuple(result)
