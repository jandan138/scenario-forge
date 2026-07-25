from __future__ import annotations

import ast
import importlib.util
import json
import math
from pathlib import Path
import subprocess
from typing import Any

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER = (
    REPO_ROOT / "scripts/ebench/render_scientific_environment_previews.py"
)


def test_preview_renderer_defers_simulator_imports() -> None:
    tree = ast.parse(RENDERER.read_text(encoding="utf-8"))
    top_level_imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.add(node.module)
    forbidden = {
        name
        for name in top_level_imports
        if name == "pxr"
        or name.startswith("pxr.")
        or name == "omni"
        or name.startswith("omni.")
        or name == "isaacsim"
        or name.startswith("isaacsim.")
    }
    assert forbidden == set()


def test_camera_plan_preserves_authored_view_and_adds_eye_level_orbits() -> None:
    module = _load_renderer_module()
    views = module.plan_camera_views(
        position=(0.0, -5.0, 5.0),
        target=(0.0, 0.0, 0.0),
    )

    assert [view["name"] for view in views] == [
        "authored",
        "eye_left",
        "eye_right",
    ]
    assert views[0]["position"] == pytest.approx([0.0, -5.0, 5.0])
    assert views[0]["target"] == pytest.approx([0.0, 0.0, 0.0])
    for view in views[1:]:
        offset = [
            view["position"][index] - view["target"][index]
            for index in range(3)
        ]
        distance = math.sqrt(sum(value * value for value in offset))
        elevation = math.degrees(math.asin(offset[2] / distance))
        assert elevation == pytest.approx(18.0)
        assert distance == pytest.approx(math.sqrt(50.0) * 1.1)


def test_batch_selection_accepts_hash_bound_pass_and_warn_retake_items(
    tmp_path: Path,
) -> None:
    catalog = {
        "catalog_digest": "a" * 64,
        "entries": [
            {
                "candidate_id": "scientific_environment_001",
                "source_usd": "/dataset/Labs/lab_001/lab_001.usd",
                "source_sha256": "1" * 64,
                "thumbnail_sha256": "2" * 64,
            },
            {
                "candidate_id": "scientific_environment_003",
                "source_usd": "/dataset/Labs/lab_003/lab_003.usd",
                "source_sha256": "3" * 64,
                "thumbnail_sha256": "4" * 64,
            },
            {
                "candidate_id": "scientific_environment_005",
                "source_usd": "/dataset/Labs/lab_005/lab_005.usd",
                "source_sha256": "5" * 64,
                "thumbnail_sha256": "6" * 64,
            },
        ],
    }
    reviews = {
        "catalog_digest": "a" * 64,
        "reviews": {
            "scientific_environment_001": {
                "selection_rank": 2,
                "status": "WARN",
                "thumbnail_sha256": "2" * 64,
                "visible_evidence": "Useful room; needs a wider view.",
            },
            "scientific_environment_003": {
                "selection_rank": 1,
                "status": "PASS",
                "thumbnail_sha256": "4" * 64,
                "visible_evidence": "Complete wet laboratory.",
            },
            "scientific_environment_005": {
                "selection_rank": 3,
                "status": "FAIL",
                "thumbnail_sha256": "6" * 64,
                "visible_evidence": "Wrong room category.",
            },
        },
    }
    catalog_path = tmp_path / "catalog.json"
    review_path = tmp_path / "reviews.yaml"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    review_path.write_text(yaml.safe_dump(reviews), encoding="utf-8")
    module = _load_renderer_module()

    selected = module.load_retake_selection(
        catalog_path=catalog_path,
        review_path=review_path,
        max_scenes=10,
    )

    assert [item["candidate_id"] for item in selected] == [
        "scientific_environment_003",
        "scientific_environment_001",
    ]
    assert [item["review_status"] for item in selected] == ["PASS", "WARN"]


def test_batch_selection_rejects_stale_catalog_digest(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.json"
    review_path = tmp_path / "reviews.yaml"
    catalog_path.write_text(
        json.dumps({"catalog_digest": "a" * 64, "entries": []}),
        encoding="utf-8",
    )
    review_path.write_text(
        yaml.safe_dump({"catalog_digest": "b" * 64, "reviews": {}}),
        encoding="utf-8",
    )
    module = _load_renderer_module()

    with pytest.raises(ValueError, match="catalog digest"):
        module.load_retake_selection(
            catalog_path=catalog_path,
            review_path=review_path,
            max_scenes=10,
        )


def test_timeout_output_handles_subprocess_bytes() -> None:
    module = _load_renderer_module()
    timeout = subprocess.TimeoutExpired(
        cmd=["isaac-python"],
        timeout=12.0,
        output=b"partial worker output\n",
    )

    assert module._format_timeout_output(timeout, 12.0) == (
        "partial worker output\n"
        "preview worker timed out after 12.0s\n"
    )


def test_runtime_version_gate_requires_isaac_sim_41() -> None:
    module = _load_renderer_module()

    assert module._is_supported_isaac_sim_version("4.1.0.0")
    assert module._is_supported_isaac_sim_version("4.1.1")
    assert not module._is_supported_isaac_sim_version("4.5.0.0-rc.7")
    assert not module._is_supported_isaac_sim_version("unknown")


def _load_renderer_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "scenario_forge_scientific_environment_preview_renderer",
        RENDERER,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
