from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_SCRIPT = REPO_ROOT / "scripts" / "verify_ika_grade_hero_acceptance.py"


def _load_acceptance_module():
    if not ACCEPTANCE_SCRIPT.is_file():
        raise FileNotFoundError(f"Missing acceptance script: {ACCEPTANCE_SCRIPT}")
    spec = importlib.util.spec_from_file_location(
        "verify_ika_grade_hero_acceptance", ACCEPTANCE_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_test_png(path: Path, *, uniform: bool = False, size: tuple[int, int] = (256, 256)) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if uniform:
        arr = np.full((size[1], size[0], 3), 128, dtype=np.uint8)
    else:
        yy, xx = np.mgrid[0:size[1], 0:size[0]]
        arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        arr[..., 0] = ((xx * 3 + yy) % 255).astype(np.uint8)
        arr[..., 1] = ((yy * 5 + 40) % 255).astype(np.uint8)
        arr[..., 2] = (((xx ^ yy) * 7) % 255).astype(np.uint8)
    Image.fromarray(arr, mode="RGB").save(path)
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _make_studio_4view(ev_dir: Path, *, uniform: bool = False) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in ("preview_iso.png", "preview_front.png", "preview_detail.png", "preview_ui.png"):
        p = ev_dir / name
        hashes[name] = _write_test_png(p, uniform=uniform, size=(512, 512))
    return hashes


def _base_appearance_meta(*, pure_box_shell: bool = False, mat_classes: int = 3, ui_mode: str = "vector_3d", tex_paths: list[str] | None = None) -> dict:
    shell_mesh = (
        {"name": "MainShell", "prim_type": "Mesh", "vertices": 8, "faces": 6, "unique_normals": 6}
        if pure_box_shell
        else {"name": "MainShell", "prim_type": "Mesh", "vertices": 168, "faces": 248, "unique_normals": 88}
    )
    materials = [
        {"name": "BrushedSteel", "metallic": 0.9, "roughness": 0.25, "opacity": 1.0, "emissive": [0.0, 0.0, 0.0]},
    ]
    if mat_classes >= 2:
        materials.append(
            {"name": "MattePolymer", "metallic": 0.05, "roughness": 0.55, "opacity": 1.0, "emissive": [0.0, 0.0, 0.0]}
        )
    if mat_classes >= 3:
        materials.append(
            {"name": "OLEDGlow", "metallic": 0.0, "roughness": 0.12, "opacity": 1.0, "emissive": [0.2, 0.85, 0.95]}
        )
    ui_meshes = (
        [
            {"name": "LCDLine1", "prim_type": "Mesh", "vertices": 320, "faces": 200, "unique_normals": 5},
            {"name": "LCDLine2", "prim_type": "Mesh", "vertices": 280, "faces": 175, "unique_normals": 5},
            {"name": "PanelLegend", "prim_type": "Mesh", "vertices": 180, "faces": 110, "unique_normals": 5},
        ]
        if ui_mode == "vector_3d"
        else []
    )
    return {
        "visual_meshes": [
            shell_mesh,
            {"name": "UpperLid", "prim_type": "Mesh", "vertices": 56, "faces": 80, "unique_normals": 32},
            {"name": "SelectDialRotor", "prim_type": "Mesh", "vertices": 144, "faces": 142, "unique_normals": 72},
            *ui_meshes,
        ],
        "materials": materials,
        "texture_files": tex_paths or [],
    }


def test_pairwise_aabb_clearance_catches_overlap_and_measures_min_gap() -> None:
    mod = _load_acceptance_module()
    clean_boxes = {
        "ButtonStart": ((0.080, -0.175, 0.270), (0.092, -0.163, 0.276)),
        "ButtonStop": ((0.100, -0.175, 0.270), (0.112, -0.163, 0.276)),
        "ButtonClear": ((0.120, -0.175, 0.270), (0.132, -0.163, 0.276)),
    }
    res_ok = mod.evaluate_pairwise_control_clearances(clean_boxes, min_gap_m=0.004)
    assert res_ok["passed"] is True
    assert res_ok["pair_count"] == 3
    assert res_ok["overlap_count"] == 0
    assert res_ok["min_gap_m"] == pytest.approx(0.008, abs=1e-6)

    bad_boxes = dict(clean_boxes)
    bad_boxes["ButtonStop"] = ((0.090, -0.175, 0.270), (0.102, -0.163, 0.276))
    res_bad = mod.evaluate_pairwise_control_clearances(bad_boxes, min_gap_m=0.004)
    assert res_bad["passed"] is False
    assert res_bad["overlap_count"] == 1
    assert res_bad["min_gap_m"] < 0.0


def test_envelope_tolerance_check_validates_frozen_manufacturer_bounds() -> None:
    mod = _load_acceptance_module()
    ok = mod.evaluate_frozen_envelope_bounds(
        measured_min=(-0.2052, -0.1994, 0.0000),
        measured_max=(0.2051, 0.1996, 0.3192),
        expected_wdh_m=(0.410, 0.399, 0.319),
        tol_m=0.0025,
    )
    assert ok["passed"] is True
    assert ok["max_abs_error_mm"] <= 0.5

    bad = mod.evaluate_frozen_envelope_bounds(
        measured_min=(-0.220, -0.1995, 0.0),
        measured_max=(0.220, 0.1995, 0.319),
        expected_wdh_m=(0.410, 0.399, 0.319),
        tol_m=0.0025,
    )
    assert bad["passed"] is False
    assert bad["max_abs_error_mm"] >= 29.0


def test_ika_grade_report_enforces_gen007_evidence_separation() -> None:
    mod = _load_acceptance_module()
    gates = [
        {"id": f"G{i}", "category": "runtime", "passed": True, "summary": "ok"}
        for i in range(1, 10)
    ]
    report = mod.build_ika_grade_asset_report(
        slug="brother-mfc-l2820dw-printer",
        asset_id="BrotherMFCL2820DW",
        articulation_root="/AssetRoot/Joints/BaseToWorld",
        isaac_runtime="4.1",
        counts={
            "links": 8,
            "revolute": 2,
            "prismatic": 5,
            "fixed": 1,
            "colliders": 42,
            "visual_prims": 180,
            "meshes": 28,
        },
        gates=gates,
    )
    assert report["implementationStatus"] == "PASS"
    assert report["evidenceSeparation"]["physics_smoke"] == "PASS"
    assert report["evidenceSeparation"]["robot_integration"] == "NOT_TESTED_DELEGATED_TO_ASTRA"


def test_load_hero_acceptance_specs_from_yaml_and_directory(tmp_path: Path) -> None:
    mod = _load_acceptance_module()
    assert mod.load_hero_acceptance_specs(None) == mod.HERO_ACCEPTANCE_SPECS

    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    spec_a = spec_dir / "hero_a.yaml"
    spec_a.write_text(
        """
schema_version: ika-grade-hero-spec/v1.0
slug: hero-alpha
evidence_slug: hero-alpha-r3
asset_id: HeroAlpha
expected_wdh_m: [0.20, 0.30, 0.25]
closed_joint_targets_rad_or_m:
  MainLidJoint: 0.0
control_links: [StartBtn]
spring_buttons:
  StartBtnJoint: -0.002
composite_knob: null
force_smoke:
  joint: MainLidJoint
  link: MainLid
  force_world_xyz: [0.0, 0.0, 10.0]
  force_pos_world_xyz: [0.0, -0.1, 0.25]
  expected_sign: -1
  min_travel: 0.2
load_tests: []
rail_transport_test: null
rtx_camera:
  eye: [0.5, -0.6, 0.4]
  target: [0.0, 0.0, 0.15]
g9a_appearance:
  ui_representation: uv_texture
  min_material_classes: 3
g9b_visual_critic:
  min_dimension_score: 8.0
""",
        encoding="utf-8",
    )
    loaded_single = mod.load_hero_acceptance_specs(spec_a)
    assert len(loaded_single) == 1
    assert loaded_single[0]["slug"] == "hero-alpha"
    assert loaded_single[0]["g9a_appearance"]["ui_representation"] == "uv_texture"

    loaded_dir = mod.load_hero_acceptance_specs(spec_dir)
    assert len(loaded_dir) == 1
    assert loaded_dir[0]["asset_id"] == "HeroAlpha"

    json_spec = tmp_path / "hero_b.json"
    json_spec.write_text(
        json.dumps({"heroes": [dict(loaded_single[0], slug="hero-beta", asset_id="HeroBeta")]}),
        encoding="utf-8",
    )
    loaded_json = mod.load_hero_acceptance_specs(json_spec)
    assert len(loaded_json) == 1
    assert loaded_json[0]["slug"] == "hero-beta"


def test_g1_bfs_joint_order_and_physx_applied_schemas_validation() -> None:
    mod = _load_acceptance_module()
    ok = mod.evaluate_g1_bfs_and_physx_schemas(
        link_count=4,
        physx_rigid_body_count=4,
        physx_articulation_count=1,
        joints_ordered=[
            {"name": "BaseToWorld", "body0": None, "body1": "/AssetRoot/Links/Base"},
            {"name": "DialPressJoint", "body0": "/AssetRoot/Links/Base", "body1": "/AssetRoot/Links/DialPressCarrier"},
            {"name": "ButtonJoint", "body0": "/AssetRoot/Links/Base", "body1": "/AssetRoot/Links/Button"},
            {"name": "SelectDialJoint", "body0": "/AssetRoot/Links/DialPressCarrier", "body1": "/AssetRoot/Links/SelectDialRotor"},
        ],
    )
    assert ok["passed"] is True
    assert ok["bfs_order_valid"] is True

    bad_order = mod.evaluate_g1_bfs_and_physx_schemas(
        link_count=4,
        physx_rigid_body_count=4,
        physx_articulation_count=1,
        joints_ordered=[
            {"name": "BaseToWorld", "body0": None, "body1": "/AssetRoot/Links/Base"},
            {"name": "DialPressJoint", "body0": "/AssetRoot/Links/Base", "body1": "/AssetRoot/Links/DialPressCarrier"},
            {"name": "SelectDialJoint", "body0": "/AssetRoot/Links/DialPressCarrier", "body1": "/AssetRoot/Links/SelectDialRotor"},
            {"name": "ButtonJoint", "body0": "/AssetRoot/Links/Base", "body1": "/AssetRoot/Links/Button"},
        ],
    )
    assert bad_order["passed"] is False
    assert bad_order["bfs_order_valid"] is False

    missing_schema = mod.evaluate_g1_bfs_and_physx_schemas(
        link_count=4,
        physx_rigid_body_count=2,
        physx_articulation_count=0,
        joints_ordered=[
            {"name": "BaseToWorld", "body0": None, "body1": "/AssetRoot/Links/Base"},
        ],
    )
    assert missing_schema["passed"] is False


def test_g9a_rejects_pure_box_primary_meshes_and_low_material_diversity(tmp_path: Path) -> None:
    mod = _load_acceptance_module()
    ev_dir = tmp_path / "evidence"
    _make_studio_4view(ev_dir, uniform=False)
    rtx_info = {"mean_luma": 64.0, "std_luma": 28.0}

    ok = mod.evaluate_g9a_objective_appearance(
        appearance_meta=_base_appearance_meta(pure_box_shell=False, mat_classes=3, ui_mode="vector_3d"),
        studio_dir=ev_dir,
        rtx_info=rtx_info,
        g9a_config={"ui_representation": "vector_3d", "min_cycles_png_bytes": 1000},
    )
    assert ok["passed"] is True
    assert ok["material_class_count"] >= 3

    bad_box = mod.evaluate_g9a_objective_appearance(
        appearance_meta=_base_appearance_meta(pure_box_shell=True, mat_classes=3, ui_mode="vector_3d"),
        studio_dir=ev_dir,
        rtx_info=rtx_info,
        g9a_config={"ui_representation": "vector_3d", "min_cycles_png_bytes": 1000},
    )
    assert bad_box["passed"] is False
    assert "MainShell" in bad_box["box_primary_mesh_violations"]

    bad_mats = mod.evaluate_g9a_objective_appearance(
        appearance_meta=_base_appearance_meta(pure_box_shell=False, mat_classes=2, ui_mode="vector_3d"),
        studio_dir=ev_dir,
        rtx_info=rtx_info,
        g9a_config={"ui_representation": "vector_3d", "min_cycles_png_bytes": 1000},
    )
    assert bad_mats["passed"] is False
    assert bad_mats["material_class_count"] < 3


def test_g9a_enforces_non_uniform_uv_texture_when_declared(tmp_path: Path) -> None:
    mod = _load_acceptance_module()
    ev_dir = tmp_path / "evidence"
    _make_studio_4view(ev_dir, uniform=False)
    rtx_info = {"mean_luma": 64.0, "std_luma": 28.0}

    uniform_tex = tmp_path / "textures" / "blank_ui.png"
    _write_test_png(uniform_tex, uniform=True, size=(128, 128))
    bad_uniform = mod.evaluate_g9a_objective_appearance(
        appearance_meta=_base_appearance_meta(ui_mode="uv_texture", tex_paths=[str(uniform_tex)]),
        studio_dir=ev_dir,
        rtx_info=rtx_info,
        g9a_config={"ui_representation": "uv_texture", "min_cycles_png_bytes": 1000},
    )
    assert bad_uniform["passed"] is False

    bad_missing = mod.evaluate_g9a_objective_appearance(
        appearance_meta=_base_appearance_meta(ui_mode="uv_texture", tex_paths=[]),
        studio_dir=ev_dir,
        rtx_info=rtx_info,
        g9a_config={"ui_representation": "uv_texture", "min_cycles_png_bytes": 1000},
    )
    assert bad_missing["passed"] is False

    rich_tex = tmp_path / "textures" / "rich_ui.png"
    _write_test_png(rich_tex, uniform=False, size=(128, 128))
    good_uv = mod.evaluate_g9a_objective_appearance(
        appearance_meta=_base_appearance_meta(ui_mode="uv_texture", tex_paths=[str(rich_tex)]),
        studio_dir=ev_dir,
        rtx_info=rtx_info,
        g9a_config={"ui_representation": "uv_texture", "min_cycles_png_bytes": 1000},
    )
    assert good_uv["passed"] is True


def test_g9b_visual_critique_enforces_isolation_rubric_rounds_and_hashes(tmp_path: Path) -> None:
    mod = _load_acceptance_module()
    src_usd = tmp_path / "asset.usda"
    src_usd.write_text("#usda 1.0\n", encoding="utf-8")
    src_sha = "sha256:" + sha256(src_usd.read_bytes()).hexdigest()

    ev_dir = tmp_path / "renders"
    png_hashes = _make_studio_4view(ev_dir, uniform=False)

    def _make_report(**overrides) -> dict:
        rep = {
            "schema_version": "ika-grade-visual-critique/v1.0",
            "slug": "hero-alpha",
            "asset_id": "HeroAlpha",
            "round": 1,
            "author_agent": "author-a",
            "critic_agent": "critic-b",
            "verdict": "PASS",
            "min_dimension_threshold": 8.0,
            "dimensions": {
                "silhouette_and_proportion": 8.6,
                "secondary_mechanism_craft": 8.4,
                "pbr_material_hierarchy": 8.5,
                "ui_silkscreen_legibility": 8.2,
                "artifact_free_integrity": 8.8,
            },
            "source_usd": {"path": str(src_usd), "sha256": src_sha},
            "reviewed_renders": [
                {"role": k, "path": str(ev_dir / k), "sha256": v}
                for k, v in png_hashes.items()
            ],
            "evidence_pack": {
                "manufacturer_evidence_paths": ["datasheet.json"],
                "frozen_spec_path": "spec.md",
                "positive_anchor_paths": ["pos.png"],
                "negative_anchor_paths": ["neg.png"],
            },
            "findings": ["All 5 dimensions >= 8.0."],
        }
        rep.update(overrides)
        return rep

    assert mod.evaluate_g9b_visual_critique_report(_make_report(), repo_root=tmp_path)["passed"] is True

    # Self-critique violation
    assert (
        mod.evaluate_g9b_visual_critique_report(
            _make_report(author_agent="same-agent", critic_agent="same-agent"),
            repo_root=tmp_path,
        )["passed"]
        is False
    )

    # One dimension < 8.0 fails even if verdict claims PASS
    low_dims = dict(_make_report()["dimensions"], ui_silkscreen_legibility=7.9)
    assert (
        mod.evaluate_g9b_visual_critique_report(
            _make_report(dimensions=low_dims),
            repo_root=tmp_path,
        )["passed"]
        is False
    )

    # Exceeding max 3 repair rounds fails
    assert (
        mod.evaluate_g9b_visual_critique_report(
            _make_report(round=4),
            repo_root=tmp_path,
        )["passed"]
        is False
    )

    # Hash mismatch fails
    assert (
        mod.evaluate_g9b_visual_critique_report(
            _make_report(source_usd={"path": str(src_usd), "sha256": "sha256:" + "0" * 64}),
            repo_root=tmp_path,
        )["passed"]
        is False
    )


def test_ika_grade_report_10_gates_includes_g9a_and_g9b() -> None:
    mod = _load_acceptance_module()
    gates = [
        {"id": f"G{i}", "category": "runtime", "passed": True} for i in range(1, 9)
    ] + [
        {"id": "G9a_objective_appearance_floor", "category": "visual_objective", "passed": True},
        {"id": "G9b_independent_visual_critic", "category": "visual_critic", "passed": True},
    ]
    report = mod.build_ika_grade_asset_report(
        slug="nespresso-creatista-plus-bne800",
        asset_id="NespressoCreatistaPlus",
        articulation_root="/AssetRoot/Joints/BaseToWorld",
        isaac_runtime="4.1",
        counts={"links": 9, "revolute": 3, "prismatic": 5, "fixed": 1, "colliders": 22, "visual_prims": 156, "meshes": 156},
        gates=gates,
    )
    assert report["schema_version"] == "ika-grade-hero-acceptance/v2.0"
    assert len(report["checks"]) == 10
    assert report["implementationStatus"] == "PASS"
    assert report["evidenceSeparation"]["visual_acceptance"] == "PASS"
    assert report["evidenceSeparation"]["robot_integration"] == "NOT_TESTED_DELEGATED_TO_ASTRA"


def test_inspect_usda_appearance_and_topology_excludes_collision_guides(tmp_path: Path) -> None:
    mod = _load_acceptance_module()
    usda = tmp_path / "asset.usda"
    usda.write_text(
        """#usda 1.0
def Xform "AssetRoot" {
    def Scope "Materials" {
        def Material "BrushedMetal" {
            def Shader "PreviewSurface" {
                uniform token info:id = "UsdPreviewSurface"
                float inputs:metallic = 0.9
                float inputs:roughness = 0.2
            }
        }
        def Material "ScreenMat" {
            def Shader "Tex" {
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @textures/ui.png@
            }
        }
    }
    def Xform "Links" {
        def Xform "Base" (
            prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysxRigidBodyAPI"]
        ) {
            def Xform "Visual" {
                def Mesh "MainShell" {
                    int[] faceVertexCounts = [4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
                    point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0), (0,0,1), (1,0,1), (1,1,1), (0,1,1), (0.5,0.5,1.1), (0.2,0.2,1.1)]
                    normal3f[] normals = [(0,0,1), (0,0,-1), (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0.7,0,0.7), (-0.7,0,0.7)]
                }
            }
            def Xform "Collision" {
                uniform token purpose = "guide"
                def Cube "ColBox" {
                    uniform token purpose = "guide"
                }
            }
        }
        def Xform "Knob" (
            prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysxRigidBodyAPI"]
        ) {
        }
    }
    def Xform "Joints" {
        def PhysicsFixedJoint "BaseToWorld" (
            prepend apiSchemas = ["PhysicsArticulationRootAPI", "PhysxArticulationAPI"]
        ) {
            rel physics:body1 = </AssetRoot/Links/Base>
        }
        def PhysicsRevoluteJoint "KnobJoint" {
            rel physics:body0 = </AssetRoot/Links/Base>
            rel physics:body1 = </AssetRoot/Links/Knob>
        }
    }
}
""",
        encoding="utf-8",
    )
    meta = mod.inspect_usda_appearance_and_topology(usda)
    assert meta["physx_rigid_body_count"] == 2
    assert meta["physx_articulation_count"] == 1
    assert [j["name"] for j in meta["joints_ordered"]] == ["BaseToWorld", "KnobJoint"]
    assert len(meta["appearance_meta"]["visual_meshes"]) == 1
    assert meta["appearance_meta"]["visual_meshes"][0]["name"] == "MainShell"
    assert meta["appearance_meta"]["texture_files"] == ["textures/ui.png"]


def test_resolve_isaac_python_respects_explicit_and_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_acceptance_module()
    fake_env_py = tmp_path / "env_isaac_python"
    fake_env_py.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_arg_py = tmp_path / "arg_isaac_python"
    fake_arg_py.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setenv("ISAAC_PYTHON", str(fake_env_py))
    assert mod.resolve_isaac_python(None) == fake_env_py
    assert mod.resolve_isaac_python(fake_arg_py) == fake_arg_py


def test_static_only_acceptance_runs_with_usd_core_without_isaac_sim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = _load_acceptance_module()
    cad_spec = importlib.util.spec_from_file_location(
        "cad_usd_kit",
        REPO_ROOT / "skills/hunyuan-isaac-articulation-assets/scripts/cad_usd_kit.py",
    )
    assert cad_spec is not None and cad_spec.loader is not None
    cad = importlib.util.module_from_spec(cad_spec)
    cad_spec.loader.exec_module(cad)

    slug = "mini-riser-hero"
    factory_root = tmp_path / "factory"
    evidence_root = tmp_path / "evidence"
    critique_dir = tmp_path / "critiques"
    critique_dir.mkdir(parents=True)

    usd_path = factory_root / "assets" / "source" / slug / "asset.usda"
    stage = cad.new_cad_stage(usd_path, "AssetRoot")
    from pxr import UsdGeom as _UsdGeom

    _UsdGeom.Scope.Define(stage, "/AssetRoot/Materials")
    _UsdGeom.Xform.Define(stage, "/AssetRoot/Links")
    _UsdGeom.Xform.Define(stage, "/AssetRoot/Joints")

    mats = {
        "PolymerBody": cad.make_pbr_material(
            stage, "/AssetRoot/Materials/PolymerBody", (0.92, 0.92, 0.90), metallic=0.04, roughness=0.48
        ),
        "BrushedTrim": cad.make_pbr_material(
            stage, "/AssetRoot/Materials/BrushedTrim", (0.72, 0.74, 0.77), metallic=0.88, roughness=0.24
        ),
        "StatusLED": cad.make_pbr_material(
            stage,
            "/AssetRoot/Materials/StatusLED",
            (0.10, 0.85, 0.55),
            metallic=0.0,
            roughness=0.15,
            emissive=(0.15, 0.90, 0.55),
        ),
        **{
            f"AuxMat{i}": cad.make_pbr_material(
                stage, f"/AssetRoot/Materials/AuxMat{i}", (0.4, 0.4, 0.45), metallic=0.2, roughness=0.5
            )
            for i in range(6)
        },
    }
    cad.make_rigid_link(
        stage, "/AssetRoot/Links/Base", pos=(0.0, 0.0, 0.0), mass_kg=2.4, approx_dims=(0.30, 0.20, 0.12)
    )
    cad.add_chamfered_box_mesh(
        stage,
        "/AssetRoot/Links/Base/Visual/MainShell",
        center=(0.0, 0.0, 0.06),
        dims_xyz=(0.30, 0.20, 0.12),
        mat=mats["PolymerBody"],
        chamfer=0.004,
    )
    for idx, label in enumerate(("POWER", "READY", "CYCLE")):
        cad.add_panel_text_mesh(
            stage,
            f"/AssetRoot/Links/Base/Visual/Legend{idx}",
            text=label,
            mat=mats["StatusLED"],
            char_height=0.008,
            pos=(-0.06 + idx * 0.06, -0.098, 0.09),
        )
    cad.add_collider_box(
        stage, "/AssetRoot/Links/Base/Collision/BaseCol", center=(0.0, 0.0, 0.059), dims_xyz=(0.29, 0.19, 0.118)
    )

    cad.make_rigid_link(
        stage, "/AssetRoot/Links/BtnA", pos=(-0.03, -0.094, 0.06), mass_kg=0.03, approx_dims=(0.016, 0.010, 0.012)
    )
    cad.add_chamfered_box_mesh(
        stage,
        "/AssetRoot/Links/BtnA/Visual/CapA",
        center=(0.0, 0.0, 0.0),
        dims_xyz=(0.016, 0.010, 0.012),
        mat=mats["BrushedTrim"],
        chamfer=0.0015,
    )
    cad.add_collider_box(
        stage, "/AssetRoot/Links/BtnA/Collision/ColA", center=(0.0, 0.0, 0.0), dims_xyz=(0.014, 0.008, 0.010)
    )

    cad.make_rigid_link(
        stage, "/AssetRoot/Links/BtnB", pos=(0.03, -0.094, 0.06), mass_kg=0.03, approx_dims=(0.016, 0.010, 0.012)
    )
    cad.add_chamfered_box_mesh(
        stage,
        "/AssetRoot/Links/BtnB/Visual/CapB",
        center=(0.0, 0.0, 0.0),
        dims_xyz=(0.016, 0.010, 0.012),
        mat=mats["BrushedTrim"],
        chamfer=0.0015,
    )
    cad.add_collider_box(
        stage, "/AssetRoot/Links/BtnB/Collision/ColB", center=(0.0, 0.0, 0.0), dims_xyz=(0.014, 0.008, 0.010)
    )

    # Pad deterministic chamfered vent louvers inside envelope so CAD richness floor (>=60 visual prims, >=150KB USDA) is met
    for i in range(60):
        cad.add_chamfered_box_mesh(
            stage,
            f"/AssetRoot/Links/Base/Visual/VentFin{i}",
            center=(-0.11 + (i % 12) * 0.018, -0.04 + (i // 12) * 0.018, 0.114),
            dims_xyz=(0.010, 0.004, 0.004),
            mat=mats["BrushedTrim"],
            chamfer=0.0005,
        )

    cad.add_base_to_world_joint(stage, "/AssetRoot/Joints/BaseToWorld", "/AssetRoot/Links/Base")
    cad.add_prismatic_joint(
        stage,
        "/AssetRoot/Joints/BtnAJoint",
        "/AssetRoot/Links/Base",
        "/AssetRoot/Links/BtnA",
        pivot_in_parent=(-0.03, -0.094, 0.06),
        axis="Y",
        lower_m=0.0,
        upper_m=0.003,
        reset_m=0.0,
        damping=2.0,
    )
    cad.add_prismatic_joint(
        stage,
        "/AssetRoot/Joints/BtnBJoint",
        "/AssetRoot/Links/Base",
        "/AssetRoot/Links/BtnB",
        pivot_in_parent=(0.03, -0.094, 0.06),
        axis="Y",
        lower_m=0.0,
        upper_m=0.003,
        reset_m=0.0,
        damping=2.0,
    )
    stage.GetRootLayer().Save()

    ev_dir = evidence_root / slug
    png_hashes = _make_studio_4view(ev_dir, uniform=False)
    usd_sha = "sha256:" + sha256(usd_path.read_bytes()).hexdigest()

    critique_report = {
        "schema_version": "ika-grade-visual-critique/v1.0",
        "slug": slug,
        "asset_id": "MiniRiserHero",
        "round": 1,
        "author_agent": "cad-author",
        "critic_agent": "independent-critic",
        "verdict": "PASS",
        "min_dimension_threshold": 8.0,
        "dimensions": {
            "silhouette_and_proportion": 8.8,
            "secondary_mechanism_craft": 8.6,
            "pbr_material_hierarchy": 8.7,
            "ui_silkscreen_legibility": 8.5,
            "artifact_free_integrity": 9.0,
        },
        "source_usd": {"path": str(usd_path), "sha256": usd_sha},
        "reviewed_renders": [
            {"role": k, "path": str(ev_dir / k), "sha256": v}
            for k, v in png_hashes.items()
        ],
        "evidence_pack": {
            "manufacturer_evidence_paths": ["datasheet.json"],
            "frozen_spec_path": "spec.md",
            "positive_anchor_paths": ["pos.png"],
            "negative_anchor_paths": ["neg.png"],
        },
        "findings": ["Clean CAD chamfering and legible silkscreen."],
    }
    (critique_dir / f"{slug}_visual_critique_report.json").write_text(
        json.dumps(critique_report, indent=2), encoding="utf-8"
    )

    spec_yaml = tmp_path / "mini_riser_spec.yaml"
    spec_yaml.write_text(
        f"""
schema_version: ika-grade-hero-spec/v1.0
slug: {slug}
evidence_slug: {slug}
asset_id: MiniRiserHero
expected_wdh_m: [0.300, 0.200, 0.120]
envelope_tol_m: 0.005
min_control_gap_m: 0.010
closed_joint_targets_rad_or_m:
  BtnAJoint: 0.0
  BtnBJoint: 0.0
control_links: [BtnA, BtnB]
spring_buttons: {{}}
composite_knob: null
force_smoke:
  joint: BtnAJoint
  link: BtnA
  force_world_xyz: [0.0, 5.0, 0.0]
  force_pos_world_xyz: [-0.03, -0.094, 0.06]
  expected_sign: 1
  min_travel: 0.001
load_tests: []
rail_transport_test: null
rtx_camera:
  eye: [0.4, -0.5, 0.3]
  target: [0.0, 0.0, 0.06]
g9a_appearance:
  ui_representation: vector_3d
  min_cycles_png_bytes: 1000
g9b_visual_critic:
  min_dimension_score: 8.0
""",
        encoding="utf-8",
    )

    # Point ISAAC_PYTHON to a non-existent path to prove static_only never invokes Isaac Sim
    monkeypatch.setenv("ISAAC_PYTHON", str(tmp_path / "missing_isaac_python"))
    summary = mod.run_9_gate_acceptance(
        factory_root=factory_root,
        evidence_root=evidence_root,
        spec_config=spec_yaml,
        critique_dir=critique_dir,
        static_only=True,
    )
    assert summary["overall_status"] == "PASS_STATIC_ONLY"
    assert summary["passed_gates"] == 5
    assert summary["total_gates"] == 5
    hero_rep = summary["heroes"][0]
    assert hero_rep["implementationStatus"] == "PASS_STATIC_ONLY"
    assert hero_rep["evidenceSeparation"]["static_contract"] == "PASS"
    assert hero_rep["evidenceSeparation"]["reopen_and_bounds"] == "PASS"
    assert hero_rep["evidenceSeparation"]["visual_acceptance"] == "PASS"
    assert hero_rep["evidenceSeparation"]["physics_smoke"] == "NOT_RUN_STATIC_ONLY"
