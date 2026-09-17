import copy
import json

import pytest
import yaml

from scenario_forge.adapters.ebench.intervention_suite import (
    compile_suite, digest, install_suite, preplaced_layout,
)


@pytest.fixture
def source():
    pose = {"position": [0, 0, 0], "orientation": [1, 0, 0, 0], "scale": [1, 1, 1]}
    names = ["basket_big", "basket_small", "dish1", "dish2", "dish3", "glass", "spoon"]
    result = {"task_data": {"initial_layout": {n: copy.deepcopy(pose) for n in names},
                            "instruction": "same instruction", "goal": [[{"object": "spoon"}]]},
              "objects": {}, "source_kind": "source_demonstration_not_model_rollout"}
    for name in names:
        result["objects"][name] = {f: {"first": list(v), "last": list(v), "count": 10}
                                   for f, v in pose.items()}
        if name.startswith("dish") or name == "glass":
            result["objects"][name]["position"]["last"] = [0.1, 0.1, 0.1]
    return result


def test_preplacement_only_changes_four_objects_and_requires_frame_match(source):
    result = preplaced_layout(source)
    assert result["spoon"] == source["task_data"]["initial_layout"]["spoon"]
    assert result["dish1"]["position"] == [0.1, 0.1, 0.1]
    assert source["task_data"]["initial_layout"]["dish1"]["position"] == [0, 0, 0]
    source["objects"]["basket_big"]["position"]["last"] = [1, 0, 0]
    with pytest.raises(ValueError, match="basket moved"):
        preplaced_layout(source)


def test_four_cells_preserve_goal_and_geometry_pair_initial_state(tmp_path, source):
    blob = tmp_path / "source.usd"
    blob.write_bytes(b"retained")
    blob.with_suffix(".usda").write_text('#usda 1.0\ndef Xform "World" { def "_scene" ( prepend payload = @./source.usd@ ) {} }')
    source.update(metadata={"path": str(blob), "sha256": digest(blob)},
                  database={"path": str(blob), "sha256": digest(blob)})
    layout = tmp_path / "layout.json"
    layout.write_text(json.dumps(source))
    task = tmp_path / "task.yml"
    task.write_text(yaml.safe_dump({"evaluation_configs": [{"num_steps": 5000}]}))
    config = {"schema": "ebench-native-intervention-build/v1", "source_layout": str(layout),
              "source_task_config": str(task), "base_scene": str(blob), "base_scene_sha256": digest(blob),
              "overlays": {k: {"path": str(blob), "sha256": digest(blob)} for k in ["control", "wide"]}}
    out = tmp_path / "suite"
    report = compile_suite(config, out)
    assert len(report["cells"]) == 4
    assert report["new_model_episodes"] == 0
    assert "@./main.usd@" in (out / "dish_control_full/scene/main.usda").read_text()
    records = {}
    for cell in report["cells"]:
        p = out / cell["cell_id"] / "tasks" / cell["task_name"] / "000/episode_metadata.json"
        records[cell["cell_id"]] = json.loads(p.read_text())["task_data"]
        assert records[cell["cell_id"]]["goal"] == source["task_data"]["goal"]
    assert records["dish_control_full"] == records["dish_wide_full"]
    assert records["dish_control_preplaced"] == records["dish_wide_preplaced"]
    shortened = copy.deepcopy(config)
    shortened["preplaced_instruction"] = "Put the spoon into the small basket."
    short_out = tmp_path / "shortened"
    short_report = compile_suite(shortened, short_out)
    for cell in short_report["cells"]:
        path = short_out / cell["cell_id"] / "tasks" / cell["task_name"] / "000/episode_metadata.json"
        metadata = json.loads(path.read_text())
        data = metadata["task_data"]
        original = records[cell["cell_id"]]
        expected = copy.deepcopy(original)
        if cell["initial_progress"] == "preplaced":
            expected["instruction"] = shortened["preplaced_instruction"]
        assert data == expected
        assert metadata["language_instruction"] == data["instruction"]
    with pytest.raises(FileExistsError):
        compile_suite(config, out)
    installed = install_suite(out, tmp_path / "genmanip")
    assert len(installed["installed"]) == 4
    with pytest.raises(FileExistsError):
        install_suite(out, tmp_path / "genmanip")
    cell = report["cells"][0]
    (out / cell["cell_id"] / "tasks" / cell["task_name"] / "000/meta_info.pkl").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Compiled cell changed"):
        install_suite(out, tmp_path / "other-genmanip")
    blob.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        compile_suite(config, tmp_path / "other")


