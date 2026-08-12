"""Build review-only USD + config handoff archives from VR adapter exports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import shutil
import zipfile

import yaml


@dataclass(frozen=True)
class USDHandoffArchive:
    root: Path
    zip_path: Path
    task_numbers: tuple[int, ...]


def build_usd_handoff_archive(
    *,
    archive_id: str,
    task_adapters: Mapping[int, Path],
    output_dir: Path,
) -> USDHandoffArchive:
    """Copy self-contained VR scenes without robots and write a deterministic ZIP."""

    if not archive_id or not task_adapters:
        raise ValueError("archive_id and task_adapters are required")
    root = output_dir / archive_id
    if root.exists():
        shutil.rmtree(root)
    tasks_root = root / "tasks"
    tasks_root.mkdir(parents=True)
    records: list[dict[str, object]] = []
    for task_number, adapter in sorted(task_adapters.items()):
        source = Path(adapter).resolve()
        required = ("scene.usd", "task_config.py", "deps", "parity_manifest.json")
        missing = [name for name in required if not (source / name).exists()]
        if missing:
            raise ValueError(
                f"task {task_number} VR adapter is incomplete: {', '.join(missing)}"
            )
        destination = tasks_root / f"task_{task_number:02d}"
        destination.mkdir()
        shutil.copy2(source / "scene.usd", destination / "scene.usd")
        shutil.copy2(source / "task_config.py", destination / "task_config.py")
        shutil.copy2(source / "parity_manifest.json", destination / "parity_manifest.json")
        shutil.copytree(source / "deps", destination / "deps")
        scene_text = (destination / "scene.usd").read_text(encoding="utf-8")
        if "@/" in scene_text or "@file:" in scene_text:
            raise ValueError(f"task {task_number} scene.usd contains an absolute asset path")
        records.append(
            {
                "task_number": task_number,
                "directory": f"tasks/task_{task_number:02d}",
                "open_usd": f"tasks/task_{task_number:02d}/scene.usd",
                "config": f"tasks/task_{task_number:02d}/task_config.py",
                "scene_sha256": _sha256(destination / "scene.usd"),
                "robot_included": False,
            }
        )
    manifest = {
        "schema_version": "scenario-forge-usd-review-handoff/v0.1",
        "archive_id": archive_id,
        "tasks": records,
        "claim_boundary": (
            "USD opening and downstream configuration handoff only; no robot model, "
            "policy-success, interaction-success, liquid-transfer, or benchmark claim."
        ),
    }
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (root / "README_CN.md").write_text(_readme(archive_id, records), encoding="utf-8")
    _write_checksums(root)
    zip_path = output_dir / f"{archive_id}.zip"
    _write_deterministic_zip(root, zip_path)
    return USDHandoffArchive(
        root=root,
        zip_path=zip_path,
        task_numbers=tuple(sorted(task_adapters)),
    )


def _readme(archive_id: str, records: Sequence[Mapping[str, object]]) -> str:
    lines = [
        f"# {archive_id}",
        "",
        "这是给 USD/VR 接入同事检查的场景交付，不含机器人。",
        "",
        "使用方法：进入对应 `tasks/task_XX/`，在 Isaac Sim 4.1 直接打开 "
        "`scene.usd`；同目录 `task_config.py` 是需要合入 VR 任务表的配置片段。",
        "请保持 `deps/` 与 `scene.usd` 的相对位置不变。",
        "",
        "| 飞书序号 | 打开的 USD | 配置 |",
        "| ---: | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| {record['task_number']} | `{record['open_usd']}` | `{record['config']}` |"
        )
    lines.extend(
        [
            "",
            "## 边界",
            "",
            "这份交付证明文件闭包与配置映射，不证明机器人能完成动作或 benchmark 成功。",
            "",
        ]
    )
    return "\n".join(lines)


def _write_checksums(root: Path) -> None:
    paths = [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS"
    ]
    lines = [f"{_sha256(path)}  {path.relative_to(root).as_posix()}" for path in paths]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_deterministic_zip(root: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = (Path(root.name) / path.relative_to(root)).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
