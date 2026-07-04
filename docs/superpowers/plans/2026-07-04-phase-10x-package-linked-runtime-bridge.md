# Phase 10.x Package-Linked Runtime Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining Phase 10.4/10.5 gap by producing downstream EOS runtime evidence that proves a real runtime lane consumed Scenario Forge-generated USD package artifacts.

**Architecture:** Keep Scenario Forge as the package compiler and evidence gate. Add the package-reading and runtime-smoke bridge in EOS, under the EBench adapter/runtime boundary, so Scenario Forge does not import simulator SDKs or run episodes. Feed the resulting package-linked runtime evidence YAML back into `scenario-forge suite phase10x`.

**Tech Stack:** Python 3.10, PyYAML, pytest, EOS project env `embodied-eval-os-py310`, EOS backend runtime env `embodied-eval-os-sim-newton-ebench-experimental-py310` or another explicitly selected runtime lane.

---

## Current Evidence

Already completed in Scenario Forge:

```text
Phase 10.1 golden package gate
Phase 10.2 external input hardening gate
Phase 10.3 EOS static import file-presence gate
Phase 10.4 evidence contract tightened to require package_artifacts
Phase 10.5 RC gate accepts only package-linked runtime smoke evidence
```

Retained backend-readiness evidence:

```text
docs/records/evidence/2026-07-04-phase10x-eos-native-smoke/eos_genmanip_native_smoke_trace.json
runtime_status: executed
asset_provenance: genmanip_runtime
```

This proves EOS / GenManip backend readiness only. It does not close Phase 10.4
because the trace does not consume a Scenario Forge package.

2026-07-04 execution update:

```text
EOS bridge branch:
  phase10x-scenario-forge-bridge

Retained package-linked evidence:
  docs/records/evidence/2026-07-04-phase10x-package-linked-runtime-smoke/

Phase 10.x strict result:
  passed on phase10x_rc_suite, package_count=50

Claim boundary:
  package handoff / USD Stage.Open only; no model score, task success,
  physics fidelity, official EBench reproduction, or leaderboard comparability.
```

## Target Runtime Evidence Shape

EOS must produce a YAML file like this:

```yaml
schema_version: phase10x-runtime-smoke-evidence/v0.1
lane: eos_usd_stage_open_smoke
status: passed
packages_tested:
  - phase10x_golden_suite_000
package_artifacts:
  - package_id: phase10x_golden_suite_000
    usd_entrypoint: packages/phase10x_golden_suite_000/scene/main.usda
    asset_lock: packages/phase10x_golden_suite_000/locks/asset_lock.yaml
    adapter_descriptor: packages/phase10x_golden_suite_000/adapters/ebench/package.yaml
    task_entrypoint: packages/phase10x_golden_suite_000/adapters/ebench/task_entrypoint.yaml
    trace_uri: file:///absolute/path/to/eos_trace_or_report.json
evidence_uri: file:///absolute/path/to/phase10x_runtime_evidence.yaml
summary: EOS runtime lane loaded the Scenario Forge package USD entrypoint and retained trace evidence.
```

The first acceptable smoke may be a USD load/import smoke, not a scored episode.
It must not claim model quality, official EBench reproduction, leaderboard
comparability, physics fidelity, or task success.

## Task 1: EOS Scenario Forge Package Loader

**Files in `/cpfs/user/zhuzihou/dev/embodied-eval-os`:**

- Create: `adapters/ebench/scenario_forge_package.py`
- Test: `tests/adapters/ebench/test_scenario_forge_package.py`

- [ ] **Step 1: Write the failing loader test**

Create a temp Scenario Forge package fixture with the exact files the gate
requires:

