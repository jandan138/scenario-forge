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


def test_publish_task_directory_copies_all_background_variant_overviews(
    tmp_path: Path,
) -> None:
    module = _script_module()
    source = tmp_path / "build/directory"
    destination = tmp_path / "docs/task-directory"
    source.mkdir(parents=True)
    releases = []
    links = []
    for index in range(2):
        image = tmp_path / "build" / f"variant-{index}.png"
        image.write_bytes(f"variant-{index}".encode())
        relative = f"../variant-{index}.png"
        releases.append(
            {
                "release_id": f"pour.v{index}",
                "evidence": {"overview_image": relative},
            }
        )
        links.append(f'<a href="{relative}">variant {index}</a>')
    (source / "task_directory.yaml").write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "task_id": "pour",
                        "candidate_evidence": None,
                        "latest_evidence": None,
                        "releases": releases,
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source / "index.html").write_text("".join(links), encoding="utf-8")

    output = module.publish_task_directory(source, destination)

    assert (destination / "assets/pour-release-01-overview.png").read_bytes() == b"variant-0"
    assert (destination / "assets/pour-release-02-overview.png").read_bytes() == b"variant-1"
    html = output.read_text(encoding="utf-8")
    assert "../variant-0.png" not in html
    assert "../variant-1.png" not in html


def test_publish_task_directory_keeps_card_and_overview_images_distinct(
    tmp_path: Path,
) -> None:
    module = _script_module()
    source = tmp_path / "build/directory"
    destination = tmp_path / "docs/task-directory"
    source.mkdir(parents=True)
    card = tmp_path / "build/task-card.png"
    overview = tmp_path / "build/task-overview.png"
    card.write_bytes(b"card-image")
    overview.write_bytes(b"overview-image")
    card_relative = "../task-card.png"
    overview_relative = "../task-overview.png"
    (source / "task_directory.yaml").write_text(
        yaml.safe_dump(
            {
                "tasks": [
                    {
                        "task_id": "stir",
                        "candidate_evidence": None,
                        "latest_evidence": None,
                        "releases": [
                            {
                                "release_id": "stir.v10_1",
                                "evidence": {
                                    "card_image": card_relative,
                                    "overview_image": overview_relative,
                                },
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source / "index.html").write_text(
        f'<a href="{overview_relative}"><img src="{card_relative}"></a>',
        encoding="utf-8",
    )

    output = module.publish_task_directory(source, destination)

    assert (destination / "assets/stir-release-01-card.png").read_bytes() == b"card-image"
    assert (destination / "assets/stir-release-01-overview.png").read_bytes() == (
        b"overview-image"
    )
    html = output.read_text(encoding="utf-8")
    assert 'href="assets/stir-release-01-overview.png"' in html
    assert 'src="assets/stir-release-01-card.png"' in html
