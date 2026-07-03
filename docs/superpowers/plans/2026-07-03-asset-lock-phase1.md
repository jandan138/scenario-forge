# Asset Lock Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 1 Fat Package / Asset Lock basics so packages can read asset manifests, generate and check asset locks, validate local assets, and require locks during package checks.

**Architecture:** Keep asset reproducibility logic inside `src/scenario_forge/assets/` with small modules for checksums, licenses, manifests, and locks. Keep package validation simulator-free and integrate asset-lock checks only through explicit options so the v0.1 bootstrap lane remains compatible.

**Tech Stack:** Python 3.10, PyYAML, dataclasses, pathlib, argparse, pytest, Ruff.

---

### Task 1: Asset Checksum Helper

**Files:**
- Create: `src/scenario_forge/assets/checksum.py`
- Test: `tests/test_asset_lock.py`

- [ ] **Step 1: Write the failing test**

```python
def test_compute_sha256_returns_prefixed_digest(tmp_path: Path) -> None:
    asset = tmp_path / "assets" / "objects" / "sample" / "model.usd"
    asset.parent.mkdir(parents=True)
    asset.write_text("#usda 1.0\n", encoding="utf-8")

    assert compute_sha256(asset).startswith("sha256:")
    assert compute_sha256(asset) == compute_sha256(asset)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_asset_lock.py::test_compute_sha256_returns_prefixed_digest -q`
Expected: FAIL because `scenario_forge.assets.checksum` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def compute_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_asset_lock.py::test_compute_sha256_returns_prefixed_digest -q`
Expected: PASS.

### Task 2: License Policy Helper

**Files:**
- Create: `src/scenario_forge/assets/licenses.py`
- Test: `tests/test_asset_lock.py`

- [ ] **Step 1: Write the failing test**

```python
def test_license_policy_rejects_missing_license() -> None:
    assert validate_license("CC-BY-4.0") is None
    assert validate_license("") == "Missing license"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_asset_lock.py::test_license_policy_rejects_missing_license -q`
Expected: FAIL because `scenario_forge.assets.licenses` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations


def validate_license(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "Missing license"
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_asset_lock.py::test_license_policy_rejects_missing_license -q`
Expected: PASS.

### Task 3: Asset Manifest Reader

**Files:**
- Modify: `src/scenario_forge/assets/manifest.py`
- Test: `tests/test_asset_lock.py`

- [ ] **Step 1: Write the failing test**

```python
def test_load_asset_manifest_reads_assets_and_rejects_missing_license(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "assets" / "asset_manifest.yaml",
        {
            "schema_version": "asset-manifest/v0.2",
            "assets": [
                {
                    "asset_id": "sample_bottle_50ml_v1",
                    "role": "manipulated_object",
                    "asset_type": "bottle",
                    "canonical_usd": "assets/objects/sample_bottle_50ml_v1/model.usd",
                    "license": "CC-BY-4.0",
                    "sha256": "sha256:" + "0" * 64,
                }
            ],
        },
    )

    manifest = load_asset_manifest(tmp_path)

    assert manifest.assets[0].asset_id == "sample_bottle_50ml_v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_asset_lock.py::test_load_asset_manifest_reads_assets_and_rejects_missing_license -q`
Expected: FAIL because `load_asset_manifest` does not exist.

- [ ] **Step 3: Write minimal implementation**

Add `AssetManifestEntry`, `AssetManifest`, `AssetManifestError`, and `load_asset_manifest(root)` to `manifest.py`. The loader reads `assets/asset_manifest.yaml`, validates schema version, requires a list of mapping assets, requires `asset_id`, `canonical_usd`, `license`, and `sha256`, rejects duplicate `asset_id`, and stores unknown fields in `metadata`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_asset_lock.py -q`
Expected: PASS for asset manifest and existing asset reference tests.

### Task 4: Asset Lock Generator and Checker

**Files:**
- Create: `src/scenario_forge/assets/lock.py`
- Test: `tests/test_asset_lock.py`

- [ ] **Step 1: Write failing tests**

```python
def test_generate_asset_lock_materializes_manifest_assets(tmp_path: Path) -> None:
    model = make_asset_manifest_package(tmp_path, content="#usda 1.0\n")

    lock = generate_asset_lock(tmp_path)

    assert lock.assets["sample_bottle_50ml_v1"].resolved_path == str(model.relative_to(tmp_path))
    assert lock.assets["sample_bottle_50ml_v1"].content_sha256 == compute_sha256(model)


def test_check_asset_lock_reports_checksum_and_missing_file(tmp_path: Path) -> None:
    model = make_asset_manifest_package(tmp_path, content="#usda 1.0\n")
    write_asset_lock(tmp_path, generate_asset_lock(tmp_path))
    model.write_text("changed\n", encoding="utf-8")

    report = check_asset_lock(tmp_path)

    assert not report.ok
    assert "Checksum mismatch for asset sample_bottle_50ml_v1" in report.messages
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_asset_lock.py::test_generate_asset_lock_materializes_manifest_assets tests/test_asset_lock.py::test_check_asset_lock_reports_checksum_and_missing_file -q`
Expected: FAIL because lock helpers do not exist.

- [ ] **Step 3: Write minimal implementation**

Implement `AssetLockEntry`, `AssetLock`, `AssetLockReport`, `generate_asset_lock(root)`, `load_asset_lock(root)`, `write_asset_lock(root, lock)`, and `check_asset_lock(root)`. Use manifest entries, compute sha256 for package-local files, reject missing license, missing file, checksum mismatch, and path escape.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_asset_lock.py -q`
Expected: PASS.

### Task 5: USD Reference Check