@pytest.fixture
def build_config(tmp_path, source):
    blob = tmp_path / 'source.usd'
    blob.write_bytes(b'retained')
    blob.with_suffix('.usda').write_text('#usda 1.0\ndef Xform "World" { def "_scene" ( prepend payload = @./source.usd@ ) {} }')
    source.update(metadata={'path': str(blob), 'sha256': digest(blob)},
                  database={'path': str(blob), 'sha256': digest(blob)})
    layout = tmp_path / 'layout.json'
    layout.write_text(json.dumps(source))
    task = tmp_path / 'task.yml'
    task.write_text(yaml.safe_dump({'evaluation_configs': [{'num_steps': 5000}]}))
    return {'schema': 'ebench-native-intervention-build/v1', 'source_layout': str(layout),
            'source_task_config': str(task), 'base_scene': str(blob), 'base_scene_sha256': digest(blob),
            'overlays': {k: {'path': str(blob), 'sha256': digest(blob)} for k in ('control', 'wide')}}


def test_bad_usd_asset_path_is_rejected_before_output_creation(tmp_path, build_config):
    bad = tmp_path / 'unsupported@overlay.usda'
    bad.write_bytes(b'overlay')
    build_config['overlays']['control'] = {'path': str(bad), 'sha256': digest(bad)}
    out = tmp_path / 'invalid-suite'
    with pytest.raises(ValueError, match='Unsupported USD asset path'):
        compile_suite(build_config, out)
    assert not out.exists()


@pytest.mark.parametrize('scene_variants', [True, False])
def test_initial_metadata_only_never_supplies_demonstration_endpoints(tmp_path, build_config, scene_variants):
    from pathlib import Path
    source_path = Path(build_config['source_layout'])
    source = json.loads(source_path.read_text())
    source.update(source_kind='source_initial_metadata_only', objects={})
    del source['database']
    source_path.write_text(json.dumps(source))
    if scene_variants:
        build_config.update(schema='ebench-native-scene-variants-build/v1', base_default_prim='root', task_prefix='metadata')
        report = compile_suite(build_config, tmp_path/'suite')
        assert report['source_kind'] == 'source_initial_metadata_only'
        assert all(c['initial_progress'] == 'full' for c in report['cells'])
    else:
        with pytest.raises(ValueError, match='demonstration endpoints'):
            compile_suite(build_config, tmp_path/'suite')
        assert not (tmp_path/'suite').exists()


def test_initial_metadata_source_hash_is_still_required(tmp_path, build_config):
    from pathlib import Path
    source_path = Path(build_config['source_layout'])
    source = json.loads(source_path.read_text())
    source.update(source_kind='source_initial_metadata_only', objects={})
    del source['database']
    source['metadata']['sha256'] = '0'*64
    source_path.write_text(json.dumps(source))
    build_config.update(schema='ebench-native-scene-variants-build/v1', base_default_prim='root', task_prefix='metadata')
    with pytest.raises(ValueError, match='Source metadata changed'):
        compile_suite(build_config, tmp_path/'suite')
    assert not (tmp_path/'suite').exists()


def test_install_rechecks_source_entrypoint_before_writing_tasks(tmp_path, build_config):
    from pathlib import Path
    out = tmp_path / 'suite'
    compile_suite(build_config, out)
    Path(build_config['base_scene']).with_suffix('.usda').write_text('# changed wrapper\n')
    destination = tmp_path / 'runtime'
    with pytest.raises(ValueError, match='Base entrypoint changed'):
        install_suite(out, destination)
    assert not destination.exists()


