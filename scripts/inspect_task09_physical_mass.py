"""Read actual PhysX rigid-body masses independently of LCD inventory values."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import traceback


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--runtime', choices=['41', '45'], required=True)
    a = p.parse_args()
    report = {'status': 'failed', 'runtime': a.runtime,
              'scene_sha256': hashlib.sha256((a.package/'assets/composed/scene.usdc').read_bytes()).hexdigest()}
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp
    app = SimulationApp({'headless': True, 'multi_gpu': False})
    try:
        import omni.usd
        import omni.physx
        from omni.isaac.dynamic_control import _dynamic_control
        try:
            from isaacsim.core.api import World
        except ImportError:
            from omni.isaac.core import World
        omni.physx.get_physx_interface().overwrite_gpu_setting(1)
        ctx = omni.usd.get_context()
        ctx.open_stage(str((a.package/f'scene/demo{a.runtime}.usda').resolve()))
        while ctx.get_stage_loading_status()[2]:
            app.update()
        stage = ctx.get_stage()
        # This audit reads masses only; it does not run the weighing controller.
        stage.SetEditTarget(stage.GetSessionLayer())
        stage.GetPrimAtPath('/World/obj_analytical_balance/BalanceRuntime').SetActive(False)
        world = World(stage_units_in_meters=1, physics_prim_path='/World/PhysicsScene',
                      set_defaults=False, physics_dt=1/120)
        world.reset()
        for _ in range(4):
            world.step(render=False)
        dc = _dynamic_control.acquire_dynamic_control_interface()
        report['bodies'] = []
        for i in range(1, 6):
            path = f'/World/obj_grain_{i:02d}'
            configured = float(stage.GetPrimAtPath(path).GetAttribute('physics:mass').Get())
            actual = float(dc.get_rigid_body_properties(dc.get_rigid_body(path)).mass)
            report['bodies'].append({'path': path, 'configured_kg': configured,
                                     'physx_kg': actual, 'pass': abs(actual-configured) <= 1e-8})
        report['status'] = 'pass' if all(x['pass'] for x in report['bodies']) else 'failed'
    except BaseException:
        report['exception'] = traceback.format_exc()
    finally:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, indent=2))
        print(json.dumps(report), flush=True)
        app.close(wait_for_replicator=False)
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
