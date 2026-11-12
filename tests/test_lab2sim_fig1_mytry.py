import pytest

import importlib.util
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

from tests.paper_publication import skip_unless_paper_published

skip_unless_paper_published()


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "paper/venues/iclr2027/figures/lab2sim/fig1_iterations/my-try/compose_mytry.py"
)
FIG1_SOURCE = Path(__file__).resolve().parents[1] / "paper/venues/iclr2027/figures/lab2sim/source"
EXPECTED_ASSETS = {
    "request": "ika_catalog_closed.png",
    "search": "ika_catalog_open.png",
    "build": "fig3_oven_usd.png",
    "fehling": "fehling_r10_hero.png",
    "powder": "powder_r4_hero.png",
    "titration": "titration_r17_hero.png",
    "oven": "oven_r2_hero.png",
}


def load_composer():
    spec = importlib.util.spec_from_file_location("lab2sim_fig1_mytry", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


composer = load_composer()


def test_mytry_uses_the_seven_fig1_photo_assets():
    assert composer.G["photo_slots"] == EXPECTED_ASSETS


@pytest.mark.local_artifacts
def test_mytry_photo_assets_are_staged():
    for name in EXPECTED_ASSETS.values():
        assert (FIG1_SOURCE / name).is_file()


@pytest.mark.local_artifacts
def test_mytry_outputs_match_draft_canvas_and_named_slots(tmp_path):
    icons = composer.rasterize_icons(composer.icon_jobs(), tmp_path / "icons")
    png = composer.compose_png(icons)
    assert png.size == (1672, 941)

    svg = composer.compose_svg(icons)
    for label in ("Bench2Sim agent", "Fehling", "Powder", "Titration", "OVEN 125", "PASS"):
        assert label in svg

    if composer.Presentation is None:
        return

    pptx_path = tmp_path / "fig1-mytry.pptx"
    composer.compose_pptx(icons, pptx_path)
    with zipfile.ZipFile(pptx_path) as archive:
        slide = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
        names = {node.get("name") for node in slide.iter() if node.get("name")}
        for name in (
            "request-photo",
            "search-photo",
            "build-photo",
            "scene-fehling",
            "scene-powder",
            "scene-titration",
            "scene-oven",
        ):
            assert name in names


def test_mytry_agent_well_only_and_vertical_dividers():
    assert "panel_body" not in composer.C
    assert composer.C["well"] == "#FCFEFE"
    assert composer.C["panel"] == "#EFF7FE"
    assert composer.C["vdiv"] == "#DAEBFE"
    assert composer.G["well"] == (321, 212, 764, 562)
    assert composer.G["well_r"] == 16
    ax, ay, aw, ah = composer.G["agent"]
    wx, wy, ww, wh = composer.G["well"]
    assert wx > ax and wy > ay
    assert wx + ww < ax + aw and wy + wh < ay + ah
    assert composer.G["vdiv_steps"] == [517, 702, 899]
    assert composer.G["vdiv_steps_y"] == (250, 618)
    assert composer.C["caption"] == "#122249"
    assert composer.G["vdiv_footer"] == [570, 812]
    assert composer.G["search"] == (340, 349, 160, 212)
    assert composer.G["spec"] == (534, 349, 152, 212)
    assert composer.G["build"] == (721, 349, 160, 212)
    admit = composer.G["admit"]
    assert admit[1] == 349 and admit[1] + admit[3] == 561


def test_step_cards_share_baseline_and_keep_draft_stack():
    """Search/Spec/Build share one row. Caption→dash stays the draft 48 px band."""
    search = composer.G["search"]
    spec = composer.G["spec"]
    build = composer.G["build"]
    assert search[1] == spec[1] == build[1] == 349
    assert search[1] + search[3] == spec[1] + spec[3] == build[1] + build[3] == 561
    sp = composer.G["search_photo"]
    bp = composer.G["build_photo"]
    assert sp[0] >= search[0] and sp[1] >= search[1]
    assert sp[0] + sp[2] <= search[0] + search[2]
    assert sp[1] + sp[3] <= search[1] + search[3]
    assert search[3] - (sp[1] - search[1]) - sp[3] <= 10
    assert bp[1] + bp[3] <= build[1] + build[3]
    caption_y = search[1] + search[3] + 14
    dash_y = composer.G["agent_dash"][1]
    assert caption_y == 575
    assert dash_y == 628
    assert 10 <= dash_y - (caption_y + 40) <= 40


def test_search_and_build_cover_the_card():
    assert composer.G.get("search_fit") == "cover"
    assert composer.G.get("build_fit") == "cover"
    search = composer.G["search"]
    spec = composer.G["spec"]
    build = composer.G["build"]
    sp = composer.G["search_photo"]
    bp = composer.G["build_photo"]
    for card, photo in ((search, sp), (build, bp)):
        left = photo[0] - card[0]
        top = photo[1] - card[1]
        right = (card[0] + card[2]) - (photo[0] + photo[2])
        bottom = (card[1] + card[3]) - (photo[1] + photo[3])
        assert max(left, top, right, bottom) <= 10
    assert spec[1] == search[1] and spec[1] + spec[3] == search[1] + search[3]


@pytest.mark.local_artifacts
def test_footer_has_no_peach_discs(tmp_path):
    import numpy as np

    icons = composer.rasterize_icons(composer.icon_jobs(), tmp_path / "icons")
    png = composer.compose_png(icons)
    region = np.asarray(png)[660:750, 330:430]
    peach = np.array([255, 244, 232])
    dist = np.sqrt(((region.astype(int) - peach) ** 2).sum(axis=2))
    assert float((dist < 12).mean()) < 0.08


def test_contain_letterbox_is_white_and_cover_fills():
    image = Image.new("RGBA", (100, 50), (10, 20, 30, 255))
    contained = composer.fit_image(image, 80, 80, "contain")
    assert contained.size == (80, 80)
    assert contained.getpixel((40, 40))[:3] == (10, 20, 30)
    assert contained.getpixel((2, 2))[:3] == (255, 255, 255)

    covered = composer.fit_image(image, 80, 80, "cover")
    assert covered.getpixel((0, 0))[:3] == (10, 20, 30)
    assert covered.getpixel((79, 79))[:3] == (10, 20, 30)
