from __future__ import annotations

import ast
import importlib.util
import math
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDERER = REPO_ROOT / "scripts/ebench/render_genmanip_orbit_video.py"


def test_cinematic_orbit_starts_at_overview_and_uses_reviewed_timing() -> None:
    module = _load_renderer()
    start = (-1.535334103560508, -2.7066693223179317, 2.7727108948839714)
    target = (0.0, -0.5139849826348019, 0.6813863721602913)

    poses = module._cinematic_orbit_camera_path(
        start_position=start,
        target=target,
        fps=30,
        hold_start_seconds=0.6,
        transition_seconds=1.2,
        orbit_seconds=9.6,
        hold_end_seconds=0.6,
        orbit_degrees=220.0,
        safe_radius_m=2.0,
        safe_height_m=2.5,
    )

    assert len(poses) == 360
    assert poses[0].position == pytest.approx(start)
    assert poses[17].position == pytest.approx(start)
    assert poses[0].target == pytest.approx(target)
    assert [pose.phase for pose in poses].count("opening_hold") == 18
    assert [pose.phase for pose in poses].count("safe_transition") == 36
    assert [pose.phase for pose in poses].count("room_orbit") == 288
    assert [pose.phase for pose in poses].count("closing_hold") == 18
    assert poses[-1].position == pytest.approx(poses[-18].position)


def test_cinematic_orbit_stays_inside_reviewed_room_and_turns_220_degrees() -> None:
    module = _load_renderer()
    target = (0.0, -0.5139849826348019, 0.6813863721602913)
    poses = module._cinematic_orbit_camera_path(
        start_position=(-1.535334103560508, -2.7066693223179317, 2.7727108948839714),
        target=target,
        fps=30,
        hold_start_seconds=0.6,
        transition_seconds=1.2,
        orbit_seconds=9.6,
        hold_end_seconds=0.6,
        orbit_degrees=220.0,
        safe_radius_m=2.0,
        safe_height_m=2.5,
    )

    room_min = (-4.327117608915344, -3.156905550663948, -0.019999999552965164)
    room_max = (3.9028825293674303, 3.1430945506639496, 2.8000000417232513)
    for pose in poses:
        assert all(math.isfinite(value) for value in (*pose.position, *pose.target))
        assert room_min[0] < pose.position[0] < room_max[0]
        assert room_min[1] < pose.position[1] < room_max[1]
        assert room_min[2] < pose.position[2] < room_max[2]

    orbit = [pose for pose in poses if pose.phase == "room_orbit"]
    start_angle = math.atan2(
        poses[17].position[1] - target[1], poses[17].position[0] - target[0]
    )
    final_angle = math.atan2(
        orbit[-1].position[1] - target[1], orbit[-1].position[0] - target[0]
    )
    wrapped_degrees = math.degrees((final_angle - start_angle) % (2.0 * math.pi))
    assert wrapped_degrees == pytest.approx(220.0)
    assert math.dist(orbit[-1].position[:2], target[:2]) == pytest.approx(2.0)
    assert orbit[-1].position[2] == pytest.approx(2.5)


def test_ffmpeg_command_produces_portable_silent_h264() -> None:
    module = _load_renderer()
    command = module._ffmpeg_command(
        ffmpeg=Path("/usr/bin/ffmpeg"),
        frames_dir=Path("/tmp/frames with spaces"),
        output_path=Path("/tmp/output movie.mp4"),
        fps=30,
    )

    assert command[0] == "/usr/bin/ffmpeg"
    assert command[command.index("-framerate") + 1] == "30"
    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"
    assert "-an" in command
    assert command[-1] == "/tmp/output movie.mp4"
    assert command[command.index("-i") + 1] == "/tmp/frames with spaces/frame_%06d.png"


def test_hdr_rgb_is_mapped_to_ldr_before_uint8_quantization() -> None:
    module = _load_renderer()
    import numpy as np

    hdr = np.asarray([[[0.0, 0.5, 1.0], [1.5, 3.0, float("nan")]]], dtype=np.float32)
    ldr = module._video_rgb_uint8(hdr, np)

    assert ldr.dtype == np.uint8
    assert ldr.tolist() == [[[0, 127, 255], [255, 255, 0]]]


def test_renderer_keeps_simulator_imports_behind_runtime_boundary() -> None:
    tree = ast.parse(RENDERER.read_text(encoding="utf-8"))
    imported_at_module_execution: set[str] = set()
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            imported_at_module_execution.update(alias.name for alias in statement.names)
        elif isinstance(statement, ast.ImportFrom) and statement.module is not None:
            imported_at_module_execution.add(statement.module)

    assert not {
        "isaacsim",
        "omni",
        "pxr",
        "genmanip",
    }.intersection(imported_at_module_execution)


def _load_renderer() -> object:
    spec = importlib.util.spec_from_file_location(
        "scenario_forge_genmanip_orbit_video", RENDERER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
