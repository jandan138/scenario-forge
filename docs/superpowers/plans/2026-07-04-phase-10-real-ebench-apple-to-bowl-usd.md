# Real EBench Apple-To-Bowl USD Canary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a narrow Phase 10.6-10.10 canary that generates one Scenario Forge package for EBench `mobile_manip/apple_to_fruit_bowl` using the official apple, bowl, scene, robot, and camera assets instead of placeholder USD assets.

**Architecture:** Keep Scenario Forge as a portable package compiler. Scenario Forge ingests a small official-asset source manifest, materializes asset bundles into a local package or records a locked external source, compiles `scene/main.usda`, exports the EBench adapter descriptor, and imports EOS evidence. EOS remains responsible for `pxr.Usd.Stage.Open`, Newton/GenManip rendering, model execution, traces, and task success checks.

**Tech Stack:** Python 3.10, YAML package artifacts, existing Scenario Forge asset lock and USD compiler modules, EOS `embodied-eval-os-py310` / Newton lanes for downstream smoke evidence.

---

## Execution Status

2026-07-04 update:

```text
Phase 10.6 Official EBench asset intake freeze:
  implemented in Scenario Forge with tests.

Phase 10.7 Single-task real-asset USD package:
  implemented and generated at /tmp/ebench-apple-to-bowl-canary.
  Scenario Forge package check and asset lock check passed.

Phase 10.8 EOS package-linked real-asset USD smoke:
  executed through the EOS bridge with runtime_status=executed and
  stage_open_status=passed.

Retained small evidence:
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/

Still open:
  Phase 10.9 engine-native tabletop render and visual review.
  Phase 10.10 task contract canary hardening.
```

## File Structure

- Create `examples/ebench_apple_to_bowl_asset_sources.yaml`: small source manifest for the official EBench apple-to-bowl assets already identified by EOS evidence.
- Create `src/scenario_forge/adapters/ebench/official_asset_intake.py`: load and validate the source manifest; copy package-local asset bundles while preserving `SubUSDs/`, annotations, and `.collect.mapping.json`.
- Create `src/scenario_forge/generation/ebench_canary/apple_to_bowl.py`: generate one package with real asset manifest, scene instances, task, metrics, robot, provenance, and EBench adapter export.
- Modify `src/scenario_forge/cli.py`: add `scenario-forge ebench canary apple-to-bowl`.
- Test `tests/test_ebench_official_asset_intake.py`: verify bundle copy, checksums, and missing-source failures using tiny local fixtures.
- Test `tests/test_ebench_apple_to_bowl_canary.py`: verify generated package has no placeholder assets, references apple/bowl/scene/robot, writes asset lock, and exports EBench package metadata.
- Update `docs/records/2026-07-04-phase10x-eos-environment-and-gates.md`: retain the Phase 10.6-10.10 plan and timing.
- Update `docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md`: keep product roadmap aligned with this canary.

## Task 1: Official Asset Source Manifest

**Files:**
- Create: `examples/ebench_apple_to_bowl_asset_sources.yaml`
- Test: `tests/test_ebench_official_asset_intake.py`

- [ ] **Step 1: Write the failing manifest loader test**

```python
from pathlib import Path

import pytest
import yaml

from scenario_forge.adapters.ebench.official_asset_intake import load_official_asset_sources


def test_loads_apple_to_bowl_official_asset_sources(tmp_path: Path) -> None:
    source = tmp_path / "asset_sources.yaml"
    apple = tmp_path / "apple_bundle"
    apple.mkdir()
    apple_usd = apple / "apple.usd"
    apple_usd.write_text("#usda 1.0\n", encoding="utf-8")
    bowl = tmp_path / "bowl_bundle"
    bowl.mkdir()
    bowl_usd = bowl / "bowl.usd"
    bowl_usd.write_text("#usda 1.0\n", encoding="utf-8")

    source.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": {
                    "apple": {"role": "manipulated_object", "source_path": str(apple_usd), "license": "research-use"},
                    "bowl": {"role": "target_container", "source_path": str(bowl_usd), "license": "research-use"},
                },
            }
        ),
        encoding="utf-8",
    )

    loaded = load_official_asset_sources(source)

    assert loaded.task_id == "mobile_manip/apple_to_fruit_bowl"
    assert loaded.assets["apple"].source_path == apple_usd
    assert loaded.assets["bowl"].source_path == bowl_usd


def test_rejects_missing_official_asset_source(tmp_path: Path) -> None:
    source = tmp_path / "asset_sources.yaml"
    source.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": {
                    "apple": {"role": "manipulated_object", "source_path": str(tmp_path / "missing.usd"), "license": "research-use"},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing official asset source"):
        load_official_asset_sources(source)
```

