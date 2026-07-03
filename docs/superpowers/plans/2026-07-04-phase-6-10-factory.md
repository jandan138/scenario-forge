# Phase 6-10 Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 6-10 so Scenario Forge can generate workflow-grounded packages, deterministic layouts, real2sim imports/cousins, benchmark suites, and suite quality evidence for static EBench export.

**Architecture:** Keep the repo as a portable package compiler. Domain packs drive workflow and layout generation; importers normalize external artifacts into package contracts; suite generation orchestrates existing scaffold, task, scene, asset-lock, and EBench export code; quality evidence inspects generated package artifacts only.

**Tech Stack:** Python 3.10, PyYAML, dataclasses, pathlib, pytest, ruff.

---

## File Structure

- Create `configs/domain_packs/scientific_workbench/atomic_skills.yaml`: supported atomic skill catalog and robot capability requirements.
- Create `configs/domain_packs/scientific_workbench/workflow_templates.yaml`: task-family templates for pick-place, sorting, staging, pipette, button, and open-place-close workflows.
- Create `configs/domain_packs/scientific_workbench/layout_constraints.yaml`: difficulty profiles and workspace constraints.
- Create `configs/domain_packs/scientific_workbench/hazards.yaml`: deterministic safety spacing inputs.
- Create `src/scenario_forge/generation/skills/skill_library.py`: load domain-pack skills and validate robot capability coverage.
- Create `src/scenario_forge/generation/workflows/workflow_composer.py`: compose task graph YAML from task family and bindings.
- Create `src/scenario_forge/generation/workflows/rollout_filter.py`: static workflow checks for required assets, predicates, and robot capabilities.
- Create `src/scenario_forge/generation/layout/`: deterministic layout planner, constraints, reachability, and safety check helpers.
- Create `src/scenario_forge/adapters/real2sim/`: real2sim result importer and contract dataclasses.
- Create `src/scenario_forge/generation/cousins/`: cousin plan and variant generator.
- Create `src/scenario_forge/generation/suite/`: suite generator, splitter, and coverage helpers.
- Create `src/scenario_forge/artifacts/suite_writer.py`: suite manifest and suite artifact writing.
- Create `src/scenario_forge/evaluation/suite_quality_evidence.py`: Phase 10 quality evidence generation.
- Modify `src/scenario_forge/cli.py`: add `workflow compose`, `layout plan`, `real2sim import`, `suite generate`, and `suite quality`.
- Modify `src/scenario_forge/scaffold.py` and `Makefile`: smoke uses the new workflow/layout path before task, scene, and EBench export.
- Add JSON schemas for workflow, layout, real2sim, cousin plan, suite spec, suite manifest v0.2, and suite quality evidence.
- Add focused tests in `tests/test_workflow_generator.py`, `tests/test_layout_generator.py`, `tests/test_real2sim_importer.py`, `tests/test_suite_generator.py`, and `tests/test_suite_quality_evidence.py`.

## Tasks

### Task 1: Phase 6 Workflow Generator

- [ ] Write failing tests for domain skill loading, workflow composition, required asset derivation, success predicate derivation, safety rule derivation, and robot capability rejection.
- [ ] Implement the skill library loader and robot capability validator.
- [ ] Implement workflow template composition for the first six task families.
- [ ] Add CLI `scenario-forge workflow compose --package <pkg> --family <family> --robot-profile <id>`.
- [ ] Verify focused tests pass.

### Task 2: Phase 7 Layout Generator

- [ ] Write failing tests that a generation plan produces `scene/layout.yaml`, `scene/instances.yaml`, and `evidence/layout_checks.yaml`.
- [ ] Implement deterministic placement using difficulty profiles and stable IDs.
- [ ] Implement static reachability and safety reports with concrete failure reasons.
- [ ] Add CLI `scenario-forge layout plan --package <pkg> --family <family> --difficulty <level>`.
- [ ] Verify focused tests pass.

### Task 3: Phase 8 Real2Sim Import And Cousins

- [ ] Write failing tests for importing a real2sim result into a v0.2 package with assets, lock, provenance, evidence, scene instances, task artifacts, and EBench export readiness.
- [ ] Implement importer contract and artifact writer without importing external real2sim code.
- [ ] Write failing tests for cousin plan variants preserving task predicates while changing layout or asset choices.
- [ ] Implement cousin generator and variation records.
- [ ] Add CLI `scenario-forge real2sim import --result <yaml> --out <pkg>` and `scenario-forge real2sim cousins --package <pkg> --plan <yaml> --out <suite>`.
- [ ] Verify focused tests pass.

### Task 4: Phase 9 Suite Generator

- [ ] Write failing tests for `suite_spec.yaml` generating multiple packages with task-family/difficulty/split distribution and suite manifest v0.2.
- [ ] Implement suite generator, splitter, coverage summary, suite asset lock, and suite validation report.
- [ ] Wire EBench suite export after suite manifest generation.
- [ ] Add CLI `scenario-forge suite generate --spec <suite_spec.yaml> --out <suite_dir>`.
- [ ] Verify focused tests pass.

### Task 5: Phase 10 Suite Quality Evidence

- [ ] Write failing tests for duplicate instruction detection, duplicate scene detection, split leakage detection, difficulty distribution reporting, and asset/license/checksum completeness.
- [ ] Implement suite quality evidence generation from suite manifest and package artifacts.
- [ ] Add CLI `scenario-forge suite quality --suite <suite_dir>`.
- [ ] Verify focused tests pass.

### Task 6: Schemas, Docs, Smoke, And Final Verification

- [ ] Add and parse all new JSON schemas in schema tests.
- [ ] Update README, roadmap Phase 6-10 statuses, design docs, and operations checks.
- [ ] Update `Makefile package-smoke` to exercise workflow/layout/suite quality where practical.
- [ ] Run `make check`.
- [ ] Commit, merge to `main`, push, verify CI/Pages, and remove the worktree.
