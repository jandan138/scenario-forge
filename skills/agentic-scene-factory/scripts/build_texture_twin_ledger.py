#!/usr/bin/env python3
"""Build a 1:1 Texture Twin Ledger, contact strips, and ledger_manifest.json.

Supports two workflows:
1) Declarative spec mode (`--spec <spec.yaml|json>`): rectifies quads, runs LAB
   color-transfer locking or macro delighting/seamless enhancement, saves twin
   textures + contact strips, and emits `ledger_manifest.json`.
2) Directory pairing mode (`--crops-dir <dir> --textures-dir <dir> --source-image <img.jpg>`):
   pairs `<surface_id>` reference crops with `<surface_id>` twin textures, computes
   CIE76 Delta-E*ab, renders `[ref_crop | twin_tex | shaded_swatch]` strips + a
   combined overview sheet, and emits `ledger_manifest.json`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from PIL import Image
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scenario_forge.adapters.texture_twin_ledger import (  # noqa: E402
    TextureTwinEntry,
    TextureTwinLedger,
    build_patch_contact_strip,
    compute_cie76_delta_e,
    enhance_macro_texture_photo,
    lock_color_to_reference_lab,
    rectify_perspective_patch,
    sha256_file,
)


def _load_spec(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"ledger spec must be a mapping: {path}")
    return data


def _rel_or_str(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _stack_strips_vertically(strips: list[Image.Image], out_path: Path) -> None:
    if not strips:
        return
    max_w = max(im.width for im in strips)
    total_h = sum(im.height for im in strips) + 6 * max(0, len(strips) - 1)
    sheet = Image.new("RGB", (max_w, total_h), (16, 18, 22))
    y = 0
    for im in strips:
        sheet.paste(im, (0, y))
        y += im.height + 6
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, format="PNG")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, help="YAML/JSON declarative ledger spec.")
    parser.add_argument("--source-image", type=Path, help="Ground-truth source photograph.")
    parser.add_argument("--crops-dir", type=Path, help="Directory of ground-truth reference crops.")
    parser.add_argument("--textures-dir", type=Path, help="Directory of 1:1 twin PNG textures.")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output ledger directory.")
    parser.add_argument("--ledger-id", default="real2sim_texture_twin_ledger_v1")
    parser.add_argument("--panel-size", type=int, default=256)
    parser.add_argument("--max-delta-e", type=float, default=12.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    out_dir = args.out_dir.resolve()
    strips_dir = out_dir / "strips"
    crops_out_dir = out_dir / "crops"
    tex_out_dir = out_dir / "textures"
    strips_dir.mkdir(parents=True, exist_ok=True)

    entries: list[TextureTwinEntry] = []
    strip_images: list[Image.Image] = []
    base_root = out_dir.parent

    if args.spec is not None:
        spec_path = args.spec.resolve()
        spec = _load_spec(spec_path)
        spec_base = spec_path.parent
        ledger_id = str(spec.get("ledger_id", args.ledger_id))
        src_img_raw = args.source_image or Path(spec["source_image"])
        src_img_path = (src_img_raw if src_img_raw.is_absolute() else (spec_base / src_img_raw)).resolve()
        source_img = Image.open(src_img_path).convert("RGB")

        raw_surfaces = spec.get("surfaces") or spec.get("entries") or []
        if not raw_surfaces:
            raise ValueError("spec contains no 'surfaces' or 'entries'")

        crops_out_dir.mkdir(parents=True, exist_ok=True)
        tex_out_dir.mkdir(parents=True, exist_ok=True)

        for item in raw_surfaces:
            surface_id = str(item["surface_id"])
            mode = str(item.get("mode", "repeated_material"))
            quad_raw = item.get("src_quad_xy")
            quad: tuple[tuple[float, float], ...] | None = None

            if item.get("reference_crop_path"):
                ref_p = Path(item["reference_crop_path"])
                ref_path = (ref_p if ref_p.is_absolute() else (spec_base / ref_p)).resolve()
                ref_img = Image.open(ref_path).convert("RGB")
            elif quad_raw is not None:
                quad = tuple((float(p[0]), float(p[1])) for p in quad_raw)
                out_sz = tuple(int(v) for v in item.get("output_size", [512, 512]))
                ref_img = rectify_perspective_patch(source_img, quad, (out_sz[0], out_sz[1]))
                ref_path = crops_out_dir / f"{surface_id}_ref.png"
                ref_img.save(ref_path, format="PNG")
            elif item.get("crop_xyxy"):
                x0, y0, x1, y1 = [int(v) for v in item["crop_xyxy"]]
                ref_img = source_img.crop((x0, y0, x1, y1))
                ref_path = crops_out_dir / f"{surface_id}_ref.png"
                ref_img.save(ref_path, format="PNG")
            else:
                raise ValueError(f"surface {surface_id!r} needs reference_crop_path, src_quad_xy, or crop_xyxy")

            rough_rel: str | None = None
            norm_rel: str | None = None

            if item.get("twin_texture_path"):
                tp = Path(item["twin_texture_path"])
                twin_path = (tp if tp.is_absolute() else (spec_base / tp)).resolve()
                twin_img = Image.open(twin_path).convert("RGB")
                if item.get("lock_lab", False):
                    twin_img = lock_color_to_reference_lab(twin_img, ref_img)
                    twin_path = tex_out_dir / f"{surface_id}.png"
                    twin_img.save(twin_path, format="PNG")
            elif item.get("base_texture_path"):
                bp = Path(item["base_texture_path"])
                base_path = (bp if bp.is_absolute() else (spec_base / bp)).resolve()
                base_img = Image.open(base_path).convert("RGB")
                twin_img = lock_color_to_reference_lab(base_img, ref_img)
                twin_path = tex_out_dir / f"{surface_id}.png"
                twin_img.save(twin_path, format="PNG")
            elif mode == "macro_photo_enhanced":
                tile_sz = int(item.get("tile_size", 512))
                maps = enhance_macro_texture_photo(ref_img, tile_size=tile_sz)
                twin_img = lock_color_to_reference_lab(maps["albedo"], ref_img)
                twin_path = tex_out_dir / f"{surface_id}.png"
                rough_path = tex_out_dir / f"{surface_id}_roughness.png"
                norm_path = tex_out_dir / f"{surface_id}_normal.png"
                twin_img.save(twin_path, format="PNG")
                maps["roughness"].save(rough_path, format="PNG")
                maps["normal"].save(norm_path, format="PNG")
                rough_rel = _rel_or_str(rough_path, base_root)
                norm_rel = _rel_or_str(norm_path, base_root)
            else:
                # direct_rectified_patch
                twin_img = ref_img
                twin_path = tex_out_dir / f"{surface_id}.png"
                twin_img.save(twin_path, format="PNG")

            de = compute_cie76_delta_e(ref_img, twin_img)
            strip_img = build_patch_contact_strip(
                ref_img, twin_img, panel_size=args.panel_size, label=surface_id
            )
            strip_path = strips_dir / f"{surface_id}_strip.png"
            strip_img.save(strip_path, format="PNG")
            strip_images.append(strip_img)

            entries.append(
                TextureTwinEntry(
                    surface_id=surface_id,
                    mode=mode,
                    reference_crop_path=_rel_or_str(ref_path, base_root),
                    reference_crop_sha256=sha256_file(ref_path),
                    twin_texture_path=_rel_or_str(twin_path, base_root),
                    twin_texture_sha256=sha256_file(twin_path),
                    contact_strip_path=_rel_or_str(strip_path, base_root),
                    roughness_map_path=rough_rel,
                    normal_map_path=norm_rel,
                    delta_e_ab=round(de, 4),
                    src_quad_xy=quad,
                    target_prims=tuple(str(p) for p in item.get("target_prims", [])),
                    notes=str(item.get("notes", "")),
                )
            )
    else:
        if args.source_image is None or args.crops_dir is None or args.textures_dir is None:
            raise ValueError("either --spec OR (--source-image, --crops-dir, --textures-dir) is required")
        ledger_id = args.ledger_id
        src_img_path = args.source_image.resolve()
        crops_dir = args.crops_dir.resolve()
        textures_dir = args.textures_dir.resolve()

        crop_files = sorted(
            p for p in crops_dir.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
        )
        for crop_path in crop_files:
            stem = crop_path.stem
            for suffix in ("_ref", "_crop", "_photo"):
                if stem.endswith(suffix):
                    stem = stem[: -len(suffix)]
                    break
            candidates = [
                textures_dir / f"{stem}.png",
                textures_dir / f"{stem}_albedo.png",
                textures_dir / f"{stem}.jpg",
            ]
            twin_path = next((c for c in candidates if c.is_file()), None)
            if twin_path is None:
                continue
            ref_img = Image.open(crop_path).convert("RGB")
            twin_img = Image.open(twin_path).convert("RGB")
            de = compute_cie76_delta_e(ref_img, twin_img)
            mode = (
                "direct_rectified_patch"
                if any(k in stem for k in ("ui", "screen", "sticker", "label", "foil", "wrap", "deck", "paddle"))
                else "repeated_material"
            )
            strip_img = build_patch_contact_strip(
                ref_img, twin_img, panel_size=args.panel_size, label=stem
            )
            strip_path = strips_dir / f"{stem}_strip.png"
            strip_img.save(strip_path, format="PNG")
            strip_images.append(strip_img)

            entries.append(
                TextureTwinEntry(
                    surface_id=stem,
                    mode=mode,
                    reference_crop_path=_rel_or_str(crop_path, base_root),
                    reference_crop_sha256=sha256_file(crop_path),
                    twin_texture_path=_rel_or_str(twin_path, base_root),
                    twin_texture_sha256=sha256_file(twin_path),
                    contact_strip_path=_rel_or_str(strip_path, base_root),
                    delta_e_ab=round(de, 4),
                )
            )

    ledger = TextureTwinLedger(
        ledger_id=ledger_id,
        source_image_path=_rel_or_str(src_img_path, base_root),
        source_image_sha256=sha256_file(src_img_path),
        entries=tuple(entries),
    )
    ledger.validate(max_delta_e_ab=float(args.max_delta_e))

    _stack_strips_vertically(strip_images, out_dir / "contact_sheet_all.png")
    manifest_path = out_dir / "ledger_manifest.json"
    manifest_path.write_text(
        json.dumps(ledger.to_mapping(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"built texture twin ledger ({len(entries)} entries): {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
