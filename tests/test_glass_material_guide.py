from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_ROOT = REPO_ROOT / "docs/glass-material-guide"


def test_glass_material_guide_covers_four_real_ab_comparisons() -> None:
    html = (PAGE_ROOT / "index.html").read_text(encoding="utf-8")
    assert "让实验玻璃真正像玻璃" in html
    assert html.count('class="comparison"') == 4
    assert html.count('class="split-control"') == 4
    for asset in (
        "250 mL 量筒",
        "325 mL 烧杯",
        "250 mL 平底烧瓶",
        "动态烧杯",
    ):
        assert asset in html
    for value in (
        "0.86629593",
        "0.97533488",
        "0.98841697",
        "frosting_roughness",
        "roughness_texture_influence",
        "enable_opacity",
        "cutout_opacity",
    ):
        assert value in html
    assert "显式写入" in html
    assert "模块默认值" in html
    assert "玻璃棒" in html and "本轮不改" in html
    assert "磨口" in html and "保留磨砂" in html
    assert "没有升级任务包" in html
    assert "ConvertAsset" in html and "Scenario Forge" in html
    assert "benchmark" in html
    assert "/cpfs/" not in html


def test_glass_material_guide_is_local_responsive_and_accessible() -> None:
    html = (PAGE_ROOT / "index.html").read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert 'href="styles.css"' in html
    assert 'src="guide.js"' in html
    assert "prefers-reduced-motion" in (PAGE_ROOT / "styles.css").read_text(encoding="utf-8")
    assert "aria-label" in html
    assert html.count('alt="') >= 8
    references = re.findall(r'(?:src|href)="([^"]+)"', html)
    for reference in references:
        if reference.startswith("#"):
            continue
        assert not reference.startswith(("http://", "https://", "file:"))
        assert (PAGE_ROOT / reference).resolve().exists(), reference


def test_glass_material_media_matches_provenance() -> None:
    provenance = json.loads((PAGE_ROOT / "assets/provenance.json").read_text(encoding="utf-8"))
    assert provenance["schema_version"] == "scenario-forge-glass-material-guide/v0.1"
    assert provenance["runtime"] == "Isaac Sim 4.1"
    assert len(provenance["comparisons"]) == 4
    for comparison in provenance["comparisons"]:
        for side in ("before", "after"):
            item = comparison[side]
            path = PAGE_ROOT / item["path"]
            assert path.is_file()
            assert sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_docs_navigation_links_to_glass_material_guide() -> None:
    docs_index = (REPO_ROOT / "docs/index.md").read_text(encoding="utf-8")
    directory = (REPO_ROOT / "docs/task-directory/index.html").read_text(encoding="utf-8")
    assert "[玻璃器皿材质升级教程](glass-material-guide/)" in docs_index
    assert 'href="../glass-material-guide/"' in directory
