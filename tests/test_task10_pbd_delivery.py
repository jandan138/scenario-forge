"""Reject partial, failed, or stale evidence when promoting a liquid package."""
import copy
import pytest

from scripts.finalize_task10_pbd import CHECKS, validate_reports


def evidence():
    return [{'status':'pass','runtime_requested':v,'runtime_version':['4.'+v[1]+'.0'],
             'pid':int(v),'scope':'full_task_fixture','controller_mode':'graph',
             'physical_containment_qualified':True,'cavity_sampling':'every_physics_step',
             'measurement_readback':'explicit_after_fetch_results','physx_errors':[],
             'input_files_sha256':{'scene41.usda':'abc'},'validator_sha256':'validator',
             'checks':dict.fromkeys(CHECKS,True)} for v in ('41','45')]


def test_dual_runtime_exact_content_is_required():
    rows = evidence()
    validate_reports(rows,{'scene41.usda':'abc'},'validator')
    for key,value in [('scope','integration_api_smoke'),('physical_containment_qualified',False),
                      ('input_files_sha256',{'scene41.usda':'changed'}),('physx_errors',['CUDA error'])]:
        altered = copy.deepcopy(rows)
        altered[0][key] = value
        with pytest.raises(ValueError):
            validate_reports(altered,{'scene41.usda':'abc'},'validator')
    with pytest.raises(ValueError):
        validate_reports(rows[:1],{'scene41.usda':'abc'},'validator')
