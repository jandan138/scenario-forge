# Task Graph And EBench Export Phase 4-5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 4 task graph/predicate/metric compilation and Phase 5 EBench adapter v0 export so a v0.2 package can become an EBench-compatible static task package.

**Architecture:** Phase 4 stays in pure portable package layers under `scenario_forge.task` and `scenario_forge.generation.workflows`, reading scene instances and writing task artifacts as YAML. Phase 5 stays under `scenario_forge.adapters.ebench`, reads Scenario Forge package contracts, validates static export gates, writes adapter artifacts under `adapters/ebench/`, and never runs episodes or mutates the portable manifest.

**Tech Stack:** Python 3.10, PyYAML, dataclasses, pathlib, pytest, ruff.

---

## File Structure

- Create `src/scenario_forge/task/__init__.py`: task compiler public exports.
- Create `src/scenario_forge/task/predicates.py`: predicate dataclasses, scene binding validation, YAML helpers.
- Create `src/scenario_forge/task/metrics.py`: primary success metric generation and loading.
- Create `src/scenario_forge/task/task_compiler.py`: `pick_place` compiler from scene instances to task artifacts.
- Create `src/scenario_forge/generation/workflows/__init__.py`: workflow namespace.
- Create `src/scenario_forge/generation/workflows/task_graph.py`: task graph dataclasses and builder.
- Create `src/scenario_forge/adapters/ebench/__init__.py`: EBench adapter exports.
- Create `src/scenario_forge/adapters/ebench/schema.py`: schema constants and descriptor builders.
- Create `src/scenario_forge/adapters/ebench/report.py`: adapter report dataclasses and writer.
- Create `src/scenario_forge/adapters/ebench/exporter.py`: package and suite exporters.
- Add JSON schemas under `src/scenario_forge/schemas/jsonschema/`: `task-v0.2`, `task-graph-v0.2`, `predicates-v0.2`, `metrics-v0.2`, `ebench-export-v0.1`.
- Modify `src/scenario_forge/cli.py`: add `task compile` and `export ebench`.
- Modify `src/scenario_forge/scaffold.py`: generate Phase 4 primary success metric and compile task artifacts.
- Modify `Makefile`: smoke test `task compile` and `export ebench`.
- Modify docs and add `examples/ebench_export_package/`.

---

### Task 1: Phase 4 Task Compiler Core

**Files:**
- Create: `src/scenario_forge/task/__init__.py`
- Create: `src/scenario_forge/task/predicates.py`
- Create: `src/scenario_forge/task/metrics.py`
- Create: `src/scenario_forge/task/task_compiler.py`
- Create: `src/scenario_forge/generation/workflows/__init__.py`
- Create: `src/scenario_forge/generation/workflows/task_graph.py`
- Test: `tests/test_task_compiler.py`

- [x] **Step 1: Write failing tests**

Add tests that call `compile_task_artifacts(package_dir, task_family="pick_place")`, assert generated files exist, and check:

```python
task = yaml.safe_load((package_dir / "task" / "task.yaml").read_text(encoding="utf-8"))
predicates = yaml.safe_load((package_dir / "task" / "predicates.yaml").read_text(encoding="utf-8"))
metrics = yaml.safe_load((package_dir / "metrics" / "metrics.yaml").read_text(encoding="utf-8"))

assert task["task_family"] == "pick_place"
assert predicates["success_predicates"][0]["object"] == "object_001"
assert predicates["success_predicates"][0]["zone"] == "target_zone"
assert metrics["metrics"][0]["role"] == "primary_success"
assert metrics["metrics"][0]["predicate"] == "object_in_zone"
assert metrics["metrics"][0]["adapter_hints"]["ebench"]["success_metric"] == "task_success"
```

Add a second test that removes the `target` tag from every scene instance and expects:

```python
with pytest.raises(TaskCompileError, match="Missing required scene role for pick_place: target_zone"):
    compile_task_artifacts(package_dir, task_family="pick_place")
```

Run: `python -m pytest tests/test_task_compiler.py -q`
Expected: FAIL because `scenario_forge.task.task_compiler` does not exist.

- [x] **Step 2: Implement minimal compiler**

Implement:

```python
@dataclass(frozen=True)
class TaskCompileResult:
    package_root: Path
    artifacts: tuple[Path, ...]
    object_instance_id: str
    target_zone_id: str

def compile_task_artifacts(package_root: str | Path, task_family: str = "pick_place") -> TaskCompileResult:
    instances = load_scene_instances(package_root / "scene" / "instances.yaml")
    object_instance = first instance with role manipulated_object or semantic tag pickable
    target_zone = first instance with semantic tag target or zone, or role target_region
    write task/task.yaml, task/task_graph.yaml, task/predicates.yaml, task/safety_rules.yaml, metrics/metrics.yaml
```

Run: `python -m pytest tests/test_task_compiler.py -q`
Expected: PASS.

---

### Task 2: Phase 4 CLI, Schemas, Scaffold, And Checks

**Files:**
- Modify: `src/scenario_forge/cli.py`
- Modify: `src/scenario_forge/scaffold.py`
- Create schema JSON files for task, task graph, predicates, metrics.
- Modify: `tests/test_cli.py`
- Modify: `tests/test_asset_schemas.py`

- [x] **Step 1: Write failing CLI and schema tests**

Add CLI test:

```python
result = run_cli("task", "compile", "--package", str(package_dir), "--family", "pick_place", cwd=tmp_path)
assert result.returncode == 0
assert "Task artifacts written:" in result.stdout
```

Add schema parse test for `task-v0.2`, `task-graph-v0.2`, `predicates-v0.2`, `metrics-v0.2`.

