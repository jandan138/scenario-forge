from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_canonical_articulation_docs_publish_v2_vr_registration_rules() -> None:
    design = (ROOT / "docs/design/articulated-instance-layout.md").read_text(encoding="utf-8")
    vr = (ROOT / "docs/operations/export-vr-teleop-package.md").read_text(encoding="utf-8")

    standard = (ROOT / "docs/standards/articulation.md").read_text(encoding="utf-8")
    assert "../standards/articulation.md" in design
    assert "../standards/articulation.md" in vr
    assert "固定基座" in standard
    assert "identity `Xform`" in standard
    assert "Instance/Joints/BaseFixed" in standard
    assert "non-kinematic" in standard
    assert "legacy" in standard
    assert "not an Xform" not in standard
    assert "every `RigidBodyAPI` link" in standard
    assert "obj_prim_list" in standard
    assert "randomized independently" in standard
