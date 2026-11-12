"""Reject stale or incomplete task09 qualification evidence."""
from copy import deepcopy

import pytest

from scripts.finalize_task09_inventory import validate_reports


def reports():
    return [{'status': 'pass', 'pid': i, 'runtime_requested': v,
             'scene_sha256': 'scene', 'runtime_content_sha256': 'content',
             'physics_dt': 1/120, 'validator_sha256': 'protocol',
             'checks': {k: True for k in ('empty', 'empty_boat', 'tare', 'incremental_loads',
                        'five_complete', 'unload_zero', 'partial_unloads', 'negative_tare',
                        'reset', 'hover_not_counted', 'stability')}}
            for i, v in enumerate(['41']*3+['45']*3)]


def test_requires_three_independent_runs_per_version():
    validate_reports(reports(), 'scene', 'content')
    with pytest.raises(ValueError):
        validate_reports(reports()[:-1], 'scene', 'content')
    rows = reports()
    rows[1]['pid'] = rows[0]['pid']
    with pytest.raises(ValueError):
        validate_reports(rows, 'scene', 'content')


def test_rejects_stale_content_or_failed_physics():
    for key, value in [('scene_sha256', 'old'), ('runtime_content_sha256', 'old'),
                       ('physics_dt', 1/60), ('validator_sha256', 'old'), ('status', 'failed')]:
        rows = reports()
        rows[2][key] = value
        with pytest.raises(ValueError):
            validate_reports(rows, 'scene', 'content')
    rows = deepcopy(reports())
    rows[2]['checks']['stability'] = False
    with pytest.raises(ValueError):
        validate_reports(rows, 'scene', 'content')
