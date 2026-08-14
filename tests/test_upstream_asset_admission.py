from __future__ import annotations

import json
from pathlib import Path

import pytest

from scenario_forge.assets.admission import (
    UpstreamAdmissionError,
    load_role_topology_audit,
    load_task02_admission,
)


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value))
    return path


def test_role_audit_accepts_locked_29_asset_split(tmp_path: Path) -> None:
    roles = ["liquid_container"] * 12 + ["liquid_conduit"]
    roles += ["rigid_tool"] * 10 + ["receptacle_support"] * 4
    roles += ["instrument_static"] * 2
    path = _write(
        tmp_path / "audit.json",
        {
            "schema_version": "aan.scientific_workbench_role_topology_audit.v1",
            "summary": {
                "asset_count": 29,
                "phase_1_count": 13,
                "phase_2_count": 16,
                "repair_required": ["graduated_cylinder_100ml", "graduated_cylinder_250ml"],
                "blocked": [],
            },
            "assets": [
                {"asset_id": f"asset_{index:02d}", "role": role} for index, role in enumerate(roles)
            ],
        },
    )

    result = load_role_topology_audit(path)

    assert result.asset_count == 29
    assert result.repair_required == (
        "graduated_cylinder_100ml",
        "graduated_cylinder_250ml",
    )


def test_blocked_task02_result_cannot_be_promoted(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "task02.json",
        {
            "schema_version": "aan.task02_r82_admission_report.v1",
            "overall_status": "blocked",
            "blocked_reasons": ["visible_mesh_convex_decomposition_not_gpu_particle_compatible"],
            "promotion": {"allowed": False},
        },
    )

    result = load_task02_admission(path)

    with pytest.raises(UpstreamAdmissionError, match="not promotable"):
        result.require_promotable()


def test_task02_status_and_promotion_must_agree(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "task02.json",
        {
            "schema_version": "aan.task02_r82_admission_report.v1",
            "overall_status": "pass",
            "blocked_reasons": [],
            "promotion": {"allowed": False},
        },
    )

    with pytest.raises(UpstreamAdmissionError, match="disagree"):
        load_task02_admission(path)
