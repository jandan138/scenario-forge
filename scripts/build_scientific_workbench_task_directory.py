#!/usr/bin/env python3
"""Build the coverage queue, ConvertAsset request, and static task directory."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from scenario_forge.generation.coverage.task_coverage import (
    build_task_coverage_plan,
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
    directory = write_task_directory(plan, releases, output_dir=args.out / "directory")
    summary = plan["summary"]
    assert isinstance(summary, Mapping)
    print(f"coverage plan: {(args.out / 'coverage_plan.yaml').resolve()}")
    print(f"ConvertAsset request: {request.resolve()}")
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


if __name__ == "__main__":
    raise SystemExit(main())
