from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import struct
import zlib

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_SCRIPT = REPO_ROOT / "scripts" / "build_out_of_domain_showcase_html.py"


def _load_builder_module():
    if not BUILDER_SCRIPT.is_file():
        raise FileNotFoundError(f"Missing showcase builder script: {BUILDER_SCRIPT}")
    spec = importlib.util.spec_from_file_location(
        "build_out_of_domain_showcase_html", BUILDER_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _minimal_png_bytes(rgb: tuple[int, int, int] = (24, 128, 120)) -> bytes:
    def _chunk(tag: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)

    raw_row = b"\x00" + bytes(rgb) * 2
    raw_img = raw_row * 2
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw_img, level=9))
        + _chunk(b"IEND", b"")
    )


def test_bimanual_reach_envelope_computes_horizontal_and_3d_distances() -> None:
    builder = _load_builder_module()
    rows = builder.compute_bimanual_reach_envelope(
        robot_base_xy=(0.0, -1.02),
        shoulder_center_xyz=(0.0, -0.78, 1.02),
        targets=[
            {
                "label": "a5_media_pack (initial grasp)",
                "role": "grasp_origin",
                "xyz_m": (-0.415, -0.152, 0.769),
            },
            {
                "label": "PaperCassette cavity (target)",
                "role": "cavity_target",
                "xyz_m": (0.0, -0.171, 0.770),
            },
        ],
    )
    assert len(rows) == 2
    first = rows[0]
    assert first["within_bimanual_sweet_spot"] is True
    assert 0.60 <= first["shoulder_3d_m"] <= 0.85
    assert 0.20 <= first["table_front_depth_m"] <= 0.35


def test_render_tabletop_layout_svg_marks_sweep_corridor_and_conflict() -> None:
    builder = _load_builder_module()
    svg_conflict = builder.render_tabletop_layout_svg(
        table={"x_range_m": [-1.0, 1.0], "y_range_m": [-0.4, 0.4], "min_edge_clearance_m": 0.1},
        robot_xy=[0.0, -1.02],
        placements=[
            {
                "id": "brother_printer",
                "role": "articulated_appliance",
                "pose": {"xyz": [0.0, 0.09, 0.755]},
                "world_xy_min_m": [-0.206, -0.1095],
                "world_xy_max_m": [0.206, 0.2895],
                "world_clearance_volumes": [
                    {
                        "id": "paper_cassette_pullout",
                        "joint": "paper_cassette",
                        "world_xy_min_m": [-0.145, -0.292],
                        "world_xy_max_m": [0.145, -0.1095],
                    }
                ],
            },
            {
                "id": "a5_media_pack",
                "role": "consumable_media",
                "pose": {"xyz": [0.0, -0.20, 0.757]},
                "world_xy_min_m": [-0.06, -0.28],
                "world_xy_max_m": [0.06, -0.12],
                "conflict": True,
            },
        ],
        mode_label="Iteration 1 · Unrepaired Corridor Intrusion",
    )
    assert "<svg" in svg_conflict
    assert "paper_cassette_pullout" in svg_conflict
    assert "brother_printer" in svg_conflict
    assert "a5_media_pack" in svg_conflict
    assert "conflict" in svg_conflict.lower()


