# Phase 10.x EOS Handoff Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 10.1-10.5 as concrete Scenario Forge suite gates that produce golden-pack, external-input, EOS static-import, runtime-smoke, and release-candidate evidence without adding simulator runners or model adapters.

**Architecture:** Add a focused `scenario_forge.evaluation.phase10x_gates` module that reads an existing generated suite, validates required handoff artifacts, imports optional downstream evidence files, and writes five YAML evidence artifacts under `suite/evidence/`. Expose it through `scenario-forge suite phase10x`; keep downstream execution in EOS / EBench by accepting runtime evidence files rather than running episodes.

**Tech Stack:** Python 3.10, PyYAML, existing Scenario Forge package/suite helpers, pytest, Ruff.

---

### Task 1: Phase 10.x Evidence API

**Files:**
- Create: `src/scenario_forge/evaluation/phase10x_gates.py`
- Test: `tests/test_phase10x_gates.py`

- [x] **Step 1: Write failing tests for passed Phase 10.x evidence**

Create a test that generates a 10-package suite, writes an external-input evidence file with LabBuilder and SimFoundry lanes, writes a passed runtime-smoke evidence file, and calls:

```python
generate_phase10x_evidence(
    suite_dir,
    eos_python=Path(sys.executable),
    external_evidence_path=external_path,
    runtime_smoke_path=runtime_path,
    rc_min_packages=10,
    rc_max_packages=20,
)
```

Assert that these files exist and report `status: passed`:

```text
evidence/golden_task_pack.yaml
evidence/external_input_hardening.yaml
evidence/eos_static_import.yaml
evidence/runtime_smoke.yaml
evidence/phase10x_rc_gate.yaml
```

Run: `python -m pytest tests/test_phase10x_gates.py -q`
Expected: FAIL with `ModuleNotFoundError` or missing `generate_phase10x_evidence`.

- [x] **Step 2: Implement the minimal evidence API**

Implement:

```python
@dataclass(frozen=True)
class Phase10xEvidenceResult:
    suite_root: Path
    overall_status: str
    evidence_paths: tuple[Path, ...]
    gate_statuses: dict[str, str]

def generate_phase10x_evidence(
    suite_dir: str | Path,
    *,
    eos_python: str | Path | None = None,
    external_evidence_path: str | Path | None = None,
    runtime_smoke_path: str | Path | None = None,
    rc_min_packages: int = 50,
    rc_max_packages: int = 100,
) -> Phase10xEvidenceResult:
    ...
```

The implementation must:

- load `suite_manifest.yaml`;
- ensure `suite_quality_evidence.yaml` exists by calling `generate_suite_quality_evidence`;
- write golden-pack evidence that passes for 10-20 packages;
- write external-input evidence that passes only when an external evidence file includes at least one lane beyond `scenario_forge_layout`;
- write EOS static-import evidence that checks each package has `adapters/ebench/package.yaml`, `adapters/ebench/task_entrypoint.yaml`, `scene/main.usda`, and `locks/asset_lock.yaml`;
- record `eos_python --version` when provided;
- write runtime-smoke evidence from a downstream evidence YAML file and pass only when its status is `passed` and package ids are in the suite;
- write RC evidence that passes only when package count is within the configured RC range and all prior gates passed.

- [x] **Step 3: Run focused tests**

Run: `python -m pytest tests/test_phase10x_gates.py -q`
Expected: PASS.

### Task 2: CLI Gate Command

**Files:**
- Modify: `src/scenario_forge/cli.py`
- Test: `tests/test_cli.py`

- [x] **Step 1: Write failing CLI tests**

Add a test for:

```bash
scenario-forge suite phase10x \
  --suite <suite_dir> \
  --eos-python <sys.executable> \
  --external-evidence <external.yaml> \
  --runtime-smoke <runtime.yaml> \
  --rc-min-packages 10 \
  --rc-max-packages 20 \
  --strict
```

Assert return code `0`, stdout contains `Phase 10.x evidence written:`, and `evidence/phase10x_rc_gate.yaml` has `overall_status: passed`.

Add a second test where runtime evidence is omitted and `--strict` returns `1` while still writing evidence.

Run: `python -m pytest tests/test_cli.py -q`
Expected: FAIL because the command is missing.

- [x] **Step 2: Add `suite phase10x` parser and handler**

Add arguments:

```text
--suite
--eos-python
--external-evidence
--runtime-smoke
--rc-min-packages
--rc-max-packages
--strict
```

The handler calls `generate_phase10x_evidence`. In non-strict mode it returns `0` when evidence generation succeeds. In strict mode it returns `0` only for `overall_status == "passed"`.

- [x] **Step 3: Run CLI tests**

Run: `python -m pytest tests/test_cli.py -q`
Expected: PASS.

### Task 3: Examples And Operations Docs

**Files:**
- Create: `examples/suite_spec_phase10x_golden.yaml`
- Create: `examples/phase10x_external_evidence.yaml`
- Create: `examples/phase10x_runtime_smoke.yaml`
- Modify: `docs/operations/development-checks.md`
- Modify: `docs/design/workflow-layout-suite-factory.md`
- Modify: `docs/strategy/scenario-forge-ebench-auto-factory-roadmap.md`

- [x] **Step 1: Write or update docs after code behavior exists**

Document the command:

```bash
scenario-forge suite generate --spec examples/suite_spec_phase10x_golden.yaml --out /tmp/scenario-forge-phase10x-suite
scenario-forge suite phase10x \
  --suite /tmp/scenario-forge-phase10x-suite \
  --eos-python "$EEOS_PYTHON" \
  --external-evidence examples/phase10x_external_evidence.yaml \
  --runtime-smoke examples/phase10x_runtime_smoke.yaml \
  --rc-min-packages 10 \
  --rc-max-packages 20 \
  --strict
```

The docs must state that formal RC default remains 50-100 packages; the example uses 10-20 for the golden-pack gate.

- [x] **Step 2: Add example evidence fixtures**

The external example must include `scenario_forge_layout`, `labuilder_layout_import`, and `simfoundry_real2sim_import` lanes. The runtime example must include package ids matching `phase10x_golden_suite_000` and `phase10x_golden_suite_001` and `status: passed`.

- [x] **Step 3: Run docs/example validation**

Run: `python -m pytest tests/test_phase10x_gates.py tests/test_cli.py -q`
Expected: PASS.

### Task 4: Make Check Integration

**Files:**
- Modify: `Makefile`

- [x] **Step 1: Add a lightweight `phase10x-smoke` target**

The target should generate the 10-task golden example into `/tmp/scenario-forge-phase10x-suite`, run `suite phase10x` with example external/runtime evidence and `--strict`, and leave heavy EOS runtime execution out of `make check`.

- [x] **Step 2: Include `phase10x-smoke` in `check`**

Update `check` to run `test lint package-smoke phase10x-smoke diff-check`.

- [x] **Step 3: Run full verification**

Run: `make check`
Expected: PASS.

### Task 5: Final Verification And Git Hygiene

**Files:**
- All changed files

- [x] **Step 1: Inspect changed files**

Run:

```bash
git diff --stat
git diff --check
git status --short --branch
```

Expected: only intended Phase 10.x files changed; no whitespace errors.

- [x] **Step 2: Run full check again**

Run: `make check`
Expected: PASS.

- [x] **Step 3: Commit**

Commit with:

```bash
git add Makefile examples docs src tests
git commit -m "feat: add phase 10x handoff gates"
```
