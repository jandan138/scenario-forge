from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts/publish_scientific_workbench_task_directory.py"


def _script_module():
    spec = importlib.util.spec_from_file_location("publish_task_directory", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publish_task_directory_copies_candidate_overview_and_rewrites_page_links(
    tmp_path: Path,
) -> None:
    module = _script_module()
    source = tmp_path / "build/directory"
    image = tmp_path / "build/candidate.png"
    destination = tmp_path / "docs/task-directory"
    source.mkdir(parents=True)
    image.write_bytes(b"candidate-image")
    image_path = "../candidate.png"
    (source / "task_directory.yaml").write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "task_id": "pour",
                        "candidate_evidence": {"overview_image": image_path},
                        "latest_evidence": None,
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source / "index.html").write_text(
        f'<a href="{image_path}"><img src="{image_path}"></a>', encoding="utf-8"
    )

    output = module.publish_task_directory(source, destination)

    assert output == destination / "index.html"
    asset = destination / "assets/pour-candidate-overview.png"
    assert asset.read_bytes() == b"candidate-image"
    html = output.read_text(encoding="utf-8")
    assert image_path not in html
    assert html.count("assets/pour-candidate-overview.png") == 2
