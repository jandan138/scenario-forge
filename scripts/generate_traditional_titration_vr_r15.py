"""Build r1.5 with a Scenario Forge-owned continuous titration policy."""
import argparse
import ast
from hashlib import sha256
import json
from pathlib import Path
import shutil

import yaml

from scripts import titration_linear_policy as policy

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_4_20260907/handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_4'
OUTPUT = ROOT/'outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_5_20260907'
TASK_ID = 'scientific_workbench_traditional_acid_base_titration_vr_r1_5'
STATION = '/World/obj_titration_station'

RUNTIME = '''
def _color(dispensed):
    return color(dispensed)

def _reset(stage):
    for name, value in initial_state().items():
        _set(stage, ROOT, 'titration:'+name, value)
    _sync_column(stage, 25.0, 25.0)
    _sync_receiver(stage, 0.0)

def compute(db):
    _bind(db)
    stage = omni.usd.get_context().get_stage()
    if stage is None or not _prim(stage, ROOT):
        return True
    if bool(_get(stage, ROOT, 'titration:reset_requested', False)):
        _reset(stage)
        return True
    previous = {name: _get(stage, ROOT, 'titration:'+name, value)
                for name, value in initial_state().items()}
    state = advance(previous, _angle(stage, db.per_instance_state),
                    float(db.inputs.deltaSeconds),
                    bool(_get(stage, ROOT, 'titration:target_container_inside', False)))
    for name, value in state.items():
        _set(stage, ROOT, 'titration:'+name, value)
    _sync_column(stage, state['burette_liquid_volume_ml'], 25.0)
    _sync_receiver(stage, state['dispensed_volume_ml'])
    return True
'''


def controller(script):
    lines = script.splitlines(keepends=True)
    nodes = [n for n in ast.parse(script).body
             if isinstance(n, ast.FunctionDef) and n.name in ('_color', '_reset', 'compute')]
    if {n.name for n in nodes} != {'_color', '_reset', 'compute'} or len(nodes) != 3:
        raise ValueError('unrecognized source controller')
    for node in sorted(nodes, key=lambda n: n.lineno, reverse=True):
        del lines[node.lineno-1:node.end_lineno]
    result = ''.join(lines)+'\n'+Path(policy.__file__).read_text()+'\n'+RUNTIME
    compile(result, '<r15 controller>', 'exec')
    return result


