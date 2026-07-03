from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scenario_forge.assets.lock import AssetLockError, check_asset_lock, generate_asset_lock, write_asset_lock
from scenario_forge.assets.manifest import AssetManifestError
from scenario_forge.package import PackageError, load_package_manifest, validate_package
from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.scene.usd_compiler import USDSceneCompilerError, compile_usd_scene
from scenario_forge.validation.usd_checks import check_usd_scene


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scenario-forge",
        description="Generate and validate evaluation-ready embodied scenario packages.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    package_parser = subparsers.add_parser("package", help="Scenario package commands")
    package_subparsers = package_parser.add_subparsers(dest="package_command", required=True)

    scaffold_parser = package_subparsers.add_parser("scaffold", help="Create a starter package")
    scaffold_parser.add_argument("--out", required=True, help="Output package directory")

    check_parser = package_subparsers.add_parser("check", help="Validate a scenario package")
    check_parser.add_argument("package_dir", help="Package directory containing manifest.yaml")
    check_parser.add_argument(
        "--require-asset-lock",
        action="store_true",
        help="Fail if locks/asset_lock.yaml is missing or invalid",
    )

    assets_parser = subparsers.add_parser("assets", help="Asset manifest and lock commands")
    assets_subparsers = assets_parser.add_subparsers(dest="assets_command", required=True)

    assets_lock_parser = assets_subparsers.add_parser("lock", help="Generate asset_lock.yaml")
    assets_lock_parser.add_argument("package_dir", help="Package directory")

    assets_check_parser = assets_subparsers.add_parser("check", help="Validate asset_lock.yaml")
    assets_check_parser.add_argument("package_dir", help="Package directory")

    scene_parser = subparsers.add_parser("scene", help="USD scene compiler commands")
    scene_subparsers = scene_parser.add_subparsers(dest="scene_command", required=True)

    scene_compile_parser = scene_subparsers.add_parser(
        "compile", help="Compile scene instances to scene/main.usda"
    )
    scene_compile_parser.add_argument("--instances", required=True, help="scene/instances.yaml")
    scene_compile_parser.add_argument("--asset-lock", required=True, help="locks/asset_lock.yaml")
    scene_compile_parser.add_argument("--out", required=True, help="Output USDA scene path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "package" and args.package_command == "scaffold":
        out_dir = scaffold_starter_package(Path(args.out))
        print(f"Created starter package: {out_dir}")
        return 0

    if args.command == "package" and args.package_command == "check":
        report = validate_package(Path(args.package_dir), require_asset_lock=args.require_asset_lock)
        for message in report.messages:
            print(message)
        if report.ok:
            print("Package OK")
            return 0
        return 1

    if args.command == "assets" and args.assets_command == "lock":
        try:
            lock_path = write_asset_lock(
                Path(args.package_dir), generate_asset_lock(Path(args.package_dir))
            )
        except (AssetLockError, AssetManifestError) as exc:
            print(exc)
            return 1
        print(f"Asset lock written: {lock_path}")
        return 0

    if args.command == "assets" and args.assets_command == "check":
        package_dir = Path(args.package_dir)
        report = check_asset_lock(package_dir, scene_paths=_package_scene_paths(package_dir))
        for message in report.messages:
            print(message)
        if report.ok:
            print("Asset lock OK")
            return 0
        return 1

    if args.command == "scene" and args.scene_command == "compile":
        instances_path = Path(args.instances)
        asset_lock_path = Path(args.asset_lock)
        out_path = Path(args.out)
        package_dir = _package_root_from_asset_lock(asset_lock_path)
        try:
            result = compile_usd_scene(
                package_root=package_dir,
                instances_path=instances_path,
                asset_lock_path=asset_lock_path,
                out_path=out_path,
            )
        except USDSceneCompilerError as exc:
            print(exc)
            return 1

        predicates_path = package_dir / "task" / "predicates.yaml"
        static_report = check_usd_scene(
            package_root=package_dir,
            scene_path=result.path,
            asset_lock_path=asset_lock_path,
            instances_path=instances_path,
            predicates_path=predicates_path if predicates_path.exists() else None,
        )
        for message in static_report.messages:
            print(message)
        if not static_report.ok:
            return 1

        print(f"Scene written: {result.path}")
        print("USD static check OK")
        return 0

    parser.error("unreachable command")
    return 2


def _package_scene_paths(package_dir: Path) -> tuple[str, ...]:
    try:
        manifest = load_package_manifest(package_dir)
    except PackageError:
        return ()
    scene_path = manifest.scene_path
    return (scene_path,) if scene_path is not None else ()


def _package_root_from_asset_lock(asset_lock_path: Path) -> Path:
    if asset_lock_path.parent.name == "locks":
        return asset_lock_path.parent.parent
    return asset_lock_path.parent


if __name__ == "__main__":
    sys.exit(main())
