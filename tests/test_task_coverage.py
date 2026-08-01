from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scenario_forge.generation.coverage.task_coverage import (
    CoveragePlanError,
    build_task_coverage_plan,
    refresh_release_evidence,
    write_convertasset_admission_request,
    write_task_directory,
)


def _catalog() -> dict[str, object]:
    return {
        "schema_version": "task-catalog/v0.2",
        "catalog_id": "wetlab",
        "domain": "scientific_workbench",
        "source": {"content_sha256": "sha256:catalog"},
        "tasks": [
            {
                "task_id": "pour",
                "source_order": 1,
                "title_zh": "倒液",
                "required_asset_roles": ["flask", "cylinder"],
            },
            {
                "task_id": "stir",
                "source_order": 2,
                "title_zh": "搅拌",
                "required_asset_roles": ["beaker", "glass_rod"],
            },
        ],
    }


def _inventory() -> dict[str, object]:
    return {
        "schema_version": "task-coverage-asset-inventory/v0.1",
        "inventory_id": "wetlab-assets",
        "default_environment_binding": "room",
        "default_table_binding": "table",
        "assets": {
            "flask": {
                "binding_id": "flask_asset",
                "admission_status": "pass",
                "manifest_sha256": "sha256:flask",
            },
            "cylinder": {
                "binding_id": "cylinder_asset",
                "admission_status": "pass",
                "manifest_sha256": "sha256:cylinder",
            },
            "beaker": {
                "binding_id": "beaker_asset",
                "admission_status": "pass",
                "manifest_sha256": "sha256:beaker",
            },
        },
    }


def test_coverage_plan_queues_only_fully_admitted_canonical_tasks() -> None:
    plan = build_task_coverage_plan(
        catalog=_catalog(),
        inventory=_inventory(),
        binding_ids={"room", "table", "flask_asset", "cylinder_asset", "beaker_asset"},
        canonical_recipe_ids={"pour"},
    )

    assert plan["summary"] == {"task_count": 2, "queued": 1, "blocked": 1}
    assert plan["tasks"][0] == {
        "task_id": "pour",
        "source_order": 1,
        "title_zh": "倒液",
        "status": "queued",
        "canonical_recipe_id": "pour",
        "required_asset_roles": ["flask", "cylinder"],
        "asset_bindings": {"flask": "flask_asset", "cylinder": "cylinder_asset"},
        "blockers": [],
    }
    assert plan["tasks"][1]["status"] == "blocked"
    assert plan["tasks"][1]["blockers"] == [
        "asset role 'glass_rod' has no inventory record",
        "canonical task recipe has not been authored",
    ]


def test_coverage_plan_blocks_failed_admission_and_unknown_binding() -> None:
    inventory = _inventory()
    assets = inventory["assets"]
    assert isinstance(assets, dict)
    assets["cylinder"] = {
        "binding_id": "missing_binding",
        "admission_status": "pass",
        "manifest_sha256": "sha256:cylinder",
    }
    plan = build_task_coverage_plan(
        catalog=_catalog(),
        inventory=inventory,
        binding_ids={"room", "table", "flask_asset", "beaker_asset"},
        canonical_recipe_ids={"pour"},
    )

    assert plan["tasks"][0]["status"] == "blocked"
    assert plan["tasks"][0]["blockers"] == [
        "asset role 'cylinder' binding 'missing_binding' is not in source bindings"
    ]


def test_coverage_plan_requires_admitted_environment_and_table() -> None:
    inventory = _inventory()
    inventory["default_environment_binding"] = "missing_room"
    with pytest.raises(CoveragePlanError, match="default_environment_binding"):
        build_task_coverage_plan(
            catalog=_catalog(),
            inventory=inventory,
            binding_ids={"room", "table", "flask_asset", "cylinder_asset", "beaker_asset"},
            canonical_recipe_ids={"pour"},
        )


