import importlib.util
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
COMPOSER_PATH = ROOT / "paper/venues/iclr2027/figures/lab2sim/compose_galleries.py"


def load_composer():
    spec = importlib.util.spec_from_file_location("lab2sim_result_composer", COMPOSER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_result_asset_inventory_covers_every_composer_input():
    import scripts.prepare_lab2sim_result_assets as staging

    composer = load_composer()
    expected = {
        name
        for case in composer.fig2_cases()
        for name in (case.station, case.detail)
    }
    expected.update(
        name
        for case in composer.fig3_cases()
        for name in (case.evidence, case.usd)
    )

    staged = {asset.name for asset in staging.ASSETS}
    assert expected <= staged
    # Appendix extras are the only staged assets the two composers do not consume.
    assert staged - expected == {"app_oven_interior.png", "app_lift2_runtime.png"}


def test_result_asset_transform_applies_crop_and_global_brightness():
    from scripts.prepare_lab2sim_result_assets import transform_image

    image = Image.new("RGB", (100, 80), (100, 100, 100))
    result = transform_image(image, crop=(10, 5, 90, 65), brightness=1.1)

    assert result.size == (80, 60)
    assert result.getpixel((0, 0))[0] > 100
    assert result.getpixel((0, 0)) == result.getpixel((79, 59))


def test_result_staging_manifest_matches_figure_provenance():
    figure_root = ROOT / "paper/venues/iclr2027/figures/lab2sim"
    manifest = json.loads((figure_root / "source/fig23-assets.json").read_text())
    provenance = json.loads((figure_root / "provenance.json").read_text())
    recorded = {}
    for figure in provenance["figures"]:
        if figure["id"] in {"fig2-gallery", "fig3-real-spec-usd", "app-extra"}:
            for record in figure["inputs"]:
                if "source_sha256" in record:
                    recorded[Path(record["asset"]).name] = record

    assert set(recorded) == {asset["name"] for asset in manifest["assets"]}
    for staged in manifest["assets"]:
        record = recorded[staged["name"]]
        assert record["source_sha256"] == staged["source_sha256"]
        assert record["asset_sha256"] == staged["asset_sha256"]
        assert (figure_root / record["source"]).resolve() == (ROOT / staged["source"]).resolve()
        assert record["status"] in {"current_delivery", "indexed manufacturer evidence"}
    assert "app_lift2_runtime.png" in recorded


def test_fig3_provenance_binds_admission_evidence_per_usd_row():
    figure_root = ROOT / "paper/venues/iclr2027/figures/lab2sim"
    provenance = json.loads((figure_root / "provenance.json").read_text())
    fig3 = next(f for f in provenance["figures"] if f["id"] == "fig3-real-spec-usd")
    usd_rows = [r for r in fig3["inputs"] if r["asset"].endswith("_usd.png")]

    assert len(usd_rows) == 2
    for record in usd_rows:
        assert record["promotion_receipt"].endswith("promotion_receipt.json")
        assert len(record["promotion_receipt_sha256"]) == 64
        assert len(record["render_manifest_sha256"]) == 64
        assert len(record["scene_sha256"]) == 64


def test_result_asset_prepare_writes_hash_manifest(tmp_path, monkeypatch):
    import scripts.prepare_lab2sim_result_assets as staging

    source = tmp_path / "source.png"
    Image.new("RGB", (10, 10), (80, 100, 120)).save(source)
    expected = tmp_path / "expected.png"
    staging.transform_image(Image.open(source), crop=None, brightness=1.0).save(
        expected, optimize=True
    )
    asset = staging.ResultAsset(
        name="selected.png",
        source="source.png",
        source_sha256=staging.file_sha256(source),
        crop=None,
        brightness=1.0,
        asset_sha256=staging.file_sha256(expected),
    )
    monkeypatch.setattr(staging, "ASSETS", (asset,))

    records = staging.prepare(tmp_path, tmp_path / "out")

    manifest = json.loads((tmp_path / "out/fig23-assets.json").read_text())
    assert manifest["assets"] == records
    assert records[0]["asset_sha256"] == staging.file_sha256(tmp_path / "out/selected.png")
