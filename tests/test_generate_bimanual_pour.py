from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import generate_scientific_workbench_bimanual_pour as generator
from tests.test_scenario_package_compiler import _write_source_scene


REPO_ROOT = Path(__file__).resolve().parents[1]


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
    assert 'over "Cabinet_02" (' not in scene_text
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
