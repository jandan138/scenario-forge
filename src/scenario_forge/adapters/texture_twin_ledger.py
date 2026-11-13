"""Pure-Python 1:1 Texture Twin Ledger, LAB color locking, and patch verification.

Provides simulator-neutral utilities for Real-to-Sim surface reconstruction:
- ``rectify_perspective_patch``: 4-point homography flattening via numpy SVD + PIL
- ``enhance_macro_texture_photo``: LAB illumination delighting + toroidal mirror-feather
  seamless tiling + roughness and tangent-space normal map derivation
- ``lock_color_to_reference_lab``: Reinhard CIE L*a*b* mean/std color transfer with
  CIE76 Delta-E verification
- ``TextureTwinEntry`` / ``TextureTwinLedger`` schema serialization and validation
- ``validate_patch_critique_report``: independent blind critic gate validation
- ``build_patch_contact_strip`` & ``compose_reprojection_comparison_board``

Never imports Blender, USD, OpenCV, or simulator SDKs.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

import numpy as np
import numpy.typing as npt
from PIL import Image, ImageDraw, ImageFilter

AnyArray = npt.NDArray[Any]
FloatArray = npt.NDArray[np.float64]
UInt8Array = npt.NDArray[np.uint8]
BoolArray = npt.NDArray[np.bool_]

TEXTURE_TWIN_LEDGER_SCHEMA_VERSION = "scenario-forge-texture-twin-ledger/v1.0"
PATCH_CRITIQUE_SCHEMA_VERSION = "scenario-forge-patch-critique-report/v1.0"
SURFACE_MODES = frozenset(
    {"repeated_material", "direct_rectified_patch", "macro_photo_enhanced"}
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_sha256(value: str, field: str = "sha256") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    cleaned = value.strip().lower().removeprefix("sha256:")
    if _SHA256_RE.fullmatch(cleaned) is None:
        raise ValueError(f"{field} must be a 64-character lowercase hex SHA-256")
    return cleaned


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _to_rgb_uint8(image: Image.Image | AnyArray) -> UInt8Array:
    if isinstance(image, Image.Image):
        return np.asarray(image.convert("RGB"), dtype=np.uint8)
    arr = np.asarray(image)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError("expected HxWx3 RGB image")
    arr = arr[:, :, :3]
    if np.issubdtype(arr.dtype, np.floating):
        if arr.max() <= 1.0 + 1e-6:
            arr = np.clip(arr * 255.0, 0.0, 255.0)
        else:
            arr = np.clip(arr, 0.0, 255.0)
    return np.asarray(arr, dtype=np.uint8)


def rgb_to_lab(rgb: Image.Image | AnyArray) -> FloatArray:
    """Convert sRGB (D65) image to CIE L*a*b* float64 array."""

    srgb = _to_rgb_uint8(rgb).astype(np.float64) / 255.0
    linear = np.where(
        srgb <= 0.04045,
        srgb / 12.92,
        np.power((srgb + 0.055) / 1.055, 2.4),
    )
    # sRGB to XYZ (D65)
    m = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ],
        dtype=np.float64,
    )
    xyz = linear @ m.T
    ref_white = np.array([0.95047, 1.00000, 1.08883], dtype=np.float64)
    xyz_norm = xyz / ref_white

    delta = 6.0 / 29.0
    delta3 = delta**3
    f = np.where(
        xyz_norm > delta3,
        np.cbrt(np.maximum(xyz_norm, 0.0)),
        xyz_norm / (3.0 * delta * delta) + 4.0 / 29.0,
    )
    l_star = 116.0 * f[:, :, 1] - 16.0
    a_star = 500.0 * (f[:, :, 0] - f[:, :, 1])
    b_star = 200.0 * (f[:, :, 1] - f[:, :, 2])
    return np.stack([l_star, a_star, b_star], axis=-1)


def lab_to_rgb(lab: FloatArray) -> UInt8Array:
    """Convert CIE L*a*b* float64 array back to sRGB uint8 array."""

    fy = (lab[:, :, 0] + 16.0) / 116.0
    fx = fy + lab[:, :, 1] / 500.0
    fz = fy - lab[:, :, 2] / 200.0

    delta = 6.0 / 29.0

    def _finv(t: FloatArray) -> FloatArray:
        return np.asarray(
            np.where(
                t > delta,
                t**3,
                3.0 * delta * delta * (t - 4.0 / 29.0),
            ),
            dtype=np.float64,
        )

    ref_white = np.array([0.95047, 1.00000, 1.08883], dtype=np.float64)
    xyz = np.stack([_finv(fx), _finv(fy), _finv(fz)], axis=-1) * ref_white

    m_inv = np.array(
        [
            [3.2404542, -1.5371385, -0.4985314],
            [-0.9692660, 1.8760108, 0.0415560],
            [0.0556434, -0.2040259, 1.0572252],
        ],
        dtype=np.float64,
    )
    linear = np.clip(xyz @ m_inv.T, 0.0, 1.0)
    srgb = np.where(
        linear <= 0.0031308,
        12.92 * linear,
        1.055 * np.power(linear, 1.0 / 2.4) - 0.055,
    )
    return np.asarray(np.clip(np.round(srgb * 255.0), 0.0, 255.0), dtype=np.uint8)


def compute_patch_lab_stats(image: Image.Image | AnyArray) -> dict[str, list[float]]:
    lab = rgb_to_lab(image)
    mean = lab.reshape(-1, 3).mean(axis=0)
    std = lab.reshape(-1, 3).std(axis=0)
    return {
        "mean_lab": [float(v) for v in mean],
        "std_lab": [float(v) for v in std],
    }


def compute_cie76_delta_e(
    image_a: Image.Image | AnyArray,
    image_b: Image.Image | AnyArray,
) -> float:
    """Compute CIE76 Delta-E*ab between the mean LAB chromaticity/lightness of two patches."""

    mean_a = rgb_to_lab(image_a).reshape(-1, 3).mean(axis=0)
    mean_b = rgb_to_lab(image_b).reshape(-1, 3).mean(axis=0)
    return float(np.linalg.norm(mean_a - mean_b))


def lock_color_to_reference_lab(
    source_image: Image.Image,
    reference_image: Image.Image,
    *,
    strength: float = 1.0,
    std_ratio_bounds: tuple[float, float] = (0.15, 6.0),
) -> Image.Image:
    """Apply Reinhard CIE L*a*b* mean/std color transfer to lock source to reference."""

    if not 0.0 <= strength <= 1.0:
        raise ValueError("strength must be in [0.0, 1.0]")
    src_lab = rgb_to_lab(source_image)
    ref_lab = rgb_to_lab(reference_image)

    src_mean = src_lab.reshape(-1, 3).mean(axis=0)
    src_std = src_lab.reshape(-1, 3).std(axis=0)
    ref_mean = ref_lab.reshape(-1, 3).mean(axis=0)
    ref_std = ref_lab.reshape(-1, 3).std(axis=0)

    safe_src_std = np.where(src_std > 1e-4, src_std, 1.0)
    raw_scale = np.where(src_std > 1e-4, ref_std / safe_src_std, 0.0)
    scale = np.clip(raw_scale, std_ratio_bounds[0], std_ratio_bounds[1])

    transferred = (src_lab - src_mean) * scale + ref_mean
    blended = (1.0 - strength) * src_lab + strength * transferred
    return Image.fromarray(lab_to_rgb(blended), mode="RGB")


def solve_homography_svd(
    dst_pts_xy: Sequence[tuple[float, float]],
    src_pts_xy: Sequence[tuple[float, float]],
) -> tuple[float, float, float, float, float, float, float, float]:
    """Solve 8-parameter perspective transform coefficients mapping dst (u,v) -> src (x,y)."""

    if len(dst_pts_xy) != 4 or len(src_pts_xy) != 4:
        raise ValueError("homography requires exactly 4 source and 4 destination points")

    rows: list[list[float]] = []
    for (u, v), (x, y) in zip(dst_pts_xy, src_pts_xy):
        rows.append([-u, -v, -1.0, 0.0, 0.0, 0.0, x * u, x * v, x])
        rows.append([0.0, 0.0, 0.0, -u, -v, -1.0, y * u, y * v, y])

    matrix = np.asarray(rows, dtype=np.float64)
    _, _, vt = np.linalg.svd(matrix)
    h = vt[-1]
    if abs(float(h[8])) < 1e-12:
        raise ValueError("perspective quad is degenerate")
    coeffs = tuple(float(h[i] / h[8]) for i in range(8))
    return coeffs  # type: ignore[return-value]


def rectify_perspective_patch(
    image: Image.Image,
    src_quad_xy: Sequence[tuple[float, float]],
    output_size: tuple[int, int],
) -> Image.Image:
    """Flatten a 4-corner perspective quad [TL, TR, BR, BL] into an axis-aligned RGB patch."""

    out_w, out_h = int(output_size[0]), int(output_size[1])
    if out_w < 2 or out_h < 2:
        raise ValueError("output_size dimensions must be >= 2")
    if len(src_quad_xy) != 4:
        raise ValueError("src_quad_xy must contain 4 (x, y) points [TL, TR, BR, BL]")

    dst_rect = [
        (0.0, 0.0),
        (float(out_w - 1), 0.0),
        (float(out_w - 1), float(out_h - 1)),
        (0.0, float(out_h - 1)),
    ]
    src_pts = [(float(pt[0]), float(pt[1])) for pt in src_quad_xy]
    coeffs = solve_homography_svd(dst_rect, src_pts)
    return image.convert("RGB").transform(
        (out_w, out_h),
        Image.Transform.PERSPECTIVE,
        coeffs,
        resample=Image.Resampling.BICUBIC,
    )


def _reflect_gaussian_lowpass(channel: FloatArray, sigma: float) -> FloatArray:
    pad = max(8, int(math.ceil(sigma * 2.5)))
    padded = np.pad(channel, ((pad, pad), (pad, pad)), mode="reflect")
    vmin, vmax = float(padded.min()), float(padded.max())
    span = max(1e-6, vmax - vmin)
    norm_u8 = np.clip((padded - vmin) / span * 255.0, 0.0, 255.0).astype(np.uint8)
    blurred_u8 = np.asarray(
        Image.fromarray(norm_u8, mode="L").filter(ImageFilter.GaussianBlur(radius=sigma)),
        dtype=np.float64,
    )
    restored = blurred_u8 / 255.0 * span + vmin
    return np.asarray(restored[pad:-pad, pad:-pad], dtype=np.float64)


def _make_raised_cosine_1d(length: int, feather_fraction: float) -> FloatArray:
    """Periodic blend weight w(i): 0 at edges (0, N-1), 1 across interior around N//2."""

    band = max(4, min(length // 2 - 1, int(round(length * feather_fraction))))
    w = np.ones(length, dtype=np.float64)
    idx = np.arange(band, dtype=np.float64)
    ramp = 0.5 * (1.0 - np.cos(math.pi * idx / float(band)))
    w[:band] = ramp
    w[-band:] = ramp[::-1]
    return w


def _toroidal_seamless_blend(arr: FloatArray, feather_fraction: float) -> FloatArray:
    """Make an HxWxC float64 image seamlessly tileable along both X and Y."""

    h, w, _ = arr.shape
    wx = _make_raised_cosine_1d(w, feather_fraction)[None, :, None]
    wy = _make_raised_cosine_1d(h, feather_fraction)[:, None, None]

    shifted_x = np.roll(arr, shift=w // 2, axis=1)
    pass_x = wx * arr + (1.0 - wx) * shifted_x

    shifted_y = np.roll(pass_x, shift=h // 2, axis=0)
    pass_xy = wy * pass_x + (1.0 - wy) * shifted_y
    return np.asarray(pass_xy, dtype=np.float64)


def enhance_macro_texture_photo(
    image: Image.Image,
    *,
    tile_size: int = 512,
    feather_fraction: float = 0.18,
    roughness_base: float = 0.55,
    normal_strength: float = 2.0,
) -> dict[str, Image.Image]:
    """Delight uneven macro illumination, make edges seamless, and derive PBR maps."""

    if tile_size < 16:
        raise ValueError("tile_size must be >= 16")
    if not 0.04 <= feather_fraction <= 0.48:
        raise ValueError("feather_fraction must be in [0.04, 0.48]")

    resized = image.convert("RGB").resize(
        (tile_size, tile_size), Image.Resampling.BICUBIC
    )
    lab = rgb_to_lab(resized)

    # 1. Delight low-frequency illumination gradient on L*, A*, and B* gently
    sigma = max(12.0, tile_size / 6.0)
    l_low = _reflect_gaussian_lowpass(lab[:, :, 0], sigma=sigma)
    lab[:, :, 0] = np.clip(lab[:, :, 0] - (l_low - float(l_low.mean())), 2.0, 98.0)

    # 2. Toroidal seamless edge continuity in LAB space
    seamless_lab = _toroidal_seamless_blend(lab, feather_fraction=feather_fraction)
    albedo_rgb = lab_to_rgb(seamless_lab)
    albedo_img = Image.fromarray(albedo_rgb, mode="RGB")

    # 3. Derive grayscale roughness and tangent-space normal maps from periodic height
    height = seamless_lab[:, :, 0] / 100.0
    height_centered = height - float(height.mean())
    rough_float = np.clip(
        roughness_base - 0.65 * height_centered,
        0.08,
        0.95,
    )
    rough_u8 = np.clip(np.round(rough_float * 255.0), 0, 255).astype(np.uint8)
    roughness_img = Image.fromarray(rough_u8, mode="L")

    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * normal_strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * normal_strength
    nx = -dx
    ny = dy
    nz = np.ones_like(height)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal_rgb = np.stack(
        [
            0.5 + 0.5 * (nx / norm),
            0.5 + 0.5 * (ny / norm),
            0.5 + 0.5 * (nz / norm),
        ],
        axis=-1,
    )
    normal_u8 = np.clip(np.round(normal_rgb * 255.0), 0, 255).astype(np.uint8)
    normal_img = Image.fromarray(normal_u8, mode="RGB")

    return {
        "albedo": albedo_img,
        "roughness": roughness_img,
        "normal": normal_img,
    }


def _render_shaded_swatch(texture: Image.Image, size: int) -> Image.Image:
    """Render a lit 3D sphere PBR material swatch over a neutral studio backdrop."""

    tex_arr = np.asarray(
        texture.convert("RGB").resize((size, size), Image.Resampling.BICUBIC),
        dtype=np.float64,
    ) / 255.0
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    nx = (xx - (size - 1) / 2.0) / (size * 0.42)
    ny = ((size - 1) / 2.0 - yy) / (size * 0.42)
    r2 = nx * nx + ny * ny
    mask = r2 <= 1.0
    nz = np.sqrt(np.maximum(0.0, 1.0 - r2))

    # Spherical equirectangular UV mapping
    u = np.clip((np.arctan2(nx, np.maximum(nz, 1e-4)) / (math.pi * 0.55) + 0.5) * (size - 1), 0, size - 1)
    v = np.clip((0.5 - np.arcsin(np.clip(ny, -1.0, 1.0)) / (math.pi * 0.65)) * (size - 1), 0, size - 1)
    sampled = tex_arr[np.round(v).astype(int), np.round(u).astype(int)]

    light_dir = np.array([-0.42, 0.52, 0.74], dtype=np.float64)
    light_dir /= np.linalg.norm(light_dir)
    ndotl = np.maximum(0.0, nx * light_dir[0] + ny * light_dir[1] + nz * light_dir[2])
    half_vec = light_dir + np.array([0.0, 0.0, 1.0])
    half_vec /= np.linalg.norm(half_vec)
    ndoth = np.maximum(0.0, nx * half_vec[0] + ny * half_vec[1] + nz * half_vec[2])
    spec = 0.14 * np.power(ndoth, 28.0)

    lit = np.clip(sampled * (0.28 + 0.78 * ndotl[:, :, None]) + spec[:, :, None], 0.0, 1.0)
    bg_grad = (0.14 + 0.08 * (1.0 - yy / max(1, size - 1)))[:, :, None] * np.ones((1, 1, 3))
    out = np.where(mask[:, :, None], lit, bg_grad)
    return Image.fromarray(np.round(out * 255.0).astype(np.uint8), mode="RGB")


def build_patch_contact_strip(
    reference_crop: Image.Image,
    twin_texture: Image.Image,
    *,
    panel_size: int = 256,
    label: str = "",
) -> Image.Image:
    """Build a 3-panel [ref_crop | twin_tex | shaded_swatch] contact sheet."""

    header_h = 30 if label else 0
    pad = 8
    total_w = panel_size * 3 + pad * 4
    total_h = panel_size + header_h + pad * 2

    board = Image.new("RGB", (total_w, total_h), (24, 26, 30))
    p1 = reference_crop.convert("RGB").resize((panel_size, panel_size), Image.Resampling.BICUBIC)
    p2 = twin_texture.convert("RGB").resize((panel_size, panel_size), Image.Resampling.BICUBIC)
    p3 = _render_shaded_swatch(twin_texture, panel_size)

    y0 = header_h + pad
    board.paste(p1, (pad, y0))
    board.paste(p2, (pad * 2 + panel_size, y0))
    board.paste(p3, (pad * 3 + panel_size * 2, y0))

    if label:
        de = compute_cie76_delta_e(reference_crop, twin_texture)
        draw = ImageDraw.Draw(board)
        draw.text(
            (pad, 8),
            f"{label} | [1] Ref Crop  [2] 1:1 Twin  [3] PBR Swatch | CIE76 dE={de:.2f}",
            fill=(232, 236, 242),
        )
    return board


def compose_reprojection_comparison_board(
    real_photo: Image.Image,
    virtual_render: Image.Image,
    *,
    target_size: tuple[int, int] | None = None,
    alpha: float = 0.5,
) -> tuple[Image.Image, dict[str, float]]:
    """Compose [real_photo | virtual_render | 50%_edge_overlay] comparison board and metrics."""

    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0.0, 1.0]")
    if target_size is None:
        w = min(960, virtual_render.width)
        h = max(64, int(round(w * virtual_render.height / max(1, virtual_render.width))))
        target_size = (w, h)
    tw, th = int(target_size[0]), int(target_size[1])

    real_r = real_photo.convert("RGB").resize((tw, th), Image.Resampling.BICUBIC)
    virt_r = virtual_render.convert("RGB").resize((tw, th), Image.Resampling.BICUBIC)

    real_arr = np.asarray(real_r, dtype=np.float64)
    virt_arr = np.asarray(virt_r, dtype=np.float64)

    real_luma = 0.299 * real_arr[:, :, 0] + 0.587 * real_arr[:, :, 1] + 0.114 * real_arr[:, :, 2]
    virt_luma = 0.299 * virt_arr[:, :, 0] + 0.587 * virt_arr[:, :, 1] + 0.114 * virt_arr[:, :, 2]

    def _edge_mag(luma: FloatArray) -> FloatArray:
        gx = np.roll(luma, -1, axis=1) - np.roll(luma, 1, axis=1)
        gy = np.roll(luma, -1, axis=0) - np.roll(luma, 1, axis=0)
        return np.asarray(np.hypot(gx, gy), dtype=np.float64)

    e_real = _edge_mag(real_luma)
    e_virt = _edge_mag(virt_luma)
    t_real = e_real > np.percentile(e_real, 85.0)
    t_virt = e_virt > np.percentile(e_virt, 85.0)

    # Dilate slightly (3x3) for geometric tolerance on edge overlap
    def _dilate3(mask: BoolArray) -> BoolArray:
        out = mask.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                out |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
        return out

    d_real = _dilate3(t_real)
    d_virt = _dilate3(t_virt)
    union = int((d_real | d_virt).sum())
    edge_iou = float((d_real & d_virt).sum() / union) if union > 0 else 1.0

    # 50% blend + cyan real edges / amber virtual edges overlay
    overlay = (1.0 - alpha) * real_arr + alpha * virt_arr
    overlay[t_real] = 0.45 * overlay[t_real] + 0.55 * np.array([0.0, 240.0, 255.0])
    overlay[t_virt] = 0.45 * overlay[t_virt] + 0.55 * np.array([255.0, 180.0, 20.0])
    overlay_img = Image.fromarray(np.clip(np.round(overlay), 0, 255).astype(np.uint8), mode="RGB")

    pad = 8
    header_h = 32
    board = Image.new("RGB", (tw * 3 + pad * 4, th + header_h + pad * 2), (20, 22, 26))
    y0 = header_h + pad
    board.paste(real_r, (pad, y0))
    board.paste(virt_r, (pad * 2 + tw, y0))
    board.paste(overlay_img, (pad * 3 + tw * 2, y0))

    mean_de = compute_cie76_delta_e(real_r, virt_r)
    r_std = float(real_luma.std())
    v_std = float(virt_luma.std())
    if r_std > 1e-6 and v_std > 1e-6:
        luma_corr = float(
            ((real_luma - real_luma.mean()) * (virt_luma - virt_luma.mean())).mean()
            / (r_std * v_std)
        )
    else:
        luma_corr = 0.0

    draw = ImageDraw.Draw(board)
    draw.text(
        (pad, 8),
        f"[1] Ground-Truth Photo | [2] Camera-Matched Render | [3] 50% Edge Overlay (dE={mean_de:.2f}, edge_iou={edge_iou:.3f})",
        fill=(235, 238, 245),
    )
    metrics = {
        "mean_delta_e_ab": round(mean_de, 4),
        "edge_iou": round(edge_iou, 4),
        "luma_correlation": round(luma_corr, 4),
    }
    return board, metrics


@dataclass(frozen=True)
class TextureTwinEntry:
    surface_id: str
    mode: str
    reference_crop_path: str
    reference_crop_sha256: str
    twin_texture_path: str
    twin_texture_sha256: str
    contact_strip_path: str | None = None
    roughness_map_path: str | None = None
    normal_map_path: str | None = None
    delta_e_ab: float = 0.0
    src_quad_xy: tuple[tuple[float, float], ...] | None = None
    target_prims: tuple[str, ...] = ()
    notes: str = ""

    def validate(self, *, max_delta_e_ab: float = 12.0) -> None:
        if not self.surface_id or not isinstance(self.surface_id, str):
            raise ValueError("surface_id must be a non-empty string")
        if self.mode not in SURFACE_MODES:
            raise ValueError(f"unsupported surface mode {self.mode!r}; expected one of {sorted(SURFACE_MODES)}")
        normalize_sha256(self.reference_crop_sha256, "reference_crop_sha256")
        normalize_sha256(self.twin_texture_sha256, "twin_texture_sha256")
        if not math.isfinite(self.delta_e_ab) or self.delta_e_ab < 0.0:
            raise ValueError(f"delta_e_ab must be finite and non-negative for {self.surface_id}")
        if self.delta_e_ab > max_delta_e_ab:
            raise ValueError(
                f"surface {self.surface_id!r} delta_e_ab={self.delta_e_ab:.3f} exceeds max {max_delta_e_ab:.3f}"
            )
        if self.src_quad_xy is not None and len(self.src_quad_xy) != 4:
            raise ValueError(f"src_quad_xy for {self.surface_id!r} must have 4 points")

    def to_mapping(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "surface_id": self.surface_id,
            "mode": self.mode,
            "reference_crop_path": self.reference_crop_path,
            "reference_crop_sha256": normalize_sha256(self.reference_crop_sha256),
            "twin_texture_path": self.twin_texture_path,
            "twin_texture_sha256": normalize_sha256(self.twin_texture_sha256),
            "delta_e_ab": float(self.delta_e_ab),
            "target_prims": list(self.target_prims),
            "notes": self.notes,
        }
        if self.contact_strip_path is not None:
            data["contact_strip_path"] = self.contact_strip_path
        if self.roughness_map_path is not None:
            data["roughness_map_path"] = self.roughness_map_path
        if self.normal_map_path is not None:
            data["normal_map_path"] = self.normal_map_path
        if self.src_quad_xy is not None:
            data["src_quad_xy"] = [[float(p[0]), float(p[1])] for p in self.src_quad_xy]
        return data

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> TextureTwinEntry:
        quad_raw = raw.get("src_quad_xy")
        quad = (
            tuple((float(pt[0]), float(pt[1])) for pt in quad_raw)
            if quad_raw is not None
            else None
        )
        prims_raw = raw.get("target_prims", ())
        return cls(
            surface_id=str(raw["surface_id"]),
            mode=str(raw["mode"]),
            reference_crop_path=str(raw["reference_crop_path"]),
            reference_crop_sha256=normalize_sha256(
                str(raw["reference_crop_sha256"]), "reference_crop_sha256"
            ),
            twin_texture_path=str(raw["twin_texture_path"]),
            twin_texture_sha256=normalize_sha256(
                str(raw["twin_texture_sha256"]), "twin_texture_sha256"
            ),
            contact_strip_path=(
                str(raw["contact_strip_path"])
                if raw.get("contact_strip_path") is not None
                else None
            ),
            roughness_map_path=(
                str(raw["roughness_map_path"])
                if raw.get("roughness_map_path") is not None
                else None
            ),
            normal_map_path=(
                str(raw["normal_map_path"])
                if raw.get("normal_map_path") is not None
                else None
            ),
            delta_e_ab=float(raw.get("delta_e_ab", 0.0)),
            src_quad_xy=quad,
            target_prims=tuple(str(p) for p in prims_raw),
            notes=str(raw.get("notes", "")),
        )


@dataclass(frozen=True)
class TextureTwinLedger:
    ledger_id: str
    source_image_path: str
    source_image_sha256: str
    entries: tuple[TextureTwinEntry, ...]
    schema_version: str = TEXTURE_TWIN_LEDGER_SCHEMA_VERSION

    def validate(self, *, max_delta_e_ab: float = 12.0) -> None:
        if self.schema_version != TEXTURE_TWIN_LEDGER_SCHEMA_VERSION:
            raise ValueError(f"unsupported ledger schema_version: {self.schema_version!r}")
        if not self.ledger_id:
            raise ValueError("ledger_id must be non-empty")
        normalize_sha256(self.source_image_sha256, "source_image_sha256")
        if not self.entries:
            raise ValueError("TextureTwinLedger must contain at least one entry")
        seen: set[str] = set()
        for entry in self.entries:
            if entry.surface_id in seen:
                raise ValueError(f"duplicate surface_id in ledger: {entry.surface_id!r}")
            seen.add(entry.surface_id)
            entry.validate(max_delta_e_ab=max_delta_e_ab)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ledger_id": self.ledger_id,
            "source_image_path": self.source_image_path,
            "source_image_sha256": normalize_sha256(self.source_image_sha256),
            "entry_count": len(self.entries),
            "max_delta_e_ab": max((e.delta_e_ab for e in self.entries), default=0.0),
            "entries": [entry.to_mapping() for entry in self.entries],
        }

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> TextureTwinLedger:
        raw_entries = raw.get("entries")
        if not isinstance(raw_entries, Sequence):
            raise ValueError("ledger entries must be a list")
        entries = tuple(TextureTwinEntry.from_mapping(item) for item in raw_entries)
        return cls(
            ledger_id=str(raw["ledger_id"]),
            source_image_path=str(raw["source_image_path"]),
            source_image_sha256=normalize_sha256(
                str(raw["source_image_sha256"]), "source_image_sha256"
            ),
            entries=entries,
            schema_version=str(
                raw.get("schema_version", TEXTURE_TWIN_LEDGER_SCHEMA_VERSION)
            ),
        )


def validate_patch_critique_report(
    report: Mapping[str, Any],
    *,
    max_delta_e_ab: float = 12.0,
    min_patch_score: float = 8.0,
) -> dict[str, Any]:
    """Validate an independent 1:1 patch-pair blind critique report."""

    if not isinstance(report, Mapping):
        raise ValueError("patch critique report must be a mapping")
    author = str(report.get("author_agent", "")).strip()
    critic = str(report.get("critic_agent", "")).strip()
    if not author or not critic:
        raise ValueError("patch critique report requires non-empty author_agent and critic_agent")
    if author == critic:
        raise ValueError(
            f"independent critic required: author_agent ({author!r}) != critic_agent ({critic!r})"
        )
    verdict = str(report.get("verdict", "")).strip().upper()
    if verdict != "PASS":
        raise ValueError(f"patch critique report verdict is {verdict!r}, expected 'PASS'")

    patches = report.get("patches")
    if patches is None:
        patches = report.get("entries")
    if not isinstance(patches, list) or not patches:
        raise ValueError("patch critique report must include a non-empty 'patches' list")

    for index, item in enumerate(patches):
        if not isinstance(item, Mapping):
            raise ValueError(f"patches[{index}] must be a mapping")
        surface_id = str(item.get("surface_id", f"patch_{index}"))
        raw_de = item.get("delta_e_ab")
        if raw_de is None or not isinstance(raw_de, (int, float)) or isinstance(raw_de, bool):
            raise ValueError(f"patch {surface_id!r} missing numeric delta_e_ab")
        if float(raw_de) > max_delta_e_ab or float(raw_de) < 0.0:
            raise ValueError(
                f"patch {surface_id!r} delta_e_ab={float(raw_de):.3f} exceeds max {max_delta_e_ab:.3f}"
            )

        raw_score = item.get("patch_score", item.get("score"))
        if raw_score is None and isinstance(item.get("scores"), Mapping):
            raw_score = min(float(v) for v in item["scores"].values())
        if raw_score is None or not isinstance(raw_score, (int, float)) or isinstance(raw_score, bool):
            raise ValueError(f"patch {surface_id!r} missing numeric patch_score")
        if float(raw_score) < min_patch_score:
            raise ValueError(
                f"patch {surface_id!r} patch_score={float(raw_score):.2f} below threshold {min_patch_score:.2f}"
            )

    return dict(report)
