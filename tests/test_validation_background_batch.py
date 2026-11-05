from collections import Counter

import pytest

from scenario_forge.generation.validation_background_batch import allocate_cases


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
