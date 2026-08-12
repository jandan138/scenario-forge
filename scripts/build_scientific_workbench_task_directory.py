#!/usr/bin/env python3
"""Build the coverage queue, ConvertAsset request, and static task directory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from scenario_forge.generation.coverage.task_coverage import (
    build_task_coverage_plan,
    refresh_release_evidence,
    write_convertasset_admission_request,
    write_task_directory,
)
from scenario_forge.generation.source_resolver import resolve_scenario_source_bindings


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_SCHEMA_VERSION = "scientific-workbench-coverage-factory-input/v0.1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "configs/task_coverage/scientific_workbench_coverage_factory.yaml",
    )
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = args.config.resolve()
    config = _mapping(yaml.safe_load(config_path.read_text(encoding="utf-8")), "config")
    if config.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError(f"config.schema_version must be {INPUT_SCHEMA_VERSION!r}")
    catalog_path = _repo_path(_required_string(config, "catalog_path"), "catalog_path")
    bindings_path = _repo_path(_required_string(config, "source_bindings_path"), "source_bindings_path")
    catalog = _mapping(yaml.safe_load(catalog_path.read_text(encoding="utf-8")), "catalog")
    inventory = _mapping(config.get("inventory"), "config.inventory")
    recipes = _string_list(config.get("canonical_recipe_ids"), "canonical_recipe_ids")
    releases = _mappings(config.get("releases", []), "releases")
    releases.extend(
        _generated_releases(
            config.get("generated_release_manifests", []),
            catalog=catalog,
            output_dir=args.out / "directory",
        )
    )

    # Resolve through the regular source boundary before a task is queued.  This
    # verifies the referenced ConvertAsset handoffs rather than trusting ids in
    # a hand-maintained inventory alone.
    sources = resolve_scenario_source_bindings(bindings_path)
    plan = build_task_coverage_plan(
        catalog=catalog,
        inventory=inventory,
        binding_ids=sources,
        canonical_recipe_ids=recipes,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "coverage_plan.yaml").write_text(
        yaml.safe_dump(plan, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    request = write_convertasset_admission_request(
        plan, args.out / "convertasset_admission_request.yaml"
    )
    refreshed_releases = refresh_release_evidence(releases, base_dir=REPO_ROOT)
    (args.out / "release_status.yaml").write_text(
        yaml.safe_dump(refreshed_releases, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    directory = write_task_directory(plan, refreshed_releases, output_dir=args.out / "directory")
    summary = plan["summary"]
    assert isinstance(summary, Mapping)
    print(f"coverage plan: {(args.out / 'coverage_plan.yaml').resolve()}")
    print(f"ConvertAsset request: {request.resolve()}")
    print(f"release status: {(args.out / 'release_status.yaml').resolve()}")
    print(f"task directory: {directory.resolve()}")
    print(f"queued={summary['queued']} blocked={summary['blocked']}")
    return 0


def _repo_path(value: str, field: str) -> Path:
    path = (REPO_ROOT / value).resolve()
    if not path.is_file():
        raise ValueError(f"{field} does not exist: {path}")
    return path


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _mappings(value: object, field: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"{field} must be a list of mappings")
    return list(value)


def _required_string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"config.{key} must be a non-empty string")
    return value


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return list(value)


def _generated_releases(
    value: object,
    *,
    catalog: Mapping[str, object],
    output_dir: Path,
) -> list[Mapping[str, object]]:
    specs = _mappings(value, "generated_release_manifests")
    tasks = _mappings(catalog.get("tasks"), "catalog.tasks")
    task_ids = {
        int(task["source_order"]): _required_string(task, "task_id") for task in tasks
    }
    releases: list[Mapping[str, object]] = []
    for spec in specs:
        manifest_path = _repo_path(
            _required_string(spec, "path"), "generated_release_manifests.path"
        )
        manifest = _mapping(
            yaml.safe_load(manifest_path.read_text(encoding="utf-8")),
            "generated release manifest",
        )
        if manifest.get("status") != "runtime_preview_complete":
            raise ValueError(f"generated release manifest is not preview-complete: {manifest_path}")
        series = _required_string(spec, "series")
        release_date = _required_string(spec, "release_date")
        background_bindings = _mapping(
            spec.get("background_bindings"),
            "generated_release_manifests.background_bindings",
        )
        packages = _mappings(manifest.get("packages"), "generated release manifest.packages")
        task_counts: dict[int, int] = {}
        for package in packages:
            task_number = int(package["task_number"])
            task_counts[task_number] = task_counts.get(task_number, 0) + 1
        for package in packages:
            task_number = int(package["task_number"])
            if task_number not in task_ids:
                raise ValueError(f"generated release references unknown task number {task_number}")
            background_id = _required_string(package, "background_id")
            background_binding = _required_string(
                background_bindings, background_id
            )
            package_root = Path(_required_string(package, "package_root")).resolve()
            try:
                package_path = package_root.relative_to(REPO_ROOT).as_posix()
            except ValueError as exc:
                raise ValueError(f"generated package is outside repository: {package_root}") from exc
            evidence_root = package_root / "adapters/ebench/genmanip/evidence/initial_scene"
            relative_evidence = Path(os.path.relpath(evidence_root, output_dir.resolve()))
            suffix = f".{background_id}" if task_counts[task_number] > 1 else ""
            releases.append(
                {
                    "task_id": task_ids[task_number],
                    "release_id": (
                        f"{task_ids[task_number]}.v{series.removeprefix('r')}_"
                        f"{release_date}_{series}{suffix}"
                    ),
                    "package_path": package_path,
                    "background_binding": background_binding,
                    "release_status": _required_string(package, "release_status"),
                    "score_ceiling": package.get("score_ceiling"),
                    "missing_capabilities": package.get("missing_capabilities", []),
                    "promotion": "candidate",
                    "evidence": {
                        "overview_image": (relative_evidence / "scene_overview.png").as_posix(),
                        "closeup_image": (relative_evidence / "task_object_closeup.png").as_posix(),
                        "runtime_reset_gate": (relative_evidence / "visual_ready_gate.yaml").as_posix(),
                    },
                    "gates": {
                        "self_contained_package": "not_run",
                        "runtime_reset": "not_run",
                        "tabletop_placement": "not_run",
                        "visual_review": "not_run",
                        "provisional_ik": "not_run",
                    },
                }
            )
    return releases


if __name__ == "__main__":
    raise SystemExit(main())
