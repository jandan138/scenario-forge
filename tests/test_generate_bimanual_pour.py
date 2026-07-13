from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts import generate_scientific_workbench_bimanual_pour as generator
from tests.test_scenario_package_compiler import _write_source_scene


REPO_ROOT = Path(__file__).resolve().parents[1]

_TASK_READY_INACTIVE_PRIMS = [
    "/World/Cube",
    "/World/lounge_booth_table",
    "/World/beaker1",
    "/World/beaker2",
    "/World/beaker3",
    "/World/conical_bottle01",
    "/World/conical_bottle02",
    "/World/conical_bottle04",
    "/World/target_plat",
    "/World/target_plat2",
    "/World/DryingBox_01",
    "/World/DryingBox_02",
    "/World/DryingBox_04",
    "/World/MuffleFurnace",
    "/World/Cabinet_01",
    "/World/Cabinet_02",
]


def _write_task_ready_source_scene(root: Path) -> Path:
    source = _write_source_scene(root)
    text = source.read_text(encoding="utf-8")
    insertion = "\n".join(
        f'    def Xform "{name}" {{}}'
        for name in [
            *(Path(path).name for path in _TASK_READY_INACTIVE_PRIMS),
            "DryingBox_03",
            "CylinderLight",
            "GroundPlane",
        ]
    )
    closing_brace = text.rfind("\n}")
    assert closing_brace > 0
    source.write_text(
        text[:closing_brace] + "\n" + insertion + text[closing_brace:],
        encoding="utf-8",
    )
    return source


