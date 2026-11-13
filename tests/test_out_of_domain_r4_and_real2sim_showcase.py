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


def test_r4_task_bundles_and_bindings_reference_legged_tables_and_native_rooms() -> None:
    expected = {
        "specialty_coffee_bar_creatista_prep.yaml": (
            "out_of_domain_env_kitchen_coffee_bar_v2",
            "CoffeeBarOakSteelTable",
            6,
        ),
        "electronics_qa_ingun_probe_lock.yaml": (
            "out_of_domain_env_smt_qa_workshop_v2",
            "SmtEsdAluminumBenchTable",
            5,
        ),
        "modern_office_brother_calibrate.yaml": (
            "out_of_domain_env_office_print_studio_v2",
            "OfficeBirchSteelTable",
            5,
        ),
    }
    bindings_path = (
        REPO_ROOT / "configs/source_bindings/out_of_domain_hero_r4_20261113.yaml"
    )
    assert bindings_path.is_file()
    bindings_doc = yaml.safe_load(bindings_path.read_text(encoding="utf-8"))
    assert bindings_doc["schema_version"] == "scenario-source-bindings/v0.5"
    bindings = bindings_doc["bindings"]

    for fname, (env_id, table_id, stage_count) in expected.items():
        assert env_id in bindings
        assert table_id in bindings
        assert (
            "out_of_domain_factory_r4_20261113/rooms/packages/"
            in bindings[env_id]["package_dir"]
        )
        assert (
            f"out_of_domain_factory_r4_20261113/tables/{table_id}/package"
            in bindings[table_id]["package_dir"]
        )

        bundle_path = REPO_ROOT / "configs/out_of_domain_tasks_r4" / fname
        assert bundle_path.is_file()
        bundle = yaml.safe_load(bundle_path.read_text(encoding="utf-8"))
        assert (
            bundle["source_bindings"]
            == "configs/source_bindings/out_of_domain_hero_r4_20261113.yaml"
        )
        assert bundle["task_draft"]["scene"]["asset_id"] == env_id
        assert bundle["task_draft"]["table"]["asset_id"] == table_id

        constraints = load_layout_constraints((REPO_ROOT / bundle["domain_pack"]).parent)
        solved = solve_relational_tabletop_layout(
            bundle["layout_request"], domain_constraints=constraints
        )
        assert solved.status == "solved"
        spec = compose_scenario_spec_from_solved_layout(bundle["task_draft"], solved)
        spec_map = spec.to_mapping()
        assert len(spec_map["success"]["predicates"]) == stage_count


def test_canary_and_media_scripts_accept_r4_and_real2sim_profiles() -> None:
    canary = _load_script_module("verify_genmanip_predicate_canary.py")
    media = _load_script_module("render_out_of_domain_canary_media.py")

    r4_plans = canary._plans_for_profile("r4")
    assert set(r4_plans) == {
        "specialty_coffee_bar_creatista_prep",
        "electronics_qa_ingun_probe_lock",
        "modern_office_brother_calibrate",
    }

    r2s_plans = canary._plans_for_profile("real2sim")
    assert "real2sim_office_desk_riser_organize" in r2s_plans
    assert len(r2s_plans["real2sim_office_desk_riser_organize"]) == 5

    r4_media = media._media_specs_for_profile("r4")
    assert set(r4_media) == {
        "specialty_coffee_bar_creatista_prep",
        "electronics_qa_ingun_probe_lock",
        "modern_office_brother_calibrate",
    }

    r2s_media = media._media_specs_for_profile("real2sim")
    assert "real2sim_office_desk_riser_organize" in r2s_media
    assert len(r2s_media["real2sim_office_desk_riser_organize"]["stages"]) == 5


