from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from scenario_forge.adapters.texture_twin_ledger import (
    TEXTURE_TWIN_LEDGER_SCHEMA_VERSION,
    TextureTwinEntry,
    TextureTwinLedger,
    build_patch_contact_strip,
    compose_reprojection_comparison_board,
    compute_cie76_delta_e,
    enhance_macro_texture_photo,
    lock_color_to_reference_lab,
    rectify_perspective_patch,
    validate_patch_critique_report,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_texture_twin_ledger_schema_roundtrip_and_validation(tmp_path: Path) -> None:
    ref_bytes = b"REF_PNG"
    twin_bytes = b"TWIN_PNG"
    src_bytes = b"SOURCE_PHOTO"
    entry = TextureTwinEntry(
        surface_id="desk_oak_laminate",
        mode="repeated_material",
        reference_crop_path="ledger/crops/desk_oak_laminate_ref.png",
        reference_crop_sha256=_sha256_bytes(ref_bytes),
        twin_texture_path="textures/desk_oak_laminate.png",
        twin_texture_sha256=_sha256_bytes(twin_bytes),
        contact_strip_path="ledger/strips/desk_oak_laminate_strip.png",
        delta_e_ab=2.4,
        src_quad_xy=((100.0, 200.0), (400.0, 210.0), (420.0, 500.0), (80.0, 490.0)),
        target_prims=("/World/table/Top",),
        notes="Warm straight-grain oak desktop",
    )
    ledger = TextureTwinLedger(
        ledger_id="real2sim_office_desk_v1",
        source_image_path="evidence/source_photo.jpg",
        source_image_sha256=_sha256_bytes(src_bytes),
        entries=(entry,),
    )
    ledger.validate(max_delta_e_ab=12.0)

    payload = ledger.to_mapping()
    assert payload["schema_version"] == TEXTURE_TWIN_LEDGER_SCHEMA_VERSION
    restored = TextureTwinLedger.from_mapping(payload)
    assert restored == ledger

    bad_entry = TextureTwinEntry(
        surface_id="desk_oak_laminate",
        mode="repeated_material",
        reference_crop_path="ledger/crops/ref.png",
        reference_crop_sha256=_sha256_bytes(ref_bytes),
        twin_texture_path="textures/twin.png",
        twin_texture_sha256=_sha256_bytes(twin_bytes),
        delta_e_ab=18.5,
    )
    bad_ledger = TextureTwinLedger(
        ledger_id="bad_ledger",
        source_image_path="evidence/source_photo.jpg",
        source_image_sha256=_sha256_bytes(src_bytes),
        entries=(bad_entry,),
    )
    with pytest.raises(ValueError, match="delta_e_ab"):
        bad_ledger.validate(max_delta_e_ab=12.0)


def test_enhance_macro_texture_photo_delights_and_makes_edges_seamless() -> None:
    rng = np.random.default_rng(42)
    h, w = 256, 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    # Fine wood-like grain + strong left-to-right uneven illumination gradient + step jump at edges
    grain = 12.0 * np.sin(xx * 0.35) + 6.0 * rng.standard_normal((h, w))
    illumination_ramp = 75.0 * (xx / w) - 37.5
    base_luma = np.clip(145.0 + grain + illumination_ramp, 10.0, 245.0)
    rgb = np.stack(
        [
            np.clip(base_luma * 1.08, 0, 255),
            np.clip(base_luma * 0.96, 0, 255),
            np.clip(base_luma * 0.80, 0, 255),
        ],
        axis=-1,
    ).astype(np.uint8)
    raw_img = Image.fromarray(rgb, mode="RGB")

    raw_left_mean = float(rgb[:, :32, :].mean())
    raw_right_mean = float(rgb[:, -32:, :].mean())
    raw_seam_jump = float(np.abs(rgb[:, 0, :].astype(float) - rgb[:, -1, :].astype(float)).mean())
    assert abs(raw_right_mean - raw_left_mean) > 40.0

    maps = enhance_macro_texture_photo(raw_img, tile_size=256, feather_fraction=0.18)
    assert set(maps.keys()) == {"albedo", "roughness", "normal"}

    albedo = np.asarray(maps["albedo"], dtype=np.float64)
    roughness = np.asarray(maps["roughness"], dtype=np.uint8)
    normal = np.asarray(maps["normal"], dtype=np.uint8)

    assert albedo.shape == (256, 256, 3)
    assert roughness.shape == (256, 256)
    assert normal.shape == (256, 256, 3)

    # Low-frequency illumination ramp must be substantially flattened
    new_left_mean = float(albedo[:, :32, :].mean())
    new_right_mean = float(albedo[:, -32:, :].mean())
    assert abs(new_right_mean - new_left_mean) < 12.0

    # Opposite tile boundaries must be continuous across wrap-around
    seam_jump_x = float(np.abs(albedo[:, 0, :] - albedo[:, -1, :]).mean())
    seam_jump_y = float(np.abs(albedo[0, :, :] - albedo[-1, :, :]).mean())
    assert seam_jump_x < raw_seam_jump * 0.35
    assert seam_jump_x < 16.0
    assert seam_jump_y < 16.0

    # Roughness and normal maps have non-degenerate micro-detail
    assert float(roughness.std()) > 1.5
    assert 115.0 <= float(normal[:, :, 0].mean()) <= 141.0
    assert 115.0 <= float(normal[:, :, 1].mean()) <= 141.0
    assert float(normal[:, :, 2].mean()) >= 200.0


def test_rectify_perspective_patch_flattens_quad_via_svd_homography() -> None:
    # Create a crisp 2x2 color checkerboard and warp it into a perspective quad on a dark canvas
    patch_w, patch_h = 160, 120
    checker = np.zeros((patch_h, patch_w, 3), dtype=np.uint8)
    checker[:60, :80] = (220, 40, 40)     # top-left: red
    checker[:60, 80:] = (40, 200, 60)     # top-right: green
    checker[60:, :80] = (40, 80, 220)     # bottom-left: blue
    checker[60:, 80:] = (230, 210, 50)    # bottom-right: yellow

    # Synthesize a canvas by sampling inverse homography onto an arbitrary skewed quad
    canvas_w, canvas_h = 400, 320
    quad = [(75.0, 50.0), (310.0, 85.0), (345.0, 265.0), (55.0, 240.0)]

    # Render synthetic perspective quad onto canvas using bilinear inverse mapping
    canvas = Image.new("RGB", (canvas_w, canvas_h), (20, 20, 20))
    # Map canvas (x, y) -> checker (u, v) via PIL PERSPECTIVE
    # rectify_perspective_patch maps output (0..W, 0..H) -> canvas quad; here we first paint the quad
    # directly by bilinear interpolation on a dense grid
    src_arr = np.asarray(canvas).copy()
    p00, p10, p11, p01 = [np.array(p, dtype=np.float64) for p in quad]
    # Use projective warp via 3x3 homography from unit square to quad
    dst_pts = np.array([[0, 0], [patch_w - 1, 0], [patch_w - 1, patch_h - 1], [0, patch_h - 1]], dtype=np.float64)
    src_pts = np.array(quad, dtype=np.float64)
    rows = []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, vt = np.linalg.svd(np.asarray(rows, dtype=np.float64))
    h_inv = vt[-1] / vt[-1, 8]
    yy, xx = np.mgrid[0:canvas_h, 0:canvas_w].astype(np.float64)
    denom = h_inv[6] * xx + h_inv[7] * yy + 1.0
    uu = (h_inv[0] * xx + h_inv[1] * yy + h_inv[2]) / denom
    vv = (h_inv[3] * xx + h_inv[4] * yy + h_inv[5]) / denom
    inside = (uu >= 0) & (uu < patch_w - 1) & (vv >= 0) & (vv < patch_h - 1)
    src_arr[inside] = checker[np.round(vv[inside]).astype(int), np.round(uu[inside]).astype(int)]
    warped_canvas = Image.fromarray(src_arr, mode="RGB")

    rectified = rectify_perspective_patch(warped_canvas, quad, output_size=(patch_w, patch_h))
    rect_arr = np.asarray(rectified, dtype=np.float64)

    # Interior of all 4 quadrants must recover the exact checkerboard colors
    assert np.allclose(rect_arr[15:45, 15:65].mean(axis=(0, 1)), [220, 40, 40], atol=8.0)
    assert np.allclose(rect_arr[15:45, 95:145].mean(axis=(0, 1)), [40, 200, 60], atol=8.0)
    assert np.allclose(rect_arr[75:105, 15:65].mean(axis=(0, 1)), [40, 80, 220], atol=8.0)
    assert np.allclose(rect_arr[75:105, 95:145].mean(axis=(0, 1)), [230, 210, 50], atol=8.0)


def test_lock_color_to_reference_lab_reduces_delta_e_below_6() -> None:
    rng = np.random.default_rng(7)
    # Reference: warm light oak patch
    ref_noise = rng.normal(0.0, 9.0, size=(128, 128, 1))
    ref_rgb = np.clip(np.array([[[198.0, 166.0, 128.0]]]) + ref_noise, 0, 255).astype(np.uint8)
    ref_img = Image.fromarray(ref_rgb, mode="RGB")

    # Shifted source texture: cool bluish-grey wood grain with large initial Delta-E
    src_noise = rng.normal(0.0, 14.0, size=(128, 128, 1))
    src_rgb = np.clip(np.array([[[112.0, 126.0, 148.0]]]) + src_noise, 0, 255).astype(np.uint8)
    src_img = Image.fromarray(src_rgb, mode="RGB")

    initial_de = compute_cie76_delta_e(src_img, ref_img)
    assert initial_de > 25.0

    locked_img = lock_color_to_reference_lab(src_img, ref_img)
    final_de = compute_cie76_delta_e(locked_img, ref_img)
    assert final_de <= 6.0

    # Verify contact strip & reprojection comparison helpers produce valid RGB boards
    strip = build_patch_contact_strip(ref_img, locked_img, panel_size=128, label="desk_oak_laminate")
    assert strip.size[0] >= 128 * 3
    board, metrics = compose_reprojection_comparison_board(ref_img, locked_img)
    assert board.size[0] >= 128 * 3
    assert math.isfinite(metrics["mean_delta_e_ab"])


def test_validate_patch_critique_report_enforces_isolation_delta_e_and_score() -> None:
    valid_report = {
        "schema_version": "scenario-forge-patch-critique-report/v1.0",
        "author_agent": "real2sim-twin",
        "critic_agent": "critic-r4",
        "verdict": "PASS",
        "patches": [
            {
                "surface_id": "desk_oak_laminate",
                "delta_e_ab": 2.1,
                "patch_score": 9.0,
            },
            {
                "surface_id": "philips_portrait_screen_ui",
                "delta_e_ab": 4.8,
                "patch_score": 8.6,
            },
        ],
    }
    validated = validate_patch_critique_report(valid_report)
    assert validated["verdict"] == "PASS"

    # Self-review (author == critic) must fail
    same_agent = {**valid_report, "critic_agent": "real2sim-twin"}
    with pytest.raises(ValueError, match="author_agent.*critic_agent|independent"):
        validate_patch_critique_report(same_agent)

    # Excessive delta_e_ab (> 12.0) must fail
    high_de = {
        **valid_report,
        "patches": [{"surface_id": "desk_oak_laminate", "delta_e_ab": 14.2, "patch_score": 8.8}],
    }
    with pytest.raises(ValueError, match="delta_e_ab"):
        validate_patch_critique_report(high_de)

    # Low patch_score (< 8.0) must fail
    low_score = {
        **valid_report,
        "patches": [{"surface_id": "desk_oak_laminate", "delta_e_ab": 3.0, "patch_score": 7.4}],
    }
    with pytest.raises(ValueError, match="patch_score|score"):
        validate_patch_critique_report(low_score)