- [ ] **Step 2: Run the failing tests**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py -q`

Expected: FAIL with `ModuleNotFoundError` or missing `load_official_asset_sources`.

- [ ] **Step 3: Implement the manifest loader**

Create `src/scenario_forge/adapters/ebench/official_asset_intake.py` with dataclasses:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class OfficialAssetSource:
    asset_id: str
    role: str
    source_path: Path
    license: str


@dataclass(frozen=True)
class OfficialAssetSources:
    task_id: str
    instruction: str
    assets: dict[str, OfficialAssetSource]


def load_official_asset_sources(path: str | Path) -> OfficialAssetSources:
    manifest_path = Path(path)
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Official asset source manifest must be a mapping: {manifest_path}")
    if data.get("schema_version") != "ebench-official-asset-sources/v0.1":
        raise ValueError("Unsupported official asset source schema_version")
    task_id = _required_string(data, "task_id")
    instruction = _required_string(data, "instruction")
    raw_assets = data.get("assets")
    if not isinstance(raw_assets, dict):
        raise ValueError("Official asset source manifest field 'assets' must be a mapping")
    assets: dict[str, OfficialAssetSource] = {}
    for asset_id, raw_asset in raw_assets.items():
        if not isinstance(asset_id, str) or not isinstance(raw_asset, dict):
            raise ValueError("Official asset entries must map asset IDs to mappings")
        source_path = Path(_required_string(raw_asset, "source_path"))
        if not source_path.exists():
            raise ValueError(f"Missing official asset source: {source_path}")
        assets[asset_id] = OfficialAssetSource(
            asset_id=asset_id,
            role=_required_string(raw_asset, "role"),
            source_path=source_path,
            license=_required_string(raw_asset, "license"),
        )
    return OfficialAssetSources(task_id=task_id, instruction=instruction, assets=assets)


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing required string field: {key}")
    return value
```

- [ ] **Step 4: Add the real source manifest**

Write `examples/ebench_apple_to_bowl_asset_sources.yaml` with the currently verified CPFS paths:

```yaml
schema_version: ebench-official-asset-sources/v0.1
task_id: mobile_manip/apple_to_fruit_bowl
instruction: Pick up the apple from the dining table and place it into the fruit bowl.
assets:
  scene:
    role: environment
    source_path: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/scene_usds/ebench/simple_pnp/task4/scene.usd
    license: research-use
  robot:
    role: robot
    source_path: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/robot_usds/lift2/robot.usd
    license: research-use
  apple:
    role: manipulated_object
    source_path: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/object_usds/custom_usd/ebench_usds/apple/ready/5948de6770a5491ea158cd9e921ebce9/5948de6770a5491ea158cd9e921ebce9.usd
    license: research-use
  bowl:
    role: target_container
    source_path: /cpfs/shared/simulation/zhuzihou/dev/_datasets/EBench-Assets/assets/object_usds/custom_usd/ebench_usds/bowl/ready/307689f1c6884e1bb85bb20f00fef294/307689f1c6884e1bb85bb20f00fef294.usd
    license: research-use
  camera_yaml:
    role: camera_config
    source_path: /cpfs/shared/simulation/zhuzihou/dev/GenManip/configs/cameras/fixed_camera_lift2_simbox.yml
    license: research-use
```

- [ ] **Step 5: Verify**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py -q`

Expected: PASS.

## Task 2: Bundle Materialization

**Files:**
- Modify: `src/scenario_forge/adapters/ebench/official_asset_intake.py`
- Test: `tests/test_ebench_official_asset_intake.py`

- [ ] **Step 1: Write the failing bundle-copy test**

```python
from scenario_forge.adapters.ebench.official_asset_intake import materialize_official_asset_bundle


