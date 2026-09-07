"""Consume the producer-filled burette and shrink the visual stir bar for VR r1.4."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

from scripts.generate_traditional_titration_vr_r13 import water_controller

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_3_20260907/handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_3'
PRODUCER = Path('/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/traditional_titration_assets_r3_filled_visuals_20260907')
OUTPUT = ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_4_20260907'
TASK_ID = 'scientific_workbench_traditional_acid_base_titration_vr_r1_4'
STATION = '/World/obj_titration_station'


def stir_bar_dimensions(floor):
    return 0.0025, 0.015, floor+0.0025+0.00015


def build(source=SOURCE, producer=PRODUCER, output=OUTPUT, refresh=False):
    from pxr import Gf, Usd, UsdGeom
    from scenario_forge.adapters.vr_object_materialization import materialize_vr_object_subtrees

    root = output/'handoff'/TASK_ID
    if root.exists():
        if not refresh or json.loads((root/'manifest.json').read_text())['status'] != 'runtime_pending':
            raise FileExistsError(root)
    manifest = json.loads((producer/'packages/station/evidence/manifest.json').read_text())
    if manifest['package_id'] != 'traditional_titration_station_r3' or manifest['overall_status'] not in ('runtime_pending', 'pass'):
        raise ValueError('unexpected producer candidate')
    if not root.exists():
        shutil.copytree(source, root, ignore=lambda directory, names: {'evidence'} if Path(directory) == source else set())
    (root/'evidence').mkdir(exist_ok=True)
    for name in ('receiver_cavity.json', 'visual_liquid_recipe.json'):
        shutil.copy2(source/'evidence'/name, root/'evidence'/name)
    shutil.rmtree(root/'deps/titration_assets')
    shutil.copytree(producer/'packages', root/'deps/titration_assets/packages')
    if (producer/'promotion_receipt.json').exists():
        shutil.copy2(producer/'promotion_receipt.json', root/'deps/titration_assets/promotion_receipt.json')
    stage = Usd.Stage.Open(str(root/'scene.usd'))
    old = stage.GetPrimAtPath(STATION)
    pose = old.GetAttribute('xformOp:translate').Get()
    receiver_rels = {name: old.GetRelationship(name).GetTargets() for name in (
        'titration:receiverLiquidVisuals', 'titration:receiverLiquidShader')}
    stage.RemovePrim(STATION)
    station = UsdGeom.Xform.Define(stage, STATION)
    station.GetPrim().GetReferences().AddReference('deps/titration_assets/packages/station/asset.usd', '/World/TitrationStation')
    attr = station.GetPrim().GetAttribute('xformOp:translate')
    (attr if attr else station.AddTranslateOp().GetAttr()).Set(pose)
    stage.GetRootLayer().Save()
    stage = None
    materialize_vr_object_subtrees(scene_path=root/'scene.usd', scene_prim_paths=[STATION],
        runtime_prim_paths=[STATION.replace('/World/', '/World/_scene/')],
        evidence_path=root/'evidence/vr_object_materialization.json')
    stage = Usd.Stage.Open(str(root/'scene.usd'))
    station = stage.GetPrimAtPath(STATION)
    for name, paths in receiver_rels.items():
        station.GetRelationship(name).SetTargets(paths)
    station.GetAttribute('titration:target_container_inside').Set(True)
    ctrl = stage.GetPrimAtPath(STATION+'/Instance/Runtime/TitrationFlowGraph/FlowController').GetAttribute('inputs:script')
    ctrl.Set(water_controller(ctrl.Get()))
    floor = json.loads((root/'evidence/receiver_cavity.json').read_text())['inner_floor_m']
    radius, straight, center = stir_bar_dimensions(floor)
    bar_root = '/World/obj_receiver_flask/VisualLiquid/StirBar'
    bar = UsdGeom.Capsule(stage.GetPrimAtPath(bar_root+'/Visual'))
    bar.GetRadiusAttr().Set(radius)
    bar.GetHeightAttr().Set(straight)
    stage.GetPrimAtPath(bar_root).GetAttribute('xformOp:translate').Set(Gf.Vec3d(0, 0, center))
    stage.GetRootLayer().Save()
    for name in ('task.yaml', 'task_config.py'):
        path = root/name
        path.write_text(path.read_text().replace('vr_r1_3', 'vr_r1_4'))
    current = json.loads((root/'manifest.json').read_text())
    for name in ('runtime_evidence', 'render_evidence', 'package_closure'):
        current.pop(name, None)
    current.update(package_id=TASK_ID, status='runtime_pending', runtime='Isaac Sim 4.5')
    current['source_revision'] = {'package_id': source.name, 'scene_sha256': sha256((source/'scene.usd').read_bytes()).hexdigest()}
    current['assets']['titration_station_package_id'] = manifest['package_id']
    current['assets'].pop('titration_station_receipt_sha256', None)
    current['claims'].update(scene_cold_start_passes=0, scene_static_validation=False,
                            materialized_state_machine_success_path=False, asset_functionality=False)
    current['stir_bar'] = {'overall_length_m': 0.020, 'diameter_m': 0.005, 'visual_only': True}
    (root/'manifest.json').write_text(json.dumps(current, indent=2, sort_keys=True)+'\n')
    (root/'README_CN.md').write_text('''# 传统酸碱滴定 VR r1.4

用 Isaac Sim 4.5 打开 scene.usd；允许场景脚本节点执行。整包保留 deps 和 task_config.py。
滴定管初始满液可见；刻度段液面随用量下降，刻度以下至滴嘴为预充假液体，不另计入 25 mL 量程。
到末刻度仍保留下段充液，不模拟排空。初始为淡蓝透明清水外观。
锥形瓶沿用 r1.3 贴壁液体；磁子改为含圆头总长 20 mm、直径 5 mm。
操作仍为 OPEN → FINE → DRIP → CLOSED，在 14.7–15.3 mL 内关闭保持 3 秒。
不含 PBD、真实化学、落滴仿真或新增机器人成功证明。
''')
    print(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--producer', type=Path, default=PRODUCER)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    parser.add_argument('--refresh-candidate', action='store_true')
    args = parser.parse_args()
    build(args.source, args.producer, args.out, args.refresh_candidate)