def test_convertasset_request_contains_only_missing_or_unadmitted_roles(tmp_path: Path) -> None:
    plan = build_task_coverage_plan(
        catalog=_catalog(),
        inventory=_inventory(),
        binding_ids={"room", "table", "flask_asset", "cylinder_asset", "beaker_asset"},
        canonical_recipe_ids={"pour"},
    )

    request_path = write_convertasset_admission_request(plan, tmp_path / "request.yaml")
    request = yaml.safe_load(request_path.read_text(encoding="utf-8"))

    assert request["schema_version"] == "scenario-forge-convertasset-admission-request/v0.1"
    assert request["requested_asset_roles"] == [
        {
            "asset_role": "glass_rod",
            "blocked_tasks": ["stir"],
            "reason": "asset role 'glass_rod' has no inventory record",
        }
    ]
    assert request["source_preservation"] == "producer_side_copy_only; original source immutable"


def test_task_directory_keeps_immutable_release_and_latest_separate(tmp_path: Path) -> None:
    plan = build_task_coverage_plan(
        catalog=_catalog(),
        inventory=_inventory(),
        binding_ids={"room", "table", "flask_asset", "cylinder_asset", "beaker_asset"},
        canonical_recipe_ids={"pour"},
    )
    release = {
        "task_id": "pour",
        "release_id": "pour.v20260801.1",
        "package_path": "releases/pour.v20260801.1",
        "background_binding": "room",
        "evidence": {
            "overview_image": "images/pour_overview.png",
            "closeup_image": "images/pour_closeup.png",
        },
        "gates": {
            "self_contained_package": "pass",
            "runtime_reset": "pass",
            "tabletop_placement": "pass",
            "visual_review": "pass",
            "provisional_ik": "pass",
        },
    }

    result = write_task_directory(
        plan,
        [release],
        output_dir=tmp_path / "directory",
    )
    index = yaml.safe_load((result / "task_directory.yaml").read_text(encoding="utf-8"))

    assert index["tasks"][0]["latest_release_id"] == "pour.v20260801.1"
    assert index["tasks"][0]["latest_status"] == "runtime_reset_provisional_ik_pass"
    assert index["tasks"][0]["latest_evidence"]["overview_image"] == "images/pour_overview.png"
    assert index["tasks"][1]["latest_release_id"] is None
    assert "倒液" in (result / "index.md").read_text(encoding="utf-8")
    assert '<img src="images/pour_overview.png"' in (result / "index.html").read_text(
        encoding="utf-8"
    )


def test_task_directory_html_keeps_wide_tables_inside_a_scroll_container(tmp_path: Path) -> None:
    plan = {
        "catalog_id": "catalog",
        "default_environment_binding": "environment",
        "default_table_binding": "table",
        "tasks": [
            {
                "task_id": "pour",
                "source_order": 1,
                "title_zh": "倒液",
                "status": "queued",
                "blockers": [],
            }
        ],
        "claim_boundary": "boundary",
    }
    releases = [
        {
            "task_id": "pour",
            "release_id": "pour.v1",
            "package_path": "packages/pour",
            "background_binding": "environment",
            "promotion": "candidate",
            "evidence": {"overview_image": "images/pour.png"},
            "gates": {
                "self_contained_package": "not_run",
                "runtime_reset": "not_run",
                "tabletop_placement": "not_run",
                "visual_review": "not_run",
                "provisional_ik": "not_run",
            },
        }
    ]

    result = write_task_directory(plan, releases, output_dir=tmp_path / "directory")

    html = (result / "index.html").read_text(encoding="utf-8")
    assert '<div class="table-scroll"><table>' in html
    assert ".table-scroll{max-width:100%;overflow-x:auto}" in html
    assert 'class="task-title"' in html
    assert 'class="release-id"' in html
    assert ".release-id{overflow-wrap:anywhere" in html
    assert 'class="scroll-hint"' in html


