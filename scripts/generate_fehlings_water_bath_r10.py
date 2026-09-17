"""Keep r9 lining water; replay heating with the tube near the beaker floor."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil

import yaml

from scripts.generate_fehlings_water_bath_r3 import GRAPH, WATER
from scripts.generate_fehlings_water_bath_r6 import contract as color_contract
from scripts.generate_fehlings_water_bath_r8 import OMNI_GLASS
from scripts.finalize_traditional_titration_vr_r14 import physical_state

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9_20260914/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9'
TASK_ID = 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10'
OUTPUT = ROOT / ('outputs/' + TASK_ID + '_20260914')


def write_task_documents(root):
    """Keep r9 sample/water while recording deep-immersion playback."""
    task = yaml.safe_load((root / 'task.yaml').read_text())
    task.update(task_id=TASK_ID, sample_volume_ml=8.0, reaction_policy=color_contract())
    (root / 'task.yaml').write_text(yaml.safe_dump(task, allow_unicode=True, sort_keys=False))
    metrics = yaml.safe_load((root / 'metrics.yaml').read_text())
    for metric in metrics['metrics']:
        metric['source_ref']['task'] = TASK_ID
    (root / 'metrics.yaml').write_text(yaml.safe_dump(metrics, allow_unicode=True, sort_keys=False))
    cfg = next(iter(runpy.run_path(str(root / 'task_config.py'))['TASKS'].values()))
    cfg['water_bath'].update(
        container='open_round_bottom_glass_test_tube_18x150mm',
        sample_volume_ml=8.0,
        reaction_policy=color_contract(),
        water_representation='lining_and_surface',
        water_shader='OmniGlass',
        heating_style='deep',
    )
    cfg['scene_usd_file_path'] = {'scene1': '__SCENE__'}
    text = repr({TASK_ID: cfg}).replace("'__SCENE__'", "str(Path(__file__).resolve().parent / 'scene.usd')")
    (root / 'task_config.py').write_text('from pathlib import Path\nTASKS = ' + text + '\n')
    shutil.copy2(ROOT / 'docs/operations/fehlings-r10-deep-immerse-guide.md', root / 'COLOR_GUIDE_CN.md')


def build(source=SOURCE, output=OUTPUT):
    """Build a runtime-pending r10 candidate from qualified r9."""
    from pxr import Usd

    source = source.resolve()
    source_manifest = json.loads((source / 'manifest.json').read_text())
    source_hash = sha256((source / 'scene.usd').read_bytes()).hexdigest()
    if (
        source_manifest['package_id'] != 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9'
        or source_manifest['status'] != 'pass'
        or source_manifest['scene_sha256'] != source_hash
    ):
        raise ValueError('qualified unchanged r9 source required')
    if not (source / OMNI_GLASS).is_file():
        raise ValueError('package-local OmniGlass required')
    root = output / 'handoff' / TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(
        source,
        root,
        ignore=lambda directory, names: {'evidence', '.thumbs'} if Path(directory) == source else set(),
    )
    evidence = root / 'evidence'
    evidence.mkdir()
    recipe = json.loads((source / 'evidence/water_recipe.json').read_text())
    stage = Usd.Stage.Open(str(root / 'scene.usd'))
    before = physical_state(stage)
    controller = stage.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get()
    water = stage.GetPrimAtPath(WATER)
    if water.GetAttribute('water:fill_height_ratio').Get() != 0.8:
        raise ValueError('r10 must keep fill 0.8')
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId', TASK_ID)
    stage.GetRootLayer().Save()
    after = physical_state(stage)
    if before != after:
        raise ValueError('unapproved physics change')
    if stage.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get() != controller:
        raise ValueError('reaction controller changed')
    digest = sha256((root / 'scene.usd').read_bytes()).hexdigest()
    recipe.update(scene_sha256=digest, heating_style='deep')
    (evidence / 'water_recipe.json').write_text(json.dumps(recipe, indent=2) + '\n')
    for name in ('sample_recipe.json', 'rack_fit.json'):
        payload = json.loads((source / 'evidence' / name).read_text())
        payload['scene_sha256'] = digest
        (evidence / name).write_text(json.dumps(payload, indent=2) + '\n')
    (evidence / 'physical_revision_audit.json').write_text(
        json.dumps(
            dict(
                status='pass',
                scene_sha256=digest,
                source_scene_sha256=source_hash,
                all_r9_physics_identical=True,
                water_volume_unchanged=True,
                water_representation='lining_and_surface',
                heating_style='deep',
            ),
            indent=2,
        )
        + '\n'
    )
    for key in ('runtime_cold_starts', 'runtime_reports', 'render_evidence', 'closure'):
        source_manifest.pop(key, None)
    source_manifest.update(
        package_id=TASK_ID,
        status='runtime_pending',
        source_package_id=source.name,
        source_scene_sha256=source_hash,
        scene_sha256=digest,
        water_representation='lining_and_surface',
        heating_style='deep',
    )
    source_manifest['claims'].update(
        scene_fixture_verified=False,
        visual_reaction_verified=False,
        in_bath_color_verified=False,
    )
    (root / 'manifest.json').write_text(json.dumps(source_manifest, indent=2) + '\n')
    write_task_documents(root)
    (root / 'README_CN.md').write_text(
        '''# 斐林水浴 r10：试管插到接近杯底再隔着假水看变色

从 r9 派生。Isaac Sim 4.5 打开 scene.usd 并允许脚本节点。假水 80% 液面、贴壁薄壳、
8 mL 五层不变。加热回放把试管竖直插到接近杯底，让样液整段在水面以下。
验收看正视 `front_bath` 图和浸入变色视频。
'''
    )
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source, args.out))
