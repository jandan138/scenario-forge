from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_articulation_docs_publish_v2_vr_registration_rules() -> None:
    design = (ROOT / "docs/design/articulated-instance-layout.md").read_text(encoding="utf-8")
    vr = (ROOT / "docs/operations/export-vr-teleop-package.md").read_text(encoding="utf-8")

    assert "identity `Xform`" in design
    assert "Instance/Joints/BaseFixed" in design
    assert "non-kinematic" in design
    assert "legacy" in design
    assert "not an Xform" not in design
    assert "every `RigidBodyAPI` link" in vr
    assert "obj_prim_list" in vr
    assert "randomized independently" in vr