def test_geometry_only_suite_preserves_non_dish_task_and_registers(tmp_path, build_config):
    from pathlib import Path
    config = copy.deepcopy(build_config)
    config.update(schema='ebench-native-scene-variants-build/v1', task_prefix='gear_r3',
                  base_default_prim='Root')
    config['overlays']['leadin'] = config['overlays'].pop('wide')
    source_path = Path(config['source_layout'])
    source = json.loads(source_path.read_text())
    source['task_data'] = {'instruction': 'Install the gear.', 'initial_layout': {'04': {'x': 1}},
                           'goal': [[{'condition_type': 'is_coupling', 'target': '04'}]]}
    source['objects'] = {}
    source_path.write_text(json.dumps(source))
    out = tmp_path / 'geometry-only'
    report = compile_suite(config, out)
    assert len(report['cells']) == 2
    for cell in report['cells']:
        metadata = json.loads((Path(cell['task_directory'])/'000/episode_metadata.json').read_text())
        assert metadata['task_data'] == source['task_data']
        assert cell['changed_initial_objects'] == []
        assert cell['initial_progress'] == 'full'
        assert 'defaultPrim = "Root"' in Path(cell['scene']).read_text()
    assert len(install_suite(out, tmp_path/'runtime')['installed']) == 2
    config['preplaced_instruction'] = 'Altered instruction'
    with pytest.raises(ValueError, match='preserves'):
        compile_suite(config, tmp_path/'invalid')


def test_pose_variants_are_paired_and_cannot_edit_asset_or_goal(tmp_path, build_config):
    from pathlib import Path
    config = copy.deepcopy(build_config)
    config.update(schema='ebench-native-scene-variants-build/v1', task_prefix='poses',
                  base_default_prim='root', layout_variants=[
                      {'id': 'p1', 'overrides': {'spoon': {'position': [.1, .2, .3]}}},
                      {'id': 'p2', 'overrides': {'spoon': {'position': [.2, .1, .3]}}}])
    source = json.loads(Path(config['source_layout']).read_text())['task_data']
    out = tmp_path/'poses'
    report = compile_suite(config, out)
    assert len(report['cells']) == 4
    by_instance = {}
    for cell in report['cells']:
        data = json.loads((Path(cell['task_directory'])/'000/episode_metadata.json').read_text())['task_data']
        assert data['goal'] == source['goal'] and data['instruction'] == source['instruction']
        assert cell['changed_initial_objects'] == ['spoon']
        by_instance.setdefault(cell['layout_variant'], []).append(data)
    assert all(pair[0] == pair[1] for pair in by_instance.values())
    assert len(install_suite(out, tmp_path/'runtime')['installed']) == 4
    config['layout_variants'][0]['overrides']['spoon']['path'] = 'replacement.usd'
    with pytest.raises(ValueError, match='pose fields'):
        compile_suite(config, tmp_path/'invalid_pose')
    assert not (tmp_path/'invalid_pose').exists()


def test_existing_scene_pose_sync_matches_metadata_world_frame(tmp_path, build_config):
    from pathlib import Path
    pytest.importorskip('pxr')
    from pxr import Usd, UsdGeom, UsdPhysics

    blob = Path(build_config['base_scene'])
    stage = Usd.Stage.CreateInMemory()
    parent = UsdGeom.Xform.Define(stage, '/root')
    parent.AddTranslateOp().Set((9, 8, 7))
    stage.SetDefaultPrim(parent.GetPrim())
    body = UsdGeom.Xform.Define(stage, '/root/obj_spoon')
    UsdPhysics.MassAPI.Apply(body.GetPrim()).CreateMassAttr(2.)
    child = UsdGeom.Cube.Define(stage, '/root/obj_spoon/mesh')
    child.AddTranslateOp().Set((1, 0, 0))
    stage.GetRootLayer().Export(str(blob))
    source_path = Path(build_config['source_layout'])
    source = json.loads(source_path.read_text())
    for key in ('metadata', 'database'):
        source[key]['sha256'] = digest(blob)
    source_path.write_text(json.dumps(source))
    config = copy.deepcopy(build_config)
    config.update(schema='ebench-native-scene-variants-build/v1', task_prefix='sync',
                  base_default_prim='root', base_scene_sha256=digest(blob),
                  initial_scene_pose_objects=['spoon'], layout_variants=[{
                      'id': 'p1', 'overrides': {'spoon': {'position': [.1, .2, .3],
                          'orientation': [2**-.5, 0, 0, 2**-.5]}}}])
    for ref in config['overlays'].values():
        ref['sha256'] = digest(blob)
    original_bytes = blob.read_bytes()
    result = compile_suite(config, tmp_path/'synced')
    for cell in result['cells']:
        composed = Usd.Stage.Open(cell['scene'])
        cache = UsdGeom.XformCache()
        p = composed.GetPrimAtPath('/root/obj_spoon')
        assert tuple(cache.GetLocalToWorldTransform(p).ExtractTranslation()) == pytest.approx((.1,.2,.3))
        assert tuple(cache.GetLocalToWorldTransform(composed.GetPrimAtPath('/root/obj_spoon/mesh')).ExtractTranslation()) == pytest.approx((.1,1.2,.3))
        assert p.GetAttribute('physics:mass').Get() == 2.
        assert cell['initial_scene_pose_objects'] == ['spoon']
    assert blob.read_bytes() == original_bytes