def build(source=SOURCE, output=OUTPUT):
    from pxr import Sdf, Usd
    from scripts.finalize_traditional_titration_vr_r14 import physical_state

    root = output/'handoff'/TASK_ID
    if root.exists():
        raise FileExistsError(root)
    shutil.copytree(source, root, ignore=lambda directory, names: {'evidence'} if Path(directory) == source else set())
    evidence = root/'evidence'
    evidence.mkdir()
    for name in ('receiver_cavity.json', 'visual_liquid_recipe.json'):
        shutil.copy2(source/'evidence'/name, evidence/name)
    stage = Usd.Stage.Open(str(root/'scene.usd'))
    station = stage.GetPrimAtPath(STATION)
    attr = stage.GetPrimAtPath(STATION+'/Instance/Runtime/TitrationFlowGraph/FlowController').GetAttribute('inputs:script')
    old_script = attr.Get()
    new_script = controller(old_script)
    attr.Set(new_script)
    for name, default in (('completion_volume_ml', -1.0), ('completion_hold_seconds', 0.0)):
        station.CreateAttribute('titration:'+name, Sdf.ValueTypeNames.Double, custom=True).Set(default)
    station.CreateAttribute('titration:policy_version', Sdf.ValueTypeNames.String, custom=True).Set(policy.POLICY_VERSION)
    stage.GetRootLayer().Save()
    original = Usd.Stage.Open(str(source/'scene.usd'))
    if physical_state(stage) != physical_state(original):
        raise ValueError('physical content changed')
    digest = sha256((root/'scene.usd').read_bytes()).hexdigest()
    (evidence/'physical_revision_audit.json').write_text(json.dumps(dict(
        status='pass', physical_content_identical=True, physical_prims=len(physical_state(stage)),
        scene_sha256=digest, source_scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest()), indent=2)+'\n')
    for name in ('task.yaml', 'metrics.yaml'):
        path = root/name
        data = yaml.safe_load(path.read_text())
        data['task_id'] = TASK_ID
        if name == 'task.yaml':
            data['instruction'] = '使用左臂自由调节旋塞流量；锥形瓶呈稳定淡粉色时，将旋塞关至≤5°并连续保持3秒，然后释放旋塞。'
            data['state_contract'] = policy.contract()
        else:
            data['metrics'] = [m for m in data['metrics'] if m['id'] not in ('coarse_open_phase', 'fine_phase')]
            total = sum(m['weight'] for m in data['metrics'])
            for metric in data['metrics']:
                metric['weight'] /= total
                if metric['id'] == 'endpoint_volume':
                    metric.update(range_ml=[policy.PINK_START, policy.PINK_END], value_source='titration:completion_volume_ml')
                if metric['id'] == 'closed_pale_pink_hold':
                    metric['value_source'] = 'titration:completion_hold_seconds'
            data['hard_requirements'] = dict(ordered_valve_sequence=[],
                overshoot_failure_threshold_ml=policy.PINK_END, overshoot_failure_before_success_only=True)
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    path = root/'task_config.py'
    namespace = {'__file__': str(path)}
    exec(compile(path.read_text(), str(path), 'exec'), namespace)
    tasks = namespace['TASKS']
    if len(tasks) != 1:
        raise ValueError('expected single task')
    config = next(iter(tasks.values()))
    config['titration_contract'].update(policy.contract())
    config['titration_contract']['hold_seconds'] = 3.0
    config['scene_usd_file_path']['scene1'] = '__SCENE_PATH__'
    body = repr(config).replace("'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')")
    path.write_text("from pathlib import Path\n_ASSETS_DIR = Path(__file__).resolve().parent\n"+f'TASKS = {{{TASK_ID!r}: {body}}}\n')
    manifest_path = root/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    for name in ('runtime_evidence', 'render_evidence', 'package_closure'):
        manifest.pop(name, None)
    manifest.update(package_id=TASK_ID, status='runtime_pending', titration_policy=policy.contract(),
                    source_revision=dict(package_id=source.name, scene_sha256=sha256((source/'scene.usd').read_bytes()).hexdigest()))
    manifest['claims'].update(scene_cold_start_passes=0, scene_static_validation=False,
                             materialized_state_machine_success_path=False)
    manifest['receiver_liquid'].update(controller_before_sha256=sha256(old_script.encode()).hexdigest(),
                                      controller_after_sha256=sha256(new_script.encode()).hexdigest())
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True)+'\n')
    recipe_path = evidence/'visual_liquid_recipe.json'
    recipe = json.loads(recipe_path.read_text())
    recipe.update(controller_before_sha256=sha256(old_script.encode()).hexdigest(),
                  controller_after_sha256=sha256(new_script.encode()).hexdigest())
    recipe_path.write_text(json.dumps(recipe, indent=2)+'\n')
    (evidence/'titration_policy.json').write_text(json.dumps(dict(
        policy=policy.contract(), scene_sha256=digest, policy_source_sha256=sha256(Path(policy.__file__).read_bytes()).hexdigest(),
        controller_sha256=sha256(new_script.encode()).hexdigest(), owner='Scenario Forge task policy'), indent=2)+'\n')
    (root/'README_CN.md').write_text('''# 传统酸碱滴定 VR r1.5

用 Isaac Sim 4.5 打开 scene.usd，允许脚本节点执行；保留 deps 和 task_config.py。

颜色属性、读取代码与渐变教学见 [液体颜色教学文档](COLOR_GUIDE_CN.md)。

旋塞≤5°完全关闭；5–90°线性增流，Q=(30/11)×(角度−5)/85 mL/s。
从重置持续保持90°，第5秒开始渐变，第5.5秒进入稳定淡粉。
累计接收13.63636 mL开始渐变，15–16.92513 mL为稳定淡粉窗口。
45°下完整淡粉窗口为1.5秒；25°为3秒，10°为12秒；关阀后颜色停留。
时间均指仿真时间；调角度不会重置已接收液量。
无需依次经过粗滴、细调、逐滴；淡粉时关至≤5°保持3秒即完成。
成功结果锁定至重置；成功前过量不可补救，但可继续观察或重置重试。
初始容量25 mL；沿用r1.4器械、玻璃滴嘴、管内和瓶内假液体以及20×5 mm磁子。
无管外落滴、PBD或真实化学求解。运行证据不代表机器人策略成功。
''')
    shutil.copy2(ROOT/'docs/operations/titration-r15-color-guide.md', root/'COLOR_GUIDE_CN.md')
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source, args.out))
