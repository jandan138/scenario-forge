from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
import struct
import zlib

import pytest
import yaml

from scenario_forge.adapters.ebench.genmanip import export_genmanip_collected_package
from scenario_forge.adapters.ebench.preview import (
    GenManipPreviewError,
    compute_preview_input_digest,
    run_genmanip_initial_preview,
    validate_genmanip_preview_evidence,
    write_genmanip_preview_request,
)
from tests.test_ebench_genmanip_export import _build_package


_TABLE_RUNTIME_ID = "00000000000000000000000000000000"
_TASK_RUNTIME_IDS = ["obj_conical_bottle03", "obj_graduated_cylinder_03"]


def test_export_writes_evidence_only_preview_request_without_changing_policy_cameras(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir

    request_path = collected_package / "evidence" / "render_request.yaml"
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))

    assert request["schema_version"] == "scenario-forge-genmanip-preview-request/v0.1"
    assert request["package_id"] == "scientific_workbench_bimanual_pour"
    assert request["purpose"] == "evidence_only"
    assert request["affects_policy_observation"] is False
    assert request["moment"] == "post_reset_pre_action"
    assert request["camera_policy_version"] == "scenario-forge/task-anchor-fit-v6"
    assert request["input_digest"] == compute_preview_input_digest(collected_package)
    assert request["expected_runtime_ids"] == {
        "robot": "lift2",
        "table": _TABLE_RUNTIME_ID,
        "task_objects": _TASK_RUNTIME_IDS,
    }

    expected_inputs = {
        "package_manifest",
        "task_config",
        "episode_metadata",
        "scene_usd",
        "evaluation_camera",
        "source_bundle",
    }
    assert set(request["inputs"]) == expected_inputs
    for role, item in request["inputs"].items():
        relative_path = Path(item["path"])
        assert not relative_path.is_absolute()
        assert ".." not in relative_path.parts
        input_path = collected_package / relative_path
        if role == "source_bundle":
            assert input_path.is_dir()
            assert item["sha256"] == _tree_sha256(input_path)
        else:
            assert item["sha256"] == _file_sha256(input_path)

    assert set(request["views"]) == {"workspace_closeup", "scene_overview"}
    assert request["views"]["workspace_closeup"]["required_runtime_ids"] == [
        _TABLE_RUNTIME_ID,
        *_TASK_RUNTIME_IDS,
    ]
    assert request["views"]["workspace_closeup"]["anchor_runtime_ids"] == [
        "lift2_end_effectors",
        *_TASK_RUNTIME_IDS,
    ]
    assert request["views"]["workspace_closeup"]["azimuth_deg"] == -35.0
    assert request["views"]["workspace_closeup"]["elevation_deg"] == 34.0
    assert request["views"]["workspace_closeup"]["minimum_distance"] == 1.0
    assert request["views"]["scene_overview"]["required_runtime_ids"] == [
        "lift2",
        _TABLE_RUNTIME_ID,
        *_TASK_RUNTIME_IDS,
    ]
    assert request["views"]["scene_overview"]["anchor_runtime_ids"] == [
        "scene_room",
        "lift2",
        _TABLE_RUNTIME_ID,
        *_TASK_RUNTIME_IDS,
    ]
    assert request["views"]["scene_overview"]["azimuth_deg"] == -125.0
    assert request["views"]["scene_overview"]["elevation_deg"] == 38.0
    assert request["views"]["scene_overview"]["framing_margin"] == 1.05
    assert request["views"]["scene_overview"]["minimum_distance"] == 1.6

    camera_path = collected_package / request["inputs"]["evaluation_camera"]["path"]
    camera_bytes = camera_path.read_bytes()
    camera_config = yaml.safe_load(camera_bytes)
    assert set(camera_config) == {"overlook_camera"}
    assert camera_config["overlook_camera"]["prim_path"].endswith("Camera_overlook")
    assert b"workspace_closeup" not in camera_bytes
    assert b"scene_overview" not in camera_bytes
    assert b"qa_camera" not in camera_bytes.lower()