def test_golden_generator_static_only_skips_runtime_and_excludes_upstream_reports(
    tmp_path: Path,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    reports = source_usd.parent / "_reports"
    reports.mkdir()
    (reports / "old.png").write_bytes(b"old render")
    output = tmp_path / "output"

    result = generator.main(
        [
            "--source-usd",
            str(source_usd),
            "--out",
            str(output),
            "--static-only",
        ]
    )

    assert result == 0
    collected = output / "adapters/ebench/genmanip"
    assert (collected / "evidence/render_request.yaml").is_file()
    assert not (output / "assets/scientific_workbench_environment/_reports").exists()
    assert not (collected / "evidence/initial_scene/visual_ready_gate.yaml").exists()

    task_config = yaml.safe_load(
        (collected / "tasks/config.yaml").read_text(encoding="utf-8")
    )
    assert task_config["evaluation_configs"][0]["robots"] == [
        {"type": "manip/lift2/R5a", "position": [-1.02, 0.0, 0.31]}
    ]
    episode = json.loads(
        (
            collected
            / "tasks/scenario_forge/scientific_workbench_bimanual_pour/000/episode_metadata.json"
        ).read_text(encoding="utf-8")
    )
    assert episode["task_data"]["initial_layout"]["lift2"]["position"] == [
        -1.02,
        0.0,
        0.31,
    ]
    initial_layout = episode["task_data"]["initial_layout"]
    assert initial_layout["00000000000000000000000000000000"]["scale"] == [
        0.003,
        0.0035,
        0.004,
    ]
    assert initial_layout["obj_conical_bottle03"]["position"] == [-0.25, 0.16, 0.81]
    assert initial_layout["obj_graduated_cylinder_03"]["position"] == [
        -0.25,
        -0.16,
        0.81,
    ]
    scene_text = (
        collected
        / "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/scene.usda"
    ).read_text(encoding="utf-8")
    assert 'over "Cube" (' in scene_text
    assert "active = false" in scene_text
    assert "double3 xformOp:translate = (-9.5, -43.3, 0)" in scene_text
    assert "quatd xformOp:orient = (0.7933533, 0, 0, 0.6087614)" in scene_text
    assert 'over "Cabinet_02" (' in scene_text
    assert 'over "CylinderLight"' in scene_text
    assert 'over "GroundPlane"' in scene_text


def test_golden_generator_default_build_runs_genmanip_preview(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_usd = _write_source_scene(tmp_path)
    output = tmp_path / "output"
    isaac_python = tmp_path / "isaac python"
    renderer_script = tmp_path / "renderer.py"
    genmanip_root = tmp_path / "GenManip"
    isaac_python.write_text("", encoding="utf-8")
    renderer_script.write_text("", encoding="utf-8")
    genmanip_root.mkdir()
    calls: list[tuple[Path, Path, Path, Path, float]] = []

    def fake_run(
        collected_root: Path,
        runtime_python: Path,
        runtime_script: Path,
        runtime_root: Path,
        *,
        timeout_seconds: float,
    ) -> object:
        calls.append(
            (
                collected_root,
                runtime_python,
                runtime_script,
                runtime_root,
                timeout_seconds,
            )
        )
        return object()

    monkeypatch.setattr(generator, "run_genmanip_initial_preview", fake_run)

    result = generator.main(
        [
            "--source-usd",
            str(source_usd),
            "--out",
            str(output),
            "--isaac-python",
            str(isaac_python),
            "--renderer-script",
            str(renderer_script),
            "--genmanip-root",
            str(genmanip_root),
            "--preview-timeout",
            "321",
        ]
    )

    assert result == 0
    assert calls == [
        (
            output / "adapters/ebench/genmanip",
            isaac_python,
            renderer_script,
            genmanip_root,
            321.0,
        )
    ]


def test_golden_task_ready_overlay_removes_unrelated_dynamic_context_in_both_scenes(
    tmp_path: Path,
) -> None:
    Usd = pytest.importorskip("pxr.Usd")
    source_usd = _write_task_ready_source_scene(tmp_path)
    output = tmp_path / "output"

    result = generator.main(
        [
            "--source-usd",
            str(source_usd),
            "--out",
            str(output),
            "--static-only",
        ]
    )

    assert result == 0
    scenario = yaml.safe_load((output / "scenario.yaml").read_text(encoding="utf-8"))
    assert scenario["scene"]["inactive_prim_paths"] == _TASK_READY_INACTIVE_PRIMS

    portable = Usd.Stage.Open(str(output / "scene/main.usda"))
    assert portable
    for path in _TASK_READY_INACTIVE_PRIMS:
        assert not portable.GetPrimAtPath(path).IsActive(), path
    for path in [
        "/World/table",
        "/World/conical_bottle03",
        "/World/graduated_cylinder_03",
        "/World/DryingBox_03",
        "/World/CylinderLight",
        "/World/GroundPlane",
    ]:
        assert portable.GetPrimAtPath(path).IsActive(), path

    collected = Usd.Stage.Open(
        str(
            output
            / "adapters/ebench/genmanip/assets/scene_usds/scenario_forge/"
            "scientific_workbench_bimanual_pour/scene.usda"
        )
    )
    assert collected
    room = "/World/scientific_workbench_bimanual_pour/room"
    for path in _TASK_READY_INACTIVE_PRIMS:
        assert not collected.GetPrimAtPath(room + path.removeprefix("/World")).IsActive(), path
    for path in [
        f"{room}/DryingBox_03",
        f"{room}/CylinderLight",
        f"{room}/GroundPlane",
        "/World/scientific_workbench_bimanual_pour/obj_table",
        "/World/scientific_workbench_bimanual_pour/obj_obj_conical_bottle03",
        "/World/scientific_workbench_bimanual_pour/obj_obj_graduated_cylinder_03",
    ]:
        assert collected.GetPrimAtPath(path).IsActive(), path
    active_physics_scenes = [
        prim.GetPath().pathString
        for prim in collected.Traverse()
        if prim.IsActive() and prim.GetTypeName() == "PhysicsScene"
    ]
    assert active_physics_scenes == ["/physicsScene"]


def test_runbook_stages_canary_in_a_private_genmanip_workspace() -> None:
    runbook = (
        REPO_ROOT / "docs/operations/generate-bimanual-pour-package.md"
    ).read_text(encoding="utf-8")

    assert "LABUTOPIA_ROOT=" in runbook
    assert "GENMANIP_SOURCE=" in runbook
    assert "CANARY_ROOT=" in runbook
    assert 'git -C "$GENMANIP_SOURCE" archive HEAD' in runbook
    assert 'rm -rf "$target"' not in runbook
    assert "shared EBench asset directory" in runbook
