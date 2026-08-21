from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

from scripts import sync_scientific_workbench_task_catalog as sync


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "configs/task_catalogs/scientific_workbench_phase1.yaml"
SNAPSHOT_PATH = REPO_ROOT / "configs/task_catalogs/sources/scientific_workbench_task_design.json"
READINESS_PATH = (
    REPO_ROOT
    / "docs/records/evidence/2026-07-31-scientific-workbench-task-design-correction/readiness.yaml"
)
MARKDOWN_PATH = REPO_ROOT / "docs/reference/scientific-workbench-task-design.md"
HTML_PATH = REPO_ROOT / "docs/reference/scientific-workbench-task-design.html"
LEGACY_CATALOG_PATH = (
    REPO_ROOT
    / "docs/records/evidence/2026-07-31-scientific-workbench-task-design-correction"
    / "legacy_pdf_catalog_v0.1.yaml"
)
LIVE_TASK_ASSET_REQUEST_PATH = (
    REPO_ROOT
    / "docs/operations/scientific-workbench-live-task-7-10-11-asset-admission-request.yaml"
)
HCI_15ML_CLOSED_INSERT_LID_REQUEST_PATH = (
    REPO_ROOT
    / "docs/operations/scientific-workbench-hci-15ml-closed-insert-lid-admission-request.yaml"
)
CONICAL_FLASK_90X35_GLASS_WARP_REQUEST_PATH = (
    REPO_ROOT
    / "docs/operations/scientific-workbench-conical-flask-90x35-glass-warp-admission-request.yaml"
)
ASSET_EXPANSION_BINDINGS_PATH = (
    REPO_ROOT / "configs/source_bindings/scientific_workbench_asset_expansion_20260810.yaml"
)
IDENTITY_CONICAL_FACADE_SHA256 = (
    "82115bd942c40214fdb2bacc6f4327111b452e67280bb3405b2451ddee6a83b9"
)


def _load_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_catalog_v02_schema_validates_the_feishu_derived_catalog() -> None:
    schema_path = REPO_ROOT / "src/scenario_forge/schemas/jsonschema/task-catalog-v0.2.schema.json"
    schema = _load_json(schema_path)
    catalog = _load_yaml(CATALOG_PATH)

    assert schema["properties"]["schema_version"]["const"] == "task-catalog/v0.2"
    Draft202012Validator(schema).validate(catalog)


def test_snapshot_pins_the_live_task_design_sheet_and_all_18_rows() -> None:
    snapshot = _load_json(SNAPSHOT_PATH)
    source = snapshot["source"]
    rows = snapshot["rows"]

    assert snapshot["schema_version"] == "task-design-source-snapshot/v0.1"
    assert isinstance(source, dict)
    assert source["wiki_url"] == ("https://aicarrier.feishu.cn/wiki/GNGCwR2uAi9dK3k6FT0cX5krnab")
    assert source["document_id"] == "YdLVdAe7noWEWTxaUTxcKD28nUh"
    assert source["document_revision"] == 1576
    assert source["spreadsheet_revision"] == 564
    assert source["sheet_id"] == "J1nUiN"
    assert source["range"] == "A1:J19"
    assert source["declared_task_count"] == 17
    assert isinstance(rows, list)
    assert len(rows) == 18


def test_catalog_uses_stable_non_lab_identity_and_live_row_order() -> None:
    catalog = _load_yaml(CATALOG_PATH)
    tasks = catalog["tasks"]
    source_consistency = catalog["source_consistency"]

    assert catalog["schema_version"] == "task-catalog/v0.2"
    assert isinstance(tasks, list)
    assert len(tasks) == 18
    assert [task["source_order"] for task in tasks] == list(range(1, 19))
    assert all(task["task_id"].startswith("scientific_workbench_") for task in tasks)
    assert all("wetlab" not in task["task_id"] for task in tasks)
    assert isinstance(source_consistency, dict)
    assert source_consistency["status"] == "warning"
    assert source_consistency["declared_task_count"] == 17
    assert source_consistency["observed_task_count"] == 18


