from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
PAGE_ROOT = REPO_ROOT / "docs/glass-material-guide"
ASSET_IDS = (
    "graduated_cylinder_250ml",
    "beaker_325ml",
    "flat_bottom_flask_250ml_29_42",
    "beaker_dynamic",
)


def test_glass_material_guide_covers_the_formal_six_asset_admission() -> None:
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
    for asset_id in ASSET_IDS:
        assert f"assets/{asset_id}_before.webp" in html
        assert f"assets/{asset_id}_after.webp" in html
        assert f"assets/{asset_id}_pathtracing.webp" in html
    assert "assets/reagent_bottle_90x55.webp" in html
    assert "assets/reagent_bottle_90x55_pathtracing.webp" in html
    assert "assets/erlenmeyer_flask_250ml_90x35_reference.webp" in html
    assert "assets/erlenmeyer_flask_250ml_90x35_candidate.webp" in html
    assert "assets/graduated_cylinder_250ml_connector_v1.webp" in html
    assert "assets/graduated_cylinder_250ml_connector_v2.webp" in html
    assert "圆形连接座" in html
    assert html.count('class="chain"') == 7
    assert "旧材质" in html
    assert "PathTracing" in html
    for value in (
        "glass_color",
        "0.99",
        "0.998",
        "reflection_color",
        "frosting_roughness",
        "0.035",
        "glass_ior",
        "1.47",
        "thin_walled",
        "depth",
        "0.002",
        "enable_opacity",
        "cutout_opacity",
        "roughness_texture_influence",
    ):
        assert value in html
    assert "试剂瓶" in html
    assert "九项完整写入" in html
    assert "已经正式重建并准入" in html
    assert "玻璃棒" in html and "本轮不改" in html
    assert "磨口" in html and "保留磨砂" in html
    assert "没有升级任务 USD" in html
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
    assert html.count('alt="') >= 16
    references = re.findall(r'(?:src|href)="([^"]+)"', html)
    for reference in references:
        if reference.startswith("#"):
            continue
        assert not reference.startswith(("http://", "https://", "file:"))
        assert (PAGE_ROOT / reference).resolve().exists(), reference


def test_glass_material_media_matches_provenance() -> None:
    provenance = json.loads((PAGE_ROOT / "assets/provenance.json").read_text(encoding="utf-8"))
    assert provenance["schema_version"] == "scenario-forge-glass-material-guide/v0.4"
    assert provenance["runtime"] == "Isaac Sim 4.1"
    assert len(provenance["comparisons"]) == 4
    for comparison in provenance["comparisons"]:
        assert comparison["asset_id"] in ASSET_IDS
        for side in ("before", "after", "pathtracing"):
            item = comparison[side]
            path = PAGE_ROOT / item["path"]
            assert path.is_file()
            assert sha256(path.read_bytes()).hexdigest() == item["sha256"]
    donor = provenance["donor"]
    assert donor["asset_id"] == "reagent_bottle_90x55"
    for side in ("rtl", "pathtracing"):
        item = donor[side]
        path = PAGE_ROOT / item["path"]
        assert path.is_file()
        assert sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert provenance["admission"]["status"] == "pass"
    assert provenance["admission"]["handoff_zip_sha256"] == (
        "e4a359ac865763ceddda35694db45d256daa48c40245134b6ff997541e77325c"
    )
    connector_revision = provenance["connector_revision"]
    assert connector_revision["revision"] == "glass_web_standard_v2"
    for side in ("v1", "v2"):
        item = connector_revision[side]
        path = PAGE_ROOT / item["path"]
        assert path.is_file()
        assert sha256(path.read_bytes()).hexdigest() == item["sha256"]
    assert {item["asset_id"] for item in provenance["original_material_assets"]} == {
        "reagent_bottle_90x55",
        "erlenmeyer_flask_250ml_90x35",
    }
    for item in provenance["original_material_assets"]:
        for field in ("candidate_path", "candidate_sha256"):
            assert item[field]
        candidate = PAGE_ROOT / item["candidate_path"]
        assert sha256(candidate.read_bytes()).hexdigest() == item["candidate_sha256"]


def test_docs_navigation_links_to_glass_material_guide() -> None:
    docs_index = (REPO_ROOT / "docs/index.md").read_text(encoding="utf-8")
    directory = (REPO_ROOT / "docs/task-directory/index.html").read_text(encoding="utf-8")
    assert "[玻璃器皿材质准入标准](glass-material-guide/)" in docs_index
    assert 'href="../glass-material-guide/"' in directory
