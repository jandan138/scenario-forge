from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BINDINGS_PATH = (
    ROOT
    / "configs/source_bindings/scientific_workbench_glass_material_v2_20260818.yaml"
)
SCRIPT_PATH = ROOT / "scripts/export_scientific_workbench_glass_material_v2.py"
RENDER_SCRIPT_PATH = (
    ROOT / "scripts/ebench/render_scientific_workbench_glass_material_v2.py"
)
EXPECTED_IDS = {
    "scientific_workbench_graduated_cylinder_250ml_glass_v2",
    "scientific_workbench_beaker_325ml_glass_v2",
    "scientific_workbench_flat_bottom_flask_250ml_29_42_glass_v2",
    "scientific_workbench_beaker_dynamic_glass_v2",
    "scientific_workbench_reagent_bottle_90x55_glass_v2",
    "scientific_workbench_erlenmeyer_flask_250ml_90x35_glass_v2",
}


def test_glass_v2_source_bindings_publish_six_independent_asset_packages() -> None:
    payload = yaml.safe_load(BINDINGS_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scenario-source-bindings/v0.5"
    assert set(payload["bindings"]) == EXPECTED_IDS
    for asset_id, binding in payload["bindings"].items():
        assert binding["resolver"] == "local_usd"
        assert binding["role"] == "rigid_object_unqualified_task_instance"
        package_name = asset_id.removeprefix("scientific_workbench_")
        assert binding["source_usd"].endswith(f"/{package_name}/asset.usd")
        assert binding["source_uri"] == f"convertasset://{asset_id}"
        assert binding["expected_sha256"] == (
            "sha256:0dc32192eef92da87ec37f0d959eb9beab638587148c081d7febefc6cb404952"
        )


def test_glass_v2_export_script_lists_the_same_six_packages() -> None:
    spec = importlib.util.spec_from_file_location("glass_v2_export", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {path.name for path in module.PACKAGES} == {
        asset_id.removeprefix("scientific_workbench_") for asset_id in EXPECTED_IDS
    }


def test_glass_v2_comparison_renderer_covers_the_same_six_assets() -> None:
    spec = importlib.util.spec_from_file_location("glass_v2_render", RENDER_SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {asset["package_name"] for asset in module.ASSETS} == {
        asset_id.removeprefix("scientific_workbench_") for asset_id in EXPECTED_IDS
    }
    assert all("before" in asset and "after" in asset for asset in module.ASSETS)