def test_live_tasks_7_10_and_11_are_not_the_old_pdf_tasks() -> None:
    catalog = _load_yaml(CATALOG_PATH)
    tasks = catalog["tasks"]
    assert isinstance(tasks, list)
    by_order = {task["source_order"]: task for task in tasks}

    task7 = by_order[7]
    assert task7["task_id"] == "scientific_workbench_glass_rod_stir"
    assert task7["title_zh"] == "玻璃棒搅拌"
    assert task7["step_count"] == 5
    assert task7["atomic_skills"] == [
        "grasp",
        "pick",
        "insert",
        "stir",
        "place",
    ]
    assert task7["required_asset_roles"] == ["glass_rod", "beaker"]
    assert task7["horizon"] == "middle"
    assert task7["precision"] == "low"
    assert task7["progress_score_total"] == 1.0
    assert [item["weight"] for item in task7["progress_score"]] == [
        0.15,
        0.20,
        0.35,
        0.20,
        0.10,
    ]

    task10 = by_order[10]
    assert task10["task_id"] == "scientific_workbench_centrifuge_load_start"
    assert task10["title_zh"] == "仪器交互/开启离心机"
    assert "setting_button" in task10["required_asset_roles"]

    task11 = by_order[11]
    assert task11["task_id"] == ("scientific_workbench_centrifuge_unload_shutdown")
    assert task11["title_zh"] == "仪器交互/结束离心"
    assert task11["step_count"] == 4
    assert task11["atomic_skills"] == ["press", "pick", "place"]
    assert "lid_open_button" in task11["required_asset_roles"]
    assert "shutdown_button" in task11["required_asset_roles"]
    assert task11["progress_score_total"] == 1.0


def test_source_warnings_are_preserved_without_silent_repairs() -> None:
    catalog = _load_yaml(CATALOG_PATH)
    tasks = catalog["tasks"]
    assert isinstance(tasks, list)
    by_order = {task["source_order"]: task for task in tasks}

    task12 = by_order[12]
    assert task12["progress_score_total"] == 0.9
    assert any("0.90" in warning for warning in task12["source_warnings"])

    assert any("核心资产" in warning for warning in by_order[13]["source_warnings"])
    assert any("锥形瓶" in warning for warning in by_order[14]["source_warnings"])
    assert any("重复" in warning for warning in by_order[17]["source_warnings"])


def test_checked_in_catalog_and_references_are_deterministic_from_snapshot() -> None:
    snapshot = _load_json(SNAPSHOT_PATH)
    catalog = sync.build_catalog(snapshot)

    assert catalog == _load_yaml(CATALOG_PATH)
    assert sync.render_markdown(catalog) == MARKDOWN_PATH.read_text(encoding="utf-8")
    assert sync.render_html(catalog) == HTML_PATH.read_text(encoding="utf-8")


def test_current_readiness_uses_only_the_live_catalog_task_ids() -> None:
    catalog = _load_yaml(CATALOG_PATH)
    readiness = _load_yaml(READINESS_PATH)
    task_statuses = readiness["tasks"]
    assert isinstance(task_statuses, list)
    catalog_tasks = catalog["tasks"]
    assert isinstance(catalog_tasks, list)

    assert readiness["schema_version"] == "task-readiness-snapshot/v0.1"
    assert {item["task_id"] for item in task_statuses} == {
        item["task_id"] for item in catalog_tasks
    }

    task7 = next(
        item for item in task_statuses if item["task_id"] == "scientific_workbench_glass_rod_stir"
    )
    assert task7["compile_status"] == "blocked"
    assert "glass rod" in " ".join(task7["blockers"]).lower()

    task11 = next(
        item
        for item in task_statuses
        if item["task_id"] == "scientific_workbench_centrifuge_unload_shutdown"
    )
    assert task11["compile_status"] == "blocked"
    blockers = " ".join(task11["blockers"])
    assert "lid-open" in blockers
    assert "shutdown" in blockers
    assert "off-state" in blockers


def test_convertasset_request_uses_live_task_7_10_11_identities() -> None:
    request = _load_yaml(LIVE_TASK_ASSET_REQUEST_PATH)
    tasks = request["tasks"]
    assert isinstance(tasks, list)

    assert {(task["source_order"], task["task_id"], task["source_title_zh"]) for task in tasks} == {
        (7, "scientific_workbench_glass_rod_stir", "玻璃棒搅拌"),
        (
            10,
            "scientific_workbench_centrifuge_load_start",
            "仪器交互/开启离心机",
        ),
        (
            11,
            "scientific_workbench_centrifuge_unload_shutdown",
            "仪器交互/结束离心",
        ),
    }
    assert request["ownership_boundary"]["consumer_specific_scale_or_physics_patch_forbidden"]


