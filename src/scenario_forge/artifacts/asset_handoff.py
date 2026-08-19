"""Build review handoffs from already-admitted external asset packages."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import zipfile


@dataclass(frozen=True)
class AssetHandoffArchive:
    root: Path
    zip_path: Path
    asset_ids: tuple[str, ...]


def build_asset_handoff_archive(
    *, archive_id: str, packages: list[Path], output_dir: Path
) -> AssetHandoffArchive:
    """Copy independent admitted packages and create a deterministic ZIP."""

    if not archive_id or not packages:
        raise ValueError("archive_id and packages are required")
    root = output_dir / archive_id
    if root.exists():
        shutil.rmtree(root)
    packages_root = root / "packages"
    packages_root.mkdir(parents=True)
    records: list[dict[str, object]] = []
    asset_ids: list[str] = []
    for source in packages:
        source = Path(source).resolve()
        manifest_path = source / "evidence/manifest.json"
        audit_path = source / "evidence/visual_material_only_audit.json"
        if not manifest_path.is_file():
            raise ValueError(f"asset package lacks admission evidence: {source}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        visual = manifest.get("visual_material_profile", {})
        if (
            manifest.get("overall_status") != "pass"
            or manifest.get("blocked_reasons")
            or manifest.get("runtime_evidence", {}).get("status") != "pass"
        ):
            raise ValueError(f"asset package is not admitted for asset handoff: {source}")
        if (
            visual.get("status") == "pass"
            and visual.get("schema_version") == "aan.visual_material_profile.v2"
        ):
            if not audit_path.is_file():
                raise ValueError(f"asset package lacks admission evidence: {source}")
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if audit.get("status") != "pass":
                raise ValueError(
                    f"asset package visual material-only audit did not pass: {source}"
                )
            visual_admission_mode = "visual_material_override"
            visual_evidence = (
                f"packages/{source.name}/evidence/visual_material_only_audit.json"
            )
        elif (
            visual.get("status") == "not_requested"
            and manifest.get("visual_preservation_fingerprint", {}).get("status")
            == "pass"
        ):
            visual_admission_mode = "original_material_visual_preservation"
            visual_evidence = (
                f"packages/{source.name}/evidence/manifest.json"
                "#visual_preservation_fingerprint"
            )
        else:
            raise ValueError(f"asset package has no admitted visual evidence: {source}")
        asset_id = str(manifest["asset_id"])
        if asset_id in asset_ids:
            raise ValueError(f"duplicate asset_id: {asset_id}")
        asset_ids.append(asset_id)
        destination = packages_root / source.name
        shutil.copytree(source, destination)
        _reject_absolute_usd_dependencies(destination)
        entrypoints = manifest["entrypoints"]
        root_usd = str(entrypoints["root_usd"])
        records.append(
            {
                "asset_id": asset_id,
                "package_id": manifest["package_id"],
                "directory": f"packages/{source.name}",
                "open_usd": f"packages/{source.name}/{root_usd}",
                "root_prim": entrypoints["asset_entry_prim"],
                "manifest": f"packages/{source.name}/evidence/manifest.json",
                "visual_admission_mode": visual_admission_mode,
                "visual_evidence": visual_evidence,
            }
        )
    payload = {
        "schema_version": "scenario-forge-asset-handoff/v0.2",
        "archive_id": archive_id,
        "asset_count": len(records),
        "assets": records,
        "task_packages_modified": False,
        "claim_boundary": (
            "Independently admitted visual-material asset packages only; no task package "
            "upgrade, robot-policy, liquid-transfer, or benchmark-success claim."
        ),
    }
    (root / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "README_CN.md").write_text(_readme(records), encoding="utf-8")
    _write_checksums(root)
    zip_path = output_dir / f"{archive_id}.zip"
    _write_zip(root, zip_path)
    return AssetHandoffArchive(root, zip_path, tuple(asset_ids))


def _reject_absolute_usd_dependencies(package: Path) -> None:
    for usd in list(package.rglob("*.usd")) + list(package.rglob("*.usda")):
        text = usd.read_text(encoding="utf-8", errors="ignore")
        if "@/" in text or "@file:" in text:
            raise ValueError(f"package USD contains an absolute runtime dependency: {usd}")


def _readme(records: list[dict[str, object]]) -> str:
    lines = [
        "# 玻璃资产交付",
        "",
        "每个 `packages/<name>/` 都是独立、自包含的 ConvertAsset package。",
        "在 Isaac Sim 4.1 中打开该目录的 `asset.usd`，入口 prim 见下表。不要只拷贝 USD。",
        "",
        "| 资产 | 打开 | 入口 prim |",
        "| --- | --- | --- |",
    ]
    for item in records:
        lines.append(f"| `{item['asset_id']}` | `{item['open_usd']}` | `{item['root_prim']}` |")
    lines.extend(
        [
            "",
        "本包没有升级任何任务 USD。每件资产要么通过显式材质覆盖审计，要么通过原材质视觉保真审计；",
            "不声明机器人策略、液体倾倒或 benchmark 成功。",
            "",
        ]
    )
    return "\n".join(lines)


def _write_checksums(root: Path) -> None:
    files = [p for p in sorted(root.rglob("*")) if p.is_file() and p.name != "SHA256SUMS"]
    lines = [f"{sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}" for p in files]
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_zip(root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                relative = (Path(root.name) / path.relative_to(root)).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(2026, 8, 18, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
