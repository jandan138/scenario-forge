#!/usr/bin/env python3
"""Synchronize the scientific-workbench catalog from Feishu Task Design.

The live Feishu sheet is the product authority. Checked-in source data is a
pinned, hash-bound snapshot so package compilation and CI remain reproducible.
Normal repository checks do not require Feishu credentials or network access.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_URL = "https://aicarrier.feishu.cn/wiki/GNGCwR2uAi9dK3k6FT0cX5krnab"
DOCUMENT_ID = "YdLVdAe7noWEWTxaUTxcKD28nUh"
TASK_DESIGN_BLOCK_ID = "EQKednVHBoOgD8xoLnLc6vAAnzd"
SHEET_TOKEN = "A6cPsrjWbhLS68tgNmzcqdf7nqd"
SHEET_ID = "J1nUiN"
SNAPSHOT_RELATIVE_PATH = "configs/task_catalogs/sources/scientific_workbench_task_design.json"
SNAPSHOT_PATH = REPO_ROOT / SNAPSHOT_RELATIVE_PATH
CATALOG_PATH = REPO_ROOT / "configs/task_catalogs/scientific_workbench_phase1.yaml"
MARKDOWN_PATH = REPO_ROOT / "docs/reference/scientific-workbench-task-design.md"
HTML_PATH = REPO_ROOT / "docs/reference/scientific-workbench-task-design.html"

ENV = {
    **os.environ,
    "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
    "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
}

EXPECTED_COLUMNS = [
    "col1",
    "实验技能类别",
    "真机/仿真/联合",
    "过程概述",
    "具身操作原子技能",
    "步骤数",
    "核心资产",
    "长程能力\nlow(<5), middle([5, 9)), high([9, -))",
    "精细能力",
    "Progress Score",
]

TASK_IDENTITIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "液体倾倒：锥形瓶→量筒",
        "scientific_workbench_pour_flask_to_cylinder",
        ("erlenmeyer_flask", "graduated_cylinder"),
    ),
    (
        "液体倾倒：量筒-> 烧杯",
        "scientific_workbench_pour_cylinder_to_beaker",
        ("graduated_cylinder", "beaker"),
    ),
    (
        "药匙取样",
        "scientific_workbench_spatula_sample_transfer",
        ("spatula", "reagent_bottle", "sample_receiver"),
    ),
    (
        "磁子放入锥形瓶/烧杯",
        "scientific_workbench_insert_stir_bar_and_closure",
        ("stir_bar", "target_vessel", "vessel_closure"),
    ),
    (
        "锥形瓶/烧杯去除瓶塞/盖子",
        "scientific_workbench_remove_vessel_closure",
        ("target_vessel", "vessel_closure", "closure_rack"),
    ),
    (
        "烧杯/锥型瓶放搅拌器上",
        "scientific_workbench_place_vessel_on_stirrer",
        ("target_vessel", "stirrer"),
    ),
    (
        "玻璃棒搅拌",
        "scientific_workbench_glass_rod_stir",
        ("glass_rod", "beaker"),
    ),
    (
        "旋紧离心管",
        "scientific_workbench_tighten_centrifuge_tube_cap",
        ("centrifuge_tube", "centrifuge_tube_cap"),
    ),
    (
        "仪器交互/开启烘箱",
        "scientific_workbench_oven_load_start",
        (
            "oven",
            "sample_vessel",
            "oven_door",
            "temperature_control",
            "start_button",
        ),
    ),
    (
        "仪器交互/开启离心机",
        "scientific_workbench_centrifuge_load_start",
        (
            "centrifuge",
            "centrifuge_tube",
            "centrifuge_lid",
            "setting_button",
            "start_button",
        ),
    ),
    (
        "仪器交互/结束离心",
        "scientific_workbench_centrifuge_unload_shutdown",
        (
            "centrifuge",
            "centrifuge_tube",
            "tube_rack_or_plate",
            "lid_open_button",
            "shutdown_button",
        ),
    ),
    (
        "仪器交互/结束烘干",
        "scientific_workbench_oven_unload_shutdown",
        ("oven", "sample_plate", "oven_door", "shutdown_button"),
    ),
    (
        "液体倾倒：基于漏斗，量筒-> 锥形瓶",
        "scientific_workbench_funnel_pour_cylinder_to_flask",
        ("funnel", "graduated_cylinder", "erlenmeyer_flask"),
    ),
    (
        "液体倾倒：锥形瓶-> 离心管",
        "scientific_workbench_funnel_pour_flask_to_centrifuge_tube",
        (
            "funnel",
            "erlenmeyer_flask",
            "centrifuge_tube",
            "centrifuge_tube_cap",
        ),
    ),
    (
        "固体样品称量",
        "scientific_workbench_solid_sample_weighing",
        (
            "balance",
            "weighing_container",
            "spatula",
            "reagent_bottle",
            "solid_sample",
        ),
    ),
    (
        "样品混合\n（烧杯）",
        "scientific_workbench_two_sample_mix",
        ("sample_container_a", "sample_container_b", "target_vessel"),
    ),
    (
        "溶液配制",
        "scientific_workbench_solution_preparation",
        (
            "target_vessel",
            "spatula",
            "reagent_bottle",
            "glass_rod",
            "solid_sample",
            "solvent",
        ),
    ),
    (
        "旋转蒸发（简化装机/启动流程）",
        "scientific_workbench_rotary_evaporation_cycle",
        (
            "rotary_evaporator",
            "round_bottom_flask",
            "water_bath",
            "lift_mechanism",
            "start_button",
            "stop_button",
            "control_knob",
        ),
    ),
)

SKILL_MAP = {
    "抓": "grasp",
    "拿起": "pick",
    "放置": "place",
    "倾倒": "pour",
    "搅拌": "stir",
    "摇晃": "shake",
    "按压": "press",
    "拉": "pull",
    "推": "push",
    "插入": "insert",
    "转动": "turn",
    "扭转": "twist",
    "递交": "handover",
    "对准": "align",
    "舀": "scoop",
}

TASK_SOURCE_WARNINGS: dict[int, list[str]] = {
    8: [
        "核心资产列包含漏斗、锥形瓶，但标题和过程仅描述离心管及离心管盖；"
        "原文保留，规范化资产角色按标题和过程取离心管与管盖。"
    ],
    12: ["Progress Score 原始权重合计为 0.90；未补写缺失的 0.10。"],
    13: [
        "标题和过程描述量筒经漏斗倒入锥形瓶，但核心资产列写为"
        "“漏斗、试剂瓶、烧杯”；原文保留，规范化角色按标题和评分条件处理。"
    ],
    14: [
        "过程原文含“抓离心管盖子（锥形瓶）”，括号内容疑似笔误；"
        "原文保留，不在 Scenario Forge 静默改写。"
    ],
    17: [
        "核心资产原文重复列出两次试剂瓶；原文保留，规范化角色只列一次。",
        "一条 Progress Score 原文在权重“（0.1）”后带问号；"
        "权重按 0.1 记录，问号作为评分描述的不确定标记保留。",
    ],
}

_DECLARED_COUNT_PATTERN = re.compile(r"第一期，\s*(\d+)\s*tasks")
_SEQUENCE_PATTERN = re.compile(r"^时序(\d+)[:：]?$")
_WEIGHT_PATTERN = re.compile(r"^(.*?)[（(](0(?:\.\d+)?|1(?:\.0+)?)[）)]([？?]?)$")


def _run_cli(args: Sequence[str]) -> dict[str, Any]:
    result = subprocess.run(
        ["lark-cli", *args, "--as", "user", "--json"],
        capture_output=True,
        text=True,
        env=ENV,
        check=True,
    )
    data = json.loads(result.stdout)
    if not isinstance(data, dict) or data.get("ok") is not True:
        raise RuntimeError(f"lark-cli returned an invalid envelope: {data!r}")
    return data


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping")
    return value


def fetch_live_snapshot(*, captured_at: str | None = None) -> dict[str, Any]:
    document = _mapping(
        _run_cli(
            [
                "docs",
                "+fetch",
                "--doc",
                DOC_URL,
                "--scope",
                "section",
                "--start-block-id",
                TASK_DESIGN_BLOCK_ID,
                "--detail",
                "with-ids",
            ]
        )["data"]["document"],
        "Feishu document",
    )
    content = str(document["content"])
    declared_match = _DECLARED_COUNT_PATTERN.search(content)
    if declared_match is None:
        raise ValueError("Task Design section no longer declares a task count")
    if (
        str(document["document_id"]) != DOCUMENT_ID
        or f'token="{SHEET_TOKEN}"' not in content
        or f'sheet-id="{SHEET_ID}"' not in content
    ):
        raise ValueError("Task Design source identity or embedded sheet changed")

    workbook = _mapping(
        _run_cli(
            [
                "sheets",
                "+workbook-info",
                "--spreadsheet-token",
                SHEET_TOKEN,
            ]
        )["data"],
        "Feishu workbook",
    )
    sheet_infos = workbook.get("sheets")
    if not isinstance(sheet_infos, list):
        raise ValueError("Feishu workbook sheets must be a list")
    sheet_info = next(
        (
            _mapping(item, "Feishu sheet metadata")
            for item in sheet_infos
            if isinstance(item, dict) and item.get("sheet_id") == SHEET_ID
        ),
        None,
    )
    if sheet_info is None:
        raise ValueError(f"embedded sheet {SHEET_ID} is missing")

    table_data = _mapping(
        _run_cli(
            [
                "sheets",
                "+table-get",
                "--spreadsheet-token",
                SHEET_TOKEN,
                "--sheet-id",
                SHEET_ID,
            ]
        )["data"],
        "Feishu table response",
    )
    sheets = table_data.get("sheets")
    if not isinstance(sheets, list) or len(sheets) != 1:
        raise ValueError("Task Design table response must contain exactly one sheet")
    table = _mapping(sheets[0], "Feishu task table")
    columns = table.get("columns")
    rows = table.get("data")
    if columns != EXPECTED_COLUMNS:
        raise ValueError(f"Task Design columns changed: {columns!r}")
    if not isinstance(rows, list) or any(
        not isinstance(row, list) or len(row) != len(EXPECTED_COLUMNS) for row in rows
    ):
        raise ValueError("Task Design rows must be a rectangular 10-column table")
    if int(sheet_info["row_count"]) != len(rows) + 1:
        raise ValueError("Task Design used range is inconsistent with workbook metadata")

    raw_table = {"columns": columns, "rows": rows}
    return {
        "schema_version": "task-design-source-snapshot/v0.1",
        "captured_at": captured_at or date.today().isoformat(),
        "source": {
            "wiki_url": DOC_URL,
            "document_id": str(document["document_id"]),
            "document_revision": int(document["revision_id"]),
            "section_block_id": TASK_DESIGN_BLOCK_ID,
            "section_sha256": _canonical_hash(content),
            "declared_task_count": int(declared_match.group(1)),
            "spreadsheet_token": SHEET_TOKEN,
            "spreadsheet_revision": int(workbook["revision"]),
            "sheet_id": SHEET_ID,
            "range": str(table["range"]),
            "content_sha256": _canonical_hash(raw_table),
        },
        "columns": columns,
        "rows": rows,
    }


def _parse_execution_mode(source_text: str) -> tuple[str, list[str]]:
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("execution mode source text is empty")
    if lines[0] == "联合":
        mode = "joint"
    elif lines[0] == "真机":
        mode = "real"
    elif lines[0] == "仿真":
        mode = "simulation"
    else:
        raise ValueError(f"unknown execution mode: {source_text!r}")
    return mode, lines[1:]


def _parse_atomic_skills(source_text: str) -> list[str]:
    source_skills = [part.strip() for part in source_text.split("、")]
    normalized: list[str] = []
    for source_skill in source_skills:
        skill = SKILL_MAP.get(source_skill)
        if skill is None:
            raise ValueError(f"unknown Task Design atomic skill: {source_skill!r}")
        if skill not in normalized:
            normalized.append(skill)
    return normalized


def _parse_progress_score(source_text: str) -> tuple[list[dict[str, Any]], float]:
    sequence: int | None = None
    criteria: list[dict[str, Any]] = []
    total = Decimal("0")
    for raw_line in source_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        sequence_match = _SEQUENCE_PATTERN.fullmatch(line)
        if sequence_match is not None:
            sequence = int(sequence_match.group(1))
            continue
        if not line.startswith("- "):
            raise ValueError(f"unsupported Progress Score line: {raw_line!r}")
        if sequence is None:
            raise ValueError("Progress Score criterion appears before a sequence")
        criterion_match = _WEIGHT_PATTERN.fullmatch(line[2:].strip())
        if criterion_match is None:
            raise ValueError(f"Progress Score weight is missing: {raw_line!r}")
        description = criterion_match.group(1).strip() + criterion_match.group(3)
        weight_decimal = Decimal(criterion_match.group(2))
        criteria.append(
            {
                "sequence": sequence,
                "description_zh": description,
                "weight": float(weight_decimal),
            }
        )
        total += weight_decimal
    if not criteria:
        raise ValueError("Progress Score contains no criteria")
    return criteria, float(total)


def build_catalog(snapshot: Mapping[str, object]) -> dict[str, Any]:
    source = _mapping(snapshot.get("source"), "snapshot source")
    rows = snapshot.get("rows")
    if not isinstance(rows, list):
        raise ValueError("snapshot rows must be a list")
    if len(rows) != len(TASK_IDENTITIES):
        raise ValueError(
            "Task Design row count changed; update stable task identities "
            f"before refreshing ({len(rows)} rows, {len(TASK_IDENTITIES)} identities)"
        )

    tasks: list[dict[str, Any]] = []
    for order, (raw_row, identity) in enumerate(
        zip(rows, TASK_IDENTITIES, strict=True),
        start=1,
    ):
        if not isinstance(raw_row, list) or len(raw_row) != 10:
            raise ValueError(f"Task Design row {order} must have 10 cells")
        expected_title, task_id, required_roles = identity
        (
            category_zh,
            title_zh,
            execution_source,
            process_zh,
            skills_source,
            step_count,
            core_assets_zh,
            horizon,
            precision,
            progress_source,
        ) = raw_row
        if title_zh != expected_title:
            raise ValueError(
                f"Task Design row {order} title changed: {title_zh!r} != {expected_title!r}"
            )
        if not isinstance(step_count, (int, float)) or isinstance(step_count, bool):
            raise ValueError(f"Task Design row {order} step count is not numeric")
        mode, mode_notes = _parse_execution_mode(str(execution_source))
        progress_score, progress_total = _parse_progress_score(str(progress_source))
        tasks.append(
            {
                "task_id": task_id,
                "source_order": order,
                "source_row": order + 1,
                "title_zh": str(title_zh),
                "level": ("basic" if category_zh == "基本实验操作" else "long_horizon"),
                "execution_mode": mode,
                "execution_mode_source_zh": str(execution_source),
                "execution_notes_zh": mode_notes,
                "process_overview_zh": str(process_zh),
                "atomic_skills_source_zh": str(skills_source),
                "atomic_skills": _parse_atomic_skills(str(skills_source)),
                "step_count": int(step_count),
                "core_assets_source_zh": str(core_assets_zh),
                "required_asset_roles": list(required_roles),
                "horizon": str(horizon),
                "precision": str(precision),
                "progress_score_source_zh": str(progress_source),
                "progress_score": progress_score,
                "progress_score_total": progress_total,
                "source_warnings": TASK_SOURCE_WARNINGS.get(order, []),
            }
        )

    declared_count = int(source["declared_task_count"])
    observed_count = len(tasks)
    warnings = [
        (
            f"Task Design 正文声明第一期 {declared_count} tasks，但嵌入表格"
            f"实际包含 {observed_count} 行任务；目录按表格 {observed_count} 行保存。"
        ),
        (
            "Task Design 注意事项称仿真液体任务暂定只评估动作、忽略液体，"
            "但多项 Progress Score 仍包含液体转移比例；两种原文均保留。"
        ),
        (
            "Task Design 正文称长程实验操作为 7-11 steps，但第 18 行"
            "旋转蒸发记录为 13 steps；未修改源值。"
        ),
    ]
    return {
        "schema_version": "task-catalog/v0.2",
        "catalog_id": "scientific_workbench_phase1",
        "domain": "scientific_workbench",
        "source": {
            "kind": "feishu_embedded_sheet",
            "uri": str(source["wiki_url"]),
            "document_id": str(source["document_id"]),
            "document_revision": int(source["document_revision"]),
            "section_block_id": str(source["section_block_id"]),
            "section_sha256": str(source["section_sha256"]),
            "spreadsheet_token": str(source["spreadsheet_token"]),
            "spreadsheet_revision": int(source["spreadsheet_revision"]),
            "sheet_id": str(source["sheet_id"]),
            "range": str(source["range"]),
            "snapshot_path": SNAPSHOT_RELATIVE_PATH,
            "content_sha256": str(source["content_sha256"]),
            "captured_at": str(snapshot["captured_at"]),
        },
        "source_consistency": {
            "status": "warning" if warnings else "pass",
            "declared_task_count": declared_count,
            "observed_task_count": observed_count,
            "warnings": warnings,
        },
        "tasks": tasks,
    }


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def render_markdown(catalog: Mapping[str, object]) -> str:
    source = _mapping(catalog.get("source"), "catalog source")
    consistency = _mapping(
        catalog.get("source_consistency"),
        "catalog source consistency",
    )
    tasks = catalog.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("catalog tasks must be a list")

    lines = [
        "# Scientific Workbench Task Design",
        "",
        (
            f"正式产品标准来自飞书 [Task Design]({source['uri']})。"
            "本页由仓库中的固定快照生成，不是第二份手工任务定义。"
        ),
        "",
        (
            f"- 文档 revision：`{source['document_revision']}`；"
            f"表格 revision：`{source['spreadsheet_revision']}`"
        ),
        f"- 工作表：`{source['sheet_id']}`，范围：`{source['range']}`",
        f"- 内容哈希：`{source['content_sha256']}`",
        f"- 快照日期：`{source['captured_at']}`",
        "",
        "## Source warnings",
        "",
    ]
    for warning in consistency["warnings"]:
        lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## Task list",
            "",
            "| # | Stable task ID | 飞书任务 | 级别 | 模式 | 步骤 | 长程 | 精细 |",
            "|---:|---|---|---|---|---:|---|---|",
        ]
    )
    for raw_task in tasks:
        task = _mapping(raw_task, "catalog task")
        lines.append(
            "| "
            + " | ".join(
                [
                    str(task["source_order"]),
                    f"`{task['task_id']}`",
                    _markdown_cell(task["title_zh"]),
                    str(task["level"]),
                    str(task["execution_mode"]),
                    str(task["step_count"]),
                    str(task["horizon"]),
                    str(task["precision"]),
                ]
            )
            + " |"
        )

    for raw_task in tasks:
        task = _mapping(raw_task, "catalog task")
        lines.extend(
            [
                "",
                f"## {task['source_order']}. {task['title_zh']}",
                "",
                f"- Stable ID：`{task['task_id']}`",
                f"- 飞书行号：`{task['source_row']}`",
                (
                    f"- 模式：{_markdown_cell(task['execution_mode_source_zh'])}"
                    f" → `{task['execution_mode']}`"
                ),
                f"- 步骤数：{task['step_count']}",
                (
                    f"- 原子技能：{task['atomic_skills_source_zh']} → "
                    + ", ".join(f"`{skill}`" for skill in task["atomic_skills"])
                ),
                (f"- 核心资产原文：{_markdown_cell(task['core_assets_source_zh'])}"),
                (
                    "- 规范化资产角色："
                    + ", ".join(f"`{role}`" for role in task["required_asset_roles"])
                ),
                (f"- 长程/精细：`{task['horizon']}` / `{task['precision']}`"),
                "",
                "过程概述：",
                "",
                str(task["process_overview_zh"]),
                "",
                (f"Progress Score（原始权重合计 `{float(task['progress_score_total']):.2f}`）："),
                "",
            ]
        )
        for criterion in task["progress_score"]:
            lines.append(
                f"- 时序 {criterion['sequence']} · "
                f"{float(criterion['weight']):.2f}："
                f"{criterion['description_zh']}"
            )
        warnings = task["source_warnings"]
        if warnings:
            lines.extend(["", "Source warning：", ""])
            lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def render_html(catalog: Mapping[str, object]) -> str:
    source = _mapping(catalog.get("source"), "catalog source")
    consistency = _mapping(
        catalog.get("source_consistency"),
        "catalog source consistency",
    )
    tasks = catalog.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("catalog tasks must be a list")

    warnings = "".join(
        f"<li>{html.escape(str(warning))}</li>" for warning in consistency["warnings"]
    )
    summary_rows: list[str] = []
    details: list[str] = []
    for raw_task in tasks:
        task = _mapping(raw_task, "catalog task")
        summary_rows.append(
            "<tr>"
            f"<td>{task['source_order']}</td>"
            f"<td><code>{html.escape(str(task['task_id']))}</code></td>"
            f"<td>{html.escape(str(task['title_zh']))}</td>"
            f"<td>{html.escape(str(task['execution_mode_source_zh']))}</td>"
            f"<td>{task['step_count']}</td>"
            f"<td>{task['horizon']}</td>"
            f"<td>{task['precision']}</td>"
            "</tr>"
        )
        score_items = "".join(
            "<li>"
            f"时序 {criterion['sequence']} · "
            f"{float(criterion['weight']):.2f}："
            f"{html.escape(str(criterion['description_zh']))}"
            "</li>"
            for criterion in task["progress_score"]
        )
        task_warnings = "".join(
            f"<li>{html.escape(str(warning))}</li>" for warning in task["source_warnings"]
        )
        warning_block = (
            f'<h3>Source warning</h3><ul class="warning">{task_warnings}</ul>'
            if task_warnings
            else ""
        )
        details.append(
            f'<section id="task-{task["source_order"]}">'
            f"<h2>{task['source_order']}. "
            f"{html.escape(str(task['title_zh']))}</h2>"
            "<dl>"
            f"<dt>Stable ID</dt><dd><code>{task['task_id']}</code></dd>"
            f"<dt>飞书行号</dt><dd>{task['source_row']}</dd>"
            f"<dt>模式</dt><dd>{html.escape(str(task['execution_mode_source_zh']))}"
            f" → <code>{task['execution_mode']}</code></dd>"
            f"<dt>原子技能</dt><dd>{html.escape(str(task['atomic_skills_source_zh']))}"
            "</dd>"
            f"<dt>核心资产原文</dt><dd>"
            f"{html.escape(str(task['core_assets_source_zh']))}</dd>"
            f"<dt>规范化角色</dt><dd><code>"
            f"{html.escape(', '.join(task['required_asset_roles']))}"
            "</code></dd>"
            "</dl>"
            "<h3>过程概述</h3>"
            f"<p>{html.escape(str(task['process_overview_zh']))}</p>"
            f"<h3>Progress Score · 合计 "
            f"{float(task['progress_score_total']):.2f}</h3>"
            f"<ul>{score_items}</ul>{warning_block}</section>"
        )

    css = """
