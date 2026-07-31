# 2026-07-31 Scientific Workbench v2 Glass and Evidence

## Outcome

Three Feishu-aligned layout-validated prototypes were regenerated at:

```text
outputs/scientific_workbench_layout_validated_prototypes_v2_20260731/
```

| Scenario | Static states | GenManip post-reset views |
|---|---:|---|
| `scientific_workbench_pour_cylinder_to_beaker` | 3 | 2 |
| `scientific_workbench_funnel_pour_cylinder_to_flask` | 3 | 2 |
| `scientific_workbench_two_sample_mix` | 4 | 2 |

All static key-state camera PNGs and all native GenManip initial-scene PNGs
are 1920×1080.  The static layer is a no-robot authored storyboard.  The
native runtime layer is post-reset, pre-action and requires `lift2`, the
eBench table, and the task objects in both views.

## Beaker

The three packages consume ConvertAsset's source-bound r2 beaker package:

```text
/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/scientific_workbench_task_assets_20260731/beaker_transparent_r2/package
```

It uses an explicitly recorded `OmniGlass` visual-material profile.  The white
opaque source PBR binding was not retained as glass merely because of its name.
No task package adds a material, scale, collider, mass, inertia, or PhysX patch.

## Render policy

Static storyboard rendering uses RayTracedLighting, anti-aliasing, 40 warmup
frames, multi-subframe capture, and fixed exposure.  It deliberately disables
physics only in a temporary session layer and cannot be interpreted as robot or
physics evidence.

The runtime evidence renderer has the same fixed exposure.  Its former whole-
room camera anchor was removed because it made the robot/table too small to
inspect.  The scene-overview camera now frames Lift2, table, and task objects
while preserving the inherited Code-as-Room environment as visible context.

## Runtime dependency repair

The selected EOS Isaac Python needs both a CuRobo Python source and its
prebuilt native extensions.  The raw CuRobo source would try to compile at
runtime and fail because this host lacks `c++`.  The documented frozen CuRobo
source provides the recorded prebuilt extensions.  The Scenario Forge adapter
now prepends the selected runtime's `bin`, Torch, CUDA-runtime, and Isaac CUDA
library paths only to the renderer subprocess.  This changes neither GenManip
nor a package's contents.

## Verification

- ConvertAsset r2: static/material-runtime/runtime-smoke gates pass; four
  object interaction gates were freshly rebound to r2 `asset.usd` and pass.
- Scenario Forge: package handoff and all ten static states pass; all six
  GenManip initial-scene views pass and record the required runtime ids.
- Code checks: targeted preview/generator tests pass and static analysis passes.

## Claim boundary

The output proves package composition and evidence rendering.  It does not
prove robot reachability, collision-free path planning, a physical grasp,
liquid dynamics, pouring, policy success, benchmark success, or task
completion.
