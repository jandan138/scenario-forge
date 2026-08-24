#!/usr/bin/env python3
"""Generate the Task 11 negative control with the raw articulated centrifuge."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TASK_ID = "scientific_workbench_centrifuge_unload_shutdown__raw_articulated_dropin"
DEFAULT_BASE = ROOT / "outputs/scientific_workbench_task11_vr_r5_20260824/vr"
DEFAULT_ARCHIVE = ROOT / "external_artifacts/incoming/离心机.zip"
DEFAULT_OUT = ROOT / "outputs/scientific_workbench_task11_raw_articulated_dropin_20260824"
RAW_ENTRY_MEMBER = "assets/usd/centrifuge_articulated.usda"
RAW_MAIN_MEMBER = "assets/usd/centrifuge.usd"
RAW_ENTRY_PRIM = "/LabSpinX8"
RAW_ROOT_XYZ = (0.22, 0.09, 0.8197413723)
OBJECTS = (
    "obj_centrifuge",
    "obj_mixed_rack",
    "obj_primary_tube",
    "obj_balance_tube",
    "obj_bg_15ml_00",
    "obj_bg_15ml_01",
    "obj_bg_15ml_02",
    "obj_bg_15ml_03",
    "obj_bg_15ml_04",
    "obj_bg_15ml_05",
    "obj_bg_50ml_00",
    "obj_bg_50ml_01",
)


def _sha_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _local_group(names: list[str]) -> dict[str, object]:
    return {
        "objs": names,
        "mode": "local",
        "yaw_range_degrees": [0.0, 0.0],
        "x_offset_range": [-0.01, 0.01],
        "y_offset_range": [-0.01, 0.01],
    }


def build(base: Path, archive: Path, output: Path) -> Path:
    from pxr import Gf, Usd, UsdGeom

    base = base.resolve()
    archive = archive.resolve()
    if output.exists():
        shutil.rmtree(output)
    vr = output / "vr"
    shutil.copytree(base, vr)
    for stale in (
        vr / "deps/centrifuge",
        vr / "evidence/full_scene_run",
    ):
        if stale.exists():
            shutil.rmtree(stale)
    materialization = vr / "object_materialization.json"
    if materialization.exists():
        materialization.unlink()

    raw_root = vr / "deps/raw_centrifuge"
    member_hashes = {}
    with zipfile.ZipFile(archive) as source:
        for member in source.namelist():
            if not member.startswith("assets/usd/") or member.endswith("/"):
                continue
            data = source.read(member)
            destination = raw_root / member
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            member_hashes[member] = _sha_bytes(data)
    if RAW_ENTRY_MEMBER not in member_hashes or RAW_MAIN_MEMBER not in member_hashes:
        raise RuntimeError("raw archive is missing its articulated or main USD entry")

    scene_path = vr / "scene.usd"
    stage = Usd.Stage.Open(str(scene_path))
    if not stage.RemovePrim("/World/obj_centrifuge"):
        raise RuntimeError("cannot remove the r5 centrifuge subtree")
    raw = UsdGeom.Xform.Define(stage, "/World/obj_centrifuge")
    raw.GetPrim().GetReferences().AddReference(
        "deps/raw_centrifuge/" + RAW_ENTRY_MEMBER,
        RAW_ENTRY_PRIM,
    )
    raw.AddTranslateOp().Set(Gf.Vec3d(*RAW_ROOT_XYZ))
    stage.GetRootLayer().Save()

    task = {
        "scene_usd_file_path": {"scene1": "__SCENE_PATH__"},
        "obj_prim_list": [f"/World/_scene/{name}" for name in OBJECTS],
        "layout_randomization": {
            "table": "table",
            "objects": [
                _local_group(
                    [
                        "obj_centrifuge",
                        "obj_primary_tube",
                        "obj_balance_tube",
                        "fluid_runtime",
                    ]
                ),
                _local_group(
                    [
                        name
                        for name in OBJECTS
                        if name == "obj_mixed_rack" or name.startswith("obj_bg_")
                    ]
                ),
            ],
        },
        "robot_cfg": {
            "position": [0.0, -1.02, 0.31],
            "orientation": [0.7071067812, 0.0, 0.0, 0.7071067812],
        },
        "physx_scene_cfg": {
            "EnableGPUDynamics": True,
            "GpuMaxParticleContacts": 1048576,
            "TimeStepsPerSecond": 120,
        },
        "validation_scope": "negative_control_raw_articulated_dropin",
    }
    body = repr(task).replace(
        "'__SCENE_PATH__'", "str(_ASSETS_DIR / 'scene.usd')"
    )
    (vr / "task_config.py").write_text(
        "from pathlib import Path\n"
        "_ASSETS_DIR = Path(__file__).resolve().parent\n"
        f"TASKS = {{{TASK_ID!r}: {body}}}\n",
        encoding="utf-8",
    )
    source_manifest = {
        "schema_version": "scenario-forge.raw-source-provenance.v1",
        "archive": {
            "source_path": str(archive),
            "sha256": _sha(archive),
        },
        "members": member_hashes,
        "raw_entry": RAW_ENTRY_MEMBER,
        "raw_entry_prim": RAW_ENTRY_PRIM,
        "raw_source_unchanged": True,
        "convertasset_centrifuge_consumed": False,
    }
    provenance = output / "provenance"
    provenance.mkdir(parents=True)
    (provenance / "raw_centrifuge_source.json").write_text(
        json.dumps(source_manifest, indent=2, sort_keys=True) + "\n"
    )
    manifest = {
        "schema_version": "scenario-forge.task11-raw-dropin.v1",
        "package_id": "scientific_workbench_task11_raw_articulated_dropin",
        "scenario_id": TASK_ID,
        "status": "negative_control_runtime_diagnostic_pending",
        "negative_control": True,
        "entrypoints": {
            "scene_usd": "vr/scene.usd",
            "task_config": "vr/task_config.py",
        },
        "raw_centrifuge": {
            "reference": "vr/deps/raw_centrifuge/" + RAW_ENTRY_MEMBER,
            "entry_prim": RAW_ENTRY_PRIM,
            "root_xyz_m": list(RAW_ROOT_XYZ),
            "expected_joint_prims": 5,
        },
        "claims": {
            "raw_source_unchanged": True,
            "convertasset_centrifuge_consumed": False,
            "raw_joint_prims_preserved": True,
            "runtime_articulation_valid": False,
            "robot_policy_success": False,
            "task11_success": False,
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(build(args.base, args.archive, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