def test_self_contained_html_inlines_lossless_png_and_mp4_with_zero_external_urls(
    tmp_path: Path,
) -> None:
    builder = _load_builder_module()
    png_path = tmp_path / "sample.png"
    mp4_path = tmp_path / "sample.mp4"
    png_bytes = _minimal_png_bytes()
    mp4_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    png_path.write_bytes(png_bytes)
    mp4_path.write_bytes(mp4_bytes)

    png_uri = builder.encode_lossless_png_data_uri(png_path)
    mp4_uri = builder.encode_mp4_data_uri(mp4_path)
    assert png_uri.startswith("data:image/png;base64,")
    assert base64.b64decode(png_uri.removeprefix("data:image/png;base64,")) == png_bytes
    assert mp4_uri.startswith("data:video/mp4;base64,")
    assert base64.b64decode(mp4_uri.removeprefix("data:video/mp4;base64,")) == mp4_bytes

    sample_model = {
        "generated_date": "2026-11-12",
        "scenarios": [
            {
                "scenario_id": "modern_office_brother_calibrate",
                "title_zh": "现代办公文印中心 · Brother 激光一体机装纸推入与扫描校准",
                "domain": "modern_office_print_hub",
                "room_id": "office_print_studio_v1",
                "room_manifest_sha256": "bedcdcd9e0421d464360786c925d12d4e82f69862de943ff7550c0a03a179c25",
                "hero": {
                    "asset_id": "BrotherMFCL2820DW",
                    "slug": "brother-mfc-l2820dw-printer",
                    "model_name": "Brother MFC-L2820DW",
                    "envelope_mm": "410 × 399 × 319 mm",
                    "mass_kg": 11.56,
                    "dof_summary": "2-DOF Orthogonal (Prismatic-Y 180mm + Revolute-X 70°)",
                    "cavity_summary": "Hollow lower Base tunnel + 5-box PaperCassette + PlatenGlass",
                    "manifest_sha256": "c8125e7bbeef95f5c87e24df0c30cd20e45c5fc0744076f26914840c22926ca4",
                    "studio_views": [
                        {"label": "Isometric AgX", "data_uri": png_uri},
                        {"label": "Front Orthographic", "data_uri": png_uri},
                        {"label": "Cavity Detail", "data_uri": png_uri},
                    ],
                    "joints": [
                        {
                            "name": "paper_cassette",
                            "type": "Prismatic Y",
                            "limits": "[-0.180 m, 0.000 m]",
                            "semantics": "extended [-0.180, -0.145] -> closed [-0.012, 0.0]",
                        }
                    ],
                },
                "initial_views": [
                    {"view_id": "scene_overview", "label": "全域总览", "data_uri": png_uri},
                    {"view_id": "task_object_closeup", "label": "任务台面特写", "data_uri": png_uri},
                ],
                "progression_video_uri": mp4_uri,
                "canary_stages": [
                    {
                        "stage_key": "t0",
                        "badge": "t = 0",
                        "title": "120 帧零动作冷启动稳态",
                        "score": 0.0,
                        "predicate_summary": "All primary & orientation leaves False (t0_score = 0.00)",
                        "physics_readout": "max_drift = 0.000 mm · cassette = -0.165 m",
                        "keyframe_uri": png_uri,
                    },
                    {
                        "stage_key": "s1",
                        "badge": "Stage 4/4",
                        "title": "合上扫描盖板完成校准",
                        "score": 1.0,
                        "predicate_summary": "scanner_lid closed [-0.08, 0.02 rad] -> True",
                        "physics_readout": "cassette = 0.000 m · sheet retained on PlatenGlass",
                        "keyframe_uri": png_uri,
                    },
                ],
                "critic1": {
                    "max_translation_drift_mm": 0.0,
                    "max_orientation_drift_deg": 0.0,
                    "max_joint_drift": 0.000075,
                    "t0_score": 0.0,
                    "final_score": 1.0,
                    "report_sha256": "sha256:125e334913bf60194be2a095bd2d4f2b623e104dab6b107c20787c624076142a",
                },
                "layout_svg_solved": "<svg viewBox='0 0 100 50'><rect width='100' height='50'/></svg>",
                "layout_svg_unrepaired": "<svg viewBox='0 0 100 50'><rect width='100' height='50'/></svg>",
                "critic_repair_note": "Iteration 1 -> Iteration 2 relocated a5_media_pack out of paper_cassette_pullout corridor.",
                "reach_rows": [
                    {
                        "label": "a5_media_pack (initial grasp)",
                        "role": "grasp_origin",
                        "xyz_str": "(-0.415, -0.152, 0.757)",
                        "table_front_depth_m": 0.248,
                        "shoulder_xy_m": 0.753,
                        "shoulder_3d_m": 0.798,
                        "within_bimanual_sweet_spot": True,
                    }
                ],
            }
        ],
        "bugs_caught": [
            {
                "title": "GenManip ArticulationView 4 层嵌套目标契约",
                "layer": "src/scenario_forge/adapters/ebench/genmanip.py",
                "detail": "Export [[candidate]] matching (1, num_dofs) ArticulationView shape.",
            }
        ],
    }

    html_text = builder.render_showcase_html(sample_model)
    audit = builder.audit_self_contained_html(html_text)
    assert audit["external_url_count"] == 0
    assert audit["png_data_uri_count"] == 7
    assert audit["mp4_data_uri_count"] == 1
    assert "Astra" in html_text
    assert "Privileged" in html_text or "特权状态推进" in html_text

    with pytest.raises(ValueError, match="external URL"):
        builder.audit_self_contained_html(
            html_text + '<script src="https://cdn.example.com/app.js"></script>'
        )
