"""Compose a portable ScenarioSpec (v0.6) from solved relational tabletop poses.

Pure package module: no simulator SDKs, OpenUSD, or LLM client imports.
"""

from __future__ import annotations

from typing import Any, Mapping

from scenario_forge.core.scenario import ScenarioSpec
from scenario_forge.generation.layout.relational_solver import RelationalLayoutResult


OUT_OF_DOMAIN_TASK_DRAFT_SCHEMA_VERSION = "out-of-domain-task-draft/v0.1"


class SpecComposerError(ValueError):
    """Raised when a task draft and solved layout cannot form a valid ScenarioSpec."""


def compose_scenario_spec_from_solved_layout(
    task_draft: Mapping[str, Any],
    solved_layout: RelationalLayoutResult,
    *,
    exception_metadata_key: str = "tabletop_placement_exception",
) -> ScenarioSpec:
    """Bind solved tabletop poses into a validated ScenarioSpec (v0.6)."""

    if not isinstance(task_draft, Mapping):
        raise SpecComposerError("task_draft must be a mapping")
    schema_version = task_draft.get("schema_version")
    if schema_version != OUT_OF_DOMAIN_TASK_DRAFT_SCHEMA_VERSION:
        raise SpecComposerError(
            f"unsupported task_draft schema_version {schema_version!r}; "
            f"expected {OUT_OF_DOMAIN_TASK_DRAFT_SCHEMA_VERSION!r}"
        )
    if solved_layout.status != "solved" or not solved_layout.placements:
        raise SpecComposerError(
            f"cannot compose ScenarioSpec from layout with status={solved_layout.status!r}"
        )

    raw_table = task_draft.get("table")
    if not isinstance(raw_table, Mapping):
        raise SpecComposerError("task_draft.table must be a mapping")
    table_obj: dict[str, object] = {
        "id": _non_empty_str(raw_table.get("id", "table"), "task_draft.table.id"),
        "asset_id": _non_empty_str(raw_table.get("asset_id"), "task_draft.table.asset_id"),
        "source_prim_path": _non_empty_str(
            raw_table.get("source_prim_path", "/World/table"),
            "task_draft.table.source_prim_path",
        ),
        "role": "table",
        "pose": dict(_mapping(raw_table.get("pose"), "task_draft.table.pose")),
    }
    if "named_frames" in raw_table and raw_table["named_frames"] is not None:
        table_obj["named_frames"] = dict(
            _mapping(raw_table["named_frames"], "task_draft.table.named_frames")
        )

    raw_bindings = _mapping(task_draft.get("object_bindings"), "task_draft.object_bindings")
    placement_by_id = {item.object_id: item for item in solved_layout.placements}

    missing_bindings = sorted(set(placement_by_id) - set(raw_bindings))
    if missing_bindings:
        raise SpecComposerError(
            "task_draft.object_bindings missing solved layout object(s): "
            + ", ".join(missing_bindings)
        )
    extra_bindings = sorted(set(raw_bindings) - set(placement_by_id))
    if extra_bindings:
        raise SpecComposerError(
            "task_draft.object_bindings contains object(s) absent from solved layout: "
            + ", ".join(extra_bindings)
        )

    objects: list[dict[str, object]] = [table_obj]
    for placement in solved_layout.placements:
        obj_id = placement.object_id
        binding = _mapping(raw_bindings[obj_id], f"task_draft.object_bindings.{obj_id}")
        pose_dict = placement.pose.to_mapping()
        raw_scale = binding.get("scale_xyz")
        if isinstance(raw_scale, (list, tuple)):
            pose_dict["scale_xyz"] = [float(v) for v in raw_scale]

        obj_entry: dict[str, object] = {
            "id": obj_id,
            "asset_id": _non_empty_str(
                binding.get("asset_id"),
                f"task_draft.object_bindings.{obj_id}.asset_id",
            ),
            "source_prim_path": _non_empty_str(
                binding.get("source_prim_path"),
                f"task_draft.object_bindings.{obj_id}.source_prim_path",
            ),
            "role": _non_empty_str(
                binding.get("role", placement.role),
                f"task_draft.object_bindings.{obj_id}.role",
            ),
            "pose": pose_dict,
        }
        if "named_frames" in binding and binding["named_frames"] is not None:
            obj_entry["named_frames"] = dict(
                _mapping(
                    binding["named_frames"],
                    f"task_draft.object_bindings.{obj_id}.named_frames",
                )
            )

        merged_meta: dict[str, object] = {}
        if "metadata" in binding and binding["metadata"] is not None:
            merged_meta.update(
                _mapping(binding["metadata"], f"task_draft.object_bindings.{obj_id}.metadata")
            )
        if placement.robot_side_exception is not None and exception_metadata_key not in merged_meta:
            merged_meta[exception_metadata_key] = placement.robot_side_exception
        if merged_meta:
            obj_entry["metadata"] = merged_meta

        objects.append(obj_entry)

    target_schema_version = str(task_draft.get("target_schema_version", "scenario-spec/v0.6"))
    raw_spec: dict[str, object] = {
        "schema_version": target_schema_version,
        "scenario_id": task_draft.get("scenario_id"),
        "domain": task_draft.get("domain"),
        "task_family": task_draft.get("task_family"),
        "instruction": task_draft.get("instruction"),
        "scene": task_draft.get("scene"),
        "objects": objects,
        "robot": task_draft.get("robot"),
        "steps": task_draft.get("steps"),
        "invariants": list(task_draft.get("invariants", [])),
        "success": task_draft.get("success"),
        "max_steps": task_draft.get("max_steps", 1800),
        "seed": task_draft.get("seed", str(solved_layout.seed).zfill(3)),
    }

    try:
        return ScenarioSpec.from_mapping(raw_spec)
    except ValueError as exc:
        raise SpecComposerError(f"composed ScenarioSpec failed validation: {exc}") from exc


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SpecComposerError(f"{field} must be a mapping")
    return value


def _non_empty_str(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpecComposerError(f"{field} must be a non-empty string")
    return value
