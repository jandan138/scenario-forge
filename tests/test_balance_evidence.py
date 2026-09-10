import pytest

from scripts.balance_evidence import validate_task_reports


def reports():
    return [dict(pid=i+1,runtime=version,initialization=mode,status='passed',
                 closure_sha256='closure',asset_sha256='asset',physics_dt=1/120,
                 checks={k:True for k in ['empty','container','tare','target','negative','reset',
                         'lifted_invalid','pressure_responds','pressure_recovers','move_recovers','overload']})
            for i,(version,mode) in enumerate((v,m) for v in ['4.1.0','4.5.0']
                                               for m in ['omitted','zero','pressed'])]


def test_both_runtimes_and_all_initialization_paths_are_required():
    validate_task_reports(reports(),'closure','asset')
    with pytest.raises(ValueError):
        validate_task_reports(reports()[:3],'closure','asset')


@pytest.mark.parametrize('field,value',[('pid',1),('closure_sha256','old'),
                                      ('asset_sha256','old'),('status','observed'),
                                      ('physics_dt',1/60),('checks',{'target':False})])
def test_stale_or_incomplete_evidence_cannot_promote(field,value):
    data=reports()
    data[-1][field]=value
    with pytest.raises(ValueError):
        validate_task_reports(data,'closure','asset')
