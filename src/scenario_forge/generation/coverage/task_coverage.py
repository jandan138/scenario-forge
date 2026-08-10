"""Pure contracts for the scientific-workbench coverage factory.

The factory decides which canonical task recipes may enter the external eBench
runtime lane.  It deliberately does not load USD, invoke ConvertAsset, or run
an IK solver.  Those actions remain with their respective adapters/producers.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping

import yaml


COVERAGE_PLAN_SCHEMA_VERSION = "scenario-forge-task-coverage-plan/v0.1"
ASSET_INVENTORY_SCHEMA_VERSION = "task-coverage-asset-inventory/v0.1"
CONVERTASSET_REQUEST_SCHEMA_VERSION = "scenario-forge-convertasset-admission-request/v0.1"
TASK_DIRECTORY_SCHEMA_VERSION = "scenario-forge-task-directory/v0.1"
REQUIRED_LATEST_GATES = (
    "self_contained_package",
    "runtime_reset",
    "tabletop_placement",
    "visual_review",
    "provisional_ik",
)
_GATE_EVIDENCE = {
    "self_contained_package": ("evidence/package_closure.yaml", "status", "pass"),
    "runtime_reset": (
        "adapters/ebench/genmanip/evidence/initial_scene/visual_ready_gate.yaml",
        "status",
        "passed",
    ),
    "tabletop_placement": ("evidence/tabletop_placement_policy.yaml", "overall_status", "pass"),
    "visual_review": ("evidence/phase11_visual_review_gate.yaml", "status", "passed"),
    "provisional_ik": ("evidence/provisional_ik_preflight.yaml", "overall_status", "pass"),
}


class CoveragePlanError(ValueError):
    """Raised when coverage inputs or release records are malformed."""


def refresh_release_evidence(
    releases: Iterable[Mapping[str, object]],
    *,
    base_dir: str | Path = ".",
) -> list[dict[str, object]]:
    """Refresh gate state from a package's recorded evidence.

    A release is promoted only when all five evidence files independently report
    their passing state. Missing evidence remains ``not_run``; a present file
    whose status does not pass is recorded as ``failed``.
    """

    root_dir = Path(base_dir)
    refreshed: list[dict[str, object]] = []
    for raw_release in releases:
        release = dict(raw_release)
        package_path = _required_string(release, "package_path", "release")
        root = Path(package_path)
        if not root.is_absolute():
            root = root_dir / root
        gates = {
            gate: _gate_status(root, relative_path, field, passing_value)
            for gate, (relative_path, field, passing_value) in _GATE_EVIDENCE.items()
        }
        release["gates"] = gates
        release["promotion"] = (
            "latest" if all(status == "pass" for status in gates.values()) else "candidate"
        )
        refreshed.append(release)
    return refreshed


def build_task_coverage_plan(
    *,
    catalog: Mapping[str, object],
    inventory: Mapping[str, object],
    binding_ids: Iterable[str],
    canonical_recipe_ids: Iterable[str],
) -> dict[str, object]:
    """Classify every catalog row without inventing missing assets or recipes."""

    catalog_id = _required_string(catalog, "catalog_id", "catalog")
    domain = _required_string(catalog, "domain", "catalog")
    catalog_tasks = _mappings(catalog.get("tasks"), "catalog.tasks")
    available_bindings = _string_set(binding_ids, "binding_ids")
    recipes = _string_set(canonical_recipe_ids, "canonical_recipe_ids")
    inventory_data = _inventory(inventory, available_bindings)

    decisions: list[dict[str, object]] = []
    for task in sorted(catalog_tasks, key=lambda item: _required_int(item, "source_order", "task")):
        task_id = _required_string(task, "task_id", "task")
        roles = _string_list(task.get("required_asset_roles"), f"task {task_id}.required_asset_roles")
        blockers: list[str] = []
        asset_bindings: dict[str, str] = {}
        for role in roles:
            record = inventory_data["assets"].get(role)
            if record is None:
                blockers.append(f"asset role '{role}' has no inventory record")
                continue
            status = record["admission_status"]
            if status != "pass":
                blockers.append(f"asset role '{role}' admission status is '{status}'")
                continue
            binding_id = record["binding_id"]
            if binding_id not in available_bindings:
                blockers.append(
                    f"asset role '{role}' binding '{binding_id}' is not in source bindings"
                )
                continue
            asset_bindings[role] = binding_id
        if task_id not in recipes:
            blockers.append("canonical task recipe has not been authored")
        decisions.append(
            {
                "task_id": task_id,
                "source_order": _required_int(task, "source_order", f"task {task_id}"),
                "title_zh": _required_string(task, "title_zh", f"task {task_id}"),
                "status": "queued" if not blockers else "blocked",
                "canonical_recipe_id": task_id if task_id in recipes else None,
                "required_asset_roles": roles,
                "asset_bindings": asset_bindings,
                "blockers": blockers,
            }
        )
    queued = sum(item["status"] == "queued" for item in decisions)
    return {
        "schema_version": COVERAGE_PLAN_SCHEMA_VERSION,
        "catalog_id": catalog_id,
        "domain": domain,
        "catalog_content_sha256": _catalog_content_sha(catalog),
        "default_environment_binding": inventory_data["default_environment_binding"],
        "default_table_binding": inventory_data["default_table_binding"],
        "required_latest_gates": list(REQUIRED_LATEST_GATES),
        "summary": {
            "task_count": len(decisions),
            "queued": queued,
            "blocked": len(decisions) - queued,
        },
        "tasks": decisions,
        "claim_boundary": (
            "A queued task has admitted source-bound assets and an authored canonical "
            "recipe. It is not a runtime-reset, IK, interaction, policy, or benchmark "
            "success claim until its versioned release gates provide that evidence."
        ),
    }


def write_convertasset_admission_request(
    plan: Mapping[str, object],
    path: str | Path,
) -> Path:
    """Emit a de-duplicated producer-side request for blocked asset roles."""

    tasks = _mappings(plan.get("tasks"), "coverage plan.tasks")
    requested: dict[str, dict[str, object]] = {}
    for task in tasks:
        task_id = _required_string(task, "task_id", "coverage plan task")
        blockers = _string_list(task.get("blockers"), f"coverage plan task {task_id}.blockers")
        for blocker in blockers:
            role = _asset_role_from_blocker(blocker)
            if role is None:
                continue
            entry = requested.setdefault(
                role,
                {"asset_role": role, "blocked_tasks": [], "reason": blocker},
            )
            blocked_tasks = entry["blocked_tasks"]
            assert isinstance(blocked_tasks, list)
            blocked_tasks.append(task_id)
    payload = {
        "schema_version": CONVERTASSET_REQUEST_SCHEMA_VERSION,
        "request_id": f"{_required_string(plan, 'catalog_id', 'coverage plan')}-asset-admission",
        "domain": _required_string(plan, "domain", "coverage plan"),
        "requested_asset_roles": [requested[role] for role in sorted(requested)],
        "consumer_contract": {
            "required_usage": "rigid_object_or_articulated_object_as_semantically_required",
            "required_admission_status": "pass",
            "required_delivery": "source-bound package plus manifest",
        },
        "source_preservation": "producer_side_copy_only; original source immutable",
        "consumer_prohibitions": [
            "no Scenario Forge asset-specific collider, mass, inertia, scale, or PhysX patch",
            "no placeholder or semantic substitution treated as coverage",
        ],
    }
    target = Path(path)
    _write_yaml(target, payload)
    return target


def _gate_status(root: Path, relative_path: str, field: str, passing_value: str) -> str:
    evidence_path = root / relative_path
    if not evidence_path.is_file():
        return "not_run"
    try:
        payload = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
    except OSError:
        return "failed"
    if not isinstance(payload, Mapping):
        return "failed"
    return "pass" if payload.get(field) == passing_value else "failed"


def write_task_directory(
    plan: Mapping[str, object],
    releases: Iterable[Mapping[str, object]],
    *,
    output_dir: str | Path,
) -> Path:
    """Write a static task directory and promote only fully-gated immutable releases.

    A release may opt out of promotion with ``promotion: candidate``.  This is
    useful for retaining reset/render evidence while a provisional IK result is
    still pending.
    """

    tasks = _mappings(plan.get("tasks"), "coverage plan.tasks")
    task_ids = {_required_string(task, "task_id", "coverage plan task") for task in tasks}
    releases_by_task: dict[str, list[dict[str, object]]] = defaultdict(list)
    for raw_release in releases:
        release = _release_mapping(raw_release, task_ids)
        releases_by_task[release["task_id"]].append(release)

    directory_tasks: list[dict[str, object]] = []
    for task in tasks:
        task_id = _required_string(task, "task_id", "coverage plan task")
        candidates = sorted(
            releases_by_task.get(task_id, []), key=lambda item: str(item["release_id"])
        )
        promoted = [item for item in candidates if item["promotion"] == "latest"]
        if len(promoted) > 1:
            raise CoveragePlanError(f"task '{task_id}' has more than one latest release")
        latest = promoted[0] if promoted else None
        candidate_releases = [item for item in candidates if item["promotion"] == "candidate"]
        # Release identifiers are immutable, ordered version labels.  Showing the
        # newest candidate keeps reset/render evidence visible without letting a
        # partial gate set impersonate the qualified `latest` release.
        candidate = candidate_releases[-1] if candidate_releases else None
        directory_tasks.append(
            {
                "task_id": task_id,
                "source_order": _required_int(task, "source_order", "coverage plan task"),
                "title_zh": _required_string(task, "title_zh", "coverage plan task"),
                "queue_status": _required_string(task, "status", "coverage plan task"),
                "blockers": _string_list(task.get("blockers"), "coverage plan task.blockers"),
                "latest_release_id": None if latest is None else latest["release_id"],
                "latest_status": None if latest is None else "runtime_reset_provisional_ik_pass",
                "latest_package_path": None if latest is None else latest["package_path"],
                "latest_background_binding": None
                if latest is None
                else latest["background_binding"],
                "latest_evidence": None if latest is None else latest["evidence"],
                "candidate_release_id": None if candidate is None else candidate["release_id"],
                "candidate_package_path": None if candidate is None else candidate["package_path"],
                "candidate_background_binding": None
                if candidate is None
                else candidate["background_binding"],
                "candidate_evidence": None if candidate is None else candidate["evidence"],
                "candidate_gates": None if candidate is None else candidate["gates"],
                "candidate_release_status": None
                if candidate is None
                else candidate["release_status"],
                "candidate_score_ceiling": None
                if candidate is None
                else candidate["score_ceiling"],
                "candidate_missing_capabilities": []
                if candidate is None
                else candidate["missing_capabilities"],
                "releases": candidates,
            }
        )

    root = Path(output_dir)
    payload = {
        "schema_version": TASK_DIRECTORY_SCHEMA_VERSION,
        "catalog_id": _required_string(plan, "catalog_id", "coverage plan"),
        "default_environment_binding": _required_string(
            plan, "default_environment_binding", "coverage plan"
        ),
        "default_table_binding": _required_string(plan, "default_table_binding", "coverage plan"),
        "tasks": directory_tasks,
        "claim_boundary": (
            "The directory exposes declared release gates. A latest release proves only "
            "the recorded self-contained package, reset, tabletop, visual, and "
            "provisional-IK gates; it does not prove collision-free motion, grasp "
            "closure, lift, interaction success, liquid transfer, policy success, or "
            "benchmark success."
        ),
    }
    _write_yaml(root / "task_directory.yaml", payload)
    (root / "index.md").write_text(_directory_markdown(payload), encoding="utf-8")
    (root / "index.html").write_text(_directory_html(payload), encoding="utf-8")
    return root


def _inventory(
    inventory: Mapping[str, object], binding_ids: set[str]
) -> dict[str, object]:
    if inventory.get("schema_version") != ASSET_INVENTORY_SCHEMA_VERSION:
        raise CoveragePlanError(
            f"inventory.schema_version must be {ASSET_INVENTORY_SCHEMA_VERSION!r}"
        )
    environment = _required_string(inventory, "default_environment_binding", "inventory")
    table = _required_string(inventory, "default_table_binding", "inventory")
    for field, binding in (
        ("default_environment_binding", environment),
        ("default_table_binding", table),
    ):
        if binding not in binding_ids:
            raise CoveragePlanError(f"inventory.{field} '{binding}' is not in source bindings")
    assets = inventory.get("assets")
    if not isinstance(assets, Mapping):
        raise CoveragePlanError("inventory.assets must be a mapping")
    records: dict[str, dict[str, str]] = {}
    for role, raw_record in assets.items():
        if not isinstance(role, str) or not role:
            raise CoveragePlanError("inventory.assets keys must be non-empty strings")
        if not isinstance(raw_record, Mapping):
            raise CoveragePlanError(f"inventory asset role '{role}' must be a mapping")
        records[role] = {
            "binding_id": _required_string(raw_record, "binding_id", f"inventory asset '{role}'"),
            "admission_status": _required_string(
                raw_record, "admission_status", f"inventory asset '{role}'"
            ),
            "manifest_sha256": _required_string(
                raw_record, "manifest_sha256", f"inventory asset '{role}'"
            ),
        }
    return {
        "default_environment_binding": environment,
        "default_table_binding": table,
        "assets": records,
    }


def _release_mapping(raw_release: Mapping[str, object], task_ids: set[str]) -> dict[str, object]:
    task_id = _required_string(raw_release, "task_id", "release")
    if task_id not in task_ids:
        raise CoveragePlanError(f"release references unknown task '{task_id}'")
    release_id = _required_string(raw_release, "release_id", "release")
    package_path = _required_string(raw_release, "package_path", "release")
    background_binding = _required_string(raw_release, "background_binding", "release")
    evidence = _evidence_mapping(raw_release.get("evidence", {}), "release.evidence")
    promotion = raw_release.get("promotion", "latest")
    if promotion not in {"latest", "candidate"}:
        raise CoveragePlanError("release.promotion must be 'latest' or 'candidate'")
    gates = raw_release.get("gates")
    if not isinstance(gates, Mapping):
        raise CoveragePlanError("release.gates must be a mapping")
    copied_gates = {
        gate: _required_string(gates, gate, "release.gates") for gate in REQUIRED_LATEST_GATES
    }
    if promotion == "latest":
        failed = [gate for gate, status in copied_gates.items() if status != "pass"]
        if failed:
            raise CoveragePlanError(
                f"release '{release_id}' cannot be promoted to latest; gates not pass: "
                + ", ".join(failed)
            )
    return {
        "task_id": task_id,
        "release_id": release_id,
        "package_path": package_path,
        "background_binding": background_binding,
        "evidence": evidence,
        "promotion": promotion,
        "gates": copied_gates,
        "release_status": _optional_release_status(raw_release.get("release_status")),
        "score_ceiling": _optional_score_ceiling(raw_release.get("score_ceiling")),
        "missing_capabilities": _optional_string_list(
            raw_release.get("missing_capabilities", []),
            "release.missing_capabilities",
        ),
    }


def _directory_markdown(payload: Mapping[str, object]) -> str:
    tasks = _mappings(payload.get("tasks"), "directory.tasks")
    lines = [
        "# Scientific Workbench Task Directory",
        "",
        "| # | Task | Queue | Current candidate | Latest qualified | Background | Evidence | Tier | Ceiling | Missing |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for task in tasks:
        latest = task["latest_release_id"] or "—"
        candidate = task["candidate_release_id"] or "—"
        background = task["latest_background_binding"] or task["candidate_background_binding"] or "—"
        evidence = task["latest_evidence"] or task["candidate_evidence"] or {}
        assert isinstance(evidence, Mapping)
        overview = evidence.get("overview_image", "—")
        lines.append(
            "| {source_order} | {title} | {queue} | `{candidate}` | `{latest}` | `{background}` | `{overview}` | {tier} | {ceiling} | {missing} |".format(
                source_order=task["source_order"],
                title=task["title_zh"],
                queue=task["queue_status"],
                candidate=candidate,
                latest=latest,
                background=background,
                overview=overview,
                tier=task.get("candidate_release_status") or "—",
                ceiling=_score_label(task.get("candidate_score_ceiling")),
                missing=", ".join(task.get("candidate_missing_capabilities", [])) or "—",
            )
        )
    lines.extend(["", "## Claim boundary", "", str(payload["claim_boundary"]), ""])
    return "\n".join(lines)


def _directory_html(payload: Mapping[str, object]) -> str:
    tasks = _mappings(payload.get("tasks"), "directory.tasks")
    rows = "\n".join(
        "<tr><td class=\"row-order\">{}</td><td class=\"task-title\">{}</td><td class=\"queue-status\">{}</td><td class=\"release-id\">{}</td><td class=\"latest-id\">{}</td><td class=\"background-binding\">{}</td><td class=\"release-tier\">{}</td><td class=\"score-ceiling\">{}</td><td class=\"missing-capabilities\">{}</td><td class=\"release-variants\">{}</td><td class=\"evidence-thumb\">{}</td></tr>".format(
            task["source_order"],
            _html(str(task["title_zh"])),
            _html(str(task["queue_status"])),
            _html(str(task["candidate_release_id"] or "—")),
            _html(str(task["latest_release_id"] or "—")),
            _html(
                str(
                    task["latest_background_binding"]
                    or task["candidate_background_binding"]
                    or "—"
                )
            ),
            _html(str(task.get("candidate_release_status") or "—")),
            _html(_score_label(task.get("candidate_score_ceiling"))),
            _html(", ".join(task.get("candidate_missing_capabilities", [])) or "—"),
            _release_variants(task.get("releases")),
            _evidence_thumbnail(task.get("latest_evidence") or task.get("candidate_evidence")),
        )
        for task in tasks
    )
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><link rel="icon" href="data:,"><title>Scientific Workbench Task Directory</title>
<style>*{box-sizing:border-box}body{font-family:system-ui,sans-serif;margin:2rem;color:#18212f}.table-scroll{max-width:100%;overflow-x:auto}table{border-collapse:collapse;min-width:1680px;width:100%;table-layout:fixed}th,td{border-bottom:1px solid #d8dee9;padding:.6rem;text-align:left;vertical-align:top}.row-order{width:3rem}.task-title{width:12rem}.queue-status{width:6rem}.release-id{overflow-wrap:anywhere;width:18rem}.latest-id{overflow-wrap:anywhere;width:10rem}.background-binding{overflow-wrap:anywhere;width:13rem}.release-tier{width:10rem;overflow-wrap:anywhere}.score-ceiling{width:5rem}.missing-capabilities{width:13rem}.release-variants{width:22rem;overflow-wrap:anywhere}.release-variants summary{cursor:pointer}.release-variants ul{margin:.5rem 0 0;padding-left:1.1rem}.evidence-thumb{width:11rem}th{background:#f4f7fb}code{font-size:.9em}img{width:144px;height:81px;object-fit:cover;border-radius:4px}p{max-width:72rem;color:#4a5568}.scroll-hint{display:none}@media(max-width:700px){body{margin:1rem}th,td{padding:.5rem}img{width:120px;height:68px}.scroll-hint{display:block;color:#4a5568}}</style>
</head><body><h1>Scientific Workbench Task Directory</h1>
<p class="scroll-hint">左右滑动查看全部列。</p><div class="table-scroll"><table><thead><tr><th class="row-order">#</th><th class="task-title">Task</th><th class="queue-status">Queue</th><th class="release-id">Current candidate</th><th class="latest-id">Latest qualified</th><th class="background-binding">Background</th><th class="release-tier">Tier</th><th class="score-ceiling">Ceiling</th><th class="missing-capabilities">Missing</th><th class="release-variants">Variants</th><th class="evidence-thumb">Evidence</th></tr></thead><tbody>""" + rows + """</tbody></table></div>
<h2>Claim boundary</h2><p>""" + _html(str(payload["claim_boundary"])) + """</p></body></html>
"""


