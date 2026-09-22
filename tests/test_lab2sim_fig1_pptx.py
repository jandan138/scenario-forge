import importlib.util
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

import pytest
from PIL import Image


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "paper/venues/iclr2027/figures/lab2sim/build_fig1_pptx.py"
)


def load_builder():
    spec = importlib.util.spec_from_file_location("lab2sim_fig1_pptx", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_builder()


def test_round_rect_adjustment_tracks_svg_radius():
    assert builder.round_rect_adjustment(10, 187, 160) == 10 / 160
    assert builder.round_rect_adjustment(22, 120, 44) == 0.5
    assert builder.round_rect_adjustment(20, 844, 540) == 20 / 540


@pytest.mark.local_artifacts
def test_manufacturer_caption_needs_a_wider_box_not_a_new_size():
    width = builder.text_width_px("manufacturer", 28, bold=False)
    assert width > 180
    assert width < 220


def test_contain_preserves_aspect_and_cover_fills():
    image = Image.new("RGBA", (100, 50), (10, 20, 30, 255))
    contained = builder.fit_image(image, 80, 80, "contain")
    assert contained.size == (80, 80)
    assert contained.getpixel((40, 40))[:3] == (10, 20, 30)
    assert contained.getpixel((2, 2))[:3] == (255, 255, 255)

    covered = builder.fit_image(image, 80, 80, "cover")
    assert covered.size == (80, 80)
    assert covered.getpixel((0, 0))[:3] == (10, 20, 30)
    assert covered.getpixel((79, 79))[:3] == (10, 20, 30)


@pytest.mark.local_artifacts
def test_builder_writes_explicit_radii_and_no_theme_effects(tmp_path):
    pytest.importorskip("pptx")
    repo = Path(__file__).resolve().parents[1]
    spec = repo / "paper/venues/iclr2027/figures/lab2sim/lab2sim-hero.figure-spec.json"
    output = tmp_path / "fig1-hero.pptx"
    builder.build_pptx(spec, output, tmp_path / "cache")

    with zipfile.ZipFile(output) as archive:
        slide = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
        effects = [
            node.get("idx")
            for node in slide.findall(".//{http://schemas.openxmlformats.org/presentationml/2006/main}style/{http://schemas.openxmlformats.org/drawingml/2006/main}effectRef")
        ]
        assert all(idx == "0" for idx in effects)
        adjustments = []
        for geom in slide.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom"):
            if geom.get("prst") != "roundRect":
                continue
            for guide in geom.findall("{http://schemas.openxmlformats.org/drawingml/2006/main}avLst/{http://schemas.openxmlformats.org/drawingml/2006/main}gd"):
                if guide.get("name") == "adj":
                    adjustments.append(int(guide.get("fmla", "val 0").split()[-1]) / 100000.0)
        assert any(abs(value - 10 / 160) < 1e-4 for value in adjustments)
        assert any(abs(value - 20 / 540) < 1e-4 for value in adjustments)
        fonts = {
            node.get("typeface")
            for node in slide.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}latin")
            if node.get("typeface")
        }
        assert "DejaVu Sans" in fonts
