# Package v0.2 Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 2 package v0.2 format support so Scenario Forge can scaffold, load, validate, and document the product package contract.

**Architecture:** Keep package-format behavior in `src/scenario_forge/package.py` and scaffold generation in `src/scenario_forge/scaffold.py`. Preserve v0.1 bootstrap loading while making the default scaffold v0.2, with simulator-neutral validation only.

**Tech Stack:** Python dataclasses, PyYAML, JSON Schema artifacts, pytest, existing CLI entry points.

---

### File Structure

- Modify `src/scenario_forge/package.py` to support both `scenario-package/v0.1` and `scenario-package/v0.2`.
- Modify `src/scenario_forge/scaffold.py` so `package scaffold` emits a v0.2 starter layout.
- Modify `src/scenario_forge/cli.py` so asset checks discover v0.2 `entrypoints.scene_usd`.
- Create `src/scenario_forge/schemas/jsonschema/scenario-package-v0.2.schema.json`.
- Create `src/scenario_forge/schemas/v2/__init__.py` and `src/scenario_forge/schemas/v2/package.py` as v0.2 helper exports.
- Modify `tests/test_package_validator.py`, `tests/test_cli.py`, and `tests/test_asset_schemas.py`.
- Update `README.md`, `docs/design/package-v0.2.md`, `docs/design/scenario-package-contract.md`, and the roadmap status block.

### Task 1: v0.2 Manifest Loader

**Files:**
- Modify: `tests/test_package_validator.py`
- Modify: `src/scenario_forge/package.py`

- [ ] **Step 1: Write failing tests**

```python
def test_v02_package_loads_manifest_contract(tmp_path: Path) -> None:
    make_v02_package(tmp_path)

    manifest = load_package_manifest(tmp_path)

    assert manifest.schema_version == "scenario-package/v0.2"
    assert manifest.package_id == "workbench_pick_place_0001"
    assert manifest.scenario_id == "workbench_pick_place_0001"
    assert manifest.package_mode == "fat"
    assert manifest.targets == ("ebench", "embodied-eval-os")
    assert manifest.exports == ("ebench", "embodied-eval-os")
    assert manifest.entrypoints["scene_usd"] == "scene/main.usda"
    assert manifest.files["scene"] == "scene/main.usda"
    assert manifest.assets["lock"] == "locks/asset_lock.yaml"
    assert manifest.validation["minimum_required_level"] == "adapter_static_validated"
    assert manifest.provenance["summary"] == "provenance/provenance.yaml"


def test_v02_manifest_rejects_invalid_package_mode(tmp_path: Path) -> None:
    make_v02_package(tmp_path)
    manifest = yaml.safe_load((tmp_path / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["package_mode"] = "thin"
    write_yaml(tmp_path / "manifest.yaml", manifest)

    with pytest.raises(PackageError, match="package_mode"):
        load_package_manifest(tmp_path)
```

- [ ] **Step 2: Run red tests**

Run: `python -m pytest tests/test_package_validator.py::test_v02_package_loads_manifest_contract tests/test_package_validator.py::test_v02_manifest_rejects_invalid_package_mode -q`

Expected: fail because only `scenario-package/v0.1` is supported.

- [ ] **Step 3: Implement loader support**

Add v0.2 constants, a version-dispatching loader, v0.2 field validation, legacy aliases (`scenario_id`, `exports`, `files`), and clear `PackageError` messages for invalid schema fields.

- [ ] **Step 4: Run green tests**

Run: `python -m pytest tests/test_package_validator.py::test_v02_package_loads_manifest_contract tests/test_package_validator.py::test_v02_manifest_rejects_invalid_package_mode tests/test_package_validator.py::test_valid_package_loads_manifest_and_reports_all_referenced_files -q`

Expected: pass and preserve v0.1 behavior.

### Task 2: v0.2 Package Validation

**Files:**
- Modify: `tests/test_package_validator.py`
- Modify: `src/scenario_forge/package.py`

- [ ] **Step 1: Write failing tests**

```python
def test_v02_validate_package_requires_entrypoint_files_and_asset_lock(tmp_path: Path) -> None:
    make_v02_package(tmp_path)

    report = validate_package(tmp_path)

    assert report.ok
    assert tmp_path / "generation_plan.yaml" in report.required_files
    assert tmp_path / "scene" / "main.usda" in report.required_files
    assert tmp_path / "locks" / "asset_lock.yaml" in report.required_files


def test_v02_validate_package_rejects_missing_metrics_file(tmp_path: Path) -> None:
    make_v02_package(tmp_path)
    (tmp_path / "metrics" / "metrics.yaml").unlink()

    report = validate_package(tmp_path)

    assert not report.ok
    assert "Missing referenced file: metrics/metrics.yaml" in report.messages


def test_v02_ebench_package_requires_known_validation_level(tmp_path: Path) -> None:
    make_v02_package(tmp_path)
    manifest = yaml.safe_load((tmp_path / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["validation"]["minimum_required_level"] = "not_run"
    write_yaml(tmp_path / "manifest.yaml", manifest)

    with pytest.raises(PackageError, match="minimum_required_level"):
        load_package_manifest(tmp_path)
```

- [ ] **Step 2: Run red tests**

Run: `python -m pytest tests/test_package_validator.py::test_v02_validate_package_requires_entrypoint_files_and_asset_lock tests/test_package_validator.py::test_v02_validate_package_rejects_missing_metrics_file tests/test_package_validator.py::test_v02_ebench_package_requires_known_validation_level -q`

