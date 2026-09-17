import json
from pathlib import Path

from PIL import Image
import pytest


def test_powder_hud_crop_is_clean_sixteen_by_nine():
    from scripts.prepare_lab2sim_fig1_assets import transform_image

    image = Image.new("RGB", (1280, 800), "white")
    for y in range(69):
        for x in range(1280):
            image.putpixel((x, y), (0, 0, 0))

    result = transform_image(image, "crop_y69_789")

    assert result.size == (1280, 720)
    assert result.getpixel((0, 0)) == (255, 255, 255)


def test_oven_brightness_transform_changes_only_global_values():
    from scripts.prepare_lab2sim_fig1_assets import transform_image

    image = Image.new("RGB", (4, 4), (100, 100, 100))
    result = transform_image(image, "brightness_1_25")

    assert result.size == image.size
    assert result.getpixel((0, 0)) == result.getpixel((3, 3))
    assert result.getpixel((0, 0))[0] > 100


def test_prepare_writes_hash_bound_manifest(tmp_path, monkeypatch):
    import scripts.prepare_lab2sim_fig1_assets as staging

    source = tmp_path / "source.png"
    Image.new("RGB", (8, 8), (12, 34, 56)).save(source)
    expected = tmp_path / "expected.png"
    staging.transform_image(Image.open(source), "copy").save(expected, optimize=True)
    asset = staging.FigureAsset(
        name="selected.png",
        source="source.png",
        source_sha256=staging.file_sha256(source),
        transform="copy",
        asset_sha256=staging.file_sha256(expected),
    )
    monkeypatch.setattr(staging, "ASSETS", (asset,))

    records = staging.prepare(tmp_path, tmp_path / "out")

    manifest = json.loads((tmp_path / "out/fig1-assets.json").read_text())
    assert records == manifest["assets"]
    assert records[0]["source_sha256"] == staging.file_sha256(source)
    assert records[0]["asset_sha256"] == staging.file_sha256(tmp_path / "out/selected.png")


def test_prepare_rejects_source_hash_mismatch(tmp_path, monkeypatch):
    import scripts.prepare_lab2sim_fig1_assets as staging

    source = tmp_path / "source.png"
    Image.new("RGB", (2, 2), "white").save(source)
    monkeypatch.setattr(
        staging,
        "ASSETS",
        (
            staging.FigureAsset(
                "selected.png",
                "source.png",
                "0" * 64,
                "copy",
                "0" * 64,
            ),
        ),
    )

    with pytest.raises(ValueError, match="source hash mismatch"):
        staging.prepare(tmp_path, tmp_path / "out")


def test_prepare_rejects_asset_hash_mismatch(tmp_path, monkeypatch):
    import scripts.prepare_lab2sim_fig1_assets as staging

    source = tmp_path / "source.png"
    Image.new("RGB", (2, 2), "white").save(source)
    monkeypatch.setattr(
        staging,
        "ASSETS",
        (
            staging.FigureAsset(
                "selected.png",
                "source.png",
                staging.file_sha256(source),
                "copy",
                "0" * 64,
            ),
        ),
    )

    with pytest.raises(ValueError, match="asset hash mismatch"):
        staging.prepare(tmp_path, tmp_path / "out")


def test_staging_manifest_matches_figure_provenance():
    repo = Path(__file__).resolve().parents[1]
    figure_root = repo / "paper/venues/iclr2027/figures/lab2sim"
    manifest = json.loads((figure_root / "source/fig1-assets.json").read_text())
    provenance = json.loads((figure_root / "provenance.json").read_text())
    fig1 = next(figure for figure in provenance["figures"] if figure["id"] == "fig1-hero")
    provenance_assets = {
        Path(record["asset"]).name: record
        for record in [*fig1["inputs"], *fig1["outputs"]]
    }

    for staged in manifest["assets"]:
        recorded = provenance_assets[staged["name"]]
        assert recorded["source_sha256"] == staged["source_sha256"]
        assert recorded["asset_sha256"] == staged["asset_sha256"]
        assert (figure_root / recorded["source"]).resolve() == (
            repo / staged["source"]
        ).resolve()
