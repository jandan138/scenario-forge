from __future__ import annotations

from pathlib import Path
import json
import zipfile

import yaml

from scenario_forge.artifacts.usd_handoff import (
    build_dual_consumer_variant_bundle,
    build_multi_task_dual_consumer_bundle,
    build_usd_handoff_archive,
    build_usd_handoff_bundle,
)
import scenario_forge.artifacts.usd_handoff as usd_handoff


def test_usd_handoff_archive_contains_scene_config_deps_and_no_robot(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter"
    (adapter / "deps/environment").mkdir(parents=True)
    (adapter / "scene.usd").write_text(
        '#usda 1.0\n(def Xform "World" { asset env = @./deps/environment/asset.usd@ })\n',
        encoding="utf-8",
    )
    (adapter / "task_config.py").write_text("TASKS = {}\n", encoding="utf-8")
    (adapter / "parity_manifest.json").write_text("{}\n", encoding="utf-8")
    (adapter / "deps/environment/asset.usd").write_text("#usda 1.0\n", encoding="utf-8")

    result = build_usd_handoff_archive(
        archive_id="regular_tasks",
        task_adapters={2: adapter},
        output_dir=tmp_path / "out",
    )

    manifest = yaml.safe_load((result.root / "manifest.yaml").read_text())
    assert manifest["tasks"][0]["open_usd"] == "tasks/task_02/scene.usd"
    assert manifest["tasks"][0]["robot_included"] is False
    assert (result.root / "tasks/task_02/task_config.py").is_file()
    assert (result.root / "SHA256SUMS").is_file()
    with zipfile.ZipFile(result.zip_path) as archive:
        assert "regular_tasks/tasks/task_02/scene.usd" in archive.namelist()


def test_usd_handoff_bundle_keeps_multiple_variants_of_one_task(tmp_path: Path) -> None:
    packages = []
    for label in ("example4", "bioclean"):
        adapter = tmp_path / label
        (adapter / "deps").mkdir(parents=True)
        (adapter / "scene.usd").write_text("#usda 1.0\n", encoding="utf-8")
        (adapter / "task_config.py").write_text("TASKS = {}\n", encoding="utf-8")
        (adapter / "parity_manifest.json").write_text("{}\n", encoding="utf-8")
        packages.append((7, label, adapter))

    result = build_usd_handoff_bundle(
        archive_id="r7_bundle",
        packages=packages,
        output_dir=tmp_path / "out",
    )

    assert (result.root / "packages/task_07__example4/scene.usd").is_file()
    assert (result.root / "packages/task_07__bioclean/scene.usd").is_file()
    manifest = yaml.safe_load((result.root / "manifest.yaml").read_text())
    assert len(manifest["packages"]) == 2


def test_dual_consumer_bundle_contains_independent_ebench_and_vr_variants(
    tmp_path: Path,
) -> None:
    packages = []
    for label in ("fill20", "fill40", "fill60", "fill80"):
        package = tmp_path / label
        (package / "ebench/deps").mkdir(parents=True)
        (package / "vr/deps").mkdir(parents=True)
        (package / "ebench/scene.usd").write_text(
            '#usda 1.0\ndef Xform "World" {}\n', encoding="utf-8"
        )
        (package / "ebench/config.yaml").write_text("config: ebench\n", encoding="utf-8")
        smoke = package / "ebench/evidence/product_smoke/report.json"
        smoke.parent.mkdir(parents=True)
        smoke.write_text('{"status":"pass"}\n', encoding="utf-8")
        (package / "ebench/deps/asset.usd").write_text("asset", encoding="utf-8")
        (package / "vr/scene.usd").write_text(
            '#usda 1.0\ndef Xform "World" {}\n', encoding="utf-8"
        )
        (package / "vr/config.py").write_text("TASKS = {}\n", encoding="utf-8")
        (package / "vr/task_config.py").write_text("TASKS = {}\n", encoding="utf-8")
        vr_smoke = package / "vr/evidence/open_smoke/report.json"
        vr_smoke.parent.mkdir(parents=True)
        vr_smoke.write_text('{"status":"pass"}\n', encoding="utf-8")
        (package / "vr/deps/asset.usd").write_text("asset", encoding="utf-8")
        (package / "manifest.json").write_text(
            json.dumps({"scenario_id": label}), encoding="utf-8"
        )
        overview = package / "ebench/evidence/initial_scene/scene_overview.png"
        overview.parent.mkdir(parents=True)
        overview.write_bytes(b"png")
        packages.append((label, package))

    result = build_dual_consumer_variant_bundle(
        archive_id="task02_r10_fill_sweep",
        variants=packages,
        default_variant="fill40",
        output_dir=tmp_path / "handoff",
    )

    manifest = yaml.safe_load((result.root / "manifest.yaml").read_text())
    assert manifest["default_variant"] == "fill40"
    assert [item["fill_level_id"] for item in manifest["variants"]] == [
        "fill20",
        "fill40",
        "fill60",
        "fill80",
    ]
    assert "960-step zero-action physics smoke" in manifest["claim_boundary"]
    assert manifest["variants"][0]["vr"]["config"] == (
        "variants/fill20/vr/task_config.py"
    )
    assert (result.root / "variants/fill20/ebench/scene.usd").is_file()
    assert (result.root / "variants/fill20/vr/scene.usd").is_file()
    assert (result.root / "variants/fill20/vr/task_config.py").is_file()
    assert (result.root / "variants/fill20/evidence/scene_overview.png").is_file()
    assert (result.root / "variants/fill20/evidence/product_smoke_report.json").is_file()
    assert (result.root / "variants/fill20/evidence/vr_open_smoke_report.json").is_file()
    with zipfile.ZipFile(result.zip_path) as archive:
        names = archive.namelist()
        assert "task02_r10_fill_sweep/variants/fill80/vr/task_config.py" in names
        assert not any("robot_oracle" in name for name in names)
    assert result.zip_path.is_file()


def test_deterministic_zip_replacement_is_atomic_on_write_failure(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    (root / "payload.txt").write_text("new payload", encoding="utf-8")
    destination = tmp_path / "bundle.zip"
    destination.write_bytes(b"previous published archive")

    class FailingZipFile:
        def __init__(self, path, *_args, **_kwargs):
            self.path = Path(path)

        def __enter__(self):
            self.path.write_bytes(b"partial")
            return self

        def writestr(self, *_args, **_kwargs):
            raise OSError("simulated archive write failure")

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(usd_handoff.zipfile, "ZipFile", FailingZipFile)

    try:
        usd_handoff._write_deterministic_zip(root, destination)
    except OSError as exc:
        assert "simulated" in str(exc)
    else:
        raise AssertionError("expected archive write failure")

    assert destination.read_bytes() == b"previous published archive"
    assert not (tmp_path / "bundle.zip.tmp").exists()


def test_multi_task_dual_consumer_bundle_preserves_variants_and_entrypoints(
    tmp_path: Path,
) -> None:
    variants = []
    for task_number, label in ((2, "fill40"), (7, "bioclean"), (8, "bioclean")):
        package = tmp_path / f"task{task_number:02d}_{label}"
        ebench = package / "ebench"
        vr = package / "vr"
        (ebench / "assets").mkdir(parents=True)
        (ebench / "tasks").mkdir()
        (ebench / "assets/scene.usda").write_text("#usda 1.0\n", encoding="utf-8")
        (ebench / "tasks/config.yaml").write_text("task: config\n", encoding="utf-8")
        (ebench / "package_manifest.json").write_text(
            json.dumps(
                {
                    "entrypoints": {
                        "scene_usd": "assets/scene.usda",
                        "task_config": "tasks/config.yaml",
                    }
                }
            ),
            encoding="utf-8",
        )
        (vr / "deps").mkdir(parents=True)
        (vr / "scene.usd").write_text("#usda 1.0\n", encoding="utf-8")
        (vr / "task_config.py").write_text("TASKS = {}\n", encoding="utf-8")
        (vr / "parity_manifest.json").write_text("{}\n", encoding="utf-8")
        report = vr / "evidence/open_smoke/report.json"
        report.parent.mkdir(parents=True)
        report.write_text('{"status":"pass"}\n', encoding="utf-8")
        variants.append((task_number, label, ebench, vr))

    result = build_multi_task_dual_consumer_bundle(
        archive_id="tasks_02_07_08_r10_1",
        variants=variants,
        output_dir=tmp_path / "handoff",
    )

    manifest = yaml.safe_load((result.root / "manifest.yaml").read_text())
    assert manifest["package_count"] == 3
    assert manifest["task_counts"] == {"task02": 1, "task07": 1, "task08": 1}
    assert manifest["packages"][1]["ebench"]["open_usd"] == (
        "task07/bioclean/ebench/assets/scene.usda"
    )
    assert manifest["packages"][1]["vr"]["config"] == (
        "task07/bioclean/vr/task_config.py"
    )
    assert (result.root / "task02/fill40/ebench/assets/scene.usda").is_file()
    assert (result.root / "task08/bioclean/vr/scene.usd").is_file()
    with zipfile.ZipFile(result.zip_path) as archive:
        assert (
            "tasks_02_07_08_r10_1/task07/bioclean/vr/task_config.py"
            in archive.namelist()
        )