**Files:**
- Modify: `src/scenario_forge/assets/lock.py`
- Test: `tests/test_asset_lock.py`

- [ ] **Step 1: Write failing test**

```python
def test_asset_lock_check_rejects_usd_reference_not_in_lock(tmp_path: Path) -> None:
    make_asset_manifest_package(tmp_path, content="#usda 1.0\n")
    extra = tmp_path / "assets" / "objects" / "extra" / "model.usd"
    extra.parent.mkdir(parents=True)
    extra.write_text("#usda 1.0\n", encoding="utf-8")
    (tmp_path / "scene.usda").write_text(
        '#usda 1.0\nrel references = @assets/objects/extra/model.usd@\n',
        encoding="utf-8",
    )
    write_asset_lock(tmp_path, generate_asset_lock(tmp_path))

    report = check_asset_lock(tmp_path, scene_paths=("scene.usda",))

    assert not report.ok
    assert "USD reference is not locked: assets/objects/extra/model.usd" in report.messages
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_asset_lock.py::test_asset_lock_check_rejects_usd_reference_not_in_lock -q`
Expected: FAIL because USD reference checking is missing.

- [ ] **Step 3: Write minimal implementation**

Add a small USDA reference scanner for `@...@` asset references. It checks only package-local `.usd` or `.usda` paths and reports references not present in locked resolved paths.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_asset_lock.py -q`
Expected: PASS.

### Task 6: Package Check Integration

**Files:**
- Modify: `src/scenario_forge/package.py`
- Modify: `src/scenario_forge/cli.py`
- Test: `tests/test_package_validator.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

```python
def test_package_check_requires_asset_lock_for_ebench_package(tmp_path: Path) -> None:
    make_minimal_package(tmp_path)

    report = validate_package(tmp_path, require_asset_lock=True)

    assert not report.ok
    assert "Missing asset lock: locks/asset_lock.yaml" in report.messages
```

```python
def test_cli_package_check_require_asset_lock_returns_nonzero_when_missing(tmp_path: Path) -> None:
    package_dir = tmp_path / "starter"
    scaffold = run_cli("package", "scaffold", "--out", str(package_dir), cwd=tmp_path)

    result = run_cli("package", "check", str(package_dir), "--require-asset-lock", cwd=tmp_path)

    assert scaffold.returncode == 0, scaffold.stderr
    assert result.returncode == 1
    assert "Missing asset lock: locks/asset_lock.yaml" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_package_validator.py::test_package_check_requires_asset_lock_for_ebench_package tests/test_cli.py::test_cli_package_check_require_asset_lock_returns_nonzero_when_missing -q`
Expected: FAIL because the option and validator argument do not exist.

- [ ] **Step 3: Write minimal implementation**

Add `require_asset_lock: bool = False` to `validate_package`. When enabled, run `check_asset_lock(package_root, scene_paths=manifest scene file if present)` and append messages. Add CLI option `--require-asset-lock` to `package check`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_package_validator.py tests/test_cli.py -q`
Expected: PASS.

### Task 7: Asset CLI Commands

**Files:**
- Modify: `src/scenario_forge/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
def test_cli_assets_lock_writes_asset_lock(tmp_path: Path) -> None:
    package_dir = make_asset_package_on_disk(tmp_path)

    result = run_cli("assets", "lock", str(package_dir), cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert (package_dir / "locks" / "asset_lock.yaml").exists()
    assert "Asset lock written" in result.stdout
```

```python
def test_cli_assets_check_reports_checksum_mismatch(tmp_path: Path) -> None:
    package_dir = make_asset_package_on_disk(tmp_path)
    run_cli("assets", "lock", str(package_dir), cwd=tmp_path)
    (package_dir / "assets" / "objects" / "sample_bottle_50ml_v1" / "model.usd").write_text(
        "changed\n",
        encoding="utf-8",
    )

    result = run_cli("assets", "check", str(package_dir), cwd=tmp_path)

    assert result.returncode == 1
    assert "Checksum mismatch for asset sample_bottle_50ml_v1" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli.py::test_cli_assets_lock_writes_asset_lock tests/test_cli.py::test_cli_assets_check_reports_checksum_mismatch -q`
Expected: FAIL because `assets` CLI does not exist.

- [ ] **Step 3: Write minimal implementation**

Add `assets lock <package_dir>` and `assets check <package_dir>` subcommands. Lock writes `locks/asset_lock.yaml`; check prints messages and returns nonzero on failure.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -q`
Expected: PASS.

### Task 8: Schemas, Docs, and Final Verification

**Files:**
- Create: `src/scenario_forge/schemas/jsonschema/asset-lock-v0.2.schema.json`
- Create: `src/scenario_forge/schemas/jsonschema/asset-manifest-v0.2.schema.json`
- Modify: `docs/design/asset-lock.md`
- Modify: `docs/operations/development-checks.md`

- [ ] **Step 1: Add schema artifacts**

Create JSON Schema files matching the implemented subset: schema version, asset ids, canonical USD paths, license, sha256, lock resolved paths, content sha256, resolver version.

- [ ] **Step 2: Update docs**

Update `docs/design/asset-lock.md` from Phase 0 draft to record the implemented Phase 1 subset and CLI commands.

- [ ] **Step 3: Run focused tests**

Run: `python -m pytest tests/test_asset_lock.py tests/test_package_validator.py tests/test_cli.py -q`
Expected: PASS.

- [ ] **Step 4: Run project checks**

Run: `make check`
Expected: PASS.

- [ ] **Step 5: Review final diff**

Run: `git status --short && git diff --stat`
Expected: only Phase 0 docs and Phase 1 asset-lock implementation/docs/tests are changed.