def _asset_role_from_blocker(blocker: str) -> str | None:
    prefix = "asset role '"
    if not blocker.startswith(prefix):
        return None
    rest = blocker[len(prefix) :]
    role, separator, _ = rest.partition("'")
    return role if separator and role else None


def _evidence_mapping(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise CoveragePlanError(f"{field} must be a mapping")
    allowed = {"overview_image", "closeup_image", "runtime_reset_gate"}
    unknown = sorted(set(value).difference(allowed))
    if unknown:
        raise CoveragePlanError(f"{field} contains unsupported keys: {', '.join(unknown)}")
    result: dict[str, str] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not isinstance(raw, str) or not raw:
            raise CoveragePlanError(f"{field} must map evidence keys to non-empty strings")
        result[key] = raw
    return result


def _evidence_thumbnail(value: object) -> str:
    if not isinstance(value, Mapping):
        return "—"
    overview = value.get("overview_image")
    if not isinstance(overview, str) or not overview:
        return "—"
    safe = _html(overview)
    return f'<a href="{safe}"><img src="{safe}" alt="scene overview"></a>'


def _release_variants(value: object) -> str:
    if not isinstance(value, list) or not value:
        return "—"
    items: list[str] = []
    for release in value:
        if not isinstance(release, Mapping):
            continue
        release_id = release.get("release_id")
        background = release.get("background_binding")
        if isinstance(release_id, str) and isinstance(background, str):
            label = f"{_html(release_id)} — {_html(background)}"
            evidence = release.get("evidence")
            overview = evidence.get("overview_image") if isinstance(evidence, Mapping) else None
            if isinstance(overview, str) and overview:
                safe = _html(overview)
                label = f'<a href="{safe}">{label}</a>'
            items.append(f"<li>{label}</li>")
    if not items:
        return "—"
    count = len(items)
    plural = "s" if count != 1 else ""
    return (
        f"<details><summary>{count} package{plural}</summary><ul>"
        + "".join(items)
        + "</ul></details>"
    )


def _score_label(value: object) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "—"
    return f"{float(value) * 100:g}%"


def _optional_release_status(value: object) -> str:
    if value is None:
        return "unspecified"
    if value not in {"canonical_candidate", "prototype"}:
        raise CoveragePlanError(
            "release.release_status must be 'canonical_candidate' or 'prototype'"
        )
    return str(value)


def _optional_score_ceiling(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CoveragePlanError("release.score_ceiling must be a number")
    score = float(value)
    if score < 0.0 or score > 1.0:
        raise CoveragePlanError("release.score_ceiling must be between 0 and 1")
    return score


def _optional_string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise CoveragePlanError(f"{field} must be a list of non-empty strings")
    return list(value)


def _catalog_content_sha(catalog: Mapping[str, object]) -> str | None:
    source = catalog.get("source")
    if not isinstance(source, Mapping):
        return None
    value = source.get("content_sha256")
    return value if isinstance(value, str) else None


def _required_string(data: Mapping[str, object], key: str, field: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise CoveragePlanError(f"{field}.{key} must be a non-empty string")
    return value


def _required_int(data: Mapping[str, object], key: str, field: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise CoveragePlanError(f"{field}.{key} must be an integer")
    return value


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise CoveragePlanError(f"{field} must be a list of non-empty strings")
    return list(value)


def _string_set(values: Iterable[str], field: str) -> set[str]:
    result = set(values)
    if not result or not all(isinstance(value, str) and value for value in result):
        raise CoveragePlanError(f"{field} must contain non-empty strings")
    return result


def _mappings(value: object, field: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise CoveragePlanError(f"{field} must be a list of mappings")
    return list(value)


def _write_yaml(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _html(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