body{font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
max-width:1180px;margin:2rem auto;padding:0 1.5rem;color:#1f2329;line-height:1.65}
h1{border-bottom:2px solid #3370ff;padding-bottom:.45rem}h2{margin-top:2.2rem}
.provenance,.warning{background:#f5f6f7;border:1px solid #dee0e3;border-radius:8px;
padding:.8rem 1rem}.warning{background:#fff7e6;border-color:#ffd591}
table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{border:1px solid #dee0e3;
padding:7px 9px;text-align:left;vertical-align:top}th{background:#3370ff;color:white}
tbody tr:nth-child(even){background:#f8f9fa}code{overflow-wrap:anywhere}
dt{font-weight:600;float:left;clear:left;width:9rem}dd{margin-left:10rem;margin-bottom:.35rem}
@media(max-width:720px){table{display:block;overflow-x:auto}dt{float:none;width:auto}
dd{margin-left:0}}
"""
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
        '<meta charset="utf-8"/>\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        "<title>Scientific Workbench Task Design</title>\n"
        f"<style>{css}</style>\n</head>\n<body>\n"
        '<div class="provenance">'
        f'正式来源：<a href="{html.escape(str(source["uri"]))}">飞书 Task Design</a>'
        f"<br/>文档 revision {source['document_revision']}；"
        f"表格 revision {source['spreadsheet_revision']}；"
        f"范围 {source['range']}；快照 {source['captured_at']}"
        f"<br/>内容哈希：<code>{source['content_sha256']}</code>"
        "</div>\n"
        "<h1>Scientific Workbench Task Design</h1>\n"
        "<p>本页由固定飞书快照生成，不是第二份手工任务定义。</p>\n"
        f'<h2>Source warnings</h2><ul class="warning">{warnings}</ul>\n'
        "<h2>Task list</h2>\n"
        "<table><thead><tr><th>#</th><th>Stable ID</th><th>飞书任务</th>"
        "<th>模式</th><th>步骤</th><th>长程</th><th>精细</th></tr></thead>"
        f"<tbody>{''.join(summary_rows)}</tbody></table>\n"
        f"{''.join(details)}\n"
        "</body>\n</html>\n"
    )


def _snapshot_text(snapshot: Mapping[str, object]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"


def _catalog_text(catalog: Mapping[str, object]) -> str:
    return yaml.safe_dump(
        dict(catalog),
        allow_unicode=True,
        sort_keys=False,
        width=1000,
    )


def _expected_artifacts(
    snapshot: Mapping[str, object],
) -> dict[Path, str]:
    catalog = build_catalog(snapshot)
    return {
        SNAPSHOT_PATH: _snapshot_text(snapshot),
        CATALOG_PATH: _catalog_text(catalog),
        MARKDOWN_PATH: render_markdown(catalog),
        HTML_PATH: render_html(catalog),
    }


def write_artifacts(snapshot: Mapping[str, object]) -> None:
    for path, content in _expected_artifacts(snapshot).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)}")


def check_live_drift() -> int:
    if not SNAPSHOT_PATH.is_file():
        print(f"missing pinned snapshot: {SNAPSHOT_PATH.relative_to(REPO_ROOT)}")
        return 1
    pinned = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    live = fetch_live_snapshot(captured_at=str(pinned["captured_at"]))
    expected = _expected_artifacts(live)
    drifted = [
        path.relative_to(REPO_ROOT)
        for path, content in expected.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != content
    ]
    if drifted:
        print("Task Design drift detected:")
        for path in drifted:
            print(f"- {path}")
        print("Run this script with --write, review the diff, then commit it.")
        return 1
    print(f"Task Design snapshot is current: {live['source']['content_sha256']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Check or refresh the pinned scientific-workbench Task Design catalog.")
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Read Feishu and fail if the pinned snapshot or generated files drift.",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="Refresh the pinned snapshot and all generated catalog references.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        return check_live_drift()
    snapshot = fetch_live_snapshot()
    write_artifacts(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
