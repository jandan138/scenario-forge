#!/usr/bin/env python3
"""Publish a generated Scientific Workbench directory into the docs Pages tree."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

import yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Generated directory/ path")
    parser.add_argument("--out", type=Path, required=True, help="Published docs/task-directory path")
    return parser


def publish_task_directory(source: str | Path, destination: str | Path) -> Path:
    """Copy public render evidence and rewrite the directory HTML to local assets."""

    source_dir = Path(source).resolve()
    destination_dir = Path(destination).resolve()
    html_path = source_dir / "index.html"
    directory_path = source_dir / "task_directory.yaml"
    if not html_path.is_file() or not directory_path.is_file():
        raise ValueError("source must contain index.html and task_directory.yaml")
    data = _mapping(yaml.safe_load(directory_path.read_text(encoding="utf-8")), "directory")
    html = html_path.read_text(encoding="utf-8")
    asset_dir = destination_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for task in _mappings(data.get("tasks"), "directory.tasks"):
        task_id = _required_string(task, "task_id", "directory task")
        for release_kind in ("candidate", "latest"):
            evidence = task.get(f"{release_kind}_evidence")
            if not isinstance(evidence, Mapping):
                continue
            html = _publish_evidence_images(
                html,
                evidence=evidence,
                source_dir=source_dir,
                destination_dir=destination_dir,
                public_stem=f"{task_id}-{release_kind}",
            )
        releases = task.get("releases", [])
        if not isinstance(releases, list):
            raise ValueError("directory task.releases must be a list")
        for index, release in enumerate(releases, start=1):
            if not isinstance(release, Mapping):
                raise ValueError("directory task.releases must contain mappings")
            evidence = release.get("evidence")
            if not isinstance(evidence, Mapping):
                continue
            html = _publish_evidence_images(
                html,
                evidence=evidence,
                source_dir=source_dir,
                destination_dir=destination_dir,
                public_stem=f"{task_id}-release-{index:02d}",
            )
    destination_dir.mkdir(parents=True, exist_ok=True)
    output = destination_dir / "index.html"
    output.write_text(html, encoding="utf-8")
    return output


def _publish_evidence_images(
    html: str,
    *,
    evidence: Mapping[str, object],
    source_dir: Path,
    destination_dir: Path,
    public_stem: str,
) -> str:
    for key, suffix in (("card_image", "card"), ("overview_image", "overview")):
        relative = evidence.get(key)
        if not isinstance(relative, str) or not relative:
            continue
        image = (source_dir / relative).resolve()
        if not image.is_file():
            raise ValueError(f"{key} does not exist: {relative}")
        public_relative = Path("assets") / f"{public_stem}-{suffix}{image.suffix}"
        shutil.copy2(image, destination_dir / public_relative)
        html = html.replace(relative, public_relative.as_posix())
    return html


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = publish_task_directory(args.source, args.out)
    print(f"Published task directory: {output}")
    return 0


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _mappings(value: object, label: str) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ValueError(f"{label} must be a list of mappings")
    return list(value)


def _required_string(data: Mapping[str, object], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}.{key} must be a non-empty string")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
