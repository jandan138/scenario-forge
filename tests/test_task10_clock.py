"""Time-step evidence must come from native callbacks, not requested configuration."""
import pytest
from scripts.task10_clock import clock_summary, runtime_settings


def test_contract_drives_frequency_and_iterations():
    cfg={'runtime_contract':{'physics_dt':1/120,'scene_min_position_iterations':64,'scene_max_position_iterations':64}}
    assert runtime_settings(cfg)=={'physics_dt':1/120,'physics_hz':120,'min_iterations':64,'max_iterations':64}
    with pytest.raises(ValueError):
        runtime_settings({'runtime_contract':{'physics_dt':.009}})


def test_clock_gate_rejects_legacy240_and_mixed_or_missing_callbacks():
    for samples,world,hz in [([],1/120,120),([1/240]*4,1/120,120),([1/120,1/60],1/120,120),([1/120]*4,1/60,120),([1/120]*4,1/120,240)]:
        with pytest.raises(ValueError):
            clock_summary(samples,1/120,world,hz)
    report=clock_summary([1/120]*120,1/120,1/120,120)
    assert report['source']=='native_physics_step_callback'
    assert report['count']==120
    assert abs(report['sum_s']-1)<1e-12


def test_controller_rejects_wrong_runtime_step_before_using_sdk_state():
    from scripts.task10_pbd_runtime import Task10PbdRuntime
    runtime=Task10PbdRuntime.__new__(Task10PbdRuntime)
    runtime.config={'runtime_contract':{'physics_dt':1/120}}
    with pytest.raises(ValueError,match='physical step'):
        runtime.update(1/240)