def test_materializes_usd_bundle_with_subusds(tmp_path: Path) -> None:
    source_bundle = tmp_path / "source" / "apple_uid"
    texture_dir = source_bundle / "SubUSDs" / "textures"
    texture_dir.mkdir(parents=True)
    source_usd = source_bundle / "apple.usd"
    source_usd.write_text("#usda 1.0\n", encoding="utf-8")
    (texture_dir / "apple_texture.png").write_bytes(b"png")
    (source_bundle / "apple_annotation.json").write_text("{}", encoding="utf-8")
    target_root = tmp_path / "package"

    result = materialize_official_asset_bundle(
        source_path=source_usd,
        package_root=target_root,
        asset_id="official_ebench_apple",
        role="manipulated_object",
        license="research-use",
    )

    assert result.canonical_usd == "assets/official_ebench_apple/apple.usd"
    assert (target_root / result.canonical_usd).exists()
    assert (target_root / "assets/official_ebench_apple/SubUSDs/textures/apple_texture.png").exists()
    assert (target_root / "assets/official_ebench_apple/apple_annotation.json").exists()
```

- [ ] **Step 2: Run the failing test**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py::test_materializes_usd_bundle_with_subusds -q`

Expected: FAIL with missing `materialize_official_asset_bundle`.

- [ ] **Step 3: Implement bundle materialization**

Add this to `src/scenario_forge/adapters/ebench/official_asset_intake.py`:

```python
from dataclasses import dataclass
import shutil

from scenario_forge.assets.checksum import compute_sha256


@dataclass(frozen=True)
class MaterializedOfficialAsset:
    asset_id: str
    role: str
    canonical_usd: str
    sha256: str
    license: str
    source_path: str

    def asset_manifest_entry(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "role": self.role,
            "asset_type": "usd_bundle",
            "canonical_usd": self.canonical_usd,
            "license": self.license,
            "sha256": self.sha256,
            "source_kind": "official_ebench_asset",
            "source_uri": self.source_path,
            "resolver_version": "scenario-forge-ebench-official-asset-intake/v0.1",
        }


def materialize_official_asset_bundle(
    *,
    source_path: str | Path,
    package_root: str | Path,
    asset_id: str,
    role: str,
    license: str,
) -> MaterializedOfficialAsset:
    source_usd = Path(source_path)
    if not source_usd.exists():
        raise ValueError(f"Missing official asset source: {source_usd}")
    root = Path(package_root)
    target_dir = root / "assets" / asset_id
    root_resolved = root.resolve()
    target_resolved = target_dir.resolve()
    if root_resolved != target_resolved and root_resolved not in target_resolved.parents:
        raise ValueError(f"Materialized asset target escapes package root: {target_dir}")
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_usd.parent, target_dir)
    target_usd = target_dir / source_usd.name
    canonical_usd = target_usd.relative_to(root).as_posix()
    return MaterializedOfficialAsset(
        asset_id=asset_id,
        role=role,
        canonical_usd=canonical_usd,
        sha256=compute_sha256(target_usd),
        license=license,
        source_path=str(source_usd),
    )
```

- [ ] **Step 4: Verify**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py -q`

Expected: PASS.

## Task 3: Single-Task Package Generator

**Files:**
- Create: `src/scenario_forge/generation/ebench_canary/apple_to_bowl.py`
- Create: `src/scenario_forge/generation/ebench_canary/__init__.py`
- Test: `tests/test_ebench_apple_to_bowl_canary.py`

- [ ] **Step 1: Write the failing package generation test**

```python
from pathlib import Path

import yaml

from scenario_forge.generation.ebench_canary.apple_to_bowl import generate_apple_to_bowl_canary


def _write_tiny_source_manifest(tmp_path: Path) -> Path:
    assets: dict[str, dict[str, str]] = {}
    for name, role in {
        "scene": "environment",
        "robot": "robot",
        "apple": "manipulated_object",
        "bowl": "target_container",
    }.items():
        bundle = tmp_path / f"{name}_bundle"
        bundle.mkdir()
        source = bundle / f"{name}.usd"
        source.write_text("#usda 1.0\n", encoding="utf-8")
        assets[name] = {
            "role": role,
            "source_path": str(source),
            "license": "research-use",
        }
    camera = tmp_path / "fixed_camera_lift2_simbox.yml"
    camera.write_text("cameras: []\n", encoding="utf-8")
    assets["camera_yaml"] = {
        "role": "camera_config",
        "source_path": str(camera),
        "license": "research-use",
    }
    source_manifest = tmp_path / "asset_sources.yaml"
    source_manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": assets,
            }
        ),
        encoding="utf-8",
    )
    return source_manifest


