from __future__ import annotations

from pathlib import Path

from scenario_forge.generation.glass_material_evidence import (
    REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS,
    build_evidence_scene,
)


def _asset(path: Path, prim: str) -> None:
    path.write_text(
        f'#usda 1.0\n(defaultPrim = "World" metersPerUnit = 1 upAxis = "Z")\n'
        f'def Xform "World" {{ def Xform "{prim}" {{}} }}\n',
        encoding="utf-8",
    )


def test_evidence_scene_uses_real_room_table_and_one_glass_asset(tmp_path: Path) -> None:
    room = tmp_path / "room.usda"
    table = tmp_path / "table.usda"
    asset = tmp_path / "asset.usda"
    _asset(room, "Room")
    _asset(table, "table")
    _asset(asset, "Beaker")
    output = tmp_path / "scene.usda"

    build_evidence_scene(
        output_path=output,
        room_usd=room,
        table_usd=table,
        asset_usd=asset,
        asset_prim_path="/World/Beaker",
        object_height_m=0.755,
    )

    text = output.read_text(encoding="utf-8")
    assert 'def Xform "room"' in text
    assert 'def Xform "table"' in text
    assert 'def Xform "obj_glass"' in text
    assert 'def DomeLight "EvidenceDome"' in text
    assert str(room.resolve()) in text
    assert str(table.resolve()) in text
    assert str(asset.resolve()) in text
    assert "inputs:glass_ior" not in text
    assert 'over "Body"' not in text
    assert "__aan_static_support_proxy" not in text
    assert "EvidenceTableTop" not in text
    assert "UsdPreviewSurface" not in text


def test_evidence_scene_overlays_reagent_bottle_omniglass_on_existing_shader(
    tmp_path: Path,
) -> None:
    room = tmp_path / "room.usda"
    table = tmp_path / "table.usda"
    asset = tmp_path / "asset.usda"
    _asset(room, "Room")
    _asset(table, "table")
    _asset(asset, "Beaker")
    output = tmp_path / "scene.usda"

    build_evidence_scene(
        output_path=output,
        room_usd=room,
        table_usd=table,
        asset_usd=asset,
        asset_prim_path="/World/Beaker",
        object_height_m=0.755,
        mdl_inputs=REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS,
    )

    text = output.read_text(encoding="utf-8")
    assert 'over "__aan_visual_materials"' in text
    assert 'over "OmniGlassRenderChangeV1"' in text
    assert "color3f inputs:glass_color = (0.99, 0.998, 1.0)" in text
    assert "color3f inputs:reflection_color = (1.0, 1.0, 1.0)" in text
    assert "float inputs:frosting_roughness = 0.035" in text
    assert "float inputs:glass_ior = 1.47" in text
    assert "bool inputs:thin_walled = false" in text
    assert "float inputs:depth = 0.002" in text
    assert REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS["glass_ior"]["value"] == 1.47
    assert REAGENT_BOTTLE_CLEAR_OMNIGLASS_INPUTS["frosting_roughness"]["value"] == 0.035


def test_evidence_scene_accepts_an_absolute_non_world_source_entry_prim(
    tmp_path: Path,
) -> None:
    room = tmp_path / "room.usda"
    table = tmp_path / "table.usda"
    asset = tmp_path / "asset.usda"
    _asset(room, "Room")
    _asset(table, "table")
    asset.write_text(
        '#usda 1.0\n(defaultPrim = "ObjectRoot" metersPerUnit = 1 upAxis = "Z")\n'
        'def Xform "ObjectRoot" {}\n',
        encoding="utf-8",
    )
    output = tmp_path / "scene.usda"

    build_evidence_scene(
        output_path=output,
        room_usd=room,
        table_usd=table,
        asset_usd=asset,
        asset_prim_path="/ObjectRoot",
        object_height_m=0.755,
    )

    assert f"@{asset.resolve()}@</ObjectRoot>" in output.read_text(encoding="utf-8")