```python
from pathlib import Path

import yaml

from adapters.ebench.scenario_forge_package import load_scenario_forge_package


def test_loads_scenario_forge_package_runtime_artifacts(tmp_path: Path) -> None:
    package = write_minimal_scenario_forge_package(tmp_path / "pkg")

    loaded = load_scenario_forge_package(package)

    assert loaded["package_id"] == "phase10x_pkg_000"
    assert loaded["scene_usd"].name == "main.usda"
    assert loaded["asset_lock"].name == "asset_lock.yaml"
    assert loaded["adapter_descriptor"].name == "package.yaml"
    assert loaded["task_entrypoint"].name == "task_entrypoint.yaml"
    assert loaded["runtime_hints"]["simulator"] == "usd_capable"


def write_minimal_scenario_forge_package(root: Path) -> Path:
    (root / "scene").mkdir(parents=True)
    (root / "locks").mkdir(parents=True)
    (root / "adapters" / "ebench").mkdir(parents=True)
    (root / "task").mkdir(parents=True)
    (root / "scene" / "main.usda").write_text("#usda 1.0\n", encoding="utf-8")
    write_yaml(root / "locks" / "asset_lock.yaml", {"schema_version": "asset-lock/v0.2", "assets": []})
    write_yaml(root / "task" / "task.yaml", {"task_id": "pick_place"})
    write_yaml(
        root / "adapters" / "ebench" / "package.yaml",
        {
            "schema_version": "ebench-scenario-export/v0.1",
            "source_package": {
                "package_id": "phase10x_pkg_000",
                "schema_version": "scenario-package/v0.2",
                "targets": ["ebench", "embodied-eval-os"],
            },
            "entrypoints": {
                "scene_usd": "../../scene/main.usda",
                "task": "../../task/task.yaml",
            },
            "assets": {"asset_lock": "../../locks/asset_lock.yaml"},
            "runtime_hints": {"simulator": "usd_capable"},
        },
    )
    write_yaml(
        root / "adapters" / "ebench" / "task_entrypoint.yaml",
        {
            "schema_version": "ebench-task-entrypoint/v0.1",
            "package_id": "phase10x_pkg_000",
            "task_id": "pick_place",
        },
    )
    return root


def write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd /cpfs/user/zhuzihou/dev/embodied-eval-os
PYTHONPATH=src:. /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  -m pytest tests/adapters/ebench/test_scenario_forge_package.py -q
```

Expected: fail because `adapters.ebench.scenario_forge_package` does not exist.

- [ ] **Step 3: Implement the minimal loader**

Create `adapters/ebench/scenario_forge_package.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_FILES = (
    "adapters/ebench/package.yaml",
    "adapters/ebench/task_entrypoint.yaml",
    "scene/main.usda",
    "locks/asset_lock.yaml",
)


def load_scenario_forge_package(package_dir: str | Path) -> dict[str, Any]:
    root = Path(package_dir)
    missing = [relative for relative in REQUIRED_FILES if not (root / relative).is_file()]
    if missing:
        raise ValueError("Scenario Forge package missing required files: " + ", ".join(missing))

    adapter_dir = root / "adapters" / "ebench"
    descriptor = _load_yaml(adapter_dir / "package.yaml")
    task_entrypoint = _load_yaml(adapter_dir / "task_entrypoint.yaml")
    source_package = descriptor.get("source_package")
    if not isinstance(source_package, dict) or not isinstance(source_package.get("package_id"), str):
        raise ValueError("EBench descriptor missing source_package.package_id")

    entrypoints = descriptor.get("entrypoints")
    assets = descriptor.get("assets")
    if not isinstance(entrypoints, dict) or not isinstance(assets, dict):
        raise ValueError("EBench descriptor missing entrypoints or assets")

    scene_usd = _resolve(adapter_dir, entrypoints.get("scene_usd"))
    asset_lock = _resolve(adapter_dir, assets.get("asset_lock"))
    for label, path in {"scene_usd": scene_usd, "asset_lock": asset_lock}.items():
        if not path.is_file():
            raise ValueError(f"Scenario Forge package {label} does not exist: {path}")

    return {
        "package_id": source_package["package_id"],
        "package_root": root,
        "adapter_descriptor": adapter_dir / "package.yaml",
        "task_entrypoint": adapter_dir / "task_entrypoint.yaml",
        "scene_usd": scene_usd,
        "asset_lock": asset_lock,
        "runtime_hints": descriptor.get("runtime_hints", {}),
        "task": task_entrypoint,
    }


def _resolve(base_dir: Path, raw_path: Any) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("EBench descriptor contains an empty path")
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve(strict=False)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}
```

- [ ] **Step 4: Verify loader test passes**

Run the same pytest command. Expected: pass.

## Task 2: EOS Package-Linked USD Load Smoke

**Files in `/cpfs/user/zhuzihou/dev/embodied-eval-os`:**

- Create: `adapters/ebench/scenario_forge_usd_smoke.py`
- Test: `tests/adapters/ebench/test_scenario_forge_usd_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

```python
from pathlib import Path

from adapters.ebench.scenario_forge_usd_smoke import build_package_linked_runtime_evidence
from tests.adapters.ebench.test_scenario_forge_package import write_minimal_scenario_forge_package


