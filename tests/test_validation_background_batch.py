from collections import Counter

import pytest

from scenario_forge.generation.validation_background_batch import (
    allocate_cases,
    allocate_cases_340,
)


def test_preserves_group_counts_and_balances_five_backgrounds():
    regular = [f'task_{i:02d}' for i in range(1, 15)]
    zero = [f'task_z{i}' for i in range(1, 7)]
    rooms = ['teaching', 'water', 'food', 'materials', 'pharma']
    cases = allocate_cases(regular, zero, rooms)
    assert len(cases) == 136
    assert sorted(Counter(c.background for c in cases).values()) == [27, 27, 27, 27, 28]
    assert len({(c.task, c.category, c.index) for c in cases}) == 136
    for task in regular:
        subset = [c for c in cases if c.task == task]
        assert {c.background for c in subset} == set(rooms)
        assert Counter(c.category for c in subset) == dict.fromkeys(
            ['mixed', 'unseen_instruction', 'unseen_prospect', 'unseen_background'], 2
        )
        for category in {c.category for c in subset}:
            assert len({c.background for c in subset if c.category == category}) == 2
    for task in zero:
        subset = [c for c in cases if c.task == task]
        assert len(subset) == 4
        assert {c.category for c in subset} == {'mixed'}
        assert len({c.background for c in subset}) == 4
    assert cases == allocate_cases(regular, zero, rooms)


def test_rejects_missing_or_duplicate_backgrounds():
    with pytest.raises(ValueError):
        allocate_cases([str(i) for i in range(14)], [f'z{i}' for i in range(6)], ['same'] * 5)


def test_layout_resampling_preserves_coupled_objects_and_other_state():
    import copy
    from scenario_forge.adapters.ebench.validation_background_metadata import resample_xy_groups

    original = {
        'task_data': {
            'instruction': 'Move the bottle.',
            'goal': [[{'threshold': 0.2}]],
            'initial_layout': {
                'bottle': {'position': [0.1, 0.2, 0.8], 'orientation': [1, 0, 0, 0]},
                'cap': {'position': [0.1, 0.2, 1.0]},
                'tray': {'position': [-0.2, 0.0, 0.8]},
            },
        },
        'validation_provenance': {'xy_jitter_m': {
            'bottle': [0.005, 0.003, 0], 'cap': [0.005, 0.003, 0],
            'tray': [-0.004, 0.002, 0],
        }},
    }
    frozen = copy.deepcopy(original)
    result, shifts = resample_xy_groups(original, seed=19, limit_m=0.01)
    assert original == frozen
    assert result['task_data']['goal'] == original['task_data']['goal']
    assert result['task_data']['instruction'] == original['task_data']['instruction']
    assert shifts['bottle'] == shifts['cap']
    assert shifts['bottle'] != shifts['tray']
    assert all(v[2] == 0 for v in shifts.values())
    assert result['task_data']['initial_layout']['bottle']['position'][2] == 0.8
    assert result == resample_xy_groups(original, seed=19, limit_m=0.01)[0]
    assert all(abs(v) <= 0.01 for delta in result['validation_provenance']['xy_jitter_m'].values() for v in delta)


def test_layout_resampling_rejects_missing_group_member():
    from scenario_forge.adapters.ebench.validation_background_metadata import resample_xy_groups

    with pytest.raises(ValueError):
        resample_xy_groups({'task_data': {'initial_layout': {}}, 'validation_provenance': {'xy_jitter_m': {'missing': [0, 0, 0]}}}, seed=1, limit_m=0.01)


def test_allocate_cases_340_preserves_136_prefix_and_balances_five_rooms_uniformly():
    regular = [f'task_{i:02d}' for i in range(1, 15)]
    zero = [f'task_z{i}' for i in range(1, 7)]
    rooms = ['teaching', 'water', 'food', 'materials', 'pharma']
    base_136 = allocate_cases(regular, zero, rooms)
    cases_340 = allocate_cases_340(regular, zero, rooms)

    assert len(cases_340) == 340
    assert len({(c.task, c.category, c.index) for c in cases_340}) == 340
    assert sorted(Counter(c.background for c in cases_340).values()) == [68, 68, 68, 68, 68]

    map_340 = {(c.task, c.category, c.index): c for c in cases_340}
    for base_case in base_136:
        assert map_340[(base_case.task, base_case.category, base_case.index)].background == base_case.background

    for task in regular:
        for category in ('mixed', 'unseen_instruction', 'unseen_prospect', 'unseen_background'):
            subset = [c for c in cases_340 if c.task == task and c.category == category]
            assert {c.index for c in subset} == {1, 2, 3, 4, 5}
            assert Counter(c.background for c in subset) == {r: 1 for r in rooms}

    for task in zero:
        subset = [c for c in cases_340 if c.task == task]
        assert {c.category for c in subset} == {'mixed'}
        assert {c.index for c in subset} == set(range(1, 11))
        assert Counter(c.background for c in subset) == {r: 2 for r in rooms}
        by_idx = {c.index: c.background for c in subset}
        assert by_idx[5] != by_idx[6]

    assert cases_340 == allocate_cases_340(regular, zero, rooms)


def test_layout_resampling_with_explicit_groups_from_zero_baseline():
    import copy
    from scenario_forge.adapters.ebench.validation_background_metadata import resample_xy_groups

    metadata_without_provenance = {
        'task_data': {
            'instruction': 'Move the bottle.',
            'goal': [[{'threshold': 0.2}]],
            'initial_layout': {
                'bottle': {'position': [0.1, 0.2, 0.8], 'orientation': [1, 0, 0, 0]},
                'cap': {'position': [0.1, 0.2, 1.0]},
                'tray': {'position': [-0.2, 0.0, 0.8]},
            },
        },
    }
    frozen = copy.deepcopy(metadata_without_provenance)
    result, shifts = resample_xy_groups(
        metadata_without_provenance,
        seed=42,
        limit_m=0.01,
        groups=[['bottle', 'cap'], ['tray']],
    )
    assert metadata_without_provenance == frozen
    assert shifts['bottle'] == shifts['cap']
    assert shifts['bottle'] != shifts['tray']
    assert result['validation_provenance']['xy_jitter_m']['bottle'] == shifts['bottle']
    assert max(abs(v) for v in shifts['bottle']) >= 0.003
    assert result['task_data']['initial_layout']['bottle']['position'][0] == pytest.approx(0.1 + shifts['bottle'][0])
    assert result['task_data']['initial_layout']['bottle']['position'][2] == 0.8
    assert result['task_data']['initial_layout']['tray']['position'][1] == pytest.approx(0.0 + shifts['tray'][1])
