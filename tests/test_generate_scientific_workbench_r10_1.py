from __future__ import annotations

import ast
import json
from pathlib import Path

import yaml

import scripts.generate_scientific_workbench_r10_1 as r10_1
import scripts.generate_scientific_workbench_r9 as r9
from scenario_forge.artifacts.usd_handoff import USDHandoffArchive


def test_task07_uses_the_acrylic_rack_as_start_and_return_fixture() -> None:
    source = next(plan.scenario for plan in r9.load_r9_plans() if plan.task_number == 7)

    scenario = r10_1.upgrade_task07(source)

    objects = {item["id"]: item for item in scenario["objects"]}
    rack = objects["obj_acrylic_rod_rack"]
    rod = objects["obj_glass_rod"]
    assert rack["pose"]["xyz"] == [0.16, -0.17, 0.755]
    assert rack["named_frames"] == {
        "middle_socket_04_aperture": {
            "xyz": [0.0, 0.0, 0.0],
            "wxyz": [1.0, 0.0, 0.0, 0.0],
        },
        "middle_socket_04_inserted_bottom": {
            "xyz": [0.0, 0.0, 0.0],
            "wxyz": [1.0, 0.0, 0.0, 0.0],
        },
    }
    assert rod["metadata"]["vr_randomization_group"] == "task07_acrylic_rack_assembly"
    assert rack["metadata"]["vr_randomization_group"] == "task07_acrylic_rack_assembly"
    steps = {item["id"]: item for item in scenario["steps"]}
    assert steps["return_rod"]["parameters"]["target_frame"] == (
        "obj_acrylic_rod_rack.middle_socket_04_inserted_bottom"
    )
    assert steps["release_rod"]["depends_on"] == ["return_rod"]
    returned = next(
        item
        for item in scenario["success"]["progress_rubric"]["items"]
        if item["id"] == "rod_returned"
    )
    assert returned["condition"] == {
        "type": "object_at_initial_pose",
        "parameters": {
            "object": "obj_glass_rod",
            "xyz_tolerance": [0.004, 0.004, 0.005],
            "released": True,
        },
    }


def test_materialized_task07_rod_pose_comes_from_the_rack_frame() -> None:
    scenario = r10_1.upgrade_task07(
        next(plan.scenario for plan in r9.load_r9_plans() if plan.task_number == 7)
    )
    rack = next(item for item in scenario["objects"] if item["id"] == "obj_acrylic_rod_rack")
    rack["named_frames"]["middle_socket_04_inserted_bottom"]["xyz"] = [0.0, 0.0, 0.01743]

    result = r10_1.materialize_task07_rod_pose(scenario)

    rod = next(item for item in result["objects"] if item["id"] == "obj_glass_rod")
    assert rod["pose"]["xyz"] == [0.16, -0.17, 0.77243]
    assert rod["pose"]["wxyz"] == [1.0, 0.0, 0.0, 0.0]


def test_task02_direct_vr_contract_has_seven_objects_and_no_scene_wrapper() -> None:
    text = r10_1.task02_direct_vr_scene()
    config = r10_1.task02_vr_config(
        scenario_id="task02_fill40",
        particle_count=580,
    )

    assert 'def Xform "_scene"' not in text
    assert 'defaultPrim = "World"' in text
    assert 'def DomeLight "vr_direct_open_light"' in text
    assert 'def Xform "obj_graduated_cylinder"' in text
    assert 'def Xform "obj_obj_' not in text
    tree = ast.parse(config)
    assert tree is not None
    namespace = {"_ASSETS_DIR": Path("/tmp/assets")}
    exec(config, namespace)
    task = namespace["TASKS"]["task02_fill40"]
    assert len(task["obj_prim_list"]) == 7
    assert all(path.startswith("/World/_scene/obj_") for path in task["obj_prim_list"])
    assert "/World/_scene/fluid_runtime" not in task["obj_prim_list"]
    assert task["layout_randomization"]["objects"][0]["objs"] == [
        "obj_graduated_cylinder",
        "fluid_runtime",
    ]


def test_finalize_runtime_release_requires_and_records_all_ten_gates(
    tmp_path: Path, monkeypatch
) -> None:
    output = tmp_path / "release"
    for task_number, variant, relative in r10_1.runtime_release_specs(output):
        package = output / relative
        if task_number == 2:
            ebench = package / "ebench"
            vr = package / "vr"
            (package / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
            (package / "manifest.json").write_text(
                json.dumps({"vr_contract": {"status": "static_pass_runtime_pending"}}),
                encoding="utf-8",
            )
            product = ebench / "evidence/product_smoke/report.json"
            product.parent.mkdir(parents=True, exist_ok=True)
            product.write_text('{"status":"pass"}\n', encoding="utf-8")
        else:
            ebench = package / "adapters/ebench/genmanip"
            vr = package / "adapters/vr_teleop"
        gate = ebench / "evidence/initial_scene/visual_ready_gate.yaml"
        gate.parent.mkdir(parents=True, exist_ok=True)
        gate.write_text("status: passed\n", encoding="utf-8")
        overview = gate.parent / "scene_overview.png"
        overview.write_bytes(b"png")
        smoke = vr / "evidence/open_smoke/report.json"
        smoke.parent.mkdir(parents=True, exist_ok=True)
        smoke.write_text('{"status":"pass"}\n', encoding="utf-8")

    def fake_bundle(**kwargs):
        root = kwargs["output_dir"] / kwargs["archive_id"]
        root.mkdir(parents=True)
        zip_path = kwargs["output_dir"] / f"{kwargs['archive_id']}.zip"
        zip_path.write_bytes(b"zip")
        assert len(kwargs["variants"]) == 10
        return USDHandoffArchive(root=root, zip_path=zip_path, task_numbers=tuple())

    monkeypatch.setattr(r10_1, "build_multi_task_dual_consumer_bundle", fake_bundle)

    destination = r10_1.finalize_runtime_release(output_dir=output)

    manifest = yaml.safe_load(destination.read_text())
    assert manifest["status"] == "runtime_complete_with_bounded_claims"
    assert manifest["package_count"] == 10
    assert manifest["task_counts"] == {"task02": 4, "task07": 5, "task08": 1}
    assert all(item["vr_open_smoke"] == "pass" for item in manifest["packages"])
    task02_manifest = json.loads(
        (output / "packages/task02/fill40/manifest.json").read_text()
    )
    assert task02_manifest["vr_contract"]["status"] == "runtime_pass"
