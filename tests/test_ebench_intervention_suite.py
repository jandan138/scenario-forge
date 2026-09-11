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


def test_install_rechecks_source_entrypoint_before_writing_tasks(tmp_path, build_config):
    from pathlib import Path
    out = tmp_path / 'suite'
    compile_suite(build_config, out)
    Path(build_config['base_scene']).with_suffix('.usda').write_text('# changed wrapper\n')
    destination = tmp_path / 'runtime'
    with pytest.raises(ValueError, match='Base entrypoint changed'):
        install_suite(out, destination)
    assert not destination.exists()
