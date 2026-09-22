from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BINDINGS_PATH = (
    ROOT
    / "configs/source_bindings/scientific_workbench_reagent_bottle_pair_20260919.yaml"
)
BOTTLE_ID = "scientific_workbench_reagent_bottle_90x55_original_simready"
PLUG_ID = "scientific_workbench_reagent_bottle_plug_45_40_original_simready"
OVERLAY_SHA = "sha256:159e6014bbacc622af35ac8202f4cda5703d4cf1db5a0704db1d57560d00362e"


def test_reagent_bottle_pair_bindings_publish_matched_original_simready_assets() -> None:
    payload = yaml.safe_load(BINDINGS_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "scenario-source-bindings/v0.5"
    assert set(payload["bindings"]) == {BOTTLE_ID, PLUG_ID}

    bottle = payload["bindings"][BOTTLE_ID]
    plug = payload["bindings"][PLUG_ID]
    for binding, package_name in (
        (bottle, "reagent_bottle_90x55_original_simready"),
        (plug, "reagent_bottle_plug_45_40_original_simready"),
    ):
        assert binding["resolver"] == "local_usd"
        assert binding["role"] == "rigid_object_unqualified_task_instance"
        assert binding["root_prim_path"] == "/ObjectRoot"
        assert binding["expected_sha256"] == OVERLAY_SHA
        assert binding["source_usd"].endswith(f"/{package_name}/asset.usd")

    assert bottle["source_uri"] == f"convertasset://{BOTTLE_ID}"
    assert plug["source_uri"] == f"convertasset://{PLUG_ID}"
    assert "glass_web_standard_20260819" in bottle["source_usd"]
    assert "reagent_bottle_pair_20260919" in plug["source_usd"]
