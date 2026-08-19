from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BINDINGS_PATH = (
    ROOT
    / "configs/source_bindings/scientific_workbench_glass_web_standard_v2_20260819.yaml"
)
EXPORT_SCRIPT = ROOT / "scripts/export_scientific_workbench_glass_web_standard_v2.py"
RENDER_SCRIPT = (
    ROOT / "scripts/ebench/render_graduated_cylinder_glass_web_standard_v2.py"
)
CYLINDER_V1 = "graduated_cylinder_250ml_glass_web_standard_v1"
CYLINDER_V2 = "graduated_cylinder_250ml_glass_web_standard_v2"
UNCHANGED_PACKAGES = {
    "beaker_325ml_glass_web_standard_v1",
    "flat_bottom_flask_250ml_29_42_glass_web_standard_v1",
    "beaker_dynamic_glass_web_standard_v1",
    "reagent_bottle_90x55_original_simready",
    "erlenmeyer_flask_250ml_90x35_original_simready",
}


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v2_binding_selects_the_new_cylinder_and_preserves_other_packages() -> None:
    payload = yaml.safe_load(BINDINGS_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scenario-source-bindings/v0.5"
    bindings = payload["bindings"]
    assert len(bindings) == 6
    cylinder = bindings[
        "scientific_workbench_graduated_cylinder_250ml_glass_web_standard_v2"
    ]
    assert cylinder["source_usd"].endswith(f"/{CYLINDER_V2}/asset.usd")
    assert cylinder["root_prim_path"] == "/World/GraduatedCylinder250ml"
    assert cylinder["source_uri"].endswith("glass_web_standard_v2")
    package_names = {Path(binding["source_usd"]).parent.name for binding in bindings.values()}
    assert package_names == {CYLINDER_V2, *UNCHANGED_PACKAGES}


def test_v2_export_and_evidence_use_independent_output_paths() -> None:
    exporter = _load(EXPORT_SCRIPT, "glass_web_standard_v2_export")
    renderer = _load(RENDER_SCRIPT, "graduated_cylinder_glass_web_standard_v2_render")
    assert exporter.ARCHIVE_ID == "scientific_workbench_glass_web_standard_v2"
    assert exporter.OUTPUT_ROOT.name == "handoff"
    assert exporter.OUTPUT_ROOT.parent.name == "scientific_workbench_glass_web_standard_v2_20260819"
    assert {path.name for path in exporter.PACKAGES} == {CYLINDER_V2, *UNCHANGED_PACKAGES}
    assert renderer.REFERENCE_PACKAGE.name == CYLINDER_V1
    assert renderer.CANDIDATE_PACKAGE.name == CYLINDER_V2
    assert renderer.MANIFEST_SCHEMA == (
        "scenario-forge-graduated-cylinder-connector-comparison/v1"
    )
    assert "round base connector" in renderer.STANDARD
    assert renderer.OUTPUT.parent.name == "evidence"
    assert renderer.OUTPUT.parent.parent.name == (
        "scientific_workbench_glass_web_standard_v2_20260819"
    )