def test_builds_phase10x_package_linked_runtime_evidence(tmp_path: Path) -> None:
    package = write_minimal_scenario_forge_package(tmp_path / "pkg")
    trace = tmp_path / "trace.json"
    trace.write_text('{"runtime_status":"executed"}', encoding="utf-8")

    evidence = build_package_linked_runtime_evidence(
        package_dirs=[package],
        suite_root=tmp_path,
        lane="eos_usd_stage_open_smoke",
        trace_uri=trace.as_uri(),
        evidence_uri=(tmp_path / "runtime_smoke.yaml").as_uri(),
        status="passed",
        summary="EOS runtime lane loaded Scenario Forge USD.",
    )

    assert evidence["schema_version"] == "phase10x-runtime-smoke-evidence/v0.1"
    assert evidence["status"] == "passed"
    assert evidence["packages_tested"] == ["phase10x_pkg_000"]
    assert evidence["package_artifacts"][0]["package_id"] == "phase10x_pkg_000"
    assert evidence["package_artifacts"][0]["usd_entrypoint"].endswith("scene/main.usda")
    assert evidence["package_artifacts"][0]["asset_lock"].endswith("locks/asset_lock.yaml")
    assert evidence["package_artifacts"][0]["adapter_descriptor"].endswith("adapters/ebench/package.yaml")
    assert evidence["package_artifacts"][0]["task_entrypoint"].endswith("adapters/ebench/task_entrypoint.yaml")
    assert evidence["package_artifacts"][0]["trace_uri"] == trace.as_uri()
```

- [ ] **Step 2: Run the failing test**

Expected: fail because `scenario_forge_usd_smoke` does not exist.

- [ ] **Step 3: Implement the evidence builder**

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.ebench.scenario_forge_package import load_scenario_forge_package


def build_package_linked_runtime_evidence(
    *,
    package_dirs: list[str | Path],
    suite_root: str | Path | None = None,
        lane: str,
        trace_uri: str,
        evidence_uri: str,
    status: str,
    summary: str,
) -> dict[str, Any]:
    loaded = [load_scenario_forge_package(path) for path in package_dirs]
    evidence_root = Path(suite_root).resolve(strict=False) if suite_root else _infer_suite_root(loaded)
    return {
        "schema_version": "phase10x-runtime-smoke-evidence/v0.1",
        "lane": lane,
        "status": status,
        "packages_tested": [item["package_id"] for item in loaded],
        "package_artifacts": [
            {
                "package_id": item["package_id"],
                "usd_entrypoint": str(_relative_or_absolute(evidence_root, item["scene_usd"])),
                "asset_lock": str(_relative_or_absolute(evidence_root, item["asset_lock"])),
                "adapter_descriptor": str(_relative_or_absolute(evidence_root, item["adapter_descriptor"])),
                "task_entrypoint": str(_relative_or_absolute(evidence_root, item["task_entrypoint"])),
                "trace_uri": trace_uri,
            }
            for item in loaded
        ],
        "evidence_uri": evidence_uri,
        "summary": summary,
    }


def _infer_suite_root(loaded: list[dict[str, Any]]) -> Path:
    first_root = Path(loaded[0]["package_root"]).resolve(strict=False)
    if first_root.parent.name == "packages":
        return first_root.parent.parent
    return first_root.parent


def _relative_or_absolute(root: Path, path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return path
```

- [ ] **Step 4: Verify evidence builder test passes**

Run:

```bash
PYTHONPATH=src:. /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  -m pytest tests/adapters/ebench/test_scenario_forge_package.py \
             tests/adapters/ebench/test_scenario_forge_usd_smoke.py -q
```

Expected: pass.

## Task 3: Runtime Lane Command

**Files in `/cpfs/user/zhuzihou/dev/embodied-eval-os`:**

- Create: `scripts/run_phase10x_scenario_forge_usd_smoke.py`
- Test: `tests/test_phase10x_scenario_forge_usd_smoke_cli.py`

- [ ] **Step 1: Write the failing CLI test**

The test should create a minimal package fixture, run the script with
`--package`, `--trace-out`, and `--runtime-evidence-out`, then assert:

```python
assert payload["runtime_status"] in {"executed", "skipped"}
assert evidence["packages_tested"] == ["phase10x_pkg_000"]
assert evidence["package_artifacts"][0]["trace_uri"].startswith("file://")
```

If the test environment lacks `pxr` or `newton`, the script may emit
`status: failed` or `status: skipped`, but it must still preserve package-linked
artifact references. The real Phase 10.4 pass must be run in the selected EOS
runtime env and must return `status: passed`.

- [ ] **Step 2: Implement the CLI**

The command must:

1. Load the Scenario Forge package using `load_scenario_forge_package`.
2. Open the USD stage using `pxr.Usd.Stage.Open` when `pxr` is available.
3. In a Newton runtime lane, additionally import the runtime module selected by
   EOS and record the result. Do not make Scenario Forge import Newton.
4. Write a JSON trace/report with `runtime_status`, `package_id`, `scene_usd`,
   `asset_lock`, `adapter_descriptor`, `task_entrypoint`,
   `stage_open_status`, and claim boundary.