def test_generates_real_asset_apple_to_bowl_package(tmp_path: Path) -> None:
    source_manifest = _write_tiny_source_manifest(tmp_path)
    package_dir = tmp_path / "out" / "ebench_apple_to_bowl_canary"

    result = generate_apple_to_bowl_canary(source_manifest, package_dir)

    assert result.package_root == package_dir
    scene = (package_dir / "scene/main.usda").read_text(encoding="utf-8")
    assert "official_ebench_apple" in scene
    assert "official_ebench_bowl" in scene
    assert "starter_rigid_object" not in scene
    assert "target_marker" not in scene
    lock = yaml.safe_load((package_dir / "locks/asset_lock.yaml").read_text(encoding="utf-8"))
    assert set(lock["assets"]) >= {
        "official_ebench_scene",
        "official_ebench_robot",
        "official_ebench_apple",
        "official_ebench_bowl",
    }
    adapter = yaml.safe_load((package_dir / "adapters/ebench/package.yaml").read_text(encoding="utf-8"))
    assert adapter["source_package"]["package_id"] == "ebench_apple_to_bowl_canary"
```

- [ ] **Step 2: Run the failing test**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py -q`

Expected: FAIL with missing module.

- [ ] **Step 3: Implement package generation**

Create `src/scenario_forge/generation/ebench_canary/apple_to_bowl.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scenario_forge.adapters.ebench.exporter import export_ebench_package
from scenario_forge.adapters.ebench.official_asset_intake import (
    load_official_asset_sources,
    materialize_official_asset_bundle,
)
from scenario_forge.artifacts.package_writer import write_yaml_artifact
from scenario_forge.assets.lock import generate_asset_lock, write_asset_lock
from scenario_forge.scaffold import scaffold_starter_package
from scenario_forge.scene.usd_compiler import compile_usd_scene


@dataclass(frozen=True)
class AppleToBowlCanaryResult:
    package_root: Path
    scene_usd: Path


def generate_apple_to_bowl_canary(asset_sources_path: str | Path, package_root: str | Path) -> AppleToBowlCanaryResult:
    root = Path(package_root)
    sources = load_official_asset_sources(asset_sources_path)
    scaffold_starter_package(root)
    _write_manifest(root)
    write_yaml_artifact(
        root / "generation_plan.yaml",
        {
            "schema_version": "generation-plan/v0.2",
            "package_id": "ebench_apple_to_bowl_canary",
            "source_task_id": sources.task_id,
            "required_assets": [
                {"role": "environment", "asset_type": "scene"},
                {"role": "robot", "asset_type": "lift2"},
                {"role": "object", "asset_type": "apple", "affordances": ["pickable"]},
                {"role": "target_container", "asset_type": "bowl", "affordances": ["container"]},
            ],
            "workflow_bindings": {"object": "apple_001", "target_container": "bowl_001"},
        },
    )
    write_yaml_artifact(
        root / "provenance" / "summary.yaml",
        {
            "schema_version": "provenance-summary/v0.1",
            "source_task_id": sources.task_id,
            "source_kind": "official_ebench_asset_canary",
        },
    )
    write_yaml_artifact(
        root / "evidence" / "validation_report.yaml",
        {
            "schema_version": "package-validation-report/v0.1",
            "status": "draft",
            "checks": [{"name": "real_ebench_asset_canary_generated", "status": "passed"}],
        },
    )

    materialized = []
    for source_key, asset_id in {
        "scene": "official_ebench_scene",
        "robot": "official_ebench_robot",
        "apple": "official_ebench_apple",
        "bowl": "official_ebench_bowl",
    }.items():
        source = sources.assets[source_key]
        materialized.append(
            materialize_official_asset_bundle(
                source_path=source.source_path,
                package_root=root,
                asset_id=asset_id,
                role=source.role,
                license=source.license,
            )
        )

    write_yaml_artifact(
        root / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [asset.asset_manifest_entry() for asset in materialized],
        },
    )
    write_yaml_artifact(
        root / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "instances": [
                _instance("environment_scene", "official_ebench_scene", "environment", [0.0, 0.0, 0.0]),
                _instance("lift2_robot_asset", "official_ebench_robot", "robot_asset", [-0.9, 0.1, -0.5]),
                _instance("apple_001", "official_ebench_apple", "manipulated_object", [-0.35, -0.22, 0.85]),
                _instance("bowl_001", "official_ebench_bowl", "target_container", [-0.35, 0.24, 0.82]),
            ],
        },
    )
    write_yaml_artifact(
        root / "task" / "task.yaml",
        {
            "schema_version": "task/v0.2",
            "task_id": sources.task_id,
            "task_family": "pick_place",
            "instruction": sources.instruction,
            "bindings": {"object": "apple_001", "target_container": "bowl_001"},
        },
    )
    write_yaml_artifact(
        root / "metrics" / "metrics.yaml",
        {
            "schema_version": "metrics/v0.2",
            "metrics": [
                {
                    "id": "apple_in_bowl",
                    "type": "predicate_satisfaction",
                    "role": "primary_success",
                    "predicate": "object_in_container",
                    "object": "apple_001",
                    "container": "bowl_001",
                    "adapter_hints": {
                        "ebench": {
                            "success_metric": "apple_in_bowl",
                            "predicate": "object_in_container",
                            "object": "apple_001",
                            "container": "bowl_001",
                        }
                    },
                }
            ],
        },
    )
    write_yaml_artifact(
        root / "robot" / "robot.yaml",
        {
            "schema_version": "robot/v0.2",
            "robot_id": "manip/lift2/R5a",
            "spawn": {"xyz": [-0.9, 0.1, -0.5], "wxyz": [1.0, 0.0, 0.0, 0.0]},
        },
    )
    write_asset_lock(root, generate_asset_lock(root))
    scene_usd = root / "scene" / "main.usda"
    compile_usd_scene(root, root / "scene" / "instances.yaml", root / "locks" / "asset_lock.yaml", scene_usd)
    export_ebench_package(root)
    return AppleToBowlCanaryResult(package_root=root, scene_usd=scene_usd)


def _write_manifest(root: Path) -> None:
    write_yaml_artifact(
        root / "manifest.yaml",
        {
            "schema_version": "scenario-package/v0.2",
            "package_id": "ebench_apple_to_bowl_canary",
            "scenario_domain": "home_manipulation",
            "package_mode": "fat",
            "targets": ["ebench", "embodied-eval-os"],
            "entrypoints": {
                "generation_plan": "generation_plan.yaml",
                "scene_usd": "scene/main.usda",
                "scene_instances": "scene/instances.yaml",
                "task": "task/task.yaml",
                "robot": "robot/robot.yaml",
                "metrics": "metrics/metrics.yaml",
            },
            "assets": {"manifest": "assets/asset_manifest.yaml", "lock": "locks/asset_lock.yaml"},
            "validation": {"report": "evidence/validation_report.yaml", "minimum_required_level": "asset_locked"},
            "provenance": {"summary": "provenance/summary.yaml"},
        },
    )


def _instance(instance_id: str, asset_id: str, role: str, xyz: list[float]) -> dict[str, object]:
    return {
        "id": instance_id,
        "asset_id": asset_id,
        "role": role,
        "pose": {"xyz": xyz, "wxyz": [1.0, 0.0, 0.0, 0.0]},
        "semantic_tags": [role],
        "initial_state": {},
    }
```

