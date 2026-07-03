# USD Scene Compiler Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build the Phase 3 USD Scene Compiler so a v0.2 package can compile `scene/instances.yaml` and `locks/asset_lock.yaml` into a static `scene/main.usda` reference stage.

**Architecture:** Keep the compiler in pure package code under `scenario_forge.scene` and `scenario_forge.validation`, with no simulator SDK imports. The compiler reads scene instance YAML, resolves asset IDs through the asset lock, writes a conservative USDA reference stage, and verifies references plus predicate bindings through static text/YAML checks.

**Tech Stack:** Python 3.10, PyYAML, dataclasses, pathlib, pytest, ruff.

---

## File Structure

- Create `src/scenario_forge/scene/__init__.py`: public scene compiler exports.
- Create `src/scenario_forge/scene/instance_binding.py`: scene instance dataclasses, YAML loader, duplicate ID and pose validation.
- Create `src/scenario_forge/scene/usd_paths.py`: safe USD prim names, USDA literal formatting, scene-relative reference paths.
- Create `src/scenario_forge/scene/usd_compiler.py`: asset-lock-backed USDA stage writer.
- Create `src/scenario_forge/validation/__init__.py`: validation package marker.
- Create `src/scenario_forge/validation/usd_checks.py`: static USD reference and predicate binding checks.
- Modify `src/scenario_forge/assets/lock.py`: expose `load_asset_lock_file(path)` for CLI-provided lock paths.
- Modify `src/scenario_forge/cli.py`: add `scenario-forge scene compile`.
- Modify `src/scenario_forge/scaffold.py`: make starter scaffold contain lockable placeholder USD assets and a compiled starter `scene/main.usda`.
- Create `src/scenario_forge/schemas/jsonschema/scene-instances-v0.2.schema.json`: schema artifact for scene instances.
- Modify tests and docs for Phase 3 status and CLI behavior.

---

### Task 1: Scene Instance Loader And Schema

**Files:**
- Create: `src/scenario_forge/scene/__init__.py`
- Create: `src/scenario_forge/scene/instance_binding.py`
- Create: `src/scenario_forge/schemas/jsonschema/scene-instances-v0.2.schema.json`
- Test: `tests/test_scene_compiler.py`
- Modify: `tests/test_asset_schemas.py`

- [x] **Step 1: Write the failing loader and schema tests**

```python
def test_load_scene_instances_rejects_duplicate_instance_ids(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "scene" / "instances.yaml",
        {
            "schema_version": "scene-instances/v0.2",
            "instances": [
                {"id": "object_001", "asset_id": "asset_a", "pose": {"xyz": [0, 0, 0], "wxyz": [1, 0, 0, 0]}},
                {"id": "object_001", "asset_id": "asset_b", "pose": {"xyz": [1, 0, 0], "wxyz": [1, 0, 0, 0]}},
            ],
        },
    )

    with pytest.raises(SceneInstanceError, match="Duplicate scene instance id: object_001"):
        load_scene_instances(tmp_path / "scene" / "instances.yaml")
```

Run: `pytest tests/test_scene_compiler.py::test_load_scene_instances_rejects_duplicate_instance_ids -q`
Expected: FAIL because `scenario_forge.scene.instance_binding` does not exist.

- [x] **Step 2: Implement the minimal loader**

```python
@dataclass(frozen=True)
class SceneInstance:
    instance_id: str
    asset_id: str
    role: str
    xyz: tuple[float, float, float]
    wxyz: tuple[float, float, float, float]
    semantic_tags: tuple[str, ...]


def load_scene_instances(path: str | Path) -> tuple[SceneInstance, ...]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    # validate schema_version, instances mapping/list shape, duplicate IDs,
    # non-empty asset IDs, pose lengths, and string semantic tags.
```

Run: `pytest tests/test_scene_compiler.py::test_load_scene_instances_rejects_duplicate_instance_ids -q`
Expected: PASS.

- [x] **Step 3: Add schema artifact coverage**

Run: `pytest tests/test_asset_schemas.py::test_scene_instances_v02_schema_artifact_exists_and_parses -q`
Expected: FAIL until `scene-instances-v0.2.schema.json` exists with `schema_version` const `scene-instances/v0.2` and required `instances`.

- [x] **Step 4: Add the JSON schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "instances"],
  "properties": {
    "schema_version": {"const": "scene-instances/v0.2"},
    "instances": {"type": "array", "items": {"type": "object"}}
  }
}
```

Run: `pytest tests/test_asset_schemas.py::test_scene_instances_v02_schema_artifact_exists_and_parses -q`
Expected: PASS.

---

### Task 2: USDA Compiler And Static Checks

**Files:**
- Create: `src/scenario_forge/scene/usd_paths.py`
- Create: `src/scenario_forge/scene/usd_compiler.py`
- Create: `src/scenario_forge/validation/__init__.py`
- Create: `src/scenario_forge/validation/usd_checks.py`
- Modify: `src/scenario_forge/assets/lock.py`
- Test: `tests/test_scene_compiler.py`

- [x] **Step 1: Write the failing compile test**

```python
def test_compile_usd_scene_writes_locked_references_and_custom_data(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)

    result = compile_usd_scene(
        package_root=package_dir,
        instances_path=package_dir / "scene" / "instances.yaml",
        asset_lock_path=package_dir / "locks" / "asset_lock.yaml",
        out_path=package_dir / "scene" / "main.usda",
    )

    source = result.path.read_text(encoding="utf-8")
    assert result.path == package_dir / "scene" / "main.usda"
    assert 'def Xform "object_001"' in source
    assert "instance_id = \"object_001\"" in source
    assert "asset_id = \"sample_bottle_50ml_v1\"" in source
    assert "@../assets/objects/sample_bottle_50ml_v1/model.usd@" in source