def test_showcase_html_renders_r4_legged_tables_and_real2sim_sections(
    tmp_path: Path,
) -> None:
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
        "edition": "r4",
        "ika_acceptance": {
            "benchmark_reference": "IKA OVEN 125 (309 KB, 16 Joints, 100 Colliders)",
            "total_dofs_verified": 24,
            "passed_gates": 40,
            "total_gates": 40,
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
        "r4_tables": [
            {
                "asset_id": "CoffeeBarOakSteelTable",
                "task_id": "specialty_coffee_bar_creatista_prep",
                "summary_zh": "42mm 倒角白橡木实木台面 + 炭黑方钢四腿与黄铜调平脚",
                "dimensions_m": "2.000 × 0.800 × 0.755 m",
                "manifest_sha256": "214296817b2debff",
                "critique_mean": 9.30,
                "studio_views": [{"label": "3/4 View", "data_uri": png_uri}],
            }
        ],
        "room_upgrades": {
            "producer_repo": "scenario-forge",
            "rooms": [
                {
                    "room_id": "kitchen_coffee_bar_v2",
                    "asset_id": "out_of_domain_env_kitchen_coffee_bar_v2",
                    "producer_repo": "scenario-forge",
                    "overall_status": "pass",
                    "manifest_sha256": "99c38fb9f0246644",
                    "texture_count": 15,
                    "cycles_critique": {
                        "verdict": "PASS",
                        "min_score": 8.6,
                        "mean_score": 8.98,
                    },
                    "rtx_critique": {
                        "verdict": "PASS",
                        "min_score": 8.8,
                        "mean_score": 9.10,
                    },
                }
            ],
        },
        "real2sim_twin": {
            "source_photo_uri": png_uri,
            "source_photo_sha256": "9a7d1149de9eb9aa",
            "pose_overlay_uri": png_uri,
            "reprojection_cycles_uri": png_uri,
            "reprojection_rtx_uri": png_uri,
            "contact_sheet_uri": png_uri,
            "camera_summary": "fov=72.0°, eye=(-0.012, -1.109, 1.372)m",
            "entry_count": 19,
            "max_delta_e_ab": 0.21,
            "reprojection_critique": {"verdict": "PASS", "min_score": 8.5, "mean_score": 8.9},
            "patch_critique": {"verdict": "PASS", "min_score": 8.6, "mean_score": 9.1},
            "strips": [
                {
                    "surface_id": "desk_oak_laminate",
                    "mode": "repeated_material",
                    "delta_e_ab": 0.0028,
                    "strip_uri": png_uri,
                }
            ],
        },
        "scenarios": [
            {
                "scenario_id": "real2sim_office_desk_riser_organize",
                "index_badge": "SCENARIO 04 · REAL-TO-SIM OPEN OFFICE WORKSTATION",
                "title_zh": "真实工位 1:1 数字孪生 · 双抽屉增高架收纳与桌面整理",
                "domain": "real2sim_open_office",
                "room_id": "real2sim_open_office_bay_v1",
                "table_id": "Real2SimBunchStandingDesk",
                "room_manifest_sha256": "abc123",
                "hero": {
                    "asset_id": "DesktopDualDrawerRiserRig",
                    "slug": "desktop-dual-drawer-riser-rig",
                    "model_name": "Dual-Drawer Monitor Riser + 15.6\" Acer Gaming Laptop",
                    "envelope_mm": "500 × 250 × 375 mm",
                    "mass_kg": 6.4,
                    "dof_summary": "3-DOF CAD Rig",
                    "cavity_summary": "5-wall hollow drawers",
                    "manifest_sha256": "def456",
                    "studio_views": [{"label": "Isometric", "data_uri": png_uri}],
                    "joints": [
                        {
                            "name": "drawer_right",
                            "type": "Prismatic",
                            "limits": "[0, 165 mm]",
                            "semantics": "closed -> open",
                        }
                    ],
                },
                "initial_views": [
                    {"view_id": "scene_overview", "label": "全域总览", "data_uri": png_uri}
                ],
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
    assert "CoffeeBarOakSteelTable" in html_out
    assert "Real-to-Sim" in html_out
    assert "desk_oak_laminate" in html_out
    assert "real2sim_office_desk_riser_organize" in html_out
