import importlib.util
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "paper/venues/iclr2027/figures/lab2sim/compose_galleries.py"
)


def load_composer():
    spec = importlib.util.spec_from_file_location("lab2sim_result_figures", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_dummy_sources(source_dir: Path, names: set[str]) -> None:
    source_dir.mkdir(parents=True)
    for index, name in enumerate(sorted(names)):
        color = (60 + 20 * index, 90 + 10 * index, 120 + 5 * index)
        Image.new("RGB", (640, 360), color).save(source_dir / name)


def test_fig2_uses_four_current_delivery_families_absent_from_fig1():
    module = load_composer()

    cases = module.fig2_cases()

    assert [case.title for case in cases] == [
        "Stopper removal",
        "Glass-rod rack",
        "Stir-bar insertion",
        "Tube water bath",
    ]
    assert [case.action for case in cases] == [
        "remove stopper",
        "rack glass rod",
        "insert stir bar",
        "heat tube in bath",
    ]
    assert [case.revision for case in cases] == ["r11", "r10.1", "r5", "r1"]
    assert all(case.status == "current_delivery" for case in cases)
    fig1_families = {"fehling", "powder", "titration", "oven"}
    assert not any(
        family in (case.station + case.detail).lower()
        for case in cases
        for family in fig1_families
    )


def test_fig2_is_composed_at_text_width_with_readable_type(tmp_path):
    module = load_composer()
    source_names = {
        name
        for case in module.fig2_cases()
        for name in (case.station, case.detail)
    }
    source_dir = tmp_path / "source"
    stage_dummy_sources(source_dir, source_names)

    outputs = module.render_fig2(source_dir, tmp_path / "out")

    assert set(outputs) == {"svg", "pdf", "png"}
    png = Image.open(outputs["png"])
    assert png.size[0] == round(module.TEXT_WIDTH_IN * module.PNG_DPI)
    svg = outputs["svg"].read_text(encoding="utf-8")
    assert "<text" in svg
    assert module.MIN_FONT_PT >= 7.0
    assert min(module.FONT_PT.values()) >= module.MIN_FONT_PT


def test_fig3_has_two_aligned_evidence_contract_usd_rows():
    module = load_composer()

    cases = module.fig3_cases()

    assert [case.title for case in cases] == ["IKA OVEN 125", "Burette stopcock"]
    assert all(len(case.contract) == 4 for case in cases)
    assert cases[0].contract == (
        "envelope 700 × 825 × 650 mm",
        "door_hinge: revolute, 0–180°",
        "handle: door-child collider",
        "shelves: placement surfaces",
    )
    assert cases[1].contract == (
        "tube 560 mm, Ø12 mm",
        "stopcock: revolute, 0–90°",
        "handle: grasp_region",
        "mount_frame: stand FixedJoint",
    )
    assert [case.admission for case in cases] == [
        "ConvertAsset · promoted · Isaac 4.1",
        "ConvertAsset · promoted · Isaac 4.5",
    ]
    assert [case.spec for case in cases] == [
        "ika-oven-125",
        "titration-burette-and-stand",
    ]


def test_fig3_exports_editable_text_with_three_column_grammar(tmp_path):
    module = load_composer()
    source_names = {
        name
        for case in module.fig3_cases()
        for name in (case.evidence, case.usd)
    }
    source_dir = tmp_path / "source"
    stage_dummy_sources(source_dir, source_names)

    outputs = module.render_fig3(source_dir, tmp_path / "out")

    assert set(outputs) == {"svg", "pdf", "png"}
    png = Image.open(outputs["png"])
    assert png.size[0] == round(module.TEXT_WIDTH_IN * module.PNG_DPI)
    svg = outputs["svg"].read_text(encoding="utf-8")
    assert "<text" in svg
    assert "Manufacturer evidence" in svg
    assert "Agent-written contract" in svg
    assert "Admitted USD" in svg
    assert "promoted" in svg
