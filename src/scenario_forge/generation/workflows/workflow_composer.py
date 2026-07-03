from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.generation.skills.skill_library import (
    SkillLibraryError,
    default_domain_pack_dir,
    load_skill_library,
)

WORKFLOW_SCHEMA_VERSION = "workflow/v0.1"
TASK_SCHEMA_VERSION = "task/v0.2"
TASK_GRAPH_SCHEMA_VERSION = "task-graph/v0.2"
PREDICATES_SCHEMA_VERSION = "predicates/v0.2"
SAFETY_RULES_SCHEMA_VERSION = "safety-rules/v0.2"
METRICS_SCHEMA_VERSION = "metrics/v0.2"


class WorkflowComposeError(ValueError):
    """Raised when workflow artifacts cannot be generated."""


@dataclass(frozen=True)
class WorkflowComposeResult:
    package_root: Path
    task_family: str
    required_asset_roles: tuple[str, ...]
    artifacts: tuple[Path, ...]


def compose_workflow_artifacts(
    package_root: str | Path,
    task_family: str,
    robot_profile: str = "franka_panda_tabletop_v1",
    bindings: dict[str, str] | None = None,
    domain_pack_dir: str | Path | None = None,
) -> WorkflowComposeResult:
    root = Path(package_root)
    pack_dir = Path(domain_pack_dir) if domain_pack_dir is not None else default_domain_pack_dir()
    template = _load_template(pack_dir, task_family)
    raw_bindings = bindings or _default_bindings(template)

    skill_ids = tuple(_node_skill(node) for node in template["nodes"])
    try:
        library = load_skill_library(pack_dir)
        required_capabilities = library.required_capabilities_for_skills(skill_ids)
        missing = library.missing_robot_capabilities(robot_profile, required_capabilities)
    except SkillLibraryError as exc:
        raise WorkflowComposeError(str(exc)) from exc
    if missing:
        raise WorkflowComposeError(
            f"Robot profile {robot_profile} missing capabilities: {', '.join(missing)}"
        )

    required_assets = _required_assets(template)
    required_roles = tuple(str(asset["role"]) for asset in required_assets)
    _validate_bindings(required_roles, raw_bindings)

    nodes = [_resolve_placeholders(node, raw_bindings) for node in template["nodes"]]
    edges = [_resolve_placeholders(edge, raw_bindings) for edge in template.get("edges", [])]
    predicates = [
        _resolve_placeholders(predicate, raw_bindings)
        for predicate in template.get("success_predicates", [])
    ]
    safety_rules = [
        _resolve_placeholders(rule, raw_bindings) for rule in template.get("safety_rules", [])
    ]
    instruction = _template_string(template, "instruction")

    generation_plan = _load_yaml_if_exists(root / "generation_plan.yaml")
    generation_plan.update(
        {
            "schema_version": generation_plan.get(
                "schema_version", "scenario-generation-plan/v0.2"
            ),
            "task_family": task_family,
            "robot_profile": robot_profile,
            "workflow": {
                "schema_version": WORKFLOW_SCHEMA_VERSION,
                "template": task_family,
                "skill_sequence": list(skill_ids),
                "required_capabilities": list(required_capabilities),
            },
            "required_assets": required_assets,
            "workflow_bindings": dict(sorted(raw_bindings.items())),
        }
    )

    artifacts = (
        write_yaml_artifact(root / "generation_plan.yaml", generation_plan),
        write_yaml_artifact(
            root / "task" / "task.yaml",
            {
                "schema_version": TASK_SCHEMA_VERSION,
                "task_id": task_family,
                "task_family": task_family,
                "instruction": instruction,
                "robot_profile": robot_profile,
                "bindings": dict(sorted(raw_bindings.items())),
            },
        ),
        write_yaml_artifact(
            root / "task" / "task_graph.yaml",
            {
                "schema_version": TASK_GRAPH_SCHEMA_VERSION,
                "task_graph_id": f"{task_family}_graph",
                "task_family": task_family,
                "nodes": nodes,
                "edges": edges,
            },
        ),
        write_yaml_artifact(
            root / "task" / "predicates.yaml",
            {
                "schema_version": PREDICATES_SCHEMA_VERSION,
                "success_predicates": predicates,
            },
        ),
        write_yaml_artifact(
            root / "task" / "safety_rules.yaml",
            {
                "schema_version": SAFETY_RULES_SCHEMA_VERSION,
                "safety_rules": safety_rules,
            },
        ),
        write_yaml_artifact(
            root / "metrics" / "metrics.yaml",
            {
                "schema_version": METRICS_SCHEMA_VERSION,
                "metrics": [_primary_metric(predicates[0] if predicates else {"type": "task_done"})],
            },
        ),
    )
    return WorkflowComposeResult(
        package_root=root,
        task_family=task_family,
        required_asset_roles=required_roles,
        artifacts=artifacts,
    )


