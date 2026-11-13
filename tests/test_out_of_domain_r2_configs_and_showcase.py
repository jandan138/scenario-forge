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


def test_r2_task_bundles_solve_and_compose_six_five_five_stage_specs() -> None:
    expected = {
        "specialty_coffee_bar_creatista_prep.yaml": (6, "dial_press", "pressed"),
        "electronics_qa_ingun_probe_lock.yaml": (5, "test_start_button", "pressed"),
        "modern_office_brother_calibrate.yaml": (5, "button_start", "pressed"),
    }
    bindings_path = REPO_ROOT / "configs/source_bindings/out_of_domain_hero_r2_20261113.yaml"
    assert bindings_path.is_file()
    bindings_doc = yaml.safe_load(bindings_path.read_text(encoding="utf-8"))
    assert bindings_doc["schema_version"] == "scenario-source-bindings/v0.5"

    for fname, (stage_count, final_joint, final_state) in expected.items():
        bundle_path = REPO_ROOT / "configs/out_of_domain_tasks_r2" / fname
        assert bundle_path.is_file(), f"missing r2 bundle: {bundle_path}"
        bundle = yaml.safe_load(bundle_path.read_text(encoding="utf-8"))
        assert (
            bundle["source_bindings"]
            == "configs/source_bindings/out_of_domain_hero_r2_20261113.yaml"
        )
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


def test_canary_and_media_scripts_expose_r2_multi_stage_profiles() -> None:
    canary = _load_script_module("verify_genmanip_predicate_canary.py")
    media = _load_script_module("render_out_of_domain_canary_media.py")
    assert hasattr(canary, "STAGE_CANARY_PLANS_R2")
    assert hasattr(media, "SCENARIO_MEDIA_SPECS_R2")
    assert len(canary.STAGE_CANARY_PLANS_R2["specialty_coffee_bar_creatista_prep"]) == 6
    assert len(canary.STAGE_CANARY_PLANS_R2["electronics_qa_ingun_probe_lock"]) == 5
    assert len(canary.STAGE_CANARY_PLANS_R2["modern_office_brother_calibrate"]) == 5
    assert len(media.SCENARIO_MEDIA_SPECS_R2["specialty_coffee_bar_creatista_prep"]["stages"]) == 6
    assert len(media.SCENARIO_MEDIA_SPECS_R2["electronics_qa_ingun_probe_lock"]["stages"]) == 5
    assert len(media.SCENARIO_MEDIA_SPECS_R2["modern_office_brother_calibrate"]["stages"]) == 5


def test_showcase_html_renders_ika_9gate_acceptance_and_r1_r2_comparison(
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
        "edition": "r2",
        "ika_acceptance": {
            "benchmark_reference": "IKA OVEN 125 (309 KB, 16 Joints, 100 Colliders)",
            "total_dofs_verified": 20,
            "all_gates_pass": True,
            "heroes": [
                {
                    "slug": "nespresso-creatista-plus-bne800",
                    "asset_id": "NespressoCreatistaPlus",
                    "usd_kb": 265.4,
                    "visual_prims": 148,
                    "collider_prims": 38,
                    "dof_count": 7,
                    "load_600f_drift_mm": 0.12,
                    "rail_transport_pass": True,
                    "gates_passed": "9/9 PASS",
                    "r1_iso_uri": png_uri,
                    "r2_iso_uri": png_uri,
                    "rtx_inspection_uri": png_uri,
                }
            ],
        },
        "scenarios": [
            {
                "scenario_id": "specialty_coffee_bar_creatista_prep",
                "title_zh": "精品咖啡吧 · r2 六步浓缩准备与拨盘按压确认",
                "domain": "specialty_coffee_bar",
                "room_id": "kitchen_coffee_bar_v1",
                "room_manifest_sha256": "abc123",
                "hero": {
                    "asset_id": "NespressoCreatistaPlus",
                    "slug": "nespresso-creatista-plus-bne800",
                    "model_name": "Breville / Nespresso Creatista Plus (BNE800) · r2 CAD",
                    "envelope_mm": "171 × 393 × 308 mm",
                    "mass_kg": 5.2,
                    "dof_summary": "7-DOF CAD (BrewLever + DripTray + Composite DialPress/Rotor + SteamWand + Buttons)",
                    "cavity_summary": "46x48mm CapsuleChute + Perforated DripTray Grate",
                    "manifest_sha256": "def456",
                    "studio_views": [
                        {"label": "Isometric AgX (OIDN)", "data_uri": png_uri},
                        {"label": "Front Studio", "data_uri": png_uri},
                        {"label": "Cavity Detail", "data_uri": png_uri},
                        {"label": "TFT UI & Encoder Macro", "data_uri": png_uri},
                    ],
                    "joints": [
                        {
                            "name": "dial_press",
                            "type": "Prismatic Y (Spring-Return)",
                            "limits": "[-2.5 mm, 0.0 mm]",
                            "semantics": "released [0.0] -> pressed [-2.6, -1.5 mm]",
                        }
                    ],
                },
                "initial_views": [
                    {"view_id": "scene_overview", "label": "全域总览", "data_uri": png_uri},
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
    assert "IKA OVEN 125" in html_out
    assert "9/9 PASS" in html_out
