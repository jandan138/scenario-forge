"""Orchestrate ConvertAsset-owned fluid-interaction asset production."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from typing import Sequence
import zipfile

import yaml

from scenario_forge.adapters.fluid_asset import (
    FluidAssetCommandPlan,
    FluidAssetHandoff,
    FluidAssetHandoffError,
    load_fluid_asset_handoff,
)


class FluidAssetGenerationError(RuntimeError):
    """Raised when a fluid asset workflow cannot safely progress."""


@dataclass(frozen=True)
class FluidAssetBatchItem:
    item_id: str
    source: Path
    prim: str


@dataclass(frozen=True)
class FluidAssetPrepareResult:
    review_root: Path
    proposal: Path


@dataclass(frozen=True)
class FluidAssetQualificationBatchItem:
    item_id: str
    proposal: Path


@dataclass(frozen=True)
class FluidAssetQualifyResult:
    handoff: FluidAssetHandoff
    zip_path: Path


def _convertasset_root(value: Path | None) -> Path:
    raw = str(value) if value is not None else os.environ.get(
        "SCENARIO_FORGE_CONVERTASSET_ROOT", ""
    )
    if not raw:
        raise FluidAssetGenerationError(
            "set --convertasset-root or SCENARIO_FORGE_CONVERTASSET_ROOT"
        )
    root = Path(raw).expanduser().resolve()
    if not (root / "main.py").is_file() or not (root / "scripts/isaac_python.sh").is_file():
        raise FluidAssetGenerationError(f"invalid ConvertAsset checkout: {root}")
    return root


def _isaac_python(value: Path | None) -> Path | None:
    raw = str(value) if value is not None else os.environ.get(
        "EEOS_ISAACSIM41_PYTHON", ""
    )
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise FluidAssetGenerationError(f"Isaac Sim Python does not exist: {path}")
    return path


def _run(command: Sequence[str], log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        stream.write("$ " + " ".join(command) + "\n\n")
        completed = subprocess.run(
            command, text=True, stdout=stream, stderr=subprocess.STDOUT, check=False
        )
    if completed.returncode:
        raise FluidAssetGenerationError(
            f"command failed with exit code {completed.returncode}; see {log}"
        )


def prepare_fluid_asset(
    *,
    source: Path,
    prim: str,
    output: Path,
    convertasset_root: Path | None = None,
    isaac_python: Path | None = None,
) -> FluidAssetPrepareResult:
    source = Path(source).expanduser().resolve()
    if not source.is_file():
        raise FluidAssetGenerationError(f"source USD does not exist: {source}")
    destination = Path(output).expanduser().resolve()
    plan = FluidAssetCommandPlan(
        _convertasset_root(convertasset_root), _isaac_python(isaac_python)
    )
    _run(plan.prepare_command(source, prim, destination), destination.parent / f".{destination.name}.prepare.log")
    proposal = destination / "proposal.yaml"
    if not proposal.is_file():
        raise FluidAssetGenerationError("ConvertAsset did not produce proposal.yaml")
    return FluidAssetPrepareResult(destination, proposal)


def _zip_directory(root: Path) -> Path:
    zip_path = root.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(str(Path(root.name) / path.relative_to(root)))
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return zip_path


def qualify_fluid_asset(
    *,
    proposal: Path,
    output: Path,
    convertasset_root: Path | None = None,
    isaac_python: Path | None = None,
) -> FluidAssetQualifyResult:
    proposal = Path(proposal).expanduser().resolve()
    destination = Path(output).expanduser().resolve()
    working = destination.parent / f".{destination.name}.working"
    diagnostics = destination.parent / f"{destination.name}_diagnostics"
    for path in (working, diagnostics):
        if path.exists():
            shutil.rmtree(path)
    plan = FluidAssetCommandPlan(
        _convertasset_root(convertasset_root), _isaac_python(isaac_python)
    )
    try:
        _run(plan.qualify_command(proposal, working), working.parent / f".{working.name}.log")
        handoff = load_fluid_asset_handoff(working)
    except (OSError, FluidAssetGenerationError, FluidAssetHandoffError) as error:
        if working.exists():
            working.replace(diagnostics)
        raise FluidAssetGenerationError(
            f"fluid asset was not promoted: {error}; diagnostics: {diagnostics}"
        ) from error
    if destination.exists():
        raise FluidAssetGenerationError(f"refusing to overwrite package: {destination}")
    working.replace(destination)
    handoff = load_fluid_asset_handoff(destination)
    return FluidAssetQualifyResult(handoff, _zip_directory(destination))


def derive_fluid_asset_partitions(
    *,
    proposal: Path,
    output: Path,
    convertasset_root: Path | None = None,
    isaac_python: Path | None = None,
) -> FluidAssetPrepareResult:
    destination = Path(output).expanduser().resolve()
    plan = FluidAssetCommandPlan(
        _convertasset_root(convertasset_root), _isaac_python(isaac_python)
    )
    _run(
        plan.derive_command(Path(proposal).expanduser().resolve(), destination),
        destination.parent / f".{destination.name}.derive.log",
    )
    derived = destination / "proposal.yaml"
    if not derived.is_file():
        raise FluidAssetGenerationError("ConvertAsset did not produce derived proposal.yaml")
    return FluidAssetPrepareResult(destination, derived)


def load_batch_request(path: Path) -> tuple[FluidAssetBatchItem, ...]:
    request_path = Path(path).resolve()
    try:
        raw = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise FluidAssetGenerationError(f"cannot read batch request: {request_path}") from error
    if not isinstance(raw, dict) or raw.get("schema_version") != "scenario-forge-fluid-asset-batch/v0.1":
        raise FluidAssetGenerationError("unsupported fluid asset batch schema")
    values = raw.get("items")
    if not isinstance(values, list) or not values:
        raise FluidAssetGenerationError("batch items must not be empty")
    result: list[FluidAssetBatchItem] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            raise FluidAssetGenerationError("batch item must be a mapping")
        item_id = str(value.get("id", ""))
        if not item_id or item_id in seen:
            raise FluidAssetGenerationError("batch item ids must be non-empty and unique")
        prim = str(value.get("prim", ""))
        if not prim.startswith("/") or prim == "/":
            raise FluidAssetGenerationError("batch prim must be an exact absolute path")
        source = Path(str(value.get("source", "")))
        if not source.is_absolute():
            source = request_path.parent / source
        result.append(FluidAssetBatchItem(item_id, source.resolve(), prim))
        seen.add(item_id)
    return tuple(result)


def prepare_fluid_asset_batch(
    *, request: Path, output: Path, convertasset_root: Path | None = None, isaac_python: Path | None = None
) -> tuple[FluidAssetPrepareResult, ...]:
    destination = Path(output).resolve()
    results = []
    for item in load_batch_request(request):
        results.append(
            prepare_fluid_asset(
                source=item.source,
                prim=item.prim,
                output=destination / item.item_id,
                convertasset_root=convertasset_root,
                isaac_python=isaac_python,
            )
        )
    return tuple(results)


def load_batch_qualification_request(
    path: Path,
) -> tuple[FluidAssetQualificationBatchItem, ...]:
    request_path = Path(path).resolve()
    try:
        raw = yaml.safe_load(request_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise FluidAssetGenerationError(
            f"cannot read batch qualification request: {request_path}"
        ) from error
    if (
        not isinstance(raw, dict)
        or raw.get("schema_version")
        != "scenario-forge-fluid-asset-qualification-batch/v0.1"
    ):
        raise FluidAssetGenerationError("unsupported fluid asset qualification batch schema")
    values = raw.get("items")
    if not isinstance(values, list) or not values:
        raise FluidAssetGenerationError("batch qualification items must not be empty")
    result: list[FluidAssetQualificationBatchItem] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            raise FluidAssetGenerationError("batch qualification item must be a mapping")
        item_id = str(value.get("id", ""))
        if not item_id or item_id in seen:
            raise FluidAssetGenerationError(
                "batch qualification item ids must be non-empty and unique"
            )
        proposal = Path(str(value.get("proposal", "")))
        if not proposal.is_absolute():
            proposal = request_path.parent / proposal
        result.append(FluidAssetQualificationBatchItem(item_id, proposal.resolve()))
        seen.add(item_id)
    return tuple(result)


def qualify_fluid_asset_batch(
    *,
    request: Path,
    output: Path,
    convertasset_root: Path | None = None,
    isaac_python: Path | None = None,
) -> tuple[FluidAssetQualifyResult, ...]:
    destination = Path(output).resolve()
    results = []
    for item in load_batch_qualification_request(request):
        results.append(
            qualify_fluid_asset(
                proposal=item.proposal,
                output=destination / item.item_id,
                convertasset_root=convertasset_root,
                isaac_python=isaac_python,
            )
        )
    return tuple(results)