Create `src/scenario_forge/generation/ebench_canary/__init__.py`:

```python
from scenario_forge.generation.ebench_canary.apple_to_bowl import (
    AppleToBowlCanaryResult,
    generate_apple_to_bowl_canary,
)

__all__ = ["AppleToBowlCanaryResult", "generate_apple_to_bowl_canary"]
```

- [ ] **Step 4: Verify the package test**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py -q`

Expected: PASS.

## Task 4: CLI Canary Command

**Files:**
- Modify: `src/scenario_forge/cli.py`
- Test: `tests/test_ebench_apple_to_bowl_canary.py`

- [ ] **Step 1: Write the failing CLI test**

```python
from scenario_forge.cli import main


def _write_tiny_source_manifest(tmp_path: Path) -> Path:
    assets: dict[str, dict[str, str]] = {}
    for name, role in {
        "scene": "environment",
        "robot": "robot",
        "apple": "manipulated_object",
        "bowl": "target_container",
    }.items():
        bundle = tmp_path / f"{name}_bundle"
        bundle.mkdir()
        source = bundle / f"{name}.usd"
        source.write_text("#usda 1.0\n", encoding="utf-8")
        assets[name] = {"role": role, "source_path": str(source), "license": "research-use"}
    camera = tmp_path / "fixed_camera_lift2_simbox.yml"
    camera.write_text("cameras: []\n", encoding="utf-8")
    assets["camera_yaml"] = {"role": "camera_config", "source_path": str(camera), "license": "research-use"}
    source_manifest = tmp_path / "asset_sources.yaml"
    source_manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": "ebench-official-asset-sources/v0.1",
                "task_id": "mobile_manip/apple_to_fruit_bowl",
                "instruction": "Pick up the apple from the dining table and place it into the fruit bowl.",
                "assets": assets,
            }
        ),
        encoding="utf-8",
    )
    return source_manifest


