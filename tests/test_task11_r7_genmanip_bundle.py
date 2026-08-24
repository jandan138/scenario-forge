from pathlib import Path
import ast


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/build_task11_r7_genmanip_validation_bundle.py"


def test_bundle_wraps_exact_r7_scene_without_reauthoring_asset_physics():
    source = SCRIPT.read_text(encoding="utf-8")
    ast.parse(source)
    assert "scientific_workbench_task11_vr_r7_20260825" in source
    assert 'AddReference(str(scene), "/World")' in source
    assert 'Sdf.CopySpec(source_flat, "/World/physicsScene"' in source
    assert '"canonical_task": True' in source
    assert '"post_initialization_object_transform_writes_allowed": False' in source
    assert "staticFriction" not in source
    assert "dynamicFriction" not in source
