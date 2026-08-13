from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts/ebench/build_task02_r8_static_preview.py"
)


def _module() -> object:
    spec = importlib.util.spec_from_file_location("task02_r8_static_preview", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preview_layer_injects_robot_and_camera_without_advancing_physics() -> None:
    text = _module().preview_usda("/tmp/scene.usd", "/tmp/robot.usd", "/tmp/table.usd")
    assert "@/tmp/scene.usd@" in text
    assert "@/tmp/robot.usd@" in text
    assert "@/tmp/table.usd@" in text
    assert 'def Xform "obj_table"' in text
    assert 'def Camera "Task02R8PreviewCamera"' in text
    assert 'over "fluid_runtime"' in text
    assert 'active = false' in text
    assert "physicsScene" not in text
