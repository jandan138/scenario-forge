from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from scenario_forge.adapters.room_support_relations import (
    RELATION_KINDS,
    SCHEMA_VERSION,
    Box3,
    CorrectionResult,
    OrientedSupport,
    apply_resting_correction,
    validate_support_sidecar,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_box3_translated_shifts_bounds() -> None:
    box = Box3(minimum=(-0.1, -0.2, 0.75), maximum=(0.1, 0.2, 0.95))
    shifted = box.translated((0.5, -0.25, 0.01))
    assert shifted.minimum == pytest.approx((0.4, -0.45, 0.76))
    assert shifted.maximum == pytest.approx((0.6, -0.05, 0.96))


def test_apply_resting_correction_in_bounds_unchanged() -> None:
    support = OrientedSupport(
        center_xy=(0.0, 2.5),
        size_xy=(1.2, 0.8),
        yaw_rad=0.0,
        top_z=0.90,
    )
    item = Box3(minimum=(-0.1, 2.4, 0.90), maximum=(0.1, 2.6, 1.15))

    result = apply_resting_correction(
        item,
        support,
        margin_m=0.02,
        vertical_tolerance_m=0.12,
    )

    assert isinstance(result, CorrectionResult)
    assert result.status == "unchanged"
    assert result.fully_supported is True
    assert result.removal_reason is None
    assert result.translation == pytest.approx((0.0, 0.0, 0.0))
    assert result.after == item


def test_apply_resting_correction_overhang_corrected_and_snapped_vertically() -> None:
    support = OrientedSupport(
        center_xy=(0.0, 0.0),
        size_xy=(1.0, 0.6),
        yaw_rad=0.0,
        top_z=0.75,
    )
    # Overhangs +X edge (half-width 0.5, usable high = 0.48) and hovers 3cm above top_z
    item = Box3(minimum=(0.38, -0.10, 0.78), maximum=(0.58, 0.10, 0.98))

    result = apply_resting_correction(
        item,
        support,
        margin_m=0.02,
        vertical_tolerance_m=0.12,
    )

    assert result.status == "corrected"
    assert result.fully_supported is True
    assert result.removal_reason is None
    assert result.translation == pytest.approx((-0.10, 0.0, -0.03))
    assert result.after.maximum[0] == pytest.approx(0.48)
    assert result.after.minimum[2] == pytest.approx(0.75)


def test_apply_resting_correction_oversized_footprint_removed() -> None:
    support = OrientedSupport(
        center_xy=(0.0, 0.0),
        size_xy=(0.40, 0.40),
        yaw_rad=0.0,
        top_z=0.80,
    )
    item = Box3(minimum=(-0.20, -0.10, 0.80), maximum=(0.20, 0.10, 1.00))

    result = apply_resting_correction(
        item,
        support,
        margin_m=0.02,
        vertical_tolerance_m=0.12,
    )

    assert result.status == "removed"
    assert result.fully_supported is False
    assert result.removal_reason == "item_footprint_exceeds_support_margin"
    assert result.translation == (0.0, 0.0, 0.0)


def test_apply_resting_correction_outside_vertical_tolerance_removed() -> None:
    support = OrientedSupport(
        center_xy=(0.0, 0.0),
        size_xy=(1.0, 1.0),
        yaw_rad=0.0,
        top_z=0.75,
    )
    item = Box3(minimum=(-0.1, -0.1, 0.95), maximum=(0.1, 0.1, 1.15))

    result = apply_resting_correction(
        item,
        support,
        margin_m=0.02,
        vertical_tolerance_m=0.12,
    )

    assert result.status == "removed"
    assert result.fully_supported is False
    assert result.removal_reason == "item_outside_vertical_support_tolerance"


def test_apply_resting_correction_with_yaw_rotation() -> None:
    # Support rotated 90 deg (pi/2): local X maps along +world Y, local Y maps along -world X
    support = OrientedSupport(
        center_xy=(1.0, 2.0),
        size_xy=(1.2, 0.5),
        yaw_rad=math.pi / 2.0,
        top_z=0.85,
    )
    # Item extends beyond world X = 1.25 (support half-depth is 0.25 along world X; usable [0.77, 1.23])
    item = Box3(minimum=(1.15, 1.90, 0.86), maximum=(1.35, 2.10, 1.02))

    result = apply_resting_correction(
        item,
        support,
        margin_m=0.02,
        vertical_tolerance_m=0.05,
    )

    assert result.status == "corrected"
    assert result.fully_supported is True
    assert result.after.maximum[0] == pytest.approx(1.23, abs=1e-6)
    assert result.after.minimum[0] >= 0.77 - 1e-6
    assert result.after.minimum[2] == pytest.approx(0.85, abs=1e-6)


def test_apply_resting_correction_rejects_negative_tolerances() -> None:
    support = OrientedSupport((0.0, 0.0), (1.0, 1.0), 0.0, 0.75)
    item = Box3((-0.1, -0.1, 0.75), (0.1, 0.1, 0.95))
    with pytest.raises(ValueError, match="non-negative"):
        apply_resting_correction(item, support, margin_m=-0.01, vertical_tolerance_m=0.05)


def _write_valid_sidecar(tmp_path: Path) -> tuple[Path, Path]:
    usd_bytes = b"PXR-USDC-TEST"
    source_usd = tmp_path / "room_source.usdc"
    source_usd.write_bytes(usd_bytes)
    sidecar = tmp_path / "support_relations.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source_usd": {"path": "room_source.usdc", "sha256": _sha256_bytes(usd_bytes)},
        "review": {"status": "pass", "reviewer": "unit-test-reviewer"},
        "relations": [
            {
                "relation_kind": "rests_on",
                "audit_status": "pass",
                "object_prim": "/Room/Cup",
                "support_prim": "/Room/Counter",
            },
            {
                "relation_kind": "stacked_on",
                "audit_status": "removed",
                "object_prim": None,
                "support_prim": "/Room/Counter",
            },
        ],
    }
    sidecar.write_text(json.dumps(payload), encoding="utf-8")
    return sidecar, source_usd


def test_validate_support_sidecar_valid_pass(tmp_path: Path) -> None:
    assert RELATION_KINDS == frozenset({"rests_on", "mounted_to", "stacked_on"})
    sidecar, source_usd = _write_valid_sidecar(tmp_path)
    validated = validate_support_sidecar(sidecar, source_usd)
    assert validated["schema_version"] == "room-support-relations-v1"
    assert len(validated["relations"]) == 2


def test_validate_support_sidecar_sha_mismatch(tmp_path: Path) -> None:
    sidecar, source_usd = _write_valid_sidecar(tmp_path)
    source_usd.write_bytes(b"MODIFIED-USD")
    with pytest.raises(ValueError, match="hash"):
        validate_support_sidecar(sidecar, source_usd)


def test_validate_support_sidecar_bad_relation_kind(tmp_path: Path) -> None:
    sidecar, source_usd = _write_valid_sidecar(tmp_path)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload["relations"][0]["relation_kind"] = "floating_near"
    sidecar.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="relation kind"):
        validate_support_sidecar(sidecar, source_usd)


def test_validate_support_sidecar_unresolved_status(tmp_path: Path) -> None:
    sidecar, source_usd = _write_valid_sidecar(tmp_path)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    payload["relations"][0]["audit_status"] = "pending"
    sidecar.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not resolved"):
        validate_support_sidecar(sidecar, source_usd)