@pytest.mark.parametrize('change', ['spawned', 'articulation', 'zero_scale'])
def test_scene_pose_sync_rejects_unsupported_source_before_writing(tmp_path, build_config, change):
    from pathlib import Path
    source_path = Path(build_config['source_layout'])
    source = json.loads(source_path.read_text())
    pose = source['task_data']['initial_layout']['spoon']
    if change == 'spawned':
        pose['path'] = 'asset.usd'
    elif change == 'articulation':
        pose['is_articulation_part'] = True
    else:
        pose['scale'] = [0, 1, 1]
    source_path.write_text(json.dumps(source))
    config = copy.deepcopy(build_config)
    config.update(schema='ebench-native-scene-variants-build/v1', task_prefix='invalid_sync',
                  base_default_prim='root', initial_scene_pose_objects=['spoon'])
    out = tmp_path/'invalid-sync'
    with pytest.raises(ValueError, match='[Ii]nitial scene pose'):
        compile_suite(config, out)
    assert not out.exists()


@pytest.mark.parametrize('author_units', [True, False])
def test_opt_in_preserves_source_stage_metadata(tmp_path, source, author_units):
    Usd = pytest.importorskip('pxr.Usd')
    blob = tmp_path / 'source.usd'
    blob.write_text('''#usda 1.0
(
 defaultPrim = "root"
 metersPerUnit = 0.01
 upAxis = "Y"
 customLayerData = { dictionary renderSettings = { double exposure = 2 } }
)
def Xform "root" {}
''')
    if not author_units:
        blob.write_text(blob.read_text().replace(' metersPerUnit = 0.01\n', ''))
    blob.with_suffix('.usda').write_text('#usda 1.0\ndef Xform "World" (prepend payload = @./source.usd@) {}')
    source.update(metadata={'path': str(blob), 'sha256': digest(blob)},
                  database={'path': str(blob), 'sha256': digest(blob)})
    layout = tmp_path / 'layout.json'
    layout.write_text(json.dumps(source))
    task = tmp_path / 'task.yml'
    task.write_text(yaml.safe_dump({'evaluation_configs': [{'num_steps': 5000}]}))
    config = {'schema': 'ebench-native-intervention-build/v1', 'source_layout': str(layout),
              'source_task_config': str(task), 'base_scene': str(blob),
              'base_scene_sha256': digest(blob), 'preserve_source_stage_metadata': True,
              'overlays': {k: {'path': str(blob), 'sha256': digest(blob)} for k in ['control', 'wide']}}
    report = compile_suite(config, tmp_path / 'suite')
    for cell in report['cells']:
        stage = Usd.Stage.Open(cell['scene'])
        assert stage.HasAuthoredMetadata('metersPerUnit') is author_units
        if author_units:
            assert stage.GetMetadata('metersPerUnit') == 0.01
        assert stage.GetMetadata('upAxis') == 'Y'
        assert stage.GetMetadata('customLayerData')['renderSettings']['exposure'] == 2
    assert report['source_stage_metadata_preserved'] is True
