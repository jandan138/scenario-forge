from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_ROOT = REPO_ROOT / "docs/liquid-cylinder-tutorial"


def test_tutorial_is_a_self_contained_evidence_bound_page() -> None:
    page = PAGE_ROOT / "index.html"
    html = page.read_text(encoding="utf-8")

    assert "让量筒真正装得住液体" in html
    assert "不是把碰撞参数一味调大" in html
    assert "580" in html
    assert "3 / 3" in html
    assert "560–570" in html
    assert "scripted oracle" in html
    assert "benchmark" in html

    for section_id in (
        "diagnosis",
        "collision-shell",
        "liquid-start",
        "package",
        "robot-proof",
        "reproduce",
    ):
        assert f'id="{section_id}"' in html

    assert html.count('class="layer-toggle"') == 3
    assert '<video controls playsinline preload="metadata"' in html
    assert "prefers-reduced-motion" in html
    assert "/cpfs/" not in html
    assert "file:" not in html
    assert "http://" not in html
    assert "https://" not in html

    local_refs = re.findall(r'(?:src|href|poster)="([^"]+)"', html)
    for reference in local_refs:
        if reference.startswith(("#", "data:")):
            continue
        assert (PAGE_ROOT / reference).resolve().is_file(), reference


def test_tutorial_media_matches_its_public_provenance() -> None:
    manifest = json.loads((PAGE_ROOT / "assets/provenance.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "scenario-forge-tutorial-media/v0.1"
    assert manifest["claim_boundary"] == {
        "benchmark_success": False,
        "liquid_metric_active": False,
        "policy_success": False,
        "scripted_robot_oracle": True,
    }
    assert manifest["scenario_id"] == "scientific_workbench_task02_r87"

    roles = {item["role"] for item in manifest["media"]}
    assert roles == {
        "initial_scene_overview",
        "task_object_closeup",
        "robot_oracle_keyframes",
        "robot_oracle_video",
    }
    for item in manifest["media"]:
        assert set(item) == {"path", "role", "sha256", "source_evidence_id"}
        artifact = PAGE_ROOT / item["path"]
        assert artifact.is_file()
        assert sha256(artifact.read_bytes()).hexdigest() == item["sha256"]


def test_docs_home_and_task_directory_link_to_the_tutorial() -> None:
    docs_index = (REPO_ROOT / "docs/index.md").read_text(encoding="utf-8")
    task_directory = (REPO_ROOT / "docs/task-directory/index.html").read_text(
        encoding="utf-8"
    )
    assert "[量筒 GPU-PBD 液体修复教程](liquid-cylinder-tutorial/)" in docs_index
    assert 'href="../liquid-cylinder-tutorial/"' in task_directory
    assert "量筒液体修复教程" in task_directory
