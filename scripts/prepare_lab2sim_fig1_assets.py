"""Stage ignored external evidence images for the Lab2Sim Figure 1 build."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re

from PIL import Image, ImageEnhance


@dataclass(frozen=True)
class FigureAsset:
    name: str
    source: str
    source_sha256: str
    transform: str
    asset_sha256: str


ASSETS = (
    FigureAsset(
        name="ika_catalog_closed.png",
        source="external_artifacts/asset_evidence/ika-oven-125/image1.png",
        source_sha256="6076b4ea89378556a0860e2cbd9c4146572fbe1ddfe32893427c56afcf13ec8d",
        transform="copy",
        asset_sha256="700b6b22facb9f5795fbdfe3bd179dda4b3edce60cb1c01bb56407e9d5ada1c3",
    ),
    FigureAsset(
        name="fehling_r10_hero.png",
        source="outputs/lab2sim_fig1_retake_20260917/fehling_r10/t30_hero_tabletop.png",
        source_sha256="e7f585a431b72a2fbd2da6bf8fdc32d456bbce1a7f26df1d843afc734c7a7f77",
        transform="copy",
        asset_sha256="2be4434170a215adf7cfa557a0c20f0bbc4caf1f9d6c70147856b31f7a1bb91e",
    ),
    FigureAsset(
        name="powder_r4_hero.png",
        source="outputs/task09_powder_bottle_r4_20260911/video/close_0960.png",
        source_sha256="6563f9f52e361d849e65343260f792ff6c68d9d8f019ecf5e58c0c93a67c8278",
        transform="crop_y69_789",
        asset_sha256="8eaabe7941d3ce79f79d7f6a318e9603531a4c7223a8125028b620ce24b72e2d",
    ),
    FigureAsset(
        name="titration_r17_hero.png",
        source=(
            "outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_7_"
            "20260908/handoff/scientific_workbench_traditional_acid_base_titration_"
            "vr_r1_7/evidence/initial_scene/after_end_scale_scene_overview.png"
        ),
        source_sha256="6dbb2964df988a37b48af60beaac7e5ab9a648d0c6725fc07474c2ac666af1d9",
        transform="copy",
        asset_sha256="99cbde05e783d48413f4d4655f043b9fec283142f8158737b56b94c3bf890e85",
    ),
    FigureAsset(
        name="ika_catalog_open.png",
        source="external_artifacts/asset_evidence/ika-oven-125/image2.png",
        source_sha256="a19453cc33ec01a0502e2faeb9cc67a31f81e00b84b9e6f4bfbe408b694d48fd",
        transform="copy",
        asset_sha256="071d25780e901793006eda3fe072aa82517cf60662d2dc1749c6c0d14626c55c",
    ),
    FigureAsset(
        name="oven_r2_hero.png",
        source=(
            "outputs/scientific_workbench_task12_oven_unload_dual_glassware_vr_r2_"
            "20260904/handoff/scientific_workbench_task12_oven_unload_dual_glassware_"
            "vr_r2/evidence/initial_scene/open_oven_station.png"
        ),
        source_sha256="59d42ae225a02ab12c21390fbd2bc0283ae857557bd11b884cdce0632e39bb44",
        transform="brightness_1_40",
        asset_sha256="1c574eee81eee6ed5c0247f7d68fed110b799f642598b10cbe0e32e7375d2cb8",
    ),
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def transform_image(image: Image.Image, transform: str) -> Image.Image:
    image = image.convert("RGB")
    if transform == "copy":
        return image
    if transform == "crop_y69_789":
        if image.size != (1280, 800):
            raise ValueError(f"powder source must be 1280x800, got {image.size}")
        return image.crop((0, 69, 1280, 789))
    brightness = re.fullmatch(r"brightness_(\d+)_(\d+)", transform)
    if brightness:
        factor = float(f"{brightness.group(1)}.{brightness.group(2)}")
        return ImageEnhance.Brightness(image).enhance(factor)
    raise ValueError(f"unknown transform: {transform}")


def prepare(repo_root: Path, output_dir: Path, *, check_only: bool = False) -> list[dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for asset in ASSETS:
        source = repo_root / asset.source
        target = output_dir / asset.name
        if not source.is_file():
            raise FileNotFoundError(f"missing external Figure 1 source: {source}")
        source_digest = file_sha256(source)
        if source_digest != asset.source_sha256:
            raise ValueError(f"source hash mismatch for {source}: {source_digest}")
        if not check_only:
            transformed = transform_image(Image.open(source), asset.transform)
            transformed.save(target, optimize=True)
        if not target.is_file():
            raise FileNotFoundError(f"missing staged Figure 1 asset: {target}")
        asset_digest = file_sha256(target)
        if asset_digest != asset.asset_sha256:
            raise ValueError(f"asset hash mismatch for {target}: {asset_digest}")
        record = asdict(asset)
        record["size"] = list(Image.open(target).size)
        records.append(record)
    manifest = output_dir / "fig1-assets.json"
    if not check_only:
        manifest.write_text(json.dumps({"assets": records}, indent=2) + "\n", encoding="utf-8")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir
        else repo_root / "paper/venues/iclr2027/figures/lab2sim/source"
    )
    records = prepare(repo_root, output_dir, check_only=args.check)
    print(json.dumps({"status": "pass", "assets": len(records), "output_dir": str(output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
