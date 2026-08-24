"""Orchestrate ConvertAsset-owned simple-SDF and multi-set liquid production."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from typing import Sequence
import zipfile

from scenario_forge.adapters.simple_sdf_liquid import (
    MultiLiquidHandoff,
    SimpleSdfLiquidCommandPlan,
    SimpleSdfLiquidHandoffError,
    load_multi_liquid_handoff,
)


class SimpleSdfLiquidGenerationError(RuntimeError):
    """Raised when the producer route cannot be promoted safely."""


@dataclass(frozen=True)
class SimpleSdfProposalResult:
    proposal: Path


@dataclass(frozen=True)
class SimpleSdfPackageResult:
    root: Path
    manifest: Path
    zip_path: Path


@dataclass(frozen=True)
class MultiLiquidPackageResult:
    handoff: MultiLiquidHandoff
    zip_path: Path


def _root(value: Path | None) -> Path:
    raw = str(value) if value is not None else os.environ.get("SCENARIO_FORGE_CONVERTASSET_ROOT", "")
    if not raw:
        raise SimpleSdfLiquidGenerationError(
            "set --convertasset-root or SCENARIO_FORGE_CONVERTASSET_ROOT"
        )
    root = Path(raw).expanduser().resolve()
    if not (root / "main.py").is_file() or not (root / "scripts/isaac_python.sh").is_file():
        raise SimpleSdfLiquidGenerationError(f"invalid ConvertAsset checkout: {root}")
    return root


def _isaac(value: Path | None) -> Path | None:
    raw = str(value) if value is not None else os.environ.get("EEOS_ISAACSIM41_PYTHON", "")
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise SimpleSdfLiquidGenerationError(f"Isaac Sim Python does not exist: {path}")
    return path


def _run(command: Sequence[str], log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        stream.write("$ " + " ".join(command) + "\n\n")
        completed = subprocess.run(
            command, text=True, stdout=stream, stderr=subprocess.STDOUT, check=False
        )
    if completed.returncode:
        raise SimpleSdfLiquidGenerationError(
            f"producer command failed with {completed.returncode}; see {log}"
        )


def _zip(root: Path) -> Path:
    destination = root.with_suffix(".zip")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(str(Path(root.name) / path.relative_to(root)))
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return destination


def propose_simple_sdf(
    *, source: Path, container: str, visual_mesh: str, particle_scale: str,
    output: Path, convertasset_root: Path | None = None,
) -> SimpleSdfProposalResult:
    destination = Path(output).expanduser().resolve()
    plan = SimpleSdfLiquidCommandPlan(_root(convertasset_root))
    _run(
        plan.collision_propose_command(
            Path(source).expanduser().resolve(), container, visual_mesh,
            particle_scale, destination,
        ),
        destination.parent / f".{destination.name}.propose.log",
    )
    proposal = destination / "proposal.yaml"
    if not proposal.is_file():
        raise SimpleSdfLiquidGenerationError("ConvertAsset did not produce proposal.yaml")
    return SimpleSdfProposalResult(proposal)


def build_simple_sdf(
    *, spec: Path, output: Path, convertasset_root: Path | None = None,
) -> SimpleSdfPackageResult:
    destination = Path(output).expanduser().resolve()
    working = destination.parent / f".{destination.name}.working"
    diagnostics = destination.parent / f"{destination.name}_diagnostics"
    for path in (working, diagnostics):
        if path.exists():
            shutil.rmtree(path)
    plan = SimpleSdfLiquidCommandPlan(_root(convertasset_root))
    try:
        _run(
            plan.collision_build_command(Path(spec).expanduser().resolve(), working),
            working.parent / f".{working.name}.log",
        )
        manifest = working / "manifest.json"
        if not manifest.is_file():
            raise SimpleSdfLiquidGenerationError("producer collision manifest is missing")
        if destination.exists():
            raise SimpleSdfLiquidGenerationError(f"refusing to overwrite: {destination}")
        working.replace(destination)
    except Exception as error:
        if working.exists():
            working.replace(diagnostics)
        raise SimpleSdfLiquidGenerationError(
            f"simple-SDF package was not promoted: {error}; diagnostics: {diagnostics}"
        ) from error
    return SimpleSdfPackageResult(destination, destination / "manifest.json", _zip(destination))


def add_sampled_liquid(
    *, spec: Path, output: Path, convertasset_root: Path | None = None,
    isaac_python: Path | None = None,
) -> MultiLiquidPackageResult:
    destination = Path(output).expanduser().resolve()
    working = destination.parent / f".{destination.name}.working"
    diagnostics = destination.parent / f"{destination.name}_diagnostics"
    for path in (working, diagnostics):
        if path.exists():
            shutil.rmtree(path)
    plan = SimpleSdfLiquidCommandPlan(_root(convertasset_root), _isaac(isaac_python))
    try:
        _run(
            plan.liquid_command(Path(spec).expanduser().resolve(), working),
            working.parent / f".{working.name}.log",
        )
        handoff = load_multi_liquid_handoff(working)
        if destination.exists():
            raise SimpleSdfLiquidGenerationError(f"refusing to overwrite: {destination}")
        working.replace(destination)
        handoff = load_multi_liquid_handoff(destination)
    except (OSError, SimpleSdfLiquidGenerationError, SimpleSdfLiquidHandoffError) as error:
        if working.exists():
            working.replace(diagnostics)
        raise SimpleSdfLiquidGenerationError(
            f"multi-liquid package was not promoted: {error}; diagnostics: {diagnostics}"
        ) from error
    return MultiLiquidPackageResult(handoff, _zip(destination))


def publish_edited_liquid(
    *, package: Path, output: Path, convertasset_root: Path | None = None,
    isaac_python: Path | None = None,
) -> MultiLiquidPackageResult:
    """Delegate editable-sampler freezing and validation to ConvertAsset."""
    source = Path(package).expanduser().resolve()
    destination = Path(output).expanduser().resolve()
    working = destination.parent / f".{destination.name}.working"
    diagnostics = destination.parent / f"{destination.name}_diagnostics"
    for path in (working, diagnostics):
        if path.exists():
            shutil.rmtree(path)
    plan = SimpleSdfLiquidCommandPlan(_root(convertasset_root), _isaac(isaac_python))
    try:
        _run(
            plan.freeze_command(source, working),
            working.parent / f".{working.name}.log",
        )
        handoff = load_multi_liquid_handoff(working)
        if destination.exists():
            raise SimpleSdfLiquidGenerationError(f"refusing to overwrite: {destination}")
        working.replace(destination)
        handoff = load_multi_liquid_handoff(destination)
    except (OSError, SimpleSdfLiquidGenerationError, SimpleSdfLiquidHandoffError) as error:
        if working.exists():
            working.replace(diagnostics)
        raise SimpleSdfLiquidGenerationError(
            f"edited liquid package was not promoted: {error}; diagnostics: {diagnostics}"
        ) from error
    return MultiLiquidPackageResult(handoff, _zip(destination))
