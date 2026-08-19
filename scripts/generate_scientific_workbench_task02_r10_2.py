#!/usr/bin/env python3
"""Upgrade Task 02's four-fill r10.1 packages to web-standard glass r10.2."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Any
import zipfile

import yaml

_BOOTSTRAP_ROOT = Path(__file__).resolve().parents[1]
for _path in (_BOOTSTRAP_ROOT, _BOOTSTRAP_ROOT / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import scripts.generate_scientific_workbench_r10_1 as r10_1  # noqa: E402
import scripts.generate_scientific_workbench_task02_r10_fill_sweep as r10  # noqa: E402
import scripts.generate_scientific_workbench_task02_r8 as r8  # noqa: E402
from scenario_forge.adapters.ebench.preview import (  # noqa: E402
    write_genmanip_preview_request,
)
from scenario_forge.artifacts.usd_handoff import (  # noqa: E402
    refresh_usd_handoff_archive,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FILL_IDS = ("fill20", "fill40", "fill60", "fill80")
DEFAULT_SOURCE = (
    REPO_ROOT
    / "outputs/scientific_workbench_tasks_02_07_08_r10_1_20260817/packages/task02"
)
DEFAULT_VISUAL_ROOT = Path(
    "/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/"
    "scientific_workbench_glass_web_standard_20260819/packages"
)
DEFAULT_CYLINDER_VISUAL = (
    DEFAULT_VISUAL_ROOT / "graduated_cylinder_250ml_glass_web_standard_v2"
)
DEFAULT_BEAKER_VISUAL = DEFAULT_VISUAL_ROOT / "beaker_325ml_glass_web_standard_v1"
DEFAULT_OUT = REPO_ROOT / "outputs/scientific_workbench_task02_r10_2_fill_sweep_20260819"
ARCHIVE_ID = "task02_r10_2_fill_sweep"

SOURCE_REFERENCE = (
    "prepend references = @deps/source/asset.usd@"
    "</World/GraduatedCylinder250ml>"
)
TARGET_REFERENCE = (
    "prepend references = @deps/target/asset.usd@</World/Beaker325ml>"
)
SOURCE_COMPOSED_REFERENCES = """prepend references = [
                @deps/source_visual/overlays/visual_material.usda@</World/GraduatedCylinder250ml>,
                @deps/source/asset.usd@</World/GraduatedCylinder250ml>,
            ]"""
TARGET_COMPOSED_REFERENCES = """prepend references = [
                @deps/target_visual/overlays/visual_material.usda@</World/Beaker325ml>,
                @deps/target/asset.usd@</World/Beaker325ml>,
            ]"""


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _tree_sha(path: Path) -> str:
    digest = sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _visual_manifest(package: Path) -> dict[str, Any]:
    manifest_path = package / "evidence/manifest.json"
    audit_path = package / "evidence/visual_material_only_audit.json"
    overlay_path = package / "overlays/visual_material.usda"
    if not all(path.is_file() for path in (manifest_path, audit_path, overlay_path)):
        raise ValueError(f"visual package is incomplete: {package}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    visual = manifest.get("visual_material_profile", {})
    if (
        manifest.get("overall_status") != "pass"
        or manifest.get("blocked_reasons")
        or manifest.get("runtime_evidence", {}).get("status") != "pass"
        or visual.get("schema_version") != "aan.visual_material_profile.v2"
        or visual.get("status") != "pass"
        or audit.get("status") != "pass"
    ):
        raise ValueError(f"visual package is not formally admitted: {package}")
    return manifest


def compose_visual_material_references(component_text: str) -> str:
    if component_text.count(SOURCE_REFERENCE) != 1:
        raise ValueError("component must contain exactly one PBD source reference")
    if component_text.count(TARGET_REFERENCE) != 1:
        raise ValueError("component must contain exactly one PBD target reference")
    return component_text.replace(
        SOURCE_REFERENCE, SOURCE_COMPOSED_REFERENCES
    ).replace(TARGET_REFERENCE, TARGET_COMPOSED_REFERENCES)


def _transfer_roots(package: Path) -> tuple[Path, Path]:
    ebench_components = tuple(
        package.glob(
            "ebench/assets/scene_usds/scenario_forge/*/source_bundle/transfer/component.usda"
        )
    )
    if len(ebench_components) != 1:
        raise ValueError("expected exactly one eBench transfer component")
    vr_component = package / "vr/deps/transfer/component.usda"
    if not vr_component.is_file():
        raise ValueError("VR transfer component is missing")
    return ebench_components[0].parent, vr_component.parent


def _compose_transfer_root(
    root: Path,
    *,
    cylinder_visual_package: Path,
    beaker_visual_package: Path,
    cylinder_manifest: dict[str, Any],
    beaker_manifest: dict[str, Any],
) -> dict[str, Any]:
    source_before = _tree_sha(root / "deps/source")
    target_before = _tree_sha(root / "deps/target")
    for name, source in (
        ("source_visual", cylinder_visual_package),
        ("target_visual", beaker_visual_package),
    ):
        destination = root / "deps" / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    component = root / "component.usda"
    component.write_text(
        compose_visual_material_references(component.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    source_after = _tree_sha(root / "deps/source")
    target_after = _tree_sha(root / "deps/target")
    if (source_before, target_before) != (source_after, target_after):
        raise ValueError("PBD source or target package changed during visual composition")
    evidence = {
        "schema_version": "scenario-forge-pbd-visual-composition/v0.1",
        "status": "pass",
        "composition_order": "visual_material_reference_stronger_than_pbd_asset_reference",
        "pbd_dependencies": {
            "source_tree_sha256_before": source_before,
            "source_tree_sha256_after": source_after,
            "target_tree_sha256_before": target_before,
            "target_tree_sha256_after": target_after,
        },
        "visual_packages": {
            "source": {
                "asset_id": cylinder_manifest["asset_id"],
                "package_id": cylinder_manifest["package_id"],
                "manifest_sha256": _sha(
                    cylinder_visual_package / "evidence/manifest.json"
                ),
            },
            "target": {
                "asset_id": beaker_manifest["asset_id"],
                "package_id": beaker_manifest["package_id"],
                "manifest_sha256": _sha(
                    beaker_visual_package / "evidence/manifest.json"
                ),
            },
        },
        "claim_boundary": (
            "Visual-material composition only. PBD vessel packages are byte-identical; "
            "no collider, mass, inertia, particle, robot-policy, or benchmark claim is added."
        ),
    }
    evidence_path = root / "evidence/visual_material_composition.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return evidence


def _source_asset_record(
    manifest: dict[str, Any], *, canonical_usd: str
) -> dict[str, Any]:
    manifest_sha = sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "asset_id": manifest["asset_id"],
        "canonical_usd": canonical_usd,
        "license": "LicenseRef-Project-Internal-Source-Bound",
        "redistributable": True,
        "sha256": "sha256:" + manifest_sha,
        "upstream_package": {
            "producer": "ConvertAsset",
            "package_id": manifest["package_id"],
            "manifest_sha256": "sha256:" + manifest_sha,
            "metadata": {
                "producer_asset_role": manifest.get("asset_role"),
                "visual_material_profile": manifest["visual_material_profile"],
            },
        },
    }


def _remove_stale_runtime_evidence(package: Path) -> None:
    for path in (
        package / "ebench/evidence/product_smoke",
        package / "ebench/evidence/initial_scene",
        package / "evidence/product_smoke",
        package / "evidence/vr_open_smoke",
        package / "vr/evidence/open_smoke",
    ):
        if path.exists():
            shutil.rmtree(path)


def upgrade_variant(
    source: Path,
    destination: Path,
    *,
    cylinder_visual_package: Path,
    beaker_visual_package: Path,
    refresh_preview_request: bool = True,
) -> Path:
    source = source.resolve()
    destination = destination.resolve()
    cylinder_visual_package = cylinder_visual_package.resolve()
    beaker_visual_package = beaker_visual_package.resolve()
    cylinder_manifest = _visual_manifest(cylinder_visual_package)
    beaker_manifest = _visual_manifest(beaker_visual_package)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

    compositions = []
    for root in _transfer_roots(destination):
        compositions.append(
            _compose_transfer_root(
                root,
                cylinder_visual_package=cylinder_visual_package,
                beaker_visual_package=beaker_visual_package,
                cylinder_manifest=cylinder_manifest,
                beaker_manifest=beaker_manifest,
            )
        )

    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["release"] = "r10.2"
    manifest["supersedes"] = "r10.1"
    manifest["status"] = "package_ready_runtime_validation_pending"
    manifest.pop("runtime_gates", None)
    manifest["claims"]["ebench_load_reset_8s"] = "pending"
    manifest["vr_contract"]["status"] = "static_pass_runtime_pending"
    manifest["visual_materials"] = {
        "graduated_cylinder": {
            "package_id": cylinder_manifest["package_id"],
            "profile": cylinder_manifest["visual_material_profile"],
        },
        "beaker": {
            "package_id": beaker_manifest["package_id"],
            "profile": beaker_manifest["visual_material_profile"],
        },
    }
    manifest["pbd_visual_composition"] = {
        "status": "pass",
        "consumer_copies": len(compositions),
        "pbd_dependencies_byte_identical": True,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    config = r10_1.task02_vr_config(
        scenario_id=str(manifest["scenario_id"]),
        particle_count=int(manifest["particle_count"]),
        include_robot_physics_overrides=False,
    )
    (destination / "vr/task_config.py").write_text(config, encoding="utf-8")
    (destination / "vr/config.py").write_text(config, encoding="utf-8")
    parity_path = destination / "vr/parity_manifest.json"
    parity = json.loads(parity_path.read_text(encoding="utf-8"))
    parity["release"] = "r10.2"
    parity["status"] = "static_pass_runtime_pending"
    parity["robot_physics_overrides"] = "omitted"
    parity["artifacts"]["scene_usd"] = {
        "path": "scene.usd",
        "sha256": "sha256:" + _sha(destination / "vr/scene.usd"),
    }
    parity["artifacts"]["task_config"] = {
        "path": "task_config.py",
        "sha256": "sha256:" + _sha(destination / "vr/task_config.py"),
    }
    parity_path.write_text(
        json.dumps(parity, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    collected_manifest_path = destination / "ebench/package_manifest.json"
    collected_manifest = json.loads(collected_manifest_path.read_text(encoding="utf-8"))
    collected_manifest["source_assets"] = [
        *[
            item
            for item in collected_manifest["source_assets"]
            if item.get("asset_id")
            not in {cylinder_manifest["asset_id"], beaker_manifest["asset_id"]}
        ],
        _source_asset_record(
            cylinder_manifest,
            canonical_usd="source_bundle/transfer/deps/source_visual/asset.usd",
        ),
        _source_asset_record(
            beaker_manifest,
            canonical_usd="source_bundle/transfer/deps/target_visual/asset.usd",
        ),
    ]
    collected_manifest["release_status"] = "runtime_validation_pending"
    collected_manifest_path.write_text(
        json.dumps(collected_manifest, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    _remove_stale_runtime_evidence(destination)
    if refresh_preview_request:
        write_genmanip_preview_request(destination / "ebench")
    r8.refresh_hashes(destination)
    return destination


def build_packages(
    *,
    source_root: Path = DEFAULT_SOURCE,
    output_dir: Path = DEFAULT_OUT,
    cylinder_visual_package: Path = DEFAULT_CYLINDER_VISUAL,
    beaker_visual_package: Path = DEFAULT_BEAKER_VISUAL,
) -> dict[str, Path]:
    packages: dict[str, Path] = {}
    for fill_id in FILL_IDS:
        packages[fill_id] = upgrade_variant(
            source_root / fill_id,
            output_dir / "packages" / fill_id,
            cylinder_visual_package=cylinder_visual_package,
            beaker_visual_package=beaker_visual_package,
        )
    return packages


def _write_preliminary_readme(root: Path) -> None:
    rows = "\n".join(
        f"| `{fill}` | `variants/{fill}/ebench/scene.usd` | "
        f"`variants/{fill}/vr/scene.usd` |" for fill in FILL_IDS
    )
    (root / "README_CN.md").write_text(
        f"""# Task 02 r10.2 四档液体双端包

