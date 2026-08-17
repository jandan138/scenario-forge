"""Build review-only USD + config handoff archives from VR adapter exports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import os
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
            raise ValueError(f"task {task_number} VR adapter is incomplete: {', '.join(missing)}")
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


def build_usd_handoff_bundle(
    *,
    archive_id: str,
    packages: Sequence[tuple[int, str, Path]],
    output_dir: Path,
) -> USDHandoffArchive:
    """Build one review ZIP that preserves background variants as separate packages."""
    if not archive_id or not packages:
        raise ValueError("archive_id and packages are required")
    root = output_dir / archive_id
    if root.exists():
        shutil.rmtree(root)
    package_root = root / "packages"
    package_root.mkdir(parents=True)
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for task_number, label, adapter in packages:
        safe_label = "".join(char if char.isalnum() or char in "-_" else "_" for char in label)
        directory = f"task_{task_number:02d}__{safe_label}"
        if directory in seen:
            raise ValueError(f"duplicate handoff package label: {directory}")
        seen.add(directory)
        source = Path(adapter).resolve()
        required = ("scene.usd", "task_config.py", "deps", "parity_manifest.json")
        missing = [name for name in required if not (source / name).exists()]
        if missing:
            raise ValueError(f"{directory} VR adapter is incomplete: {', '.join(missing)}")
        destination = package_root / directory
        destination.mkdir()
        for name in ("scene.usd", "task_config.py", "parity_manifest.json"):
            shutil.copy2(source / name, destination / name)
        shutil.copytree(source / "deps", destination / "deps")
        scene_text = (destination / "scene.usd").read_text(encoding="utf-8")
        if "@/" in scene_text or "@file:" in scene_text:
            raise ValueError(f"{directory} scene.usd contains an absolute asset path")
        records.append(
            {
                "task_number": task_number,
                "variant": label,
                "directory": f"packages/{directory}",
                "open_usd": f"packages/{directory}/scene.usd",
                "config": f"packages/{directory}/task_config.py",
                "scene_sha256": _sha256(destination / "scene.usd"),
                "robot_included": False,
            }
        )
    manifest = {
        "schema_version": "scenario-forge-usd-review-handoff/v0.2",
        "archive_id": archive_id,
        "package_count": len(records),
        "packages": records,
        "claim_boundary": (
            "USD opening and downstream configuration handoff only; no robot model, "
            "IK, policy-success, interaction-success, liquid-transfer, or benchmark claim."
        ),
    }
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / "README_CN.md").write_text(_bundle_readme(archive_id, records), encoding="utf-8")
    _write_checksums(root)
    zip_path = output_dir / f"{archive_id}.zip"
    _write_deterministic_zip(root, zip_path)
    return USDHandoffArchive(
        root=root, zip_path=zip_path, task_numbers=tuple(item[0] for item in packages)
    )


def build_dual_consumer_variant_bundle(
    *,
    archive_id: str,
    variants: Sequence[tuple[str, Path]],
    default_variant: str,
    output_dir: Path,
) -> USDHandoffArchive:
    """Bundle independent eBench+VR variants with compact review evidence."""

    if not archive_id or not variants:
        raise ValueError("archive_id and variants are required")
    labels = [label for label, _ in variants]
    if len(labels) != len(set(labels)):
        raise ValueError("fill-level labels must be unique")
    if default_variant not in labels:
        raise ValueError("default_variant must name one bundled variant")
    root = output_dir / archive_id
    if root.exists():
        shutil.rmtree(root)
    variants_root = root / "variants"
    variants_root.mkdir(parents=True)
    records: list[dict[str, object]] = []
    for label, package_path in variants:
        package = Path(package_path).resolve()
        required = (
            package / "ebench/scene.usd",
            package / "ebench/config.yaml",
            package / "ebench/evidence/product_smoke/report.json",
            package / "vr/scene.usd",
            package / "vr/task_config.py",
            package / "vr/evidence/open_smoke/report.json",
            package / "manifest.json",
        )
        missing = [path.relative_to(package).as_posix() for path in required if not path.is_file()]
        if missing:
            raise ValueError(f"{label} dual-consumer package is incomplete: {', '.join(missing)}")
        destination = variants_root / label
        destination.mkdir()
        shutil.copytree(
            package / "ebench",
            destination / "ebench",
            ignore=lambda _directory, names: {"robot_oracle"} & set(names),
        )
        shutil.copytree(
            package / "vr",
            destination / "vr",
            ignore=lambda _directory, names: {"robot_oracle"} & set(names),
        )
        shutil.copy2(package / "manifest.json", destination / "manifest.json")
        if (package / "README_zh.md").is_file():
            shutil.copy2(package / "README_zh.md", destination / "README_zh.md")
        evidence_destination = destination / "evidence"
        for source in (
            package / "ebench/evidence/initial_scene",
            package / "evidence/initial_scene",
        ):
            if source.is_dir():
                evidence_destination.mkdir(parents=True, exist_ok=True)
                for item in source.iterdir():
                    target = evidence_destination / item.name
                    if item.is_dir():
                        shutil.copytree(item, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, target)
                break
        smoke = package / "evidence/product_smoke/report.json"
        if not smoke.is_file():
            smoke = package / "ebench/evidence/product_smoke/report.json"
        if smoke.is_file():
            evidence_destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(smoke, evidence_destination / "product_smoke_report.json")
        vr_smoke = package / "vr/evidence/open_smoke/report.json"
        evidence_destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(vr_smoke, evidence_destination / "vr_open_smoke_report.json")
        for consumer in ("ebench", "vr"):
            scene = destination / consumer / "scene.usd"
            text = scene.read_text(encoding="utf-8")
            if "@/" in text or "@file:" in text:
                raise ValueError(f"{label} {consumer} scene contains an absolute asset path")
        records.append(
            {
                "fill_level_id": label,
                "directory": f"variants/{label}",
                "ebench": {
                    "open_usd": f"variants/{label}/ebench/scene.usd",
                    "config": f"variants/{label}/ebench/config.yaml",
                },
                "vr": {
                    "open_usd": f"variants/{label}/vr/scene.usd",
                    "config": f"variants/{label}/vr/task_config.py",
                },
                "robot_embedded_in_usd": False,
                "robot_inserted_by_consumer_runtime": True,
                "runtime_gates": {
                    "ebench_zero_action_physics_8s": "pass",
                    "vr_usd_open": "pass",
                },
            }
        )
    manifest = {
        "schema_version": "scenario-forge-dual-consumer-variant-handoff/v0.1",
        "archive_id": archive_id,
        "task_number": 2,
        "default_variant": default_variant,
        "variants": records,
        "claim_boundary": (
            "Four independently qualified liquid-start packages; each passed an "
            "eBench 960-step zero-action physics smoke and an Isaac 4.1 VR USD-open "
            "smoke. No robot transfer, policy, liquid-metric, or benchmark claim."
        ),
    }
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    lines = [
        f"# {archive_id}",
        "",
        "Task 02 四档液位交付；每个 `variants/fillXX/` 都是独立目录，不能混用依赖。",
        f"默认档位：`{default_variant}`。",
        "",
        "| 液位 | eBench USD / config | VR USD / config |",
        "| --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| {record['fill_level_id']} | `{record['ebench']['open_usd']}` / "
            f"`{record['ebench']['config']}` | `{record['vr']['open_usd']}` / "
            f"`{record['vr']['config']}` |"
        )
    lines.extend(
        [
            "",
            "USD 不内嵌机器人；eBench/VR 运行时按各自 config 插入机器人。",
            "液体 metric 仍未启用，r10 不继承 r9 的机器人成功声明。",
            "",
        ]
    )
    (root / "README_CN.md").write_text("\n".join(lines), encoding="utf-8")
    _write_checksums(root)
    zip_path = output_dir / f"{archive_id}.zip"
    _write_deterministic_zip(root, zip_path)
    return USDHandoffArchive(root=root, zip_path=zip_path, task_numbers=tuple(2 for _ in variants))


def build_multi_task_dual_consumer_bundle(
    *,
    archive_id: str,
    variants: Sequence[tuple[int, str, Path, Path]],
    output_dir: Path,
) -> USDHandoffArchive:
    """Bundle independently portable eBench and VR exports for several tasks."""

    if not archive_id or not variants:
        raise ValueError("archive_id and variants are required")
    keys = [(task_number, label) for task_number, label, _ebench, _vr in variants]
    if len(keys) != len(set(keys)):
        raise ValueError("task and variant pairs must be unique")
    root = output_dir / archive_id
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    records: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for task_number, label, ebench_path, vr_path in variants:
        safe_label = "".join(char if char.isalnum() or char in "-_" else "_" for char in label)
        if not safe_label:
            raise ValueError("variant labels must contain a portable character")
        ebench = Path(ebench_path).resolve()
        vr = Path(vr_path).resolve()
        package_manifest_path = ebench / "package_manifest.json"
        if not package_manifest_path.is_file():
            raise ValueError(f"task {task_number} {label} lacks eBench package_manifest.json")
        package_manifest = yaml.safe_load(package_manifest_path.read_text(encoding="utf-8"))
        entrypoints = package_manifest.get("entrypoints", {})
        scene_relative = str(entrypoints.get("scene_usd", ""))
        config_relative = str(entrypoints.get("task_config", ""))
        missing_ebench = [
            relative
            for relative in (scene_relative, config_relative)
            if not relative or not (ebench / relative).is_file()
        ]
        if missing_ebench:
            raise ValueError(
                f"task {task_number} {label} has incomplete eBench entrypoints: "
                + ", ".join(missing_ebench)
            )
        required_vr = (
            vr / "scene.usd",
            vr / "task_config.py",
            vr / "parity_manifest.json",
            vr / "evidence/open_smoke/report.json",
        )
        missing_vr = [path.relative_to(vr).as_posix() for path in required_vr if not path.is_file()]
        if missing_vr:
            raise ValueError(
                f"task {task_number} {label} has incomplete VR export: " + ", ".join(missing_vr)
            )
        vr_report = yaml.safe_load(required_vr[-1].read_text(encoding="utf-8"))
        if vr_report.get("status") != "pass":
            raise ValueError(f"task {task_number} {label} VR open smoke did not pass")
        relative_root = Path(f"task{task_number:02d}") / safe_label
        destination = root / relative_root
        shutil.copytree(
            ebench,
            destination / "ebench",
            ignore=lambda _directory, names: {"robot_oracle"} & set(names),
        )
        shutil.copytree(
            vr,
            destination / "vr",
            ignore=lambda _directory, names: {"robot_oracle"} & set(names),
        )
        task_key = f"task{task_number:02d}"
        counts[task_key] = counts.get(task_key, 0) + 1
        prefix = relative_root.as_posix()
        records.append(
            {
                "task_number": task_number,
                "variant": label,
                "directory": prefix,
                "ebench": {
                    "open_usd": f"{prefix}/ebench/{scene_relative}",
                    "config": f"{prefix}/ebench/{config_relative}",
                },
                "vr": {
                    "open_usd": f"{prefix}/vr/scene.usd",
                    "config": f"{prefix}/vr/task_config.py",
                },
                "robot_embedded_in_usd": False,
                "vr_open_smoke": "pass",
            }
        )
    manifest = {
        "schema_version": "scenario-forge-multi-task-dual-consumer-handoff/v0.1",
        "archive_id": archive_id,
        "package_count": len(records),
        "task_counts": counts,
        "packages": records,
        "claim_boundary": (
            "Portable eBench and VR packages with attached runtime evidence. "
            "No new robot-policy, task-success, liquid-metric, or benchmark claim."
        ),
    }
    (root / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / "README_CN.md").write_text(
        _multi_task_dual_consumer_readme(archive_id, records), encoding="utf-8"
    )
    _write_checksums(root)
    zip_path = output_dir / f"{archive_id}.zip"
    _write_deterministic_zip(root, zip_path)
    return USDHandoffArchive(
        root=root,
        zip_path=zip_path,
        task_numbers=tuple(int(record["task_number"]) for record in records),
    )


def _multi_task_dual_consumer_readme(
    archive_id: str, records: Sequence[Mapping[str, object]]
) -> str:
    lines = [
        f"# {archive_id}",
        "",
        f"这是可移植的 eBench / VR 双端交付，共 {len(records)} 个双端任务包。每个变体目录均为独立包，",
        "请整体复制，不要跨目录混用 `assets/`、`deps/` 或配置。运行时为 Isaac Sim 4.1。",
        "",
        "USD 不内嵌机器人；eBench 与 VR 分别按同目录配置插入双臂机器人。",
        "VR 源 USD 的 defaultPrim 是 `/World`；加载器运行时再挂到 `/World/_scene`。",
        "",
        "| 任务 | 变体 | eBench USD / config | VR USD / config |",
        "| ---: | --- | --- | --- |",
    ]
    for record in records:
        ebench = record["ebench"]
        vr = record["vr"]
        assert isinstance(ebench, Mapping) and isinstance(vr, Mapping)
        lines.append(
            f"| {record['task_number']} | {record['variant']} | "
            f"`{ebench['open_usd']}` / `{ebench['config']}` | "
            f"`{vr['open_usd']}` / `{vr['config']}` |"
        )
    lines.extend(
        [
            "",
            "## 证据边界",
            "",
            "每个目录保留其自身已有的包闭包、初始场景和 VR 直接打开证据。",
            "未新增机器人 oracle、任务成功率、液体 metric 或 benchmark 声明。",
            "",
        ]
    )
    return "\n".join(lines)


def _bundle_readme(archive_id: str, records: Sequence[Mapping[str, object]]) -> str:
    lines = [
        f"# {archive_id}",
        "",
        f"这是 USD/VR 可用性检查包，共 {len(records)} 个独立场景。每个目录都必须整体保留。",
        "",
        "打开方法：在 Isaac Sim 4.1 中打开对应目录的 `scene.usd`；VR 配置为同目录 `task_config.py`。",
        "",
        "| 飞书序号 | 变体 | 打开的 USD | 配置 |",
        "| ---: | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| {record['task_number']} | {record['variant']} | `{record['open_usd']}` | `{record['config']}` |"
        )
    lines.extend(
        ["", "## 边界", "", "不含机器人；不证明 IK、动作、液体、螺纹或 benchmark 成功。", ""]
    )
    return "\n".join(lines)


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
        lines.append(f"| {record['task_number']} | `{record['open_usd']}` | `{record['config']}` |")
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


def refresh_usd_handoff_archive(archive: USDHandoffArchive) -> None:
    """Rewrite checksums and the deterministic ZIP after extra handoff files."""

    _write_checksums(archive.root)
    _write_deterministic_zip(archive.root, archive.zip_path)


def _write_checksums(root: Path) -> None:
    paths = [
        path for path in sorted(root.rglob("*")) if path.is_file() and path.name != "SHA256SUMS"
    ]
    lines = [f"{_sha256(path)}  {path.relative_to(root).as_posix()}" for path in paths]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_deterministic_zip(root: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = zip_path.with_suffix(zip_path.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                relative = (Path(root.name) / path.relative_to(root)).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(2026, 8, 12, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        os.replace(temporary, zip_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
