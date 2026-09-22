import pytest

import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "paper/venues/iclr2027/figures/bench/protocol/teaser-exact/compose_teaser.py"
)
FIG1_SOURCE = Path(__file__).resolve().parents[1] / "paper/venues/iclr2027/figures/lab2sim/source"


def load_composer():
    spec = importlib.util.spec_from_file_location("protocol_teaser_exact", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


composer = load_composer()


def test_teaser_canvas_and_seven_panels():
    assert composer.CANVAS == (3864, 1536)
    assert composer.C["panel"] == "#F5F7FA"
    assert composer.C["teal"] == "#087F75"
    assert composer.G["pipeline"] == (24, 36, 1032, 720)
    assert composer.G["skills"] == (1152, 36, 1578, 456)
    assert composer.G["wetlab"] == (2808, 36, 1032, 720)
    assert composer.G["difficulty"] == (24, 796, 1032, 712)
    assert composer.G["suite"] == (1152, 508, 1578, 456)
    assert composer.G["generalization"] == (1152, 980, 1578, 528)
    assert composer.G["scoring"] == (2808, 796, 1032, 712)
    assert composer.G["mid_x"] == [1184, 1566, 1948, 2330]


def _slot_file(filename: str) -> Path:
    local = MODULE_PATH.parent / "source" / filename
    return local if local.is_file() else FIG1_SOURCE / filename


@pytest.mark.local_artifacts
def test_teaser_filled_slots_exist_and_empty_slots_are_declared():
    for name in composer.G["photo_slots"].values():
        assert _slot_file(name).is_file()
    assert "skills_1" not in composer.G["empty_slots"]
    assert "skills_1" in composer.G["photo_slots"]
    assert "skills_4" in composer.G["photo_slots"]
    assert "gen_fg_1" in composer.G["empty_slots"]
    assert "pipe_search" not in composer.G["empty_slots"]


def test_teaser_skill_frames_are_task01_phases():
    assert composer.G.get("skills_frame_times") == [15, 60, 82, 142]


@pytest.mark.local_artifacts
def test_teaser_wetlab_photos_are_selected_stills():
    assert composer.G["wet_frame_times"] == {"dualarm": 14}
    assert composer.G["wet_title_band"] == 73
    assert composer.G["photo_slots"]["wet_dualarm"] == "wet_dualarm.png"
    assert composer.G["photo_slots"]["wet_liquid"] == "wet_liquid.png"
    assert composer.G["photo_slots"]["wet_centrifuge"] == "wet_centrifuge.png"
    assert composer.G["photo_slots"]["wet_reaction"] == "wet_reaction.png"
    png = composer.compose_png()
    x, y, w, h = composer.G["wet_cards"][0]
    # Photo band interior, not the white title strip.
    assert png.getpixel((x + w // 2, y + 70))[:3] != (255, 255, 255)
    rx, ry, rw, rh = composer.G["wet_cards"][3]
    left = png.getpixel((rx + rw // 4, ry + 70))[:3]
    right = png.getpixel((rx + 3 * rw // 4, ry + 70))[:3]
    assert left != right


@pytest.mark.local_artifacts
def test_teaser_wet_liquid_is_front_still_without_robot_arms():
    import numpy as np
    from PIL import Image

    path = MODULE_PATH.parent / "source" / "wet_liquid.png"
    image = np.array(Image.open(path).convert("RGB"))
    height, width = image.shape[:2]
    assert (width, height) == (1280, 720)
    lower_mid = image[int(height * 0.45) : int(height * 0.85), int(width * 0.30) : int(width * 0.70)]
    black_frac = float((lower_mid.mean(axis=2) < 40).mean())
    assert black_frac < 0.08


@pytest.mark.local_artifacts
def test_teaser_wet_centrifuge_is_left_of_tight_candidate():
    from hashlib import sha256

    source = MODULE_PATH.parent / "source"
    wet = sha256((source / "wet_centrifuge.png").read_bytes()).hexdigest()
    tight = sha256((source / "candidates" / "isaac" / "centrifuge_tight.png").read_bytes()).hexdigest()
    assert wet != tight


@pytest.mark.local_artifacts
def test_teaser_png_matches_locked_canvas():
    png = composer.compose_png()
    assert png.size == (3864, 1536)
    # Request/Results-style rule: side panels stay panel blue-gray, not white flood.
    assert png.getpixel((500, 140))[:3] == (245, 247, 250)
    # Skill card interior is a task_01 frame, not an empty white card.
    assert png.getpixel((1300, 220))[:3] != (255, 255, 255)


def test_teaser_child_boxes_and_type_are_parent_relative_locks():
    assert composer.TYPE["title"]["size"] == 55
    assert composer.TYPE["step"]["size"] == 37
    assert composer.G["pipe_search"] == (81, 352, 209, 158)
    assert composer.HEAD["pipeline"]["right_box"] == (816, 156, 196, 24)
    assert composer.C["arrow"] == "#617086"
    assert composer.C["sub"] == "#617086"
    assert composer.HEAD["pipeline"]["sub_box"] == (69, 156, 235, 27)
    assert composer.HEAD["skills"]["sub_box"] == (1189, 148, 557, 24)
    assert composer.HEAD["pipeline"]["icon"] == (71, 77, 56, 62)
    assert composer.HEAD["generalization"]["icon"] == (1198, 1022, 54, 54)
    assert composer.HEAD["scoring"]["icon"] == (2853, 839, 59, 56)
    assert composer.G["wet_icons"][0] == (2956, 246, 249, 89)
    assert composer.G["diff_icons"][0] == (98, 1001, 52, 27)
    assert composer.G["wet_cards"][0] == (2848, 210, 467, 237)
    assert composer.G["diff_pills"][0] == (64, 970, 953, 91)
    assert composer.G["score_steps"][0] == (2848, 972, 213, 123)
    pipe = composer.G["pipeline"]
    frac = composer.parent_frac(pipe, composer.G["pipe_spec"])
    assert abs(frac[0] - (306 - pipe[0]) / pipe[2]) < 1e-9
    assert composer.HEAD["pipeline"]["title_box"] == (159, 74, 465, 51)
    assert composer.G["arrows"]["pipe"] == [(280, 436, 19, 8), (518, 436, 19, 8), (760, 436, 19, 8)]
    assert composer.G["arrows"]["skills"][0] == (1380, 441, 165, 6)
    assert composer.G["arrows"]["score"][0] == (3068, 1032, 23, 9)
    assert composer.G["arrows"]["flow"][0] == [(1056, 392), (1096, 392), (1096, 266), (1150, 266)]
    assert composer.G["arrows"]["flow"][3] == [(2730, 1260), (2806, 1260)]
    assert composer.G["pipe_dot_d"] == 44
    assert composer.G["pipe_dots"] == [166, 408, 650, 891]
    assert composer.G["gen_cards"][0] == (1184, 1098, 361, 335)
    assert composer.G["gen_quotes"][0] == (1966, 1172, 325, 93)
    assert composer.G["gen_quote_lines"][0][0] == (1989, 1188, 161, 21)
    assert composer.C["quote"] == "#F5F7FA"
    assert composer.G["quote_r"] == 16
    assert composer.TYPE["quote"]["size"] == 27
    assert composer.TYPE["gen_col"]["size"] == 29


@pytest.mark.local_artifacts
def test_teaser_pptx_hybrid_uses_locked_boxes():
    import tempfile

    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    png = composer.compose_png()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "teaser-exact.pptx"
        composer.compose_pptx(png, path)
        prs = Presentation(str(path))
    slide = prs.slides[0]
    names = [shape.name for shape in slide.shapes]
    assert "teaser-raster" not in names
    pictures = [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(pictures) >= 8
    pipe = next(shape for shape in slide.shapes if shape.name == "pipeline")
    assert int(pipe.left) == int(round(24 * composer.EMU_PER_PX))
    assert int(pipe.top) == int(round(36 * composer.EMU_PER_PX))
    assert int(pipe.width) == int(round(1032 * composer.EMU_PER_PX))
    assert int(pipe.height) == int(round(720 * composer.EMU_PER_PX))
    skill = next(shape for shape in slide.shapes if shape.name == "skills_1")
    x, y, w, h = composer.G["skills_cards"][0]
    assert int(skill.left) == int(round(x * composer.EMU_PER_PX))
    assert int(skill.top) == int(round(y * composer.EMU_PER_PX))
    assert int(skill.width) == int(round(w * composer.EMU_PER_PX))
    assert int(skill.height) == int(round(h * composer.EMU_PER_PX))
    texts = [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]
    assert any("Skills to Protocols" in text for text in texts)
    assert any("Grasp" in text for text in texts)


def _compose_pptx_slide():
    import tempfile

    from pptx import Presentation

    png = composer.compose_png()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "teaser-exact.pptx"
        composer.compose_pptx(png, path)
        return Presentation(str(path)).slides[0]


@pytest.mark.local_artifacts
def test_teaser_pptx_r24_hardening():
    from pptx.oxml.ns import qn

    slide = _compose_pptx_slide()
    title = next(shape for shape in slide.shapes if shape.name == "title-skills")
    assert title.text_frame.word_wrap is False
    quote = next(shape for shape in slide.shapes if shape.name == "gen-q0-0")
    assert quote.text_frame.word_wrap is False
    names = [shape.name for shape in slide.shapes]
    assert "arrow-skills-0-shaft" in names
    assert "arrow-skills-0-head" in names
    pipe = next(shape for shape in slide.shapes if shape.name == "pipeline")
    style = pipe._element.find(qn("p:style"))
    effect = None if style is None else style.find(qn("a:effectRef"))
    assert effect is None or effect.get("idx") == "0"


@pytest.mark.local_artifacts
def test_teaser_r25_suite_captions_teal_and_admit_fill():
    assert composer.C["admit"] == "#EBF5F2"
    png = composer.compose_png()
    assert png.getpixel((1360, 936))[:3] == (8, 127, 117)
    assert png.getpixel((890, 410))[:3] == (235, 245, 242)


@pytest.mark.local_artifacts
def test_teaser_r26_spatial_hollow_and_liquids_plural():
    assert composer.WET_LABELS[1][0] == "Liquids & glassware"
    png = composer.compose_png()
    assert png.getpixel((123, 1131))[:3] != (8, 127, 117)


@pytest.mark.local_artifacts
def test_teaser_r27_perceptual_eye_is_pointed():
    import numpy as np

    png = np.array(composer.compose_png().convert("RGB"))
    crop = png[1341:1385, 95:151]
    teal = (crop[:, :, 1] > 90) & (crop[:, :, 0] < 60)
    xs = np.where(teal[0])[0]
    assert len(xs) <= 4
