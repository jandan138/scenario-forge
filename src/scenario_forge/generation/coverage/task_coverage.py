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
    gallery_tasks = [
        task
        for task in tasks
        if task.get("candidate_release_id") or task.get("latest_release_id")
    ]
    cards = "\n".join(_directory_task_card(task) for task in gallery_tasks)
    rows = "\n".join(_directory_matrix_row(task) for task in tasks)
    candidate_count = len(gallery_tasks)
    canonical_count = sum(
        task.get("candidate_release_status") == "canonical_candidate"
        for task in gallery_tasks
    )
    prototype_count = sum(
        task.get("candidate_release_status") == "prototype" for task in gallery_tasks
    )
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>Scientific Workbench · 任务目录</title>
<style>
:root{--ink:#10243b;--muted:#607083;--line:#d7e0e8;--paper:#f5f8fa;--card:#fff;--teal:#087f78;--teal-soft:#dff4f1;--amber:#b56708;--amber-soft:#fff0d5;--navy:#102f50}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,"Noto Sans SC","PingFang SC",system-ui,sans-serif}.shell{max-width:1440px;margin:auto;padding:0 32px 72px}.masthead{padding:68px 0 34px;border-bottom:1px solid var(--line);display:grid;grid-template-columns:minmax(0,1fr) auto;gap:40px;align-items:end}.eyebrow{color:var(--teal);font-size:.78rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase}.masthead h1{font-size:clamp(2.2rem,5vw,5rem);line-height:.98;letter-spacing:-.055em;margin:14px 0 20px;max-width:860px}.lead{color:var(--muted);font-size:1.05rem;line-height:1.75;max-width:760px;margin:0}.stats{display:grid;grid-template-columns:repeat(3,116px);border:1px solid var(--line);background:var(--card)}.stat{padding:20px;border-right:1px solid var(--line)}.stat:last-child{border:0}.stat strong{display:block;font:700 2rem/1 Georgia,serif;color:var(--navy)}.stat span{display:block;color:var(--muted);font-size:.75rem;margin-top:8px}.section-head{display:flex;justify-content:space-between;gap:24px;align-items:end;margin:50px 0 22px}.section-head h2{font-size:1.7rem;letter-spacing:-.03em;margin:0}.section-head p{color:var(--muted);margin:0;max-width:590px;line-height:1.6}.version-switch,.filters{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 14px;align-items:center}.version-switch{padding:10px 12px;background:#eaf0f4;border:1px solid var(--line);width:max-content}.version-switch span{font-size:.76rem;font-weight:800;color:var(--muted);margin-right:4px}.version,.filter{border:1px solid var(--line);background:#fff;color:var(--navy);padding:9px 14px;border-radius:999px;font-weight:700;cursor:pointer}.version[aria-pressed="true"],.filter[aria-pressed="true"]{background:var(--navy);border-color:var(--navy);color:#fff}.task-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.task-card{background:var(--card);border:1px solid var(--line);display:grid;grid-template-columns:minmax(220px,42%) 1fr;min-height:270px;overflow:hidden;box-shadow:0 8px 28px rgba(16,47,80,.045)}.task-card[hidden],[data-release-version][hidden]{display:none}.evidence-rail{display:block;background:#dfe7ec;min-height:270px;position:relative}.evidence-rail img{width:100%;height:100%;position:absolute;inset:0;object-fit:cover}.evidence-empty{height:100%;display:grid;place-items:center;color:var(--muted);font-weight:700}.card-body{padding:22px;display:flex;flex-direction:column}.card-kicker{display:flex;align-items:center;justify-content:space-between;gap:10px;color:var(--teal);font-size:.75rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}.tier{padding:5px 8px;background:var(--teal-soft);color:var(--teal);letter-spacing:0;text-transform:none}.tier.prototype{background:var(--amber-soft);color:var(--amber)}.card-body h3{font-size:1.3rem;line-height:1.25;margin:14px 0 10px}.release{font-family:ui-monospace,SFMono-Regular,monospace;color:var(--muted);font-size:.72rem;overflow-wrap:anywhere;margin:0 0 16px}.meter{height:5px;background:#e7edf1;margin:2px 0 8px}.meter span{display:block;height:100%;background:var(--teal)}.meta{display:flex;justify-content:space-between;color:var(--muted);font-size:.78rem}.missing{margin:16px 0 0;color:var(--amber);font-size:.78rem;line-height:1.45}.release-variants{margin-top:auto;padding-top:12px;font-size:.75rem}.release-variants summary{cursor:pointer;color:var(--navy);font-weight:700}.release-variants ul{margin:8px 0 0;padding-left:18px}.release-variants a{color:var(--teal)}.matrix-wrap{overflow:auto;border:1px solid var(--line);background:#fff}.coverage-matrix{width:100%;border-collapse:collapse;min-width:940px}.coverage-matrix th,.coverage-matrix td{padding:15px 16px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}.coverage-matrix th{background:var(--navy);color:#fff;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase}.coverage-matrix td{font-size:.84rem}.coverage-matrix tr:last-child td{border:0}.matrix-order{font:700 1.1rem Georgia,serif;color:var(--teal)}.status-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--amber);margin-right:7px}.status-dot.has-release{background:var(--teal)}.matrix-code{font-family:ui-monospace,SFMono-Regular,monospace;font-size:.72rem;color:var(--muted);overflow-wrap:anywhere}.claim{margin-top:44px;border-left:4px solid var(--amber);background:var(--amber-soft);padding:20px 24px}.claim h2{font-size:1rem;margin:0 0 8px}.claim p{color:#704916;line-height:1.65;margin:0;font-size:.86rem}@media(max-width:1080px){.masthead{grid-template-columns:1fr}.stats{width:max-content}.task-grid{grid-template-columns:1fr}}@media(max-width:760px){.shell{padding:0 16px 48px}.masthead{padding-top:42px}.stats{grid-template-columns:repeat(3,1fr);width:100%}.stat{padding:14px}.task-card{grid-template-columns:1fr}.evidence-rail{min-height:210px}.section-head{align-items:start;flex-direction:column}.masthead h1{font-size:2.7rem}.version-switch{width:100%}}
</style></head><body><main class="shell"><header class="masthead"><div><div class="eyebrow">Scenario Forge / Scientific Workbench</div><h1>实验任务，<br>按证据说话。</h1><p class="lead">统一的 2 米工作台、eBench 双臂布局与可替换实验室背景。先看真实 Isaac Sim 图，再看哪些能力已经具备、哪些仍是原型。</p></div><div class="stats"><div class="stat"><strong>""" + str(len(tasks)) + """</strong><span>飞书任务总数</span></div><div class="stat"><strong>""" + str(candidate_count) + """</strong><span>已有场景候选</span></div><div class="stat"><strong>""" + str(canonical_count) + """</strong><span>完整语义候选</span></div></div></header>
<section><div class="section-head"><div><div class="eyebrow">Evidence gallery</div><h2>可检查的任务场景</h2></div><p>卡片展示的是初始场景证据，不是机器人策略成功率。绿色代表完整语义候选，琥珀色代表仍缺交互或液体能力的原型。</p></div><div class="version-switch" role="group" aria-label="任务包版本"><span>场景版本</span><button class="version" data-version="r6" aria-pressed="true">r6 · 动态桌面布景</button><button class="version" data-version="r5" aria-pressed="false">r5 · 基础桌面</button></div><div class="filters" role="group" aria-label="任务筛选"><button class="filter" data-filter="all" aria-pressed="true">全部 """ + str(candidate_count) + """</button><button class="filter" data-filter="canonical_candidate" aria-pressed="false">完整语义 """ + str(canonical_count) + """</button><button class="filter" data-filter="prototype" aria-pressed="false">原型 """ + str(prototype_count) + """</button><button class="filter" data-filter="queued" aria-pressed="false">已排队</button></div><div class="task-grid">""" + cards + """</div></section>
<section><div class="section-head"><div><div class="eyebrow">Coverage matrix</div><h2>18 项任务全表</h2></div><p>保持飞书原始顺序。没有候选包的任务也不会从页面消失，阻塞原因原样展示。</p></div><div class="matrix-wrap"><table class="coverage-matrix"><thead><tr><th>#</th><th>任务</th><th>状态</th><th>候选层级</th><th>分数上限</th><th>背景 / 缺口</th></tr></thead><tbody>""" + rows + """</tbody></table></div></section>
<aside class="claim"><h2>证据边界</h2><p>""" + _html(str(payload["claim_boundary"])) + """</p></aside></main><script>const buttons=[...document.querySelectorAll('.filter')],cards=[...document.querySelectorAll('.task-card')],versions=[...document.querySelectorAll('.version')];function applyFilter(value){cards.forEach(card=>{card.hidden=value!=='all'&&card.dataset.tier!==value&&card.dataset.queue!==value});buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.filter===value)))}function applyVersion(value){document.querySelectorAll('[data-release-version]').forEach(node=>{node.hidden=node.dataset.releaseVersion!==value});versions.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.version===value)))}buttons.forEach(button=>button.addEventListener('click',()=>applyFilter(button.dataset.filter)));versions.forEach(button=>button.addEventListener('click',()=>applyVersion(button.dataset.version)));applyVersion('r6');</script></body></html>
"""


def _directory_task_card(task: Mapping[str, object]) -> str:
    releases = task.get("releases")
    r6 = _preferred_series_release(releases, "r6")
    r5 = _preferred_series_release(releases, "r5")
    fallback = r6 or r5 or _last_release(releases)
    image = _versioned_evidence_rails(task, r6=r6, r5=r5, fallback=fallback)
    tier = str(task.get("candidate_release_status") or "unspecified")
    tier_label = {
        "canonical_candidate": "完整语义候选",
        "prototype": "原型",
    }.get(tier, "未分层")
    ceiling = task.get("candidate_score_ceiling")
    ceiling_number = float(ceiling) if isinstance(ceiling, (int, float)) else 0.0
    missing = ", ".join(task.get("candidate_missing_capabilities", [])) or "无已知语义缺口"
    release_labels = _versioned_release_labels(r6=r6, r5=r5, fallback=fallback)
    return (
        f'<article class="task-card" data-tier="{_html(tier)}" data-queue="{_html(str(task["queue_status"]))}">'
        + image
        + '<div class="card-body">'
        + f'<div class="card-kicker"><span>Task {task["source_order"]:02d}</span><span class="tier {_html(tier)}">{_html(tier_label)}</span></div>'
        + f'<h3>{_html(str(task["title_zh"]))}</h3><p class="release">{release_labels}</p>'
        + f'<div class="meter" aria-label="可计分上限 {_score_label(ceiling)}"><span style="width:{ceiling_number * 100:g}%"></span></div>'
        + f'<div class="meta"><span>可计分上限</span><strong>{_html(_score_label(ceiling))}</strong></div>'
        + f'<p class="missing">能力边界：{_html(missing)}</p>'
        + f'<div class="release-variants">{_release_variants(task.get("releases"))}</div></div></article>'
    )


def _preferred_series_release(value: object, series: str) -> Mapping[str, object] | None:
    if not isinstance(value, list):
        return None
    matching = [
        release
        for release in value
        if isinstance(release, Mapping)
        and f"_{series}" in str(release.get("release_id", ""))
    ]
    return sorted(matching, key=lambda item: str(item.get("release_id", "")))[-1] if matching else None


def _last_release(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, list):
        return None
    releases = [release for release in value if isinstance(release, Mapping)]
    return releases[-1] if releases else None


def _versioned_evidence_rails(
    task: Mapping[str, object],
    *,
    r6: Mapping[str, object] | None,
    r5: Mapping[str, object] | None,
    fallback: Mapping[str, object] | None,
) -> str:
    rails: list[str] = []
    for series, release in (("r6", r6 or fallback), ("r5", r5 or fallback)):
        evidence = release.get("evidence") if isinstance(release, Mapping) else None
        overview = evidence.get("overview_image") if isinstance(evidence, Mapping) else None
        hidden = "" if series == "r6" else " hidden"
        if isinstance(overview, str) and overview:
            safe = _html(overview)
            rails.append(
                f'<a class="evidence-rail" data-release-version="{series}"{hidden} href="{safe}">'
                f'<img src="{safe}" alt="{_html(str(task["title_zh"]))} {series} 场景总览" loading="eager"></a>'
            )
        else:
            rails.append(
                f'<div class="evidence-rail" data-release-version="{series}"{hidden}>'
                '<div class="evidence-empty">暂无渲染证据</div></div>'
            )
    return "".join(rails)


def _versioned_release_labels(
    *,
    r6: Mapping[str, object] | None,
    r5: Mapping[str, object] | None,
    fallback: Mapping[str, object] | None,
) -> str:
    labels: list[str] = []
    for series, release in (("r6", r6 or fallback), ("r5", r5 or fallback)):
        release_id = release.get("release_id", "—") if isinstance(release, Mapping) else "—"
        hidden = "" if series == "r6" else " hidden"
        labels.append(
            f'<span data-release-version="{series}"{hidden}>{_html(str(release_id))}</span>'
        )
    return "".join(labels)


def _directory_matrix_row(task: Mapping[str, object]) -> str:
    has_release = bool(task.get("candidate_release_id") or task.get("latest_release_id"))
    tier = task.get("candidate_release_status") or "—"
    background = task.get("latest_background_binding") or task.get("candidate_background_binding")
    missing = task.get("candidate_missing_capabilities", [])
    detail = ", ".join(missing) if isinstance(missing, list) and missing else ", ".join(task.get("blockers", []))
    detail = detail or "无已记录缺口"
    context = f"{background or '未绑定背景'} · {detail}"
    return (
        f'<tr><td class="matrix-order">{task["source_order"]:02d}</td>'
        f'<td><strong>{_html(str(task["title_zh"]))}</strong><div class="matrix-code">{_html(str(task["task_id"]))}</div></td>'
        f'<td><span class="status-dot{" has-release" if has_release else ""}"></span>{_html(str(task["queue_status"]))}</td>'
        f'<td>{_html(str(tier))}</td><td>{_html(_score_label(task.get("candidate_score_ceiling")))}</td>'
        f'<td>{_html(context)}</td></tr>'
    )


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
