from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from scenario_forge.generation.layout.constraints import load_layout_constraints
from scenario_forge.generation.layout.relational_solver import (
    solve_relational_tabletop_layout,
)
from scenario_forge.generation.spec_composer import (
    compose_scenario_spec_from_solved_layout,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(script_name: str):
    path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r3_task_bundles_and_bindings_reference_v2_swarm_rooms() -> None:
    expected = {
        "specialty_coffee_bar_creatista_prep.yaml": (
            "out_of_domain_env_kitchen_coffee_bar_v2",
            6,
            "dial_press",
            "pressed",
        ),
        "electronics_qa_ingun_probe_lock.yaml": (
            "out_of_domain_env_smt_qa_workshop_v2",
            5,
            "test_start_button",
            "pressed",
        ),
        "modern_office_brother_calibrate.yaml": (
            "out_of_domain_env_office_print_studio_v2",
            5,
            "button_start",
            "pressed",
        ),
    }
    bindings_path = (
        REPO_ROOT / "configs/source_bindings/out_of_domain_hero_r3_20261113.yaml"
    )
    assert bindings_path.is_file()
    bindings_doc = yaml.safe_load(bindings_path.read_text(encoding="utf-8"))
    assert bindings_doc["schema_version"] == "scenario-source-bindings/v0.5"
    bindings = bindings_doc["bindings"]
    for env_id, _, _, _ in expected.values():
        assert env_id in bindings
        assert "out_of_domain_factory_r3_20261113/rooms/packages/" in bindings[env_id]["package_dir"]

    for fname, (env_id, stage_count, final_joint, final_state) in expected.items():
        bundle_path = REPO_ROOT / "configs/out_of_domain_tasks_r3" / fname
        assert bundle_path.is_file(), f"missing r3 bundle: {bundle_path}"
        bundle = yaml.safe_load(bundle_path.read_text(encoding="utf-8"))
        assert (
            bundle["source_bindings"]
            == "configs/source_bindings/out_of_domain_hero_r3_20261113.yaml"
        )
        assert bundle["task_draft"]["scene"]["asset_id"] == env_id
        constraints = load_layout_constraints((REPO_ROOT / bundle["domain_pack"]).parent)
        solved = solve_relational_tabletop_layout(
            bundle["layout_request"], domain_constraints=constraints
        )
        assert solved.status == "solved"
        spec = compose_scenario_spec_from_solved_layout(bundle["task_draft"], solved)
        spec_map = spec.to_mapping()
        preds = spec_map["success"]["predicates"]
        rubric_items = spec_map["success"]["progress_rubric"]["items"]
        assert len(preds) == stage_count
        assert len(rubric_items) == stage_count
        assert abs(sum(float(it["weight"]) for it in rubric_items) - 1.0) < 1e-6
        last_pred = preds[-1]
        assert last_pred["parameters"]["joint"] == final_joint
        assert last_pred["parameters"]["state"] == final_state


def test_canary_and_media_scripts_accept_r3_profile() -> None:
    canary = _load_script_module("verify_genmanip_predicate_canary.py")
    media = _load_script_module("render_out_of_domain_canary_media.py")
    assert canary._plans_for_profile("r3") is canary.STAGE_CANARY_PLANS_R2
    assert media._media_specs_for_profile("r3") is media.SCENARIO_MEDIA_SPECS_R2


def test_showcase_html_renders_r3_gen008_g9b_and_swarm_rooms(tmp_path: Path) -> None:
    from tests.test_out_of_domain_showcase_html import _minimal_png_bytes

    builder = _load_script_module("build_out_of_domain_showcase_html.py")
    png_path = tmp_path / "img.png"
    mp4_path = tmp_path / "vid.mp4"
    png_path.write_bytes(_minimal_png_bytes())
    mp4_path.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")
    png_uri = builder.encode_lossless_png_data_uri(png_path)
    mp4_uri = builder.encode_mp4_data_uri(mp4_path)

    model = {
        "generated_date": "2026-11-13",
        "edition": "r3",
        "ika_acceptance": {
            "benchmark_reference": "IKA OVEN 125 (309 KB, 16 Joints, 100 Colliders)",
            "total_dofs_verified": 21,
            "passed_gates": 30,
            "total_gates": 30,
            "all_gates_pass": True,
            "heroes": [
                {
                    "slug": "nespresso-creatista-plus-bne800",
                    "asset_id": "NespressoCreatistaPlus",
                    "usd_kb": 2800.0,
                    "visual_prims": 156,
                    "collider_prims": 22,
                    "dof_count": 8,
                    "load_600f_drift_mm": 0.0001,
                    "rail_transport_pass": True,
                    "gates_passed": "10/10 PASS",
                    "g9b": {
                        "verdict": "PASS",
                        "min_dimension_score": 8.7,
                        "dimensions": {"silhouette_and_proportion": 9.2},
                    },
                    "r1_iso_uri": png_uri,
                    "r2_iso_uri": png_uri,
                    "rtx_inspection_uri": png_uri,
                }
            ],
        },
        "room_upgrades": {
            "rooms": [
                {
                    "room_id": "kitchen_coffee_bar_v2",
                    "asset_id": "out_of_domain_env_kitchen_coffee_bar_v2",
                    "overall_status": "pass",
                    "manifest_sha256": "abc123",
                    "texture_count": 15,
                    "cycles_critique": {"verdict": "PASS", "min_score": 8.6, "mean_score": 8.98},
                    "rtx_critique": {"verdict": "PASS", "min_score": 8.5, "mean_score": 8.80},
                }
            ]
        },
        "scenarios": [
            {
                "scenario_id": "specialty_coffee_bar_creatista_prep",
                "index_badge": "SCENARIO 01 · SPECIALTY COFFEE BAR · R3 SWARM",
                "title_zh": "精品咖啡吧 · r3 实证",
                "domain": "specialty_coffee_bar",
                "room_id": "kitchen_coffee_bar_v2",
                "room_manifest_sha256": "abc123",
                "hero": {
                    "asset_id": "NespressoCreatistaPlus",
                    "slug": "nespresso-creatista-plus-bne800",
                    "model_name": "Breville / Nespresso Creatista Plus (BNE800) · r2 CAD",
                    "envelope_mm": "171 × 393 × 308 mm",
                    "mass_kg": 5.2,
                    "dof_summary": "8-DOF CAD",
                    "cavity_summary": "46x48mm CapsuleChute",
                    "manifest_sha256": "def456",
                    "studio_views": [{"label": "Isometric", "data_uri": png_uri}],
                    "joints": [
                        {
                            "name": "dial_press",
                            "type": "Prismatic",
                            "limits": "[0, 3.2 mm]",
                            "semantics": "released -> pressed",
                        }
                    ],
                },
                "initial_views": [{"view_id": "scene_overview", "label": "全域总览", "data_uri": png_uri}],
                "progression_video_uri": mp4_uri,
                "canary_stages": [
                    {
                        "stage_key": "t0",
                        "badge": "t = 0",
                        "title": "Cold Reset",
                        "score": 0.0,
                        "predicate_summary": "All False",
                        "physics_readout": "0.000 mm",
                        "keyframe_uri": png_uri,
                    }
                ],
                "critic1": {
                    "max_translation_drift_mm": 0.0,
                    "max_orientation_drift_deg": 0.0,
                    "max_joint_drift": 0.0,
                    "t0_score": 0.0,
                    "final_score": 1.0,
                    "report_sha256": "sha256:000",
                },
                "layout_svg_solved": "<svg viewBox='0 0 100 50'><rect width='100' height='50'/></svg>",
                "layout_svg_unrepaired": None,
                "critic_repair_note": None,
                "reach_rows": [],
            }
        ],
        "bugs_caught": [],
    }

    html_out = builder.render_showcase_html(model)
    audit = builder.audit_self_contained_html(html_out)
    assert audit["external_url_count"] == 0
    assert "30/30 PASS" in html_out
    assert "10/10 PASS" in html_out
    assert "kitchen_coffee_bar_v2" in html_out
    assert "out_of_domain_factory_r3_20261113" in html_out
