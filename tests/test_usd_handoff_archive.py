from __future__ import annotations

from pathlib import Path
import zipfile

import yaml

from scenario_forge.artifacts.usd_handoff import build_usd_handoff_archive


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