Run: `python -m pytest tests/test_cli.py::test_cli_task_compile_writes_pick_place_artifacts tests/test_asset_schemas.py::test_task_phase4_schema_artifacts_exist_and_parse -q`
Expected: FAIL because CLI command and schemas do not exist.

- [x] **Step 2: Add CLI and schema artifacts**

Register:

```text
scenario-forge task compile --package ./pkg --family pick_place
```

Create JSON schemas with draft 2020-12, `schema_version` consts, and required key coverage.

Run the same focused tests.
Expected: PASS.

- [x] **Step 3: Update scaffold**

Call `compile_task_artifacts(root, task_family="pick_place")` from scaffold after scene instances exist. Ensure starter `metrics/metrics.yaml` contains a primary success metric with EBench hints.

Run: `python -m pytest tests/test_cli.py::test_cli_scaffold_creates_checkable_starter_package -q`
Expected: PASS and scaffold metrics include `role: primary_success`.

---

### Task 3: Phase 5 EBench Package Exporter

**Files:**
- Create: `src/scenario_forge/adapters/ebench/__init__.py`
- Create: `src/scenario_forge/adapters/ebench/schema.py`
- Create: `src/scenario_forge/adapters/ebench/report.py`
- Create: `src/scenario_forge/adapters/ebench/exporter.py`
- Test: `tests/test_ebench_adapter.py`

- [x] **Step 1: Write failing package export tests**

Use `scaffold_starter_package`, `compile_task_artifacts`, and `export_ebench_package`. Assert:

```python
result = export_ebench_package(package_dir)
export_yaml = yaml.safe_load((package_dir / "adapters" / "ebench" / "package.yaml").read_text(encoding="utf-8"))
report = yaml.safe_load((package_dir / "adapters" / "ebench" / "adapter_report.yaml").read_text(encoding="utf-8"))

assert result.ok
assert export_yaml["schema_version"] == "ebench-scenario-export/v0.1"
assert export_yaml["source_package"]["package_id"] == "tabletop_pick_place_starter"
assert export_yaml["runtime_hints"]["success_metric"] == "task_success"
assert report["status"] == "passed"
assert "scene_usd" in report["entrypoints"]
assert "asset_lock" in report["entrypoints"]
```

Add blocker tests for missing `locks/asset_lock.yaml`, missing `scene/main.usda`, and no primary success metric.

Run: `python -m pytest tests/test_ebench_adapter.py -q`
Expected: FAIL because `scenario_forge.adapters.ebench.exporter` does not exist.

- [x] **Step 2: Implement package exporter**

Implement:

```python
@dataclass(frozen=True)
class EBenchExportResult:
    ok: bool
    output_dir: Path
    artifacts: tuple[Path, ...]
    blockers: tuple[str, ...]

def export_ebench_package(package_dir: str | Path, out_dir: str | Path | None = None) -> EBenchExportResult:
    manifest = load_package_manifest(package_dir)
    validate manifest targets include ebench
    validate package static files and asset lock with validate_package
    load metrics/metrics.yaml and require metric role primary_success
    write adapters/ebench/package.yaml, task_entrypoint.yaml, adapter_report.yaml
```

Run: `python -m pytest tests/test_ebench_adapter.py -q`
Expected: PASS.

---

### Task 4: EBench CLI, Suite Export, Schema, Example, And Docs

**Files:**
- Modify: `src/scenario_forge/cli.py`
- Modify: `Makefile`
- Create: `src/scenario_forge/schemas/jsonschema/ebench-export-v0.1.schema.json`
- Create: `examples/ebench_export_package/README.md`
- Create: `examples/ebench_export_package/adapters/ebench/package.yaml`
- Create: `examples/ebench_export_package/adapters/ebench/task_entrypoint.yaml`
- Create: `examples/ebench_export_package/adapters/ebench/adapter_report.yaml`
- Modify: docs and README.
- Test: `tests/test_cli.py`
- Test: `tests/test_asset_schemas.py`

- [x] **Step 1: Write failing CLI, suite, and schema tests**

Add CLI package export test:

```python
result = run_cli("export", "ebench", "--package", str(package_dir), cwd=tmp_path)
assert result.returncode == 0
assert "EBench package export written:" in result.stdout
```

Add suite export test:

```python
suite_manifest = {"schema_version": "scenario-suite/v0.1", "packages": [{"package_id": "starter", "path": str(package_dir), "split": "smoke", "difficulty": "easy", "task_family": "pick_place"}]}
result = run_cli("export", "ebench", "--suite", str(suite_dir), cwd=tmp_path)
assert (suite_dir / "adapters" / "ebench" / "task_index.yaml").exists()
```

Add schema parse test for `ebench-export-v0.1`.

Run focused tests and expect FAIL because CLI suite/export schema are missing.

- [x] **Step 2: Implement CLI and suite export**

Register:

```text
scenario-forge export ebench --package ./pkg
scenario-forge export ebench --suite ./suite
```

Suite export reads `suite_manifest.yaml` under the suite dir and writes `suite_export.yaml`, `task_index.yaml`, and `adapter_report.yaml`.

Run focused tests and expect PASS.

- [x] **Step 3: Update smoke/docs/example**

Update `Makefile package-smoke` to run:

```bash
scenario-forge task compile --package "$(SMOKE_OUT)" --family pick_place
scenario-forge export ebench --package "$(SMOKE_OUT)"
```

Update roadmap Phase 4/5 statuses, `docs/design/ebench-adapter.md`, `docs/operations/development-checks.md`, and README current status.

Run: `make check`
Expected:  all tests, ruff, smoke, and diff check pass.