def test_preview_evidence_with_matching_digest_writes_visual_ready_gate(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    evidence_dir = _write_passing_evidence(collected_package, request)

    validate_genmanip_preview_evidence(collected_package)

    gate_path = evidence_dir / "visual_ready_gate.yaml"
    gate = _load_yaml(gate_path)
    assert gate["schema_version"] == "scenario-forge-genmanip-preview-gate/v0.1"
    assert gate["status"] == "passed"
    assert gate["package_id"] == request["package_id"]
    assert gate["input_digest"] == request["input_digest"]
    assert set(gate["views"]) == {"workspace_closeup", "scene_overview"}
    assert gate["next_stage"] == "clean_room_visual_review"
    assert gate["verification_scope"] == "structural_artifact_and_runtime_prim_presence"
    assert "on-camera visibility" in gate["claim_boundary"]
    assert "task success" in gate["claim_boundary"]


def test_preview_evidence_validation_accepts_relative_collected_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    _write_passing_evidence(collected_package, request)
    monkeypatch.chdir(collected_package.parent)

    result = validate_genmanip_preview_evidence(Path(collected_package.name))

    assert result.status == "passed"
    assert result.gate_path.is_file()


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        ("missing_image", "missing|workspace_closeup"),
        ("stale_input", "digest|sha256|hash"),
        ("stale_source_bundle", "digest|sha256|hash"),
        ("redirected_input", "input|digest|sha256|hash"),
        ("wrong_package_id", "package_id.*package manifest|package manifest.*package_id"),
        ("tampered_runtime_log", "runtime log.*sha256|runtime log.*hash"),
        ("stale_request", "request.*sha256|request.*hash"),
        ("wrong_image_hash", "sha256|hash"),
    ],
)
def test_preview_evidence_rejects_missing_stale_or_mismatched_artifacts(
    tmp_path: Path,
    corrupt: str,
    message: str,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    request = _load_yaml(collected_package / "evidence" / "render_request.yaml")
    evidence_dir = _write_passing_evidence(collected_package, request)

    if corrupt == "missing_image":
        (evidence_dir / "workspace_closeup.png").unlink()
    elif corrupt == "stale_input":
        config_path = collected_package / request["inputs"]["task_config"]["path"]
        config_path.write_text(
            config_path.read_text(encoding="utf-8") + "\n# changed after render\n",
            encoding="utf-8",
        )
    elif corrupt == "stale_source_bundle":
        source_bundle = collected_package / (
            "assets/scene_usds/scenario_forge/scientific_workbench_bimanual_pour/"
            "source_bundle/scientific_workbench_environment/scene.usda"
        )
        source_bundle.write_text(
            source_bundle.read_text(encoding="utf-8") + "\n# changed after render\n",
            encoding="utf-8",
        )
    elif corrupt == "redirected_input":
        request_path = collected_package / "evidence" / "render_request.yaml"
        redirected_request = _load_yaml(request_path)
        inputs = redirected_request["inputs"]
        assert isinstance(inputs, dict)
        scene_input = inputs["scene_usd"]
        assert isinstance(scene_input, dict)
        original_scene = collected_package / scene_input["path"]
        alternate_scene = collected_package / "alternate_scene.usda"
        alternate_scene.write_bytes(original_scene.read_bytes())
        scene_input["path"] = alternate_scene.relative_to(collected_package).as_posix()
        scene_input["sha256"] = _file_sha256(alternate_scene)
        request_path.write_text(
            yaml.safe_dump(redirected_request, sort_keys=False), encoding="utf-8"
        )
        manifest_path = evidence_dir / "render_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["request_sha256"] = _file_sha256(request_path)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif corrupt == "tampered_runtime_log":
        runtime_log = evidence_dir / "runtime.log"
        runtime_log.write_text(
            runtime_log.read_text(encoding="utf-8") + "tampered after render\n",
            encoding="utf-8",
        )
    elif corrupt == "wrong_package_id":
        request_path = collected_package / "evidence" / "render_request.yaml"
        wrong_request = _load_yaml(request_path)
        wrong_request["package_id"] = "wrong-package"
        wrong_request["input_digest"] = "sha256:" + sha256(
            json.dumps(
                {
                    "package_id": wrong_request["package_id"],
                    "inputs": wrong_request["inputs"],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        request_path.write_text(
            yaml.safe_dump(wrong_request, sort_keys=False), encoding="utf-8"
        )
        manifest_path = evidence_dir / "render_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["package_id"] = wrong_request["package_id"]
        manifest["input_digest"] = wrong_request["input_digest"]
        manifest["request_sha256"] = _file_sha256(request_path)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif corrupt == "stale_request":
        request_path = collected_package / "evidence" / "render_request.yaml"
        stale_request = _load_yaml(request_path)
        views = stale_request["views"]
        assert isinstance(views, dict)
        overview = views["scene_overview"]
        assert isinstance(overview, dict)
        overview["elevation_deg"] = 12.0
        request_path.write_text(
            yaml.safe_dump(stale_request, sort_keys=False), encoding="utf-8"
        )
    else:
        manifest_path = evidence_dir / "render_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["views"]["scene_overview"]["sha256"] = "sha256:" + ("0" * 64)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    with pytest.raises(GenManipPreviewError, match=message):
        validate_genmanip_preview_evidence(collected_package)

    assert not (evidence_dir / "visual_ready_gate.yaml").exists()


@pytest.mark.parametrize("entrypoint", ["run", "validate"])
def test_preview_entrypoints_do_not_unlink_gate_through_external_evidence_symlink(
    tmp_path: Path, entrypoint: str
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    external = tmp_path / "external-evidence"
    external.mkdir()
    external_gate = external / "visual_ready_gate.yaml"
    external_gate.write_text("owner: external\n", encoding="utf-8")
    (collected_package / "evidence" / "initial_scene").symlink_to(
        external, target_is_directory=True
    )

    with pytest.raises(GenManipPreviewError):
        if entrypoint == "run":
            run_genmanip_initial_preview(
                collected_package,
                tmp_path / "missing-isaac-python",
                tmp_path / "missing-renderer.py",
                tmp_path / "missing-genmanip",
            )
        else:
            validate_genmanip_preview_evidence(collected_package)

    assert external_gate.read_text(encoding="utf-8") == "owner: external\n"


def test_preview_request_writer_rejects_external_evidence_symlink(
    tmp_path: Path,
) -> None:
    collected_package = export_genmanip_collected_package(_build_package(tmp_path)).output_dir
    evidence = collected_package / "evidence"
    evidence.rename(collected_package / "original-evidence")
    external = tmp_path / "external-request-output"
    external.mkdir()
    evidence.symlink_to(external, target_is_directory=True)

    with pytest.raises(GenManipPreviewError, match="escapes"):
        write_genmanip_preview_request(collected_package)

    assert not (external / "render_request.yaml").exists()


def _write_passing_evidence(
    collected_package: Path,
    request: dict[str, object],
) -> Path:
    evidence_dir = collected_package / "evidence" / "initial_scene"
    evidence_dir.mkdir(parents=True)
    image_specs = {
        "workspace_closeup": (34, 89, 144),
        "scene_overview": (91, 117, 74),
    }
    views: dict[str, object] = {}
    request_views = request["views"]
    assert isinstance(request_views, dict)
    for index, (view_name, color) in enumerate(image_specs.items()):
        image_path = evidence_dir / f"{view_name}.png"
        _write_rgb_png(image_path, width=1280, height=720, color=color)
        view_request = request_views[view_name]
        assert isinstance(view_request, dict)
        views[view_name] = {
            "status": "pass",
            "image_path": image_path.name,
            "sha256": _file_sha256(image_path),
            "resolution": [1280, 720],
            "present_runtime_ids": view_request["required_runtime_ids"],
            "camera": {
                "position": [0.3 + index, -0.8, 1.4],
                "look_at": [0.3, 0.0, 0.8],
                "focal_length_mm": 24.0,
            },
        }

    runtime_log = evidence_dir / "runtime.log"
    runtime_log.write_text("GenManip initial preview render completed\n", encoding="utf-8")
    manifest = {
        "schema_version": "scenario-forge-genmanip-preview-evidence/v0.1",
        "package_id": request["package_id"],
        "input_digest": request["input_digest"],
        "request_sha256": _file_sha256(
            collected_package / "evidence" / "render_request.yaml"
        ),
        "purpose": "evidence_only",
        "moment": "post_reset_pre_action",
        "render_status": "pass",
        "runtime": {
            "engine": "Isaac Sim",
            "isaac_sim_version": "test",
            "genmanip_revision": "test",
        },
        "runtime_log_path": runtime_log.name,
        "runtime_log_sha256": _file_sha256(runtime_log),
        "runtime_log_scan": {
            "status": "pass",
            "scope": "known_blocking_material_signals",
            "scanned_streams": ["renderer_runtime_log", "subprocess_stdout", "subprocess_stderr"],
            "blocking_signal_count": 0,
            "blocking_signals": [],
        },
        "views": views,
        "claim_boundary": (
            "Initial-scene visual evidence only; not task success, policy success, "
            "physics fidelity, or liquid-transfer evidence."
        ),
    }
    (evidence_dir / "render_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence_dir


def _write_rgb_png(
    path: Path,
    *,
    width: int,
    height: int,
    color: tuple[int, int, int],
) -> None:
    row = bytes(color) * width
    pixels = (b"\x00" + row) * height
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(pixels))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _file_sha256(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _tree_sha256(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_file_sha256(path).removeprefix("sha256:")))
    return "sha256:" + digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data
