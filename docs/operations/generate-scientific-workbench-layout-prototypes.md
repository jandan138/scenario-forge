# Generate Scientific Workbench Layout Prototypes

This workflow compiles the currently asset-ready rows from the pinned Feishu
Task Design into portable Scenario Forge packages and EBench/GenManip handoffs.

## Current task set

| Source row | Scenario | Status | Active score ceiling |
|---|---|---|---:|
| 2 | `scientific_workbench_pour_cylinder_to_beaker` | layout-validated prototype | 0.60 |
| 13 | `scientific_workbench_funnel_pour_cylinder_to_flask` | layout-validated prototype | 0.60 |
| 16 | `scientific_workbench_two_sample_mix` | layout-validated prototype | 0.70 |
| 6 | `scientific_workbench_place_vessel_on_stirrer` | blocked: asset identity | 0.00 |

The two archive candidates labelled as magnetic stirrers are not admitted: visual
screening identified a laboratory scale and a stand-mounted heating apparatus.
Do not rename either asset to unblock row 6.

## Build

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_layout_prototypes.py \
  --bindings configs/source_bindings/scientific_workbench_layout_prototypes_20260731.yaml \
  --task all \
  --out outputs/scientific_workbench_layout_validated_prototypes_20260731
```

Add Isaac 4.1 authored-state previews:

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_layout_prototypes.py \
  --bindings configs/source_bindings/scientific_workbench_layout_prototypes_20260731.yaml \
  --task all \
  --out outputs/scientific_workbench_layout_validated_prototypes_20260731 \
  --render \
  --isaac-python /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python
```

`readiness.yaml` at the output root records completed and blocked rows. Every
completed package has:

```text
<scenario-id>/
  scene/main.usda
  task/task.yaml
  metrics/metrics.yaml
  adapters/ebench/genmanip/
  adapters/ebench/genmanip/evidence/authored_key_states/
```

Give the EBench engineer the complete
`<scenario-id>/adapters/ebench/genmanip/` directory. Keep the whole
`<scenario-id>/` directory when transferring the portable package or inspecting
provenance.

## Evidence and claim boundary

Each authored key state contains a package-relative `scene.usda`, one workspace
close-up, two room/table overview views, `contact_sheet.png`,
`render_manifest.json`, and `runtime.log`. These are static visualizations. The
evidence layer preserves metre units and adds a preview-only dome light; the
renderer disables physics only in its in-memory session layer. An effectively
black camera frame fails the render instead of being accepted merely because a
PNG file exists.

The images establish that the selected room, centered worktable, and task assets
compose visibly at the reviewed authored poses. They do not establish robot
reachability, collision-free motion, liquid transfer, policy success, benchmark
success, or task completion.

Liquid score items remain in `metrics/metrics.yaml` with `active: false`. The
rubric uses `declared_sum + zero`, so unavailable liquid metrics contribute zero
and are never silently removed or renormalized.