Expected: fail because v0.2 validation is not implemented.

- [ ] **Step 3: Implement validation**

For v0.2, validate required entrypoints, `assets.manifest`, `assets.lock`, `validation.report`, and `provenance.summary`. Always run `check_asset_lock` for v0.2 packages because formal v0.2 packages carry an asset lock.

- [ ] **Step 4: Run green tests**

Run: `python -m pytest tests/test_package_validator.py -q`

Expected: all package validator tests pass.

### Task 3: v0.2 Scaffold and CLI Scene Discovery

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/scenario_forge/scaffold.py`
- Modify: `src/scenario_forge/cli.py`

- [ ] **Step 1: Write failing tests**

```python
def test_cli_scaffold_creates_v02_starter_package(tmp_path: Path) -> None:
    out_dir = tmp_path / "starter"

    scaffold = run_cli("package", "scaffold", "--out", str(out_dir), cwd=tmp_path)
    check = run_cli("package", "check", str(out_dir), cwd=tmp_path)

    manifest = yaml.safe_load((out_dir / "manifest.yaml").read_text(encoding="utf-8"))
    assert scaffold.returncode == 0, scaffold.stderr
    assert check.returncode == 0, check.stdout + check.stderr
    assert manifest["schema_version"] == "scenario-package/v0.2"
    assert manifest["entrypoints"]["scene_usd"] == "scene/main.usda"
    assert (out_dir / "locks" / "asset_lock.yaml").exists()
    assert "Package OK" in check.stdout


def test_cli_assets_check_uses_v02_manifest_scene_for_usd_reference_check(tmp_path: Path) -> None:
    package_dir = make_asset_package_on_disk(tmp_path)
    add_v02_manifest_with_scene(package_dir)
    extra = package_dir / "assets" / "objects" / "extra" / "model.usd"
    extra.parent.mkdir(parents=True)
    extra.write_text("#usda 1.0\n", encoding="utf-8")
    (package_dir / "scene" / "main.usda").write_text(
        '#usda 1.0\nrel references = @../assets/objects/extra/model.usd@\n',
        encoding="utf-8",
    )
    lock = run_cli("assets", "lock", str(package_dir), cwd=tmp_path)

    result = run_cli("assets", "check", str(package_dir), cwd=tmp_path)

    assert lock.returncode == 0, lock.stderr
    assert result.returncode == 1
    assert "USD reference is not locked: assets/objects/extra/model.usd" in result.stdout
```

- [ ] **Step 2: Run red tests**

Run: `python -m pytest tests/test_cli.py::test_cli_scaffold_creates_v02_starter_package tests/test_cli.py::test_cli_assets_check_uses_v02_manifest_scene_for_usd_reference_check -q`

Expected: fail because scaffold emits v0.1 and CLI only checks `files.scene`.

- [ ] **Step 3: Implement scaffold and CLI support**

Generate the v0.2 directory tree with tiny YAML placeholders, an empty asset manifest, and an empty asset lock. Update `_package_scene_paths()` to use `manifest.scene_path`.

- [ ] **Step 4: Run green tests**

Run: `python -m pytest tests/test_cli.py -q`

Expected: CLI tests pass.

### Task 4: Schema Artifact and Docs

**Files:**
- Modify: `tests/test_asset_schemas.py`
- Create: `src/scenario_forge/schemas/jsonschema/scenario-package-v0.2.schema.json`
- Create: `src/scenario_forge/schemas/v2/__init__.py`
- Create: `src/scenario_forge/schemas/v2/package.py`
- Modify: `README.md`
- Modify: `docs/design/package-v0.2.md`
- Modify: `docs/design/scenario-package-contract.md`
- Modify: `docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md`

- [ ] **Step 1: Write failing schema test**

```python
def test_schema_package_v02_artifact_exists_and_parses() -> None:
    schema_path = Path("src/scenario_forge/schemas/jsonschema/scenario-package-v0.2.schema.json")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == "scenario-package/v0.2"
    assert "entrypoints" in schema["required"]
    assert "assets" in schema["required"]
```

- [ ] **Step 2: Run red test**

Run: `python -m pytest tests/test_asset_schemas.py::test_schema_package_v02_artifact_exists_and_parses -q`

Expected: fail because the v0.2 schema artifact does not exist.

- [ ] **Step 3: Add schema/helper/docs**

Add a JSON Schema matching the implemented manifest contract, a v2 schema helper export, and update docs from draft status to Phase 2 package contract implemented for scaffold/load/check scope.

- [ ] **Step 4: Run green test and full verification**

Run:

```bash
python -m pytest tests/test_asset_schemas.py -q
make check
```

Expected: schema tests and full project checks pass.

### Completion Audit

- `package scaffold` must emit `scenario-package/v0.2` by default.
- `load_package_manifest` must accept both v0.1 and v0.2.
- v0.2 manifests must expose package ID, mode, targets, entrypoints, assets, validation, and provenance through typed helpers.
- v0.2 package validation must check referenced entrypoint and artifact files.
- v0.2 packages must require and validate `locks/asset_lock.yaml`.
- CLI asset checks must inspect the v0.2 scene entrypoint.
- JSON Schema artifact for `scenario-package/v0.2` must exist.
- Docs must say the Phase 2 package-format scope is implemented, while USD compiler and EBench adapter remain future work.
- `make check` must pass before marking the goal complete.