def test_hci_15ml_closed_insert_lid_admission_pins_scale_gates_and_isaac_video() -> None:
    request = _load_yaml(HCI_15ML_CLOSED_INSERT_LID_REQUEST_PATH)
    catalog_identity = request["catalog_identity"]
    tube = request["deliveries"]["closed_tube"]
    scale = tube["non_uniform_scale"]
    gates = request["runtime_qualification"]["required_pass_records"]
    video = request["runtime_qualification"]["isaac_demo"]

    assert catalog_identity["canonical_feishu_task"] is False
    assert scale["k_d"] == [0.50, 0.55]
    assert scale["k_h"] == [0.33, 0.37]
    assert tube["assembly"] == "closed_rigid"
    assert gates == ["socket_insertion_clearance", "lid_contact_cycle"]
    assert video["format"] == "mp4"
    assert video["sequence"] == ["lid_open", "tube_insert", "lid_close"]
    assert video["engine"] == "isaac_sim_4.1"


def test_conical_flask_90x35_glass_warp_admission_pins_bake_not_consumer_scale() -> None:
    request = _load_yaml(CONICAL_FLASK_90X35_GLASS_WARP_REQUEST_PATH)
    flask = request["deliveries"]["conical_flask_90x35_glass_warp"]
    warp = flask["axisymmetric_warp"]
    facade = flask["producer_facade"]
    package = flask["package"]
    exception = request["producer_boundary"]["uniform_geometry_scale_only_exception"]

    assert request["catalog_identity"]["canonical_feishu_task"] is False
    assert request["producer_boundary"]["consumer_specific_scale_or_physics_patch_forbidden"]
    assert "bake_axisymmetric_krz_and_kh" in exception
    assert "this flask" in exception.lower() or "this conical flask" in exception.lower()
    assert flask["asset_id"] == "scientific_workbench_conical_flask_90x35_glass_warp"
    assert flask["do_not_replace_binding"] == "scientific_workbench_conical_bottle03_dynamic"
    assert flask["source"]["identity_facade_sha256"] == IDENTITY_CONICAL_FACADE_SHA256
    assert facade["bake_axisymmetric_krz_and_kh"] is True
    assert facade["root_scale_must_be_identity"] is True
    assert warp["target_belly_od_mm"] == 90.0
    assert warp["target_inner_mouth_mm"] == 35.0
    assert warp["target_height_mm"] == 150.0
    assert warp["measurement_tolerance_mm"] == 1.0
    assert package["asset_role"] == "dynamic"
    assert package["asset_entry_prim"] == "/World/ConicalFlask90x35Warp"
    assert flask["interaction"]["open_top"]["required"] is True
    assert flask["interaction"]["colliders"][0]["mode"] == "preserve"
    assert flask["interaction"]["colliders"][0]["approximation"] == "sdf"
    assert "250 mL" in " ".join(request["handoff"]["claims_not_requested"]) or (
        "volume_250ml" in request["handoff"]["claims_not_requested"]
    )
    assert "gpu_pbd" in request["handoff"]["claims_not_requested"]
    assert "pour_success" in request["handoff"]["claims_not_requested"]


def test_conical_flask_90x35_glass_warp_binding_does_not_replace_bottle03() -> None:
    bindings = _load_yaml(ASSET_EXPANSION_BINDINGS_PATH)["bindings"]
    bottle03 = bindings["scientific_workbench_conical_bottle03_dynamic"]
    warp = bindings["scientific_workbench_conical_flask_90x35_glass_warp_dynamic"]

    assert bottle03["package_dir"].endswith("conical_bottle_identity/package")
    assert bottle03["expected_scope_prims"] == ["/World/conical_bottle03"]
    assert warp["resolver"] == "convert_asset_package"
    assert warp["usage"] == "rigid_object"
    assert warp["license"] == "LicenseRef-Internal-Restricted"
    assert warp["redistributable"] is False
    assert warp["expected_scope_prims"] == ["/World/ConicalFlask90x35Warp"]
    assert warp["package_dir"].endswith(
        "scientific_workbench_conical_flask_90x35_glass_warp_20260821/package"
    )
    assert "lab" not in warp["package_dir"].split("/")[-2]
    assert warp["producer_revision"] == (
        "scientific-workbench-conical-flask-90x35-glass-warp-20260821"
    )


def test_legacy_pdf_catalog_is_archived_but_not_active() -> None:
    legacy = _load_yaml(LEGACY_CATALOG_PATH)
    active = _load_yaml(CATALOG_PATH)

    assert legacy["schema_version"] == "task-catalog/v0.1"
    assert legacy["source"]["filename"] == "湿实验具身操作评测任务设计.pdf"
    assert len(legacy["tasks"]) == 19
    assert active["schema_version"] == "task-catalog/v0.2"
