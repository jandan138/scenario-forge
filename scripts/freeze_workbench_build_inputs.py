"""One-time migration of explicit workbench input closures; no asset conversion."""
from pathlib import Path
import argparse
import json
from scripts.retained_build_inputs import freeze_input


def migrate(repo: Path, index: Path) -> None:
    outputs = repo / 'outputs'
    store = repo / 'external_artifacts/build_inputs/v1'
    r9 = outputs / 'scientific_workbench_tasks_02_07_08_r9_20260816/rich_bases/scientific_workbench_r9_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry'
    adapter = 'adapters/ebench/genmanip'
    scene = next((r9 / adapter / 'assets/scene_usds/scenario_forge').glob('*/scene.usda'))
    episode = next((r9 / adapter / 'tasks/scenario_forge').glob('*/002/episode_metadata.json'))
    entries = {}
    entries['task02_base'] = freeze_input(r9, store, 'task02-base', [
        'scenario.yaml', str(scene.parent.relative_to(r9)),
        f'{adapter}/tasks/config.yaml', str(episode.relative_to(r9)),
        f'{adapter}/cameras', f'{adapter}/package_manifest.json',
        f'{adapter}/evidence/render_request.yaml',
    ])
    fixture = outputs / 'scientific_workbench_tasks_02_07_08_r10_1_20260817/packages/task07/teaching_research'
    bundle = next((fixture / adapter / 'assets/scene_usds/scenario_forge').glob('*/source_bundle'))
    entries['rod_rack'] = freeze_input(fixture, store, 'rod-rack', [
        'adapters/vr_teleop/deps/objects/obj_glass_rod',
        'adapters/vr_teleop/deps/objects/obj_acrylic_rod_rack',
        str((bundle / 'scientific_workbench_r7_glass_stirring_rod_300mm').relative_to(fixture)),
        str((bundle / 'scientific_workbench_r10_1_acrylic_spoon_rack').relative_to(fixture)),
        f'{adapter}/package_manifest.json',
    ])
    metadata = outputs / 'scientific_workbench_task02_r10_2_fill_sweep_20260819/packages/fill40/ebench'
    episode = next((metadata / 'tasks/scenario_forge').glob('*/002/episode_metadata.json'))
    entries['robot_adapter_metadata'] = freeze_input(metadata, store, 'robot-adapter-metadata', [
        'config.yaml', 'cameras', str(episode.relative_to(metadata)),
    ])
    environment = metadata.parent / 'vr/deps/r7_scene'
    entries['environment'] = freeze_input(environment, store, 'environment', ['scene.usda', 'source_bundle'])
    oven = outputs / 'scientific_workbench_task09_r15_20260901/handoff/scientific_workbench_task09_r15_vr'
    entries['oven_layout'] = freeze_input(oven, store, 'oven-layout', [
        'scene.usd', 'deps', 'task_config.py', 'manifest.json', 'README_CN.md', 'task_r15.json',
    ])
    stir = outputs / 'scientific_workbench_insert_stir_bar_into_beaker_vr_r3_20260824'
    entries['stirrer_layout'] = freeze_input(stir, store, 'stirrer-layout', [
        'manifest.json', 'scenario.json', 'vr/scene.usd', 'vr/legacy_scene.usd', 'vr/deps',
    ])
    data = {'schema_version': 'scenario-forge-build-inputs/v1', 'inputs': entries,
            'policy': 'explicit runtime closures and authoring metadata; no handoff ZIP or preview collections'}
    index.parent.mkdir(parents=True, exist_ok=True)
    if index.exists():
        raise FileExistsError(index)
    index.write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k:v['bytes'] for k,v in entries.items()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--index', type=Path, required=True)
    args = parser.parse_args()
    migrate(args.repo, args.index)
