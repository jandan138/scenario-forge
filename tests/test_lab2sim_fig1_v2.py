"""Delivery contracts for the author v2 reconstruction, independent of old rounds."""

import importlib.util
import builtins
import json
from pathlib import Path
import shutil
import zipfile
from xml.etree import ElementTree as ET

import pytest


HERE = Path(__file__).resolve().parents[1] / (
    "paper/venues/iclr2027/figures/lab2sim/fig1_iterations/my-try"
)


def composer():
    spec = importlib.util.spec_from_file_location("fig1_v2", HERE / "compose_v2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_layout_import_does_not_require_external_reference_or_pptx(tmp_path, monkeypatch):
    """A clean checkout can inspect layout and archive contracts without render inputs."""
    repo = tmp_path / "checkout"
    (repo / "src/scenario_forge").mkdir(parents=True)
    figure = repo / "paper/figure"
    figure.mkdir(parents=True)
    for name in ("compose_v2.py", "compose_mytry.py", "text-locks-v2.json"):
        shutil.copy2(HERE / name, figure / name)
    original_import = builtins.__import__

    def without_pptx(name, *args, **kwargs):
        if name == "pptx" or name.startswith("pptx."):
            raise ModuleNotFoundError("python-pptx is not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_pptx)
    spec = importlib.util.spec_from_file_location("portable_figure", figure / "compose_v2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert len([o for o in module.layout() if o["kind"] == "photo"]) == 10
    assert module.new_round(figure / "rounds", "r99-portable").is_dir()


def test_v2_has_four_panels_and_ten_independent_photo_slots():
    m = composer()
    objects = m.layout()
    by_id = {o["id"]: o for o in objects}
    assert len(by_id) == len(objects)
    assert by_id["panel-interactivity"]["box"] == [1044, 54, 606, 336]
    assert by_id["panel-scenes"]["box"] == [1044, 405, 606, 474]
    photos = [o for o in objects if o["kind"] == "photo"]
    assert {o["slot"] for o in photos} == {
        "request",
        "search",
        "build",
        "oven-controls",
        "balance",
        "stopcock",
        "fehling",
        "powder",
        "titration",
        "oven",
    }
    for o in objects:
        x, y, w, h = o["box"]
        assert 0 <= x <= x + w <= 1672
        assert 0 <= y <= y + h <= 941
    for key in ("fehling", "powder", "titration", "oven"):
        p = next(o for o in photos if o["slot"] == key)
        assert p["box"][2] / p["box"][3] > 1.6


def test_v2_rounds_cannot_overwrite_history(tmp_path):
    m = composer()
    dest = m.new_round(tmp_path, "r13-test")
    marker = dest / "keep.txt"
    marker.write_text("original")
    with pytest.raises(FileExistsError):
        m.new_round(tmp_path, "r13-test")
    assert marker.read_text() == "original"
    with pytest.raises(ValueError):
        m.new_round(tmp_path, "../escape")


@pytest.mark.local_artifacts
def test_v2_assets_have_real_sources_and_hashes():
    m = composer()
    manifest = json.loads((HERE / "assets-v2/manifest.json").read_text())
    m.validate_assets(manifest, HERE)
    assert len(manifest["assets"]) == 10
    assert all(a["kind"] != "reference_crop" for a in manifest["assets"])
    assert all(a["source_sha256"] and a["sha256"] for a in manifest["assets"])


def test_colleague_gallery_uses_selected_experiments_and_identical_lighting():
    current = json.loads((HERE / "assets-v2/manifest.json").read_text())["assets"]
    baseline = json.loads(
        (HERE / "rounds/r19-final-office-review/assets-v2/manifest.json").read_text()
    )["assets"]
    tasks = {
        "fehling": "task_12_fehling_test",
        "powder": "task_09_solid_weighing",
        "titration": "task_10_titration_experiment",
        "oven": "task_11_remove_container_from_oven",
    }
    by_id = {a["slot"]: a for a in baseline}
    lighting = []
    for asset in current:
        key = asset["slot"]
        if key not in tasks:
            assert asset["sha256"] == by_id[key]["sha256"]
            continue
        capture = asset["lineage"][0]
        assert capture["source_root_id"] == "colleague-scientific-experiments"
        assert capture["scene"].startswith(tasks[key] + "/")
        assert capture["scene_unchanged"]
        assert capture["state"] == "authored_static_state"
        assert capture["camera"]["azimuth_deg"] == -100
        assert capture["camera"]["elevation_deg"] == 30
        lighting.append(capture["lighting"])
    assert len(lighting) == 4
    assert all(value == lighting[0] for value in lighting)


@pytest.mark.local_artifacts
def test_v2_pptx_preserves_named_geometry_and_editable_labels(tmp_path):
    m = composer()
    path = tmp_path / "v2.pptx"
    m.write_pptx(m.layout(), path)
    with zipfile.ZipFile(path) as z:
        xml = ET.fromstring(z.read("ppt/slides/slide1.xml"))
        ns = {
            "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        }
        texts = [n.text for n in xml.findall(".//a:t", ns)]
        assert "Task-critical interactivity" in texts
        assert "Robot-ready Isaac scenes" in texts
        assert "Force-coupled balance" in texts
        names = {n.get("name") for n in xml.findall(".//p:cNvPr", ns)}
        assert {"photo-" + key for key in m.SLOTS} <= names
        for pic in xml.findall(".//p:pic", ns):
            ext = pic.find(".//a:ext", ns)
            assert int(ext.get("cx")) < m.emu(1672)
        assert b'TargetMode="External"' not in z.read("ppt/slides/_rels/slide1.xml.rels")