def _load_template(pack_dir: Path, task_family: str) -> dict[str, Any]:
    path = pack_dir / "workflow_templates.yaml"
    if not path.exists():
        raise WorkflowComposeError(f"Missing workflow templates file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise WorkflowComposeError(f"Workflow templates file must be a mapping: {path}")
    if data.get("schema_version") != "workflow-templates/v0.1":
        raise WorkflowComposeError("Unsupported workflow templates schema_version")
    templates = data.get("templates")
    if not isinstance(templates, dict):
        raise WorkflowComposeError("Workflow templates field 'templates' must be a mapping")
    template = templates.get(task_family)
    if not isinstance(template, dict):
        raise WorkflowComposeError(f"Unsupported task_family: {task_family}")
    return template


def _required_assets(template: dict[str, Any]) -> list[dict[str, Any]]:
    value = template.get("required_assets")
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise WorkflowComposeError("Workflow template field 'required_assets' must be a list")
    return [dict(item) for item in value]


def _node_skill(node: Any) -> str:
    if not isinstance(node, dict) or not isinstance(node.get("skill"), str):
        raise WorkflowComposeError("Workflow node must include a string 'skill'")
    return node["skill"]


def _template_string(template: dict[str, Any], key: str) -> str:
    value = template.get(key)
    if not isinstance(value, str) or not value:
        raise WorkflowComposeError(f"Workflow template field {key!r} must be a string")
    return value


def _validate_bindings(required_roles: tuple[str, ...], bindings: dict[str, str]) -> None:
    missing = tuple(role for role in required_roles if role not in bindings)
    if missing:
        raise WorkflowComposeError(f"Missing workflow bindings: {', '.join(missing)}")


def _default_bindings(template: dict[str, Any]) -> dict[str, str]:
    return {str(asset["role"]): str(asset["role"]) for asset in _required_assets(template)}


def _resolve_placeholders(value: Any, bindings: dict[str, str]) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        binding_key = value[1:]
        try:
            return bindings[binding_key]
        except KeyError as exc:
            raise WorkflowComposeError(f"Missing workflow binding: {binding_key}") from exc
    if isinstance(value, dict):
        return {key: _resolve_placeholders(item, bindings) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_placeholders(item, bindings) for item in value]
    return value


def _primary_metric(predicate: dict[str, Any]) -> dict[str, Any]:
    predicate_type = str(predicate.get("type", "task_done"))
    metric: dict[str, Any] = {
        "id": "task_success",
        "type": "predicate_satisfaction",
        "role": "primary_success",
        "predicate": predicate_type,
        "adapter_hints": {
            "ebench": {
                "success_metric": "task_success",
                "predicate": predicate_type,
            }
        },
    }
    for key in ("object", "zone", "source", "target", "container"):
        if key in predicate:
            metric[key] = predicate[key]
            metric["adapter_hints"]["ebench"][key] = predicate[key]
    return metric


def _load_yaml_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    raise WorkflowComposeError(f"YAML artifact must be a mapping: {path}")