```

Run: `pytest tests/test_scene_compiler.py::test_compile_usd_scene_writes_locked_references_and_custom_data -q`
Expected: FAIL because `compile_usd_scene` does not exist.

- [x] **Step 2: Implement minimal USDA writing**

```python
@dataclass(frozen=True)
class USDSceneCompileResult:
    path: Path
    instance_count: int
    references: tuple[str, ...]


def compile_usd_scene(package_root: str | Path, instances_path: str | Path, asset_lock_path: str | Path, out_path: str | Path) -> USDSceneCompileResult:
    instances = load_scene_instances(instances_path)
    lock = load_asset_lock_file(asset_lock_path)
    # fail on missing asset_id, write root World, one Xform prim per instance,
    # scene-relative references, customData, pose ops, a RobotSpawn prim,
    # a DistantLight, and a Camera.
```

Run: `pytest tests/test_scene_compiler.py::test_compile_usd_scene_writes_locked_references_and_custom_data -q`
Expected: PASS.

- [x] **Step 3: Write failing static check tests**

```python
def test_check_usd_scene_rejects_unlocked_reference(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)
    compile_usd_scene(package_dir, package_dir / "scene" / "instances.yaml", package_dir / "locks" / "asset_lock.yaml", package_dir / "scene" / "main.usda")
    (package_dir / "scene" / "main.usda").write_text('#usda 1.0\nrel references = @../assets/objects/extra/model.usd@\n', encoding="utf-8")

    report = check_usd_scene(package_dir, package_dir / "scene" / "main.usda", package_dir / "locks" / "asset_lock.yaml", package_dir / "scene" / "instances.yaml")

    assert not report.ok
    assert "USD reference is not locked: assets/objects/extra/model.usd" in report.messages
```

Run: `pytest tests/test_scene_compiler.py::test_check_usd_scene_rejects_unlocked_reference -q`
Expected: FAIL because `check_usd_scene` does not exist.

- [x] **Step 4: Implement static checks**

```python
@dataclass(frozen=True)
class USDStaticCheckReport:
    ok: bool
    messages: tuple[str, ...]


def check_usd_scene(package_root: str | Path, scene_path: str | Path, asset_lock_path: str | Path, instances_path: str | Path, predicates_path: str | Path | None = None) -> USDStaticCheckReport:
    # confirm scene exists, every text reference is locked, every instance has
    # a prim plus customData, and optional predicates bind to known instance IDs.
```

Run: `pytest tests/test_scene_compiler.py -q`
Expected: PASS.

---

### Task 3: CLI, Scaffold, Docs, And Full Verification

**Files:**
- Modify: `src/scenario_forge/cli.py`
- Modify: `src/scenario_forge/scaffold.py`
- Modify: `docs/design/usd-scene-compiler.md`
- Modify: `docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md`
- Modify: `docs/operations/development-checks.md`
- Test: `tests/test_cli.py`

- [x] **Step 1: Write failing CLI test**

```python
def test_cli_scene_compile_writes_usda_for_locked_instances(tmp_path: Path) -> None:
    package_dir = make_scene_package(tmp_path)

    result = run_cli(
        "scene",
        "compile",
        "--instances",
        str(package_dir / "scene" / "instances.yaml"),
        "--asset-lock",
        str(package_dir / "locks" / "asset_lock.yaml"),
        "--out",
        str(package_dir / "scene" / "main.usda"),
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Scene written:" in result.stdout
    assert 'def Xform "object_001"' in (package_dir / "scene" / "main.usda").read_text(encoding="utf-8")
```

Run: `pytest tests/test_cli.py::test_cli_scene_compile_writes_usda_for_locked_instances -q`
Expected: FAIL because `scene compile` is not registered.

- [x] **Step 2: Add CLI command**

```python
scene_parser = subparsers.add_parser("scene", help="USD scene compiler commands")
scene_subparsers = scene_parser.add_subparsers(dest="scene_command", required=True)
compile_parser = scene_subparsers.add_parser("compile", help="Compile scene instances to USDA")
compile_parser.add_argument("--instances", required=True)
compile_parser.add_argument("--asset-lock", required=True)
compile_parser.add_argument("--out", required=True)
```

Run: `pytest tests/test_cli.py::test_cli_scene_compile_writes_usda_for_locked_instances -q`
Expected: PASS.

- [x] **Step 3: Make scaffold compile-ready**

Write starter placeholder USD assets under `assets/objects/starter_rigid_object/model.usd` and `assets/markers/starter_target_marker/model.usd`, include them in `assets/asset_manifest.yaml`, include matching lock entries in `locks/asset_lock.yaml`, and write a compiled `scene/main.usda` referencing those locked paths.

Run: `pytest tests/test_cli.py::test_cli_scaffold_creates_checkable_starter_package -q`
Expected: PASS and the generated `scene/main.usda` contains `@../assets/`.

- [x] **Step 4: Update docs**

Update the Phase 3 status in the roadmap and `docs/design/usd-scene-compiler.md` from draft to implemented for static USDA compilation. Add the `scene compile` smoke command to `docs/operations/development-checks.md`.

- [x] **Step 5: Full verification and commit**

Run: `make check`
Expected: tests pass, ruff passes, package smoke passes, `git diff --check` passes.

Run:
```bash
git status --short
git add docs src tests
git commit -m "feat: add usd scene compiler"
```

Expected: a clean commit containing Phase 3 implementation, tests, schema, docs, and this plan.