def test_task_directory_shows_candidate_evidence_without_promoting_it(tmp_path: Path) -> None:
    plan = build_task_coverage_plan(
        catalog=_catalog(),
        inventory=_inventory(),
        binding_ids={"room", "table", "flask_asset", "cylinder_asset", "beaker_asset"},
        canonical_recipe_ids={"pour"},
    )
    result = write_task_directory(
        plan,
        [
            {
                "task_id": "pour",
                "release_id": "pour.v20260801.1",
                "package_path": "releases/pour.v20260801.1",
                "background_binding": "room",
                "promotion": "candidate",
                "evidence": {"overview_image": "images/pour_candidate.png"},
                "gates": {
                    "self_contained_package": "not_run",
                    "runtime_reset": "pass",
                    "tabletop_placement": "pass",
                    "visual_review": "not_run",
                    "provisional_ik": "not_run",
                },
            }
        ],
        output_dir=tmp_path / "directory",
    )
    index = yaml.safe_load((result / "task_directory.yaml").read_text(encoding="utf-8"))

    assert index["tasks"][0]["latest_release_id"] is None
    assert index["tasks"][0]["candidate_release_id"] == "pour.v20260801.1"
    assert index["tasks"][0]["candidate_evidence"] == {
        "overview_image": "images/pour_candidate.png"
    }
    assert '<img src="images/pour_candidate.png"' in (result / "index.html").read_text(
        encoding="utf-8"
    )
    assert "| # | Task | Queue | Current candidate | Latest qualified |" in (
        result / "index.md"
    ).read_text(encoding="utf-8")


def test_task_directory_refuses_to_promote_partial_gate_release(tmp_path: Path) -> None:
    plan = build_task_coverage_plan(
        catalog=_catalog(),
        inventory=_inventory(),
        binding_ids={"room", "table", "flask_asset", "cylinder_asset", "beaker_asset"},
        canonical_recipe_ids={"pour"},
    )
    with pytest.raises(CoveragePlanError, match="cannot be promoted"):
        write_task_directory(
            plan,
            [
                {
                    "task_id": "pour",
                    "release_id": "pour.v1",
                    "package_path": "releases/pour.v1",
                    "background_binding": "room",
                    "gates": {
                        "self_contained_package": "pass",
                        "runtime_reset": "pass",
                        "tabletop_placement": "pass",
                        "visual_review": "pass",
                        "provisional_ik": "not_run",
                    },
                }
            ],
            output_dir=tmp_path / "directory",
        )


def test_refresh_release_evidence_promotes_only_complete_candidate(tmp_path: Path) -> None:
    package = tmp_path / "package"
    (package / "evidence").mkdir(parents=True)
    (package / "adapters/ebench/genmanip/evidence/initial_scene").mkdir(parents=True)
    evidence = {
        "evidence/package_closure.yaml": {"status": "pass"},
        "evidence/tabletop_placement_policy.yaml": {"overall_status": "pass"},
        "evidence/phase11_visual_review_gate.yaml": {"status": "passed"},
        "evidence/provisional_ik_preflight.yaml": {"overall_status": "pass"},
        "adapters/ebench/genmanip/evidence/initial_scene/visual_ready_gate.yaml": {
            "status": "passed"
        },
    }
    for relative, payload in evidence.items():
        (package / relative).write_text(yaml.safe_dump(payload), encoding="utf-8")
    release = {
        "task_id": "pour",
        "release_id": "pour.v4",
        "package_path": str(package),
        "background_binding": "room",
        "promotion": "candidate",
        "gates": {gate: "not_run" for gate in (
            "self_contained_package",
            "runtime_reset",
            "tabletop_placement",
            "visual_review",
            "provisional_ik",
        )},
    }

    refreshed = refresh_release_evidence([release])

    assert refreshed == [
        {
            **release,
            "promotion": "latest",
            "gates": {
                "self_contained_package": "pass",
                "runtime_reset": "pass",
                "tabletop_placement": "pass",
                "visual_review": "pass",
                "provisional_ik": "pass",
            },
        }
    ]


def test_refresh_release_evidence_retains_candidate_for_missing_gate(tmp_path: Path) -> None:
    release = {
        "task_id": "pour",
        "release_id": "pour.v4",
        "package_path": str(tmp_path / "missing-package"),
        "background_binding": "room",
        "promotion": "candidate",
        "gates": {gate: "not_run" for gate in (
            "self_contained_package",
            "runtime_reset",
            "tabletop_placement",
            "visual_review",
            "provisional_ik",
        )},
    }

    refreshed = refresh_release_evidence([release])

    assert refreshed[0]["promotion"] == "candidate"
    assert refreshed[0]["gates"] == {
        "self_contained_package": "not_run",
        "runtime_reset": "not_run",
        "tabletop_placement": "not_run",
        "visual_review": "not_run",
        "provisional_ik": "not_run",
    }