def test_cli_generates_apple_to_bowl_canary(tmp_path: Path) -> None:
    source_manifest = _write_tiny_source_manifest(tmp_path)
    out_dir = tmp_path / "generated"

    code = main(
        [
            "ebench",
            "canary",
            "apple-to-bowl",
            "--asset-sources",
            str(source_manifest),
            "--out",
            str(out_dir),
        ]
    )

    assert code == 0
    assert (out_dir / "scene/main.usda").exists()
    assert (out_dir / "adapters/ebench/package.yaml").exists()
```

- [ ] **Step 2: Run the failing test**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py::test_cli_generates_apple_to_bowl_canary -q`

Expected: FAIL with unknown CLI command.

- [ ] **Step 3: Implement CLI wiring**

Add parser hierarchy:

```text
scenario-forge ebench canary apple-to-bowl --asset-sources examples/ebench_apple_to_bowl_asset_sources.yaml --out /tmp/ebench-apple-to-bowl-canary
```

The command should print the package path and `scene/main.usda`.

- [ ] **Step 4: Verify**

Run: `PYTHONPATH=src python -m pytest tests/test_ebench_apple_to_bowl_canary.py -q`

Expected: PASS.

## Task 5: Real CPFS Canary Generation

**Files:**
- Generated outside git: `/tmp/ebench-apple-to-bowl-canary`
- Retain evidence under: `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/`
- Modify: `docs/records/2026-07-04-phase10x-eos-environment-and-gates.md`

- [ ] **Step 1: Generate the real package**

Run:

```bash
PYTHONPATH=src python -m scenario_forge.cli ebench canary apple-to-bowl \
  --asset-sources examples/ebench_apple_to_bowl_asset_sources.yaml \
  --out /tmp/ebench-apple-to-bowl-canary
```

Expected:

```text
Package written: /tmp/ebench-apple-to-bowl-canary
USD entrypoint: /tmp/ebench-apple-to-bowl-canary/scene/main.usda
```

- [ ] **Step 2: Validate the package**

Run:

```bash
PYTHONPATH=src python -m scenario_forge.cli package check /tmp/ebench-apple-to-bowl-canary --require-asset-lock
PYTHONPATH=src python -m scenario_forge.cli assets check /tmp/ebench-apple-to-bowl-canary
```

Expected: both commands pass.

- [ ] **Step 3: Run EOS Stage.Open smoke**

Use the pushed EOS bridge branch and the normal EOS environment:

```bash
PYTHONPATH=/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/src:/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge \
  /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  /root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/scripts/run_phase10x_scenario_forge_usd_smoke.py \
  --suite-root /tmp \
  --package /tmp/ebench-apple-to-bowl-canary \
  --trace-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/apple_to_bowl_usd_smoke_trace.json \
  --runtime-evidence-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/apple_to_bowl_runtime_smoke.yaml
```

Expected: `runtime_status: executed`, `stage_open_status: passed`.

- [ ] **Step 4: Record claim boundary**

Append to `docs/records/2026-07-04-phase10x-eos-environment-and-gates.md`:

```text
The first real-asset apple-to-bowl USD canary uses official EBench apple, bowl,
scene, and robot USD bundles. This is real asset composition evidence and EOS
USD load evidence. It is not model success, official EBench reproduction,
official material/camera parity, or leaderboard evidence.
```

