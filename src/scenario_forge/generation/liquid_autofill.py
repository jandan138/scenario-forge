"""Orchestrate ConvertAsset-owned GPU-PBD liquid production and handoff."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Sequence

from scenario_forge.adapters.liquid_autofill import (
    LiquidAutofillCommandPlan,
    LiquidAutofillHandoffError,
    build_request,
    load_producer_handoff,
)
from scenario_forge.artifacts.liquid_alias import (
    LiquidAliasPackage,
    build_liquid_alias_package,
)


class LiquidAutofillGenerationError(RuntimeError):
    """Raised when a liquid artifact cannot be promoted safely."""


@dataclass(frozen=True)
class LiquidInspectionResult:
    report: Path


@dataclass(frozen=True)
class LiquidAutofillResult:
    package: LiquidAliasPackage
    diagnostics: Path


def _convertasset_root(value: Path | None) -> Path:
    raw = str(value) if value is not None else os.environ.get(
        "SCENARIO_FORGE_CONVERTASSET_ROOT", ""
    )
    if not raw:
        raise LiquidAutofillGenerationError(
            "set --convertasset-root or SCENARIO_FORGE_CONVERTASSET_ROOT"
        )
    root = Path(raw).expanduser().resolve()
    if not (root / "main.py").is_file() or not (
        root / "scripts/isaac_python.sh"
    ).is_file():
        raise LiquidAutofillGenerationError(f"invalid ConvertAsset checkout: {root}")
    return root


def _isaac_python(value: Path | None) -> Path | None:
    raw = str(value) if value is not None else os.environ.get(
        "EEOS_ISAACSIM41_PYTHON", ""
    )
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise LiquidAutofillGenerationError(f"Isaac Sim Python does not exist: {path}")
    return path


def _run(
    command: Sequence[str], *, log: Path, clean_runtime_environment: bool = False
) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        stream.write("$ " + " ".join(command) + "\n\n")
        stream.flush()
        # Isaac may leave short-lived descendants holding inherited file
        # descriptors.  A pipe-based capture can therefore wait forever after
        # the command itself exits; direct log redirection tracks the actual
        # producer process and keeps its complete diagnostics.
        environment = None
        if clean_runtime_environment:
            environment = dict(os.environ)
            for name in (
                "PYTHONPATH",
                "LD_LIBRARY_PATH",
                "CARB_APP_PATH",
                "EXP_PATH",
                "ISAAC_PATH",
                "ISAAC_SIM_ROOT",
            ):
                environment.pop(name, None)
            environment["ACCEPT_EULA"] = "Y"
            environment.setdefault("PRIVACY_CONSENT", "Y")
        completed = subprocess.run(
            command,
            text=True,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
            env=environment,
        )
    if completed.returncode:
        raise LiquidAutofillGenerationError(
            f"command failed with exit code {completed.returncode}; see {log}"
        )


def _slug(prim_path: str) -> str:
    leaf = prim_path.rstrip("/").rsplit("/", 1)[-1]
    value = re.sub(r"[^A-Za-z0-9_]+", "_", leaf).strip("_").lower()
    return value or "container"


def inspect_liquid_candidates(
    *,
    scene: Path,
    output: Path | None = None,
    convertasset_root: Path | None = None,
    isaac_python: Path | None = None,
) -> LiquidInspectionResult:
    source = Path(scene).expanduser().resolve()
    if not source.is_file():
        raise LiquidAutofillGenerationError(f"source scene does not exist: {source}")
    report = (
        Path(output).expanduser().resolve()
        if output is not None
        else source.parent / f"{source.stem}__liquid_inspection.json"
    )
    plan = LiquidAutofillCommandPlan(
        _convertasset_root(convertasset_root), _isaac_python(isaac_python)
    )
    _run(plan.inspect_command(source, report), log=report.with_suffix(".log"))
    if not report.is_file():
        raise LiquidAutofillGenerationError("ConvertAsset did not write an inspection report")
    return LiquidInspectionResult(report=report)


def add_liquid(
    *,
    scene: Path,
    container: str,
    fill: float,
    output: Path | None = None,
    convertasset_root: Path | None = None,
    isaac_python: Path | None = None,
    fluid_profile: Path | None = None,
    fixed_container_validation: bool = False,
    initial_particle_count: int | None = None,
) -> LiquidAutofillResult:
    source = Path(scene).expanduser().resolve()
    destination = (
        Path(output).expanduser().resolve()
        if output is not None
        else source.parent
    )
    slug = _slug(container)
    fill_id = f"fill{round(float(fill) * 100):02d}"
    base = f"{source.stem}__liquid__{slug}__{fill_id}"
    diagnostics = destination / f"{base}_diagnostics"
    working = destination / f".{base}_working"
    formal_alias = destination / f"{base}.usd"
    formal_zip = destination / f"{base}.zip"
    formal_deps = destination / f"{base}_deps"
    for path in (working, diagnostics):
        if path.exists():
            shutil.rmtree(path)
    working.mkdir(parents=True)
    plan = LiquidAutofillCommandPlan(
        _convertasset_root(convertasset_root), _isaac_python(isaac_python)
    )
    try:
        request = build_request(
            scene=source,
            container=container,
            fill=fill,
            fluid_profile=fluid_profile,
            fixed_container_validation=fixed_container_validation,
            initial_particle_count=initial_particle_count,
        )
        request_path = working / "request.json"
        request_path.write_text(
            json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        producer_root = working / "producer"
        _run(
            plan.autofill_command(request_path, producer_root),
            log=working / "logs/convertasset_autofill.log",
        )
        producer = load_producer_handoff(producer_root)

        closure = working / "source_closure"
        _run(
            plan.closure_command(source, closure, scope=producer.scene_root_prim),
            log=working / "logs/convertasset_closure.log",
        )

        provisional = working / "provisional"
        provisional_package = build_liquid_alias_package(
            source_scene=source,
            producer=producer,
            closure_dir=closure,
            output_dir=provisional,
            container_slug=slug,
            fill=fill,
            integration_evidence=None,
        )
        integration = working / "full_scene_8s.json"
        _run(
            plan.integration_command(
                scene=provisional_package.alias_usd,
                analysis=producer.analysis_path,
                manifest=producer.manifest_path,
                output=integration,
            ),
            log=working / "logs/full_scene_8s.log",
            clean_runtime_environment=plan.isaac_python is not None,
        )
        result = build_liquid_alias_package(
            source_scene=source,
            producer=producer,
            closure_dir=closure,
            output_dir=destination,
            container_slug=slug,
            fill=fill,
            integration_evidence=integration,
        )
    except (
        OSError,
        ValueError,
        LiquidAutofillHandoffError,
        LiquidAutofillGenerationError,
    ) as error:
        for path in (formal_alias, formal_zip):
            if path.exists():
                path.unlink()
        if formal_deps.exists():
            shutil.rmtree(formal_deps)
        if working.exists():
            working.replace(diagnostics)
        raise LiquidAutofillGenerationError(
            f"liquid package was not promoted: {error}; diagnostics: {diagnostics}"
        ) from error
    diagnostics.mkdir(parents=True, exist_ok=True)
    shutil.copy2(integration, diagnostics / "full_scene_8s.json")
    if (working / "logs").is_dir():
        shutil.copytree(working / "logs", diagnostics / "logs")
    shutil.rmtree(working)
    return LiquidAutofillResult(package=result, diagnostics=diagnostics)
