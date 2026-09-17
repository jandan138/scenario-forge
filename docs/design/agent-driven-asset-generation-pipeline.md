# Agent-Driven Asset Generation Pipeline

Status: current design (methodology formalization, documentation only — no
pipeline code). Date: 2026-09-17.

This document formalizes the semi-automated pipeline used to produce complex
articulated assets (the IKA OVEN 125 and the traditional titration burette)
from natural-language experiment requirements, and defines how generated
assets join the existing intake/ConvertAsset/admission path.

Companion documents:

- Rules: [asset-generation standards](../standards/asset-generation.md)
  (GEN-001..GEN-007)
- Spec format: [asset spec template](../standards/templates/asset-spec-template.md)
- Step-by-step: [operations runbook](../operations/generate-articulated-asset.md)
- Agent tooling: [skills/](../../skills/README.md)

## Boundary statement

Asset generation is **producer-role work** executed by an agent using an
external skill package (currently
`skills/hunyuan-isaac-articulation-assets/`, Hunyuan3D → Blender cleanup →
PhysX/Isaac articulated USD, with a Blender-only procedural fallback route).
Scenario Forge owns only the contracts: the asset spec format, the evidence
grading and hash discipline, the stage gates, and the admission request.

This pipeline changes nothing about ownership downstream: ConvertAsset still
owns conversion and physics qualification (ASSET-001), raw USD and evidence
images never enter git (VAL-005, GEN-004), and a generated asset is admitted
exactly like any other producer delivery — through the existing ConvertAsset
boundary validated by `adapters/convert_asset.py`. The skill's presence in
the repo confers no qualification on any asset (GEN-001).

## Five-stage pipeline

### Stage A — Requirement capture

| | |
|---|---|
| Input | Experiment requirement as natural language, tutorial video, and/or images (external materials, hash-indexed if stored) |
| Agent action | Extract the asset-relevant requirements: which devices/objects the experiment needs, which are articulated or dimension-critical, what interactions the robot must perform |
| Output | Asset request list (draft spec front matter + one row per requested asset) |
| Gate | Human confirms scope and priorities |

### Stage B — Evidence search

| | |
|---|---|
| Input | Asset request list |
| Agent action | Proactively find the real asset: manufacturer catalog pages, datasheets, official photos, usage videos. Register every item with an evidence grade E (exact) / F (family) / D (derived) / U (unknown) per GEN-002 |
| Output | Evidence register under `external_artifacts/asset_evidence/<slug>/`, per-item SHA-256 recorded in `MANIFEST.sha256`, catalog digest indexed in `external_artifacts/README.md` |
| Gate | Human reviews grading and coverage (GEN-006) |

### Stage C — Spec synthesis

| | |
|---|---|
| Input | Evidence register + [asset spec template](../standards/templates/asset-spec-template.md) |
| Agent action | Synthesize the ultra-detailed asset spec: frozen manufacturer spec table, decomposition decision, prim tree, joint contracts, state variables, interaction semantics, QA matrix, delivery conventions, open-measurements punch list, image inventory |
| Output | Committed markdown spec at `docs/design/asset-specs/<slug>.md` |
| Gate | Human sign-off = **spec freeze** (GEN-003, GEN-006). Later changes require re-sign-off |

### Stage D — Skill-driven generation

| | |
|---|---|
| Input | Frozen spec + skill package |
| Agent action | Iterate: generate/repair geometry (Hunyuan route or Blender-only fallback), author USD + articulation per the skill's contract, run the static contract gate `skills/hunyuan-isaac-articulation-assets/scripts/check_articulation_usd.py` under Isaac Kit Python (full path, never wired into repo checks) |
| Output | Raw USD tree under `external_artifacts/incoming/<slug>_generated/` (or a documented external path) + static gate report stored externally with hash indexed |
| Gate | Human reviews the static gate report; any FAIL blocks (GEN-005). Static pass is not runtime acceptance (GEN-007) |

### Stage E — Existing admission path

| | |
|---|---|
| Input | Generated source tree + static gate report |
| Agent action | Snapshot the source immutably (same pattern as `scripts/intake_external_environment.py`), fill a ConvertAsset admission request YAML (precedents: `docs/operations/scientific-workbench-*-admission-request.yaml`) |
| Output | ConvertAsset qualified package → existing admission via `load_convert_asset_package_handoff` → source bindings → asset lock → scenario compile |
| Gate | Existing ASSET/USD/ART/MAT/VAL rules, unchanged. Nothing in stage E is new |

## Iteration loops

- **D → C**: generation reveals spec gaps (unmeasurable dimensions, wrong
  decomposition). Amend the spec and re-freeze before continuing; do not
  patch around a stale spec.
- **E → D**: ConvertAsset rejection returns to the producer as an explicit
  capability-gap request with source hashes and failure evidence (ASSET-006).

## Stage gate summary

| Stage | Agent does | Human signs off | Blocking artifact |
|---|---|---|---|
| A | Draft request list | Scope/priorities | Request list |
| B | Search + grade evidence | Grading/coverage review | Evidence register + hashes |
| C | Synthesize spec | Spec freeze | `docs/design/asset-specs/<slug>.md` |
| D | Generate + iterate + static gate | Gate report review, FAIL blocks | USD tree + gate report (external, hashed) |
| E | Intake snapshot + admission request | Existing qualification gates | ConvertAsset package + manifest |

## Mapping to the existing pipeline

```
A requirement ──► B evidence ──► C spec (git) ──► D generation (skill, external USD)
                                                      │
                              intake snapshot ◄───────┘
                                  │
                              ConvertAsset conversion/qualification (external)
                                  │
                              admission (adapters/convert_asset.py)
                                  │
                              source bindings → asset lock → scenario compile
```

Stages A–D add a producer front-end; stage E reuses the documented pipeline
unchanged (see [architecture](architecture.md) and
[asset intake standards](../standards/asset-intake.md)).

## Non-goals

- No skill invocation from `src/`; no simulator SDK in pure package layers.
- No CI wiring of Isaac-dependent checks; the static gate runs only in stage D
  under Isaac Kit Python.
- No claim that the pipeline produces qualified assets; qualification remains
  ConvertAsset's decision.
- No benchmark or leaderboard claims from generated assets.
