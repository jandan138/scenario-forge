# Scenario Forge Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap a new `scenario-forge` repo that can scaffold and validate portable embodied scenario packages.

**Architecture:** Use a `src/` Python package with pure package layers and adapter boundaries. Keep simulator-specific behavior out of core validation.

**Tech Stack:** Python 3.10+, PyYAML, pytest, Ruff, dataclasses, argparse.

---

### Task 1: Package Validation

**Files:**
- Create: `src/scenario_forge/package.py`
- Test: `tests/test_package_validator.py`

- [x] Write tests for loading a valid manifest.
- [x] Write tests for missing referenced files.
- [x] Write tests for unsupported export targets.
- [x] Implement manifest loading and structural validation.
- [x] Run `python -m pytest -q tests/test_package_validator.py`.

### Task 2: CLI Scaffold And Check

**Files:**
- Create: `src/scenario_forge/cli.py`
- Create: `src/scenario_forge/scaffold.py`
- Test: `tests/test_cli.py`

- [x] Write tests for `package scaffold`.
- [x] Write tests for nonzero invalid package checks.
- [x] Implement starter package scaffold.
- [x] Implement `package check`.
- [x] Run `python -m pytest -q tests/test_cli.py`.

### Task 3: Adapter Boundary

**Files:**
- Create: `src/scenario_forge/adapters/base.py`
- Create: `src/scenario_forge/adapters/convert_asset.py`
- Test: `tests/test_convert_asset_adapter.py`

- [x] Write tests for dry command plans.
- [x] Implement ConvertAsset command-plan helpers.
- [x] Add adapter protocol types.
- [x] Run `python -m pytest -q tests/test_convert_asset_adapter.py`.

### Task 4: Repo Governance

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `CLAUDE.md`
- Create: `Makefile`
- Create: `docs/**`

- [x] Document architecture boundaries.
- [x] Document artifact policy.
- [x] Document package contract.
- [x] Add `make check`.

### Task 5: Verification

**Files:**
- No new production files.

- [x] Run `python -m pytest -q`.
- [x] Run `python -m ruff check src tests scripts`.
- [x] Run `make package-smoke`.
- [x] Run `git diff --check`.
