# Three-view background package QA

Date: 2026-08-03

## Outcome

The GenManip initial-scene preview contract now emits three evidence views for
new packages:

- `scene_overview.png` proves the complete room, eBench table, Lift2, and task
  layout are composed together;
- `workspace_closeup.png` checks table/robot framing with the visual room hidden;
- `task_object_closeup.png` frames only the task objects closely enough to
  inspect material, scale, pose, and mutual spacing.

The third view addresses a practical review gap in background variants: a wide
room overview can look plausible while the actual vessels are too small to
judge.  It is evidence-only and does not execute actions or evaluate task
success.

## Contract and compatibility

New request, evidence, and gate schemas use v0.2.  The validator and renderer
still accept the existing v0.1 two-view contract so previously generated task
packages remain checkable.  The task-object view derives its required and
anchor runtime IDs from the package's declared task objects; no simulator SDK
is imported into Scenario Forge's pure package layers.

The room is hidden for the two closeups and restored for the overview.  The
renderer continues to run through the external GenManip/Isaac process boundary
without modifying the GenManip repository.

## Changed files

- `src/scenario_forge/adapters/ebench/preview.py`
- `scripts/ebench/render_genmanip_initial_preview.py`
- `tests/test_ebench_genmanip_preview.py`
- `docs/design/scenario-spec-and-genmanip-export.md`
- `docs/operations/generate-scientific-workbench-background-variants.md`

## Verification

Focused adapter, orchestration, and background-variant tests were run with the
managed EOS development interpreter:

```text
PYTHONPATH=src python -m pytest -q \
  tests/test_ebench_genmanip_preview.py \
  tests/test_genmanip_preview_orchestration.py \
  tests/test_scientific_workbench_background_variants.py -x
```

Result: 84 passed.

## Claim boundary

Three passing images establish only post-reset, pre-action composition and
readability.  They do not establish reachability, grasp success, collision-free
motion, liquid transfer, policy performance, or benchmark success.
