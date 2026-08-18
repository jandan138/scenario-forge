from __future__ import annotations

from pathlib import Path

from scenario_forge.generation.glass_material_evidence import build_evidence_scene


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
