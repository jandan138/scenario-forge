"""Build a relocatable alias USD and deterministic ZIP for one liquid start."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import zipfile
from typing import Any, Mapping

from scenario_forge.adapters.liquid_autofill import LiquidAutofillProducerHandoff


@dataclass(frozen=True)
class LiquidAliasPackage:
    alias_usd: Path
    dependencies: Path
    zip_path: Path
    manifest: Path


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON mapping: {path}")
    return value


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _tree_sha(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _safe_relative(root: Path, value: object, label: str) -> Path:
    relative = Path(str(value))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label} must be package-relative")
    resolved = root / relative
    if not resolved.is_file():
        raise ValueError(f"missing {label}: {resolved}")
    return resolved


def _copy_producer(producer: LiquidAutofillProducerHandoff, destination: Path) -> None:
    destination.mkdir(parents=True)
    shutil.copy2(producer.overlay_usd, destination / "producer_overlay.usda")
    shutil.copy2(producer.analysis_path, destination / "analysis.json")
    shutil.copy2(producer.recipe_path, destination / "recipe.json")
    shutil.copy2(producer.manifest_path, destination / "producer_manifest.json")
    if (producer.root / "evidence").is_dir():
        shutil.copytree(
            producer.root / "evidence",
            destination / "evidence",
            ignore=shutil.ignore_patterns("fixed_container_fixture_*.usda"),
        )


def _reject_absolute_usd_dependencies(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".usd", ".usda"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "@/" in text or "@file:" in text:
            raise ValueError(f"package contains an absolute USD dependency: {path}")


def _write_checksums(alias: Path, dependencies: Path) -> Path:
    destination = dependencies / "checksums.sha256"
    records = []
    files = [alias, *sorted(item for item in dependencies.rglob("*") if item.is_file())]
    for path in files:
        if path == destination:
            continue
        base = alias.parent
        records.append(f"{_sha(path)}  {path.relative_to(base).as_posix()}")
    destination.write_text("\n".join(records) + "\n", encoding="utf-8")
    return destination


def _write_zip(alias: Path, dependencies: Path, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in [alias, *sorted(item for item in dependencies.rglob("*") if item.is_file())]:
            info = zipfile.ZipInfo(path.relative_to(alias.parent).as_posix())
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    temporary.replace(destination)


def build_liquid_alias_package(
    *,
    source_scene: Path,
    producer: LiquidAutofillProducerHandoff,
    closure_dir: Path,
    output_dir: Path,
    container_slug: str,
    fill: float,
    integration_evidence: Path | None,
) -> LiquidAliasPackage:
    closure = Path(closure_dir).resolve()
    closure_handoff = _load_json(closure / "usd_closure_handoff.json")
    if (
        closure_handoff.get("schema_version") != "aan.usd_closure_handoff.v1"
        or closure_handoff.get("overall_status") != "pass"
        or closure_handoff.get("blocked_reasons")
    ):
        raise ValueError("source USD dependency closure is not admitted")
    source_root = _safe_relative(
        closure, closure_handoff.get("root_usd"), "localized source root USD"
    )
    fill_id = f"fill{round(float(fill) * 100):02d}"
    base = f"{Path(source_scene).stem}__liquid__{container_slug}__{fill_id}"
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    alias = destination / f"{base}.usd"
    dependencies = destination / f"{base}_deps"
    zip_path = destination / f"{base}.zip"
    if dependencies.exists():
        shutil.rmtree(dependencies)
    if alias.exists():
        alias.unlink()
    if zip_path.exists():
        zip_path.unlink()

    source_destination = dependencies / "source"
    liquid_destination = dependencies / "liquid"
    shutil.copytree(closure, source_destination)
    _copy_producer(producer, liquid_destination)
    source_relative = source_root.relative_to(closure).as_posix()
    alias.write_text(
        "#usda 1.0\n"
        "(\n"
        f'    defaultPrim = "{producer.default_prim}"\n'
        "    subLayers = [\n"
        f"        @{dependencies.name}/liquid/producer_overlay.usda@,\n"
        f"        @{dependencies.name}/source/{source_relative}@,\n"
        "    ]\n"
        ")\n",
        encoding="utf-8",
    )
    integration_status = "not_provided"
    if integration_evidence is not None:
        evidence = _load_json(integration_evidence)
        integration_status = str(evidence.get("overall_status", "blocked"))
        if integration_status != "pass":
            raise ValueError("full-scene eight-second integration did not pass")
        target = dependencies / "evidence" / "full_scene_8s.json"
        target.parent.mkdir(parents=True)
        shutil.copy2(integration_evidence, target)

    manifest_payload = {
        "schema_version": "scenario-forge-liquid-alias-package/v0.1",
        "alias_usd": alias.name,
        "default_prim": producer.default_prim,
        "source_scene_name": Path(source_scene).name,
        "source_scene_sha256": producer.manifest["source_binding"]["scene_sha256"],
        "source_closure_sha256": _tree_sha(source_destination),
        "container_prim": producer.manifest["source_binding"]["container_prim"],
        "fill_profile": producer.manifest["fill_profile"],
        "recipe": producer.manifest["recipe"],
        "producer_qualification": producer.manifest["qualification"],
        "validation_fixture": producer.manifest.get("validation_fixture"),
        "collision_profile": producer.manifest.get("collision_profile"),
        "full_scene_integration_8s": integration_status,
        "claim": "qualified_gpu_pbd_loaded_start",
        "license_policy": "internal_only",
        "robot_policy_success": False,
        "liquid_transfer_success": False,
        "metric_enabled": False,
        "benchmark_success": False,
        "claim_boundary": (
            "Qualified loaded-start liquid only; a kinematic container is evidence-only "
            "when declared, while the delivered source rigid body remains dynamic. No robot, "
            "pour, metric, or benchmark claim."
        ),
    }
    manifest_path = dependencies / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (dependencies / "README_CN.md").write_text(
        "# GPU-PBD 初始液体场景\n\n"
        f"在 Isaac Sim 4.1 中打开 `../{alias.name}`。必须保留 `{dependencies.name}/` 目录。\n\n"
        f"- 容器：`{manifest_payload['container_prim']}`\n"
        f"- 目标液位：{float(fill):.0%}（稳定后 live `points` q95 高度）\n"
        "- 配方：Task 02 r10.3 blue GPU-PBD\n"
        "- 独立动态容器的 kinematic 设置仅存在于验证 fixture；交付刚体保持 dynamic。\n"
        "- 边界：不包含机器人、倾倒成功、metric 或 benchmark 结论。\n",
        encoding="utf-8",
    )
    _reject_absolute_usd_dependencies(dependencies)
    _write_checksums(alias, dependencies)
    _write_zip(alias, dependencies, zip_path)
    return LiquidAliasPackage(
        alias_usd=alias,
        dependencies=dependencies,
        zip_path=zip_path,
        manifest=manifest_path,
    )
