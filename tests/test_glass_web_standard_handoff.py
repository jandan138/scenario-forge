from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BINDINGS_PATH = (
    ROOT
    / "configs/source_bindings/scientific_workbench_glass_web_standard_20260819.yaml"
)
EXPORT_SCRIPT = ROOT / "scripts/export_scientific_workbench_glass_web_standard.py"
RENDER_SCRIPT = (
    ROOT / "scripts/ebench/render_scientific_workbench_glass_web_standard.py"
)
EXPECTED = {
    "scientific_workbench_graduated_cylinder_250ml_glass_web_standard_v1": (
        "graduated_cylinder_250ml_glass_web_standard_v1",
        "/World/GraduatedCylinder250ml",
        "sha256:0dc32192eef92da87ec37f0d959eb9beab638587148c081d7febefc6cb404952",
    ),
    "scientific_workbench_beaker_325ml_glass_web_standard_v1": (
        "beaker_325ml_glass_web_standard_v1",
        "/World/Beaker325ml",
        "sha256:0dc32192eef92da87ec37f0d959eb9beab638587148c081d7febefc6cb404952",
    ),
    "scientific_workbench_flat_bottom_flask_250ml_29_42_glass_web_standard_v1": (
        "flat_bottom_flask_250ml_29_42_glass_web_standard_v1",
        "/World/FlatBottomFlask2942",
        "sha256:0dc32192eef92da87ec37f0d959eb9beab638587148c081d7febefc6cb404952",
    ),
    "scientific_workbench_beaker_dynamic_glass_web_standard_v1": (
        "beaker_dynamic_glass_web_standard_v1",
        "/World/Beaker",
        "sha256:0dc32192eef92da87ec37f0d959eb9beab638587148c081d7febefc6cb404952",
    ),
    "scientific_workbench_reagent_bottle_90x55_original_simready": (
        "reagent_bottle_90x55_original_simready",
        "/ObjectRoot",
        "sha256:159e6014bbacc622af35ac8202f4cda5703d4cf1db5a0704db1d57560d00362e",
    ),
    "scientific_workbench_erlenmeyer_flask_250ml_90x35_original_simready": (
        "erlenmeyer_flask_250ml_90x35_original_simready",
        "/ObjectRoot",
        "sha256:159e6014bbacc622af35ac8202f4cda5703d4cf1db5a0704db1d57560d00362e",
    ),
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_web_standard_bindings_publish_four_page_recipe_and_two_original_assets() -> None:
    payload = yaml.safe_load(BINDINGS_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scenario-source-bindings/v0.5"
    assert set(payload["bindings"]) == set(EXPECTED)
    for asset_id, (package_name, root_prim, expected_sha) in EXPECTED.items():
        binding = payload["bindings"][asset_id]
        assert binding["resolver"] == "local_usd"
        assert binding["role"] == "rigid_object_unqualified_task_instance"
        assert binding["source_usd"].endswith(f"/{package_name}/asset.usd")
        assert binding["root_prim_path"] == root_prim
        assert binding["expected_sha256"] == expected_sha
        assert binding["source_uri"] == f"convertasset://{asset_id}"


def test_web_standard_export_and_renderer_cover_the_same_six_packages() -> None:
    exporter = _load(EXPORT_SCRIPT, "glass_web_standard_export")
    renderer = _load(RENDER_SCRIPT, "glass_web_standard_render")
    expected_packages = {value[0] for value in EXPECTED.values()}
    assert {path.name for path in exporter.PACKAGES} == expected_packages
    assert {asset["package_name"] for asset in renderer.ASSETS} == expected_packages
    assert all("reference" in asset and "candidate" in asset for asset in renderer.ASSETS)