当前状态：`package_ready_runtime_validation_pending`。USD、相对依赖、玻璃材质与 VR
配置已经升级；Isaac Sim 4.1 四档回归证据随后补齐，不能将本首包描述为新一轮运行验证通过。

量筒使用 `glass_web_standard_v2`，烧杯使用 `glass_web_standard_v1`。原 GPU-PBD
碰撞包、粒子数、液体外观及液位不变。默认使用 `fill40`。

| 档位 | eBench USD | VR USD |
| --- | --- | --- |
{rows}

eBench 配置为同目录 `config.yaml`；VR 配置为同目录 `task_config.py`。
VR USD 直接打开时 defaultPrim 是 `/World` 并自带 DomeLight；运行时由 loader 挂载到
`/World/_scene`。USD 不内嵌机器人。
""",
        encoding="utf-8",
    )


def _write_checksums(root: Path) -> None:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        lines.append(f"{_sha(path)}  {path.relative_to(root).as_posix()}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _zip_tree(root: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            info = zipfile.ZipInfo(
                (Path(root.name) / path.relative_to(root)).as_posix(),
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    temporary.replace(destination)


def build_preliminary_handoff(
    packages: dict[str, Path], *, output_dir: Path = DEFAULT_OUT
) -> Path:
    root = output_dir / "handoff" / ARCHIVE_ID
    if root.exists():
        shutil.rmtree(root)
    for fill_id, package in packages.items():
        destination = root / "variants" / fill_id
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package / "ebench", destination / "ebench")
        shutil.copytree(package / "vr", destination / "vr")
        shutil.copy2(package / "manifest.json", destination / "manifest.json")
    manifest = {
        "schema_version": "scenario-forge-dual-consumer-variant-handoff/v0.2",
        "archive_id": ARCHIVE_ID,
        "release": "r10.2",
        "status": "package_ready_runtime_validation_pending",
        "default_variant": "fill40",
        "variants": list(FILL_IDS),
        "claim_boundary": (
            "Package shape and admitted visual composition complete; new Isaac 4.1 "
            "runtime validation and robot-policy success are not claimed yet."
        ),
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    _write_preliminary_readme(root)
    _write_checksums(root)
    destination = output_dir / "handoff" / f"{ARCHIVE_ID}.zip"
    _zip_tree(root, destination)
    return destination


def finalize_validated_package(package: Path) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "ebench_zero_action_physics_8s": "pass",
        "vr_usd_open_isaac41": "pass",
    }
    if manifest.get("runtime_gates") != required:
        raise ValueError(f"runtime gates are incomplete: {package}")
    visual_gate = package / "ebench/evidence/initial_scene/visual_ready_gate.yaml"
    if yaml.safe_load(visual_gate.read_text(encoding="utf-8")).get("status") != "passed":
        raise ValueError(f"visual gate is incomplete: {package}")
    manifest["status"] = "runtime_complete_visual_ready"
    manifest["vr_contract"]["status"] = "runtime_pass"
    manifest["visual_review"] = {
        "status": "pass_with_observation",
        "review_mode": "local_human_style_not_independent",
        "observation": (
            "The admitted thick-wall OmniGlass is transparent and the cylinder connector "
            "is no longer cyan plastic. Against the dark worktop it renders darker than the "
            "previous material; this is visible reflection/refraction, not a missing-material "
            "or opaque fallback. The four fill levels remain distinguishable."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    parity_path = package / "vr/parity_manifest.json"
    parity = json.loads(parity_path.read_text(encoding="utf-8"))
    parity["status"] = "runtime_pass"
    parity["open_smoke"] = "evidence/open_smoke/report.json"
    parity_path.write_text(
        json.dumps(parity, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    r8.refresh_hashes(package)


def finalize_validated_handoff(
    packages: dict[str, Path], *, output_dir: Path = DEFAULT_OUT
) -> Path:
    for package in packages.values():
        finalize_validated_package(package)
    overviews = {
        fill_id: package / "ebench/evidence/initial_scene/scene_overview.png"
        for fill_id, package in packages.items()
    }
    if not all(path.is_file() for path in overviews.values()):
        raise ValueError("all four fixed-camera overview renders are required")
    archive = r10.finalize_r10_handoff(
        packages=packages,
        output_dir=output_dir,
        fill_level_ids=FILL_IDS,
        default_variant="fill40",
        archive_id=ARCHIVE_ID,
        visual_ready="pass",
        overviews=overviews,
    )
    manifest_path = archive.root / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "release": "r10.2",
            "status": "runtime_complete_visual_ready",
            "visual_materials": {
                "graduated_cylinder": "glass_web_standard_v2",
                "beaker": "glass_web_standard_v1",
            },
            "visual_review": "pass_with_observation",
        }
    )
    manifest_path.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    _write_preliminary_readme(archive.root)
    readme = archive.root / "README_CN.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "当前状态：`package_ready_runtime_validation_pending`。USD、相对依赖、玻璃材质与 VR\n"
            "配置已经升级；Isaac Sim 4.1 四档回归证据随后补齐，不能将本首包描述为新一轮运行验证通过。",
            "当前状态：`runtime_complete_visual_ready`。四档均通过 Isaac Sim 4.1 eBench\n"
            "加载/复位/960 步零动作检查、VR direct-open 与固定机位视觉 gate。",
        )
        + "\n预览：`evidence/fill_sweep_closeup_quad.png` 和 "
        "`evidence/fill_sweep_overview_quad.png`。\n",
        encoding="utf-8",
    )
    review = {
        "schema_version": "scenario-forge-render-visual-review/v0.1",
        "status": "pass_with_observation",
        "review_mode": "local_human_style_not_independent",
        "images": {
            fill_id: f"variants/{fill_id}/evidence/task_object_closeup.png"
            for fill_id in FILL_IDS
        },
        "visible_findings": [
            "All four glass vessels are visible and identifiable.",
            "The cylinder body, inner bottom, spout, rim, hex base, and round connector are transparent; the connector has no cyan-plastic appearance.",
            "The beaker body, rim, and spout are transparent with no missing-material fallback.",
            "Fill levels increase monotonically from fill20 to fill80.",
            "Thick-wall glass and liquid appear dark against the navy worktop under this RTX lighting; this is non-blocking but should be considered when judging aesthetics.",
        ],
        "claim_boundary": "Visible render QA only; not an independent blind review or robot-policy result.",
    }
    evidence = archive.root / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "visual_review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    refresh_usd_handoff_archive(archive)
    return archive.zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cylinder-visual", type=Path, default=DEFAULT_CYLINDER_VISUAL)
    parser.add_argument("--beaker-visual", type=Path, default=DEFAULT_BEAKER_VISUAL)
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args()
    if args.finalize_existing:
        packages = {fill_id: args.out / "packages" / fill_id for fill_id in FILL_IDS}
        print(finalize_validated_handoff(packages, output_dir=args.out))
        return 0
    packages = build_packages(
        source_root=args.source_root,
        output_dir=args.out,
        cylinder_visual_package=args.cylinder_visual,
        beaker_visual_package=args.beaker_visual,
    )
    print(build_preliminary_handoff(packages, output_dir=args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
