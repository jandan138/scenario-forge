"""Stage hash-bound raster sources for Lab2Sim Figures 2 and 3."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image, ImageEnhance


@dataclass(frozen=True)
class ResultAsset:
    name: str
    source: str
    source_sha256: str
    crop: tuple[int, int, int, int] | None
    brightness: float
    asset_sha256: str


# Figure 2: four current-delivery families that do not appear in Figure 1.
STOPPER = (
    "outputs/scientific_workbench_task05_task09_r11_20260817/packages/task05/"
    "adapters/ebench/genmanip/evidence/initial_scene"
)
GLASS_ROD = (
    "outputs/scientific_workbench_tasks_02_07_08_r10_1_20260817/packages/task07/"
    "analytical_instrumentation/adapters/ebench/genmanip/evidence/initial_scene"
)
STIR_BAR = (
    "outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r5_20260825/"
    "vr/evidence/initial_scene"
)
WATER_BATH = (
    "outputs/scientific_workbench_water_bath_tube_heat_vr_r1_20260902/"
    "vr/evidence/initial_scene"
)
# Figure 3: the two author-confirmed end-to-end agent traces.
TITRATION = (
    "outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_7_"
    "20260908/handoff/scientific_workbench_traditional_acid_base_titration_"
    "vr_r1_7/evidence/initial_scene"
)
OVEN_RETAKE = "outputs/lab2sim_fig3_retake_20260917/oven_r2"
OVEN_HANDOFF = (
    "outputs/scientific_workbench_task12_oven_unload_dual_glassware_vr_r2_"
    "20260904/handoff/scientific_workbench_task12_oven_unload_dual_glassware_vr_r2"
)

# Figure 2 detail insets are 4:3 crops; Figure 3 image panels share one aspect ratio (about 1.15:1) so that the
# manufacturer view and the admitted-USD view can be compared directly.
ASSETS = (
    ResultAsset(
        "fig2_stopper_station.png",
        f"{STOPPER}/room_corner_b.png",
        "7c0b50cc61b6125c0653b4dced3023cb3fafd9c2ffb5485defb068333bcd9e43",
        (300, 175, 1620, 918),
        1.0,
        "5297d461d69f2f36beadf3e84b372544d5e302dbaffb80716a874595eba10aab",
    ),
    ResultAsset(
        "fig2_stopper_detail.png",
        f"{STOPPER}/task_object_closeup.png",
        "23517465224ee5fb17b9739a9911ee28d92a85064e5afc080868598f6d4650d9",
        (680, 400, 1160, 760),
        1.0,
        "5e2851f968c5d221c776b22160068ab45658d2de7547334dcb71fbaa3862de67",
    ),
    ResultAsset(
        "fig2_glassrod_station.png",
        f"{GLASS_ROD}/room_corner_b.png",
        "8fde4e7fe7868668c5e67e17fc80161e3fa43105f0021690f4fd8171baded32e",
        (300, 175, 1620, 918),
        1.0,
        "62a2042bded462de2f03695ab4e4e9d023bab9b05d19573c418801a838f53920",
    ),
    ResultAsset(
        "fig2_glassrod_detail.png",
        f"{GLASS_ROD}/task_object_closeup.png",
        "574fcb96b45c5b1160bab06a1a7821ffefd1327a296441d48e29ea6452945109",
        (700, 440, 1260, 860),
        1.0,
        "63c552a3d639a9ee1ad8f31451cdc0f8ad4eb338dc499c88e15e595e2516623d",
    ),
    ResultAsset(
        "fig2_stirbar_station.png",
        f"{STIR_BAR}/workspace_closeup.png",
        "3d38e489d9a8785a48ce92b8ead41d75ba94e114d4f636d49deddbfbddaa1f63",
        None,
        1.0,
        "56f80ed7d031a19f124bdfad20d856ff1f0376593ce92b6e7f8614d3196bb4be",
    ),
    ResultAsset(
        "fig2_stirbar_detail.png",
        f"{STIR_BAR}/task_object_closeup.png",
        "dcc8bdcf676b5752a3ea5dff7fc9d1ef1b3933098f45df3b6af16b31afec3c47",
        (560, 230, 1200, 710),
        1.0,
        "11cb3e9667249596812a328582872ee6c96fda97bc7cdad8bbf62882a66a9319",
    ),
    ResultAsset(
        "fig2_waterbath_station.png",
        f"{WATER_BATH}/scene_overview.png",
        "7064ecb45bde83b107601eb5ba71100119982dcf5aaa9f340a6c47a7a4dd72f6",
        None,
        1.0,
        "7bc523525b0007c4db50ae30e666283c622a0828ba39d813bfcc1e596ea59d28",
    ),
    ResultAsset(
        "fig2_waterbath_detail.png",
        f"{WATER_BATH}/tube_immersed_in_pbd_water.png",
        "27a98d9dbb53573ea8120fb9e07b4b0d8f64b7bdcabd013baf8d3b3500ff7d1d",
        (200, 0, 920, 540),
        1.0,
        "eb6cd9a8e2406c781ad3a3935556d9f414c1bf75bc9cd021d7b2aa72a3b7c5c3",
    ),
    ResultAsset(
        "fig3_oven_real.png",
        "external_artifacts/asset_evidence/ika-oven-125/image2.png",
        "a19453cc33ec01a0502e2faeb9cc67a31f81e00b84b9e6f4bfbe408b694d48fd",
        (0, 60, 1000, 930),
        1.0,
        "32b366d229832b1d4a32d5ff4a14b5b6ec07807df0037f34becee0d5a6f95373",
    ),
    ResultAsset(
        "fig3_oven_usd.png",
        f"{OVEN_RETAKE}/hero_open_threequarter.png",
        "5a0b5d9aa410a314bb1d1e3d2e34bb4886f43c18fb9775799048e71b2e473162",
        (280, 0, 1522, 1080),
        1.0,
        "01cb8809732a8537005d8973c467d0bda4f84984d6972981c09a6ff946cc4946",
    ),
    ResultAsset(
        "fig3_burette_real.png",
        "external_artifacts/asset_evidence/traditional-titration-burette-and-stand/image3.png",
        "806e512b71edd4cbeb5be9c353f4dde503197b4f8a227a201a3aa25cce35bec4",
        (1040, 160, 1546, 600),
        1.0,
        "cc170fc91fe99321ab9ddcf590e4830232fcce615a8e6c5b757a469d379581c1",
    ),
    ResultAsset(
        "fig3_burette_usd.png",
        f"{TITRATION}/after_end_scale_burette_lower.png",
        "581c5a869dac37bb7679b7e05b6134032b8cb39eb8c7f169583932aefd2babef",
        (420, 0, 1410, 860),
        1.04,
        "f2fbe02b8a99b4103c2740183dbdc24a8dc01a84f489923d82f03af96e98d9e8",
    ),
    # Appendix "additional renders": OVEN r2 loaded shelf and the Lift2 runtime frame.
    ResultAsset(
        "app_oven_interior.png",
        f"{OVEN_HANDOFF}/evidence/initial_scene/lower_shelf_dual_glassware.png",
        "c75cd2e133e223205bab797b23bdc32778f7051293a4f70c0a7b412377c94843",
        None,
        1.0,
        "d1934d99a8fcec071fe334ecaa7b9dd141b4ce641327dfacca146ddd1a18ebd1",
    ),
    ResultAsset(
        "app_lift2_runtime.png",
        "docs/records/evidence/2026-07-05-phase11-small-multi-task-canary/"
        "remote_to_holder_phase11_executed_episode_initial_overlook.png",
        "35d90e1d89dc71ef50aaf5a3ea89caf2eb1c13224140f88982bd97cfa8577122",
        None,
        1.0,
        "3677c8e4442be6c220470e90b503f79cc5a1044e08b9f8599e9d9ae8bea42364",
    ),
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def transform_image(
    image: Image.Image,
    *,
    crop: tuple[int, int, int, int] | None,
    brightness: float,
) -> Image.Image:
    image = image.convert("RGB")
    if crop is not None:
        image = image.crop(crop)
    if brightness != 1.0:
        image = ImageEnhance.Brightness(image).enhance(brightness)
    return image


def prepare(repo_root: Path, output_dir: Path, *, check_only: bool = False) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for asset in ASSETS:
        source = repo_root / asset.source
        target = output_dir / asset.name
        if not source.is_file():
            raise FileNotFoundError(f"missing external result source: {source}")
        source_digest = file_sha256(source)
        if source_digest != asset.source_sha256:
            raise ValueError(f"source hash mismatch for {source}: {source_digest}")
        if not check_only:
            image = transform_image(
                Image.open(source),
                crop=asset.crop,
                brightness=asset.brightness,
            )
            image.save(target, optimize=True)
        if not target.is_file():
            raise FileNotFoundError(f"missing staged result asset: {target}")
        asset_digest = file_sha256(target)
        if asset.asset_sha256 and asset_digest != asset.asset_sha256:
            raise ValueError(f"asset hash mismatch for {target}: {asset_digest}")
        record = asdict(asset)
        record["asset_sha256"] = asset_digest
        record["size"] = list(Image.open(target).size)
        records.append(record)
    if not check_only:
        (output_dir / "fig23-assets.json").write_text(
            json.dumps({"assets": records}, indent=2) + "\n",
            encoding="utf-8",
        )
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