5. Write the Phase 10.x runtime evidence YAML with `package_artifacts`.

- [ ] **Step 3: Run the command against a real Scenario Forge package**

Generate the package in Scenario Forge:

```bash
cd /cpfs/user/zhuzihou/dev/scenario-forge
PYTHONPATH=src python -m scenario_forge.cli suite generate \
  --spec examples/suite_spec_phase10x_golden.yaml \
  --out /tmp/scenario-forge-phase10x-suite
```

Run EOS smoke:

```bash
cd /cpfs/user/zhuzihou/dev/embodied-eval-os
PYTHONPATH=src:. /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  scripts/run_phase10x_scenario_forge_usd_smoke.py \
  --suite-root /tmp/scenario-forge-phase10x-suite \
  --package /tmp/scenario-forge-phase10x-suite/packages/phase10x_golden_suite_000 \
  --trace-out /tmp/phase10x-sf-usd-smoke/trace.json \
  --runtime-evidence-out /tmp/phase10x-sf-usd-smoke/runtime_smoke.yaml
```

Expected local static lane: package-linked evidence is written. Expected runtime
lane pass: `status: passed` only when the selected EOS runtime actually opens or
imports the Scenario Forge USD entrypoint.
The evidence paths for `usd_entrypoint`, `asset_lock`, `adapter_descriptor`, and
`task_entrypoint` must be relative to `--suite-root`, for example
`packages/phase10x_golden_suite_000/scene/main.usda`.

## Task 4: Feed Evidence Back Into Scenario Forge

**Files in `/cpfs/user/zhuzihou/dev/scenario-forge`:**

- No production code expected unless Task 3 reveals a missing portable artifact.
- Optional record update: `docs/records/2026-07-04-phase10x-eos-environment-and-gates.md`

- [ ] **Step 1: Run Scenario Forge gate using EOS-produced runtime evidence**

```bash
cd /cpfs/user/zhuzihou/dev/scenario-forge
PYTHONPATH=src python -m scenario_forge.cli suite phase10x \
  --suite /tmp/scenario-forge-phase10x-suite \
  --eos-python /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  --external-evidence examples/phase10x_external_evidence.yaml \
  --runtime-smoke /tmp/phase10x-sf-usd-smoke/runtime_smoke.yaml \
  --rc-min-packages 10 \
  --rc-max-packages 20 \
  --strict
```

Expected: `Phase 10.x overall status: passed` only if the EOS evidence has
`status: passed` and complete `package_artifacts`.

- [ ] **Step 2: Record the result**

If passed, append the trace URI, runtime evidence URI, package id, USD entrypoint,
task entrypoint, and runtime lane to
`docs/records/2026-07-04-phase10x-eos-environment-and-gates.md`.

If failed, record the exact blocker and keep Phase 10.4 open.

## Task 5: Phase 10.5 RC Gate

**Files in `/cpfs/user/zhuzihou/dev/scenario-forge`:**

- Create or update a 50-100 task suite spec only after Task 4 passes on the
  golden suite.
- Runtime evidence may cover a representative 1-3 package smoke, but the RC gate
  must include known blockers and must not claim benchmark readiness.

- [ ] **Step 1: Generate the RC suite**

```bash
PYTHONPATH=src python -m scenario_forge.cli suite generate \
  --spec <rc-suite-spec.yaml> \
  --out /tmp/scenario-forge-phase10x-rc-suite
```

- [ ] **Step 2: Run Phase 10.x with default RC package range**

```bash
PYTHONPATH=src python -m scenario_forge.cli suite phase10x \
  --suite /tmp/scenario-forge-phase10x-rc-suite \
  --eos-python /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  --external-evidence examples/phase10x_external_evidence.yaml \
  --runtime-smoke <package-linked-runtime-smoke.yaml> \
  --strict
```

Expected: pass only when package count is 50-100 and all Phase 10.x gates pass.

## Self-Review

Spec coverage:

- The plan keeps simulator/runtime execution in EOS, not Scenario Forge.
- The plan proves package linkage with `package_artifacts`.
- The plan distinguishes native backend readiness from Scenario Forge package
  handoff evidence.
- The plan requires suite-relative artifact paths for `usd_entrypoint`,
  `asset_lock`, `adapter_descriptor`, and `task_entrypoint`, so EOS evidence can
  be checked against the package layout instead of free-form strings.
- The plan leaves model evaluation, scores, leaderboards, and episode runners
  outside Scenario Forge.

Known open risk:

- Scenario Forge's current placeholder USD assets are static `Xform` stubs. A
  USD load/import smoke can close the package handoff gate, but it cannot claim
  physics fidelity or task success until later asset/physics work produces
  runtime-grade meshes, collision, and robot bindings.