## Task 6: Engine-Native Tabletop Render And Visual Review

**Files:**
- EOS create: `/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/scripts/run_phase10x_scenario_forge_tabletop_render.py`
- EOS test: `/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/tests/test_phase10x_scenario_forge_tabletop_render_cli.py`
- Retain image outside git or under artifact storage: `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png`
- Retain small metadata in git: `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_render_metadata.json`
- Retain review summary in git: `docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_visual_review.md`

- [ ] **Step 1: Add EOS render CLI contract test**

In EOS, write `tests/test_phase10x_scenario_forge_tabletop_render_cli.py` so a tiny package fixture can be passed to the CLI with `--dry-run`. The dry run must write metadata without importing Newton/Isaac:

```python
from __future__ import annotations

import json
from pathlib import Path

from tests.test_phase10x_scenario_forge_usd_smoke_cli import _write_package


def test_tabletop_render_cli_dry_run_writes_camera_metadata(tmp_path: Path) -> None:
    from scripts.run_phase10x_scenario_forge_tabletop_render import main

    package = _write_package(tmp_path / "pkg", package_id="ebench_apple_to_bowl_canary")
    image_out = tmp_path / "tabletop_overview.png"
    metadata_out = tmp_path / "tabletop_overview_render_metadata.json"

    code = main(
        [
            "--package",
            str(package),
            "--image-out",
            str(image_out),
            "--metadata-out",
            str(metadata_out),
            "--camera-name",
            "tabletop_overview",
            "--dry-run",
        ]
    )

    assert code == 0
    metadata = json.loads(metadata_out.read_text(encoding="utf-8"))
    assert metadata["package_id"] == "ebench_apple_to_bowl_canary"
    assert metadata["camera"]["name"] == "tabletop_overview"
    assert metadata["camera"]["intent"] == "full_tabletop_overview"
    assert metadata["claim_boundary"] == (
        "Engine-native visual canary only. Not task success, not official camera parity, "
        "not official material parity, and not leaderboard evidence."
    )
```

- [ ] **Step 2: Implement EOS render CLI**

Create `/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/scripts/run_phase10x_scenario_forge_tabletop_render.py`.

The CLI must:

- accept `--package`, `--image-out`, `--metadata-out`, `--camera-name tabletop_overview`, and `--dry-run`;
- read the Scenario Forge package through `adapters.ebench.scenario_forge_package.load_scenario_forge_package`;
- in dry run, write metadata only;
- in real run, use the selected EOS runtime lane's native camera/sensor API to render the package scene, not a synthetic image, collage, or file copy;
- place a camera intended to see the full tabletop work surface, apple, bowl, scene context, and robot or robot spawn;
- write PNG output, metadata JSON, and no model/task score.

Use this metadata shape:

```json
{
  "schema": "scenario_forge_tabletop_overview_render.v0",
  "package_id": "ebench_apple_to_bowl_canary",
  "scene_usd": "/tmp/ebench-apple-to-bowl-canary/scene/main.usda",
  "camera": {
    "name": "tabletop_overview",
    "intent": "full_tabletop_overview",
    "engine_native": true,
    "pose_source": "eos_runtime_tabletop_overview_camera",
    "resolution": [1280, 720]
  },
  "visible_targets_expected": ["tabletop", "apple", "bowl", "scene_context", "robot_or_spawn"],
  "image_path": "tabletop_overview.png",
  "claim_boundary": "Engine-native visual canary only. Not task success, not official camera parity, not official material parity, and not leaderboard evidence."
}
```

- [ ] **Step 3: Run the real engine-native render**

Use the EOS Newton / EBench runtime environment selected for visual canaries:

```bash
PYTHONPATH=/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/src:/root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge \
  /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-newton-ebench-experimental-py310/bin/python \
  /root/.config/superpowers/worktrees/embodied-eval-os/phase10x-scenario-forge-bridge/scripts/run_phase10x_scenario_forge_tabletop_render.py \
  --package /tmp/ebench-apple-to-bowl-canary \
  --image-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png \
  --metadata-out docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_render_metadata.json \
  --camera-name tabletop_overview
```

Expected:

```text
render_status: executed
image_path: docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png
camera.name: tabletop_overview
camera.engine_native: true
```

- [ ] **Step 4: Run clean-room visual review**

