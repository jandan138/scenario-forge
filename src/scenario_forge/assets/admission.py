from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


ROLE_AUDIT_SCHEMA = "aan.scientific_workbench_role_topology_audit.v1"
TASK02_ADMISSION_SCHEMA = "aan.task02_r82_admission_report.v1"
ROLE_NAMES = frozenset(
    {"liquid_container", "liquid_conduit", "rigid_tool", "receptacle_support", "instrument_static"}
)


class UpstreamAdmissionError(ValueError):
    """Raised when an upstream admission result is malformed or not promotable."""


@dataclass(frozen=True)
class RoleAuditSummary:
    asset_count: int
    phase_1_count: int
    phase_2_count: int
    repair_required: tuple[str, ...]
    blocked: tuple[str, ...]


@dataclass(frozen=True)
class Task02Admission:
    overall_status: str
    blocked_reasons: tuple[str, ...]
    promotion_allowed: bool

    def require_promotable(self) -> None:
        if self.overall_status != "pass" or not self.promotion_allowed:
            reasons = ", ".join(self.blocked_reasons) or "upstream admission did not pass"
            raise UpstreamAdmissionError(f"Task 02 component is not promotable: {reasons}")


def _mapping(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise UpstreamAdmissionError("upstream admission document must be a mapping")
    return value


def load_role_topology_audit(path: str | Path) -> RoleAuditSummary:
    value = _mapping(path)
    if value.get("schema_version") != ROLE_AUDIT_SCHEMA:
        raise UpstreamAdmissionError("unsupported role topology audit schema")
    assets = value.get("assets")
    if not isinstance(assets, list) or len(assets) != 29:
        raise UpstreamAdmissionError("role topology audit must contain exactly 29 assets")
    asset_ids: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise UpstreamAdmissionError("role topology audit asset entries must be mappings")
        asset_id = asset.get("asset_id")
        role = asset.get("role")
        if not isinstance(asset_id, str) or not asset_id or asset_id in asset_ids:
            raise UpstreamAdmissionError("role topology audit asset IDs must be unique")
        if role not in ROLE_NAMES:
            raise UpstreamAdmissionError(f"unsupported asset role: {role!r}")
        asset_ids.add(asset_id)
    summary = value.get("summary")
    if not isinstance(summary, dict):
        raise UpstreamAdmissionError("role topology audit summary must be a mapping")
    counts = (
        summary.get("asset_count"),
        summary.get("phase_1_count"),
        summary.get("phase_2_count"),
    )
    if counts != (29, 13, 16):
        raise UpstreamAdmissionError("role topology audit count contract is inconsistent")
    return RoleAuditSummary(
        asset_count=29,
        phase_1_count=13,
        phase_2_count=16,
        repair_required=tuple(summary.get("repair_required", [])),
        blocked=tuple(summary.get("blocked", [])),
    )


def load_task02_admission(path: str | Path) -> Task02Admission:
    value = _mapping(path)
    if value.get("schema_version") != TASK02_ADMISSION_SCHEMA:
        raise UpstreamAdmissionError("unsupported Task 02 admission schema")
    status = value.get("overall_status")
    reasons = value.get("blocked_reasons")
    promotion = value.get("promotion")
    if status not in {"pass", "blocked"}:
        raise UpstreamAdmissionError("Task 02 admission status must be pass or blocked")
    if not isinstance(reasons, list) or not all(isinstance(item, str) for item in reasons):
        raise UpstreamAdmissionError("Task 02 blocked reasons must be a list of strings")
    if not isinstance(promotion, dict) or not isinstance(promotion.get("allowed"), bool):
        raise UpstreamAdmissionError("Task 02 promotion result is required")
    allowed = promotion["allowed"]
    if (status == "pass") != allowed:
        raise UpstreamAdmissionError("Task 02 status and promotion result disagree")
    return Task02Admission(status, tuple(reasons), allowed)
