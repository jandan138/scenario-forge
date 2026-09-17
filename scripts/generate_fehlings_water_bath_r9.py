"""Keep r8 fill/contact; open the fake-water core so in-bath color can be seen."""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import runpy
import shutil

import yaml

from scripts.generate_fehlings_water_bath_r3 import GRAPH, WATER
from scripts.generate_fehlings_water_bath_r6 import contract as color_contract
from scripts.generate_fehlings_water_bath_r8 import OMNI_GLASS, WATER_RECIPE as R8_WATER
from scripts.finalize_traditional_titration_vr_r14 import physical_state

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r8_20260914/handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r8'
TASK_ID = 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9'
OUTPUT = ROOT / ('outputs/' + TASK_ID + '_20260914')
LINING_THICKNESS = 0.0015
WATER_RECIPE = dict(R8_WATER, representation='lining_and_surface', lining_thickness_m=LINING_THICKNESS)


def water_lining_mesh(profile, segments=96, thickness=LINING_THICKNESS):
    """Thin wall-hugging shell with an open core; meniscus stays a separate surface."""
    def ring(height, radius):
        return [
            (
                radius * math.cos(2 * math.pi * index / segments),
                radius * math.sin(2 * math.pi * index / segments),
                height,
            )
            for index in range(segments)
        ]

    profile = tuple((float(height), float(radius)) for height, radius in profile)
    outer = [point for height, radius in profile for point in ring(height, radius)]
    inner = [
        point
        for height, radius in profile
        for point in ring(height, max(radius - thickness, 1e-4))
    ]
    points = outer + inner
    counts = []
    indices = []
    levels = len(profile)
    inner_base = levels * segments
    for level in range(levels - 1):
        for index in range(segments):
            nxt = (index + 1) % segments
            counts.append(4)
            indices.extend(
                [
                    level * segments + index,
                    level * segments + nxt,
                    (level + 1) * segments + nxt,
                    (level + 1) * segments + index,
                ]
            )
            counts.append(4)
            indices.extend(
                [
                    inner_base + level * segments + index,
                    inner_base + (level + 1) * segments + index,
                    inner_base + (level + 1) * segments + nxt,
                    inner_base + level * segments + nxt,
                ]
            )
    top = (levels - 1) * segments
    for index in range(segments):
        nxt = (index + 1) % segments
        counts.append(4)
        indices.extend([top + index, top + nxt, inner_base + top + nxt, inner_base + top + index])
        counts.append(4)
        indices.extend([index, inner_base + index, inner_base + nxt, nxt])
    return points, counts, indices


def water_surface_ring(profile, segments=96, thickness=LINING_THICKNESS):
    """Meniscus as a wall-hugging ring so the front view does not go through a glass disk."""
    height, radius = (float(profile[-1][0]), float(profile[-1][1]))
    inner_radius = max(radius - thickness, 1e-4)
    points = []
    for ring_radius in (radius, inner_radius):
        for index in range(segments):
            angle = 2 * math.pi * index / segments
            points.append((ring_radius * math.cos(angle), ring_radius * math.sin(angle), height))
    counts = [4] * segments
    indices = []
    for index in range(segments):
        nxt = (index + 1) % segments
        indices.extend([index, nxt, segments + nxt, segments + index])
    return points, counts, indices


def apply_water_lining(stage, recipe=WATER_RECIPE):
    """Replace the solid VisualWater body and full-disk meniscus with an open lining."""
    from pxr import Gf, UsdGeom

    water = stage.GetPrimAtPath(WATER)
    profile = [tuple(map(float, value)) for value in water.GetAttribute('water:profile_m').Get()]
    for name, mesh_data in (
        ('body', water_lining_mesh(profile, thickness=recipe['lining_thickness_m'])),
        ('surface', water_surface_ring(profile, thickness=recipe['lining_thickness_m'])),
    ):
        points, counts, indices = mesh_data
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(WATER + '/' + name))
        mesh.GetPointsAttr().Set([Gf.Vec3f(*point) for point in points])
        mesh.GetFaceVertexCountsAttr().Set(counts)
        mesh.GetFaceVertexIndicesAttr().Set(indices)
        xs, ys, zs = zip(*points)
        mesh.GetExtentAttr().Set(
            [Gf.Vec3f(min(xs), min(ys), min(zs)), Gf.Vec3f(max(xs), max(ys), max(zs))]
        )
    return recipe


def write_task_documents(root):
    """Keep r8 timing/sample while recording the lining-water identity."""
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
    )
    cfg['scene_usd_file_path'] = {'scene1': '__SCENE__'}
    text = repr({TASK_ID: cfg}).replace("'__SCENE__'", "str(Path(__file__).resolve().parent / 'scene.usd')")
    (root / 'task_config.py').write_text('from pathlib import Path\nTASKS = ' + text + '\n')
    shutil.copy2(ROOT / 'docs/operations/fehlings-r9-front-bath-guide.md', root / 'COLOR_GUIDE_CN.md')


def build(source=SOURCE, output=OUTPUT):
    """Build a runtime-pending r9 candidate from qualified r8."""
    from pxr import Usd

    source = source.resolve()
    source_manifest = json.loads((source / 'manifest.json').read_text())
    source_hash = sha256((source / 'scene.usd').read_bytes()).hexdigest()
    if (
        source_manifest['package_id'] != 'scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r8'
        or source_manifest['status'] != 'pass'
        or source_manifest['scene_sha256'] != source_hash
    ):
        raise ValueError('qualified unchanged r8 source required')
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
    apply_water_lining(stage)
    stage.GetDefaultPrim().SetCustomDataByKey('scenario_forge:taskId', TASK_ID)
    stage.GetRootLayer().Save()
    after = physical_state(stage)
    if before != after:
        raise ValueError('unapproved physics change')
    if stage.GetPrimAtPath(GRAPH + '/FlowController').GetAttribute('inputs:script').Get() != controller:
        raise ValueError('reaction controller changed')
    digest = sha256((root / 'scene.usd').read_bytes()).hexdigest()
    recipe.update(material=dict(WATER_RECIPE), scene_sha256=digest, lining_thickness_m=LINING_THICKNESS)
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
                all_r8_physics_identical=True,
                water_volume_unchanged=True,
                water_representation='lining_and_surface',
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
    )
    source_manifest['claims'].update(
        scene_fixture_verified=False,
        visual_reaction_verified=False,
        in_bath_color_verified=False,
    )
    (root / 'manifest.json').write_text(json.dumps(source_manifest, indent=2) + '\n')
    write_task_documents(root)
    (root / 'README_CN.md').write_text(
        '''# 斐林水浴 r9：正对隔着烧杯清水看清浸入变色

从 r8 派生。Isaac Sim 4.5 打开 scene.usd 并允许脚本节点。试管、8 mL 五层、80% 液面
和接触判定不变。烧杯假水改成贴壁薄壳加液面，中间留空，避免实心水柱把管底砖红吃黑。
验收看正视 `front_bath` 图和浸入变色视频，不看出水图、不看掠射 through_wall。
'''
    )
    return root


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source, args.out))