Use `render-visual-reviewer` with a fresh clean-room reviewer. Provide only the image path and this visual expectation, not code, manifests, diffs, or suspected issues:

```text
Task: Inspect this render image as a human visual QA reviewer.
Context: The target should be an apple-to-bowl tabletop manipulation scene rendered from an engine-native overview camera.
Images:
- A: /cpfs/user/zhuzihou/dev/scenario-forge/docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview.png
Check:
- Is the image nonblank and rendered from a useful tabletop overview?
- Is the full task-relevant table/work surface visible?
- Are apple and bowl visible and identifiable?
- Is scene context visible enough to understand this is a tabletop manipulation scene?
- Is a robot or robot spawn visible, or at least not contradicted by the image?
- Are there obvious blocking artifacts: camera clipping, severe occlusion, missing textures, black fallback materials, broken mesh, floating parts, z-fighting, or placeholder/starter assets?
Output: PASS/WARN/FAIL with concise visible evidence and a retake recommendation for WARN or FAIL.
Constraints: Do not inspect code, manifests, repo files, or implementation details.
```

Write the returned verdict to:

```text
docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_visual_review.md
```

- [ ] **Step 5: Enforce Phase 10.9 acceptance**

Phase 10.9 can close only if:

```text
1. tabletop_overview.png exists and is produced by the engine-native render CLI.
2. tabletop_overview_render_metadata.json records camera.engine_native=true.
3. The visual review verdict is PASS.
4. The review says apple and bowl are visible and identifiable.
5. The review does not report blank image, camera clipping, missing table, or placeholder/starter assets.
```

If the review returns WARN, retake the render with a revised engine-native camera pose and repeat Step 4. If the review returns FAIL, keep Phase 10.9 open.

## Task 7: Verification And Commit

**Files:**
- All files touched above.
- Scenario Forge commit should include source manifests, package generator, docs, small metadata, and visual review summary.
- EOS branch commit should include the engine-native render CLI and its tests.
- Do not commit `tabletop_overview.png` unless it is explicitly small enough and allowed by artifact policy; otherwise retain it in artifact storage and commit only its path, size, and sha256 in metadata.

- [ ] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_ebench_official_asset_intake.py tests/test_ebench_apple_to_bowl_canary.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full Scenario Forge check**

Run: `make check`

Expected: PASS.

- [ ] **Step 3: Check git diff**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intended implementation, tests, examples, docs, and retained evidence are changed.

- [ ] **Step 4: Commit**

Run:

```bash
git add src/scenario_forge/adapters/ebench/official_asset_intake.py \
  src/scenario_forge/generation/ebench_canary \
  src/scenario_forge/cli.py \
  tests/test_ebench_official_asset_intake.py \
  tests/test_ebench_apple_to_bowl_canary.py \
  examples/ebench_apple_to_bowl_asset_sources.yaml \
  docs/records/2026-07-04-phase10x-eos-environment-and-gates.md \
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_render_metadata.json \
  docs/records/evidence/2026-07-04-phase10-real-ebench-apple-to-bowl-usd/tabletop_overview_visual_review.md \
  docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md \
  docs/superpowers/plans/2026-07-04-phase-10-real-ebench-apple-to-bowl-usd.md
git commit -m "feat: add real ebench apple-to-bowl usd canary"
```

Expected: one commit with no large USD payloads committed.

In the EOS bridge worktree, commit the render CLI separately:

```bash
git add scripts/run_phase10x_scenario_forge_tabletop_render.py \
  tests/test_phase10x_scenario_forge_tabletop_render_cli.py
git commit -m "feat: add scenario forge tabletop render canary"
```

Expected: EOS bridge commit contains only EOS runtime/render lane code and tests.

## Completion Criteria

- `scene/main.usda` references package-local copies of official EBench apple, bowl, scene, and robot USD bundles.
- `locks/asset_lock.yaml` has checksums for the canonical USD files.
- `adapters/ebench/package.yaml` and `task_entrypoint.yaml` identify `mobile_manip/apple_to_fruit_bowl`.
- EOS Stage.Open evidence is retained for the generated package.
- EOS retains one engine-native `tabletop_overview` render PNG and a clean-room visual review PASS before claiming Phase 10.9 visual canary closure.
- Documentation states the boundary: real USD asset package, not task success or leaderboard evidence.
