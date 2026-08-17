# Task 02 r10 four-fill dual-consumer handoff

Date: 2026-08-17

## Outcome

Scenario Forge packaged ConvertAsset's promoted fill sweep into four independent
r10 dual-consumer packages (eBench + VR) and one ZIP. ConvertAsset physics was
not retouched. r9 robot-oracle evidence was not copied.

```text
outputs/scientific_workbench_task02_r10_fill_sweep_20260817/handoff/task02_r10_fill_sweep.zip
```

Default variant is `fill40`. Runtime is Isaac Sim 4.1 only. Producer claims stop
at `gpu_pbd_dynamic_loaded_start` plus prescribed-transfer 50% target reception.
`robot_policy_success=False`, `liquid_metrics_active=False`, `score_ceiling=0.60`.
This release does not inherit the r9 scripted-oracle 3/3 result.

## Measured fill (q95)

| Variant | Particles | Target | Measured q95 |
| --- | ---: | ---: | --- |
| fill20 | 290 | 20% | 21.63–21.72% |
| fill40 | 580 | 40% | 38.90–38.95% |
| fill60 | 972 | 60% | 58.57–58.62% |
| fill80 | 1327 | 80% | 75.09–75.16% (at the ±5% floor) |

## Visual gate

Isaac Sim 4.1 rendered a fixed-camera `scene_overview.png` for each variant.
Two reproducible montages are shipped:

- `handoff/evidence/fill_sweep_closeup_quad.png` is the primary liquid-level
  comparison. It crops the same reviewed task-object camera for all four fills.
- `handoff/evidence/fill_sweep_overview_quad.png` preserves the full-room view.

`fill_sweep_quad.png` is a compatibility alias of the closeup montage. Local
human-style visual QA found the graduated cylinder identifiable and the four
levels monotonically increasing, with no missing, floating, or clipped task
objects. This was not an independent blind review. `visual_ready=pass`.

## Consumer runtime gates

Every variant was checked independently in the managed Isaac Sim 4.1 runtime:

- eBench: native GenManip scene construction, reset/recovery, then exactly 960
  real physics steps (8 seconds at 120 Hz), with zero actions and
  `render_without_physics=false`.
- VR: `scene.usd` opened in Isaac Sim 4.1, `/World` was the default prim, the
  Source/Target/ParticleSet prims resolved, and `task_config.py` parsed.

All eight checks passed. Particle counts remained 290 / 580 / 972 / 1327 and
the maximum task-object translation during each zero-action smoke was 5.01 mm
(the target beaker settling); all other tabletop objects remained below 1 mm.
These gates do not claim robot transfer, teleoperation, policy success, an
active liquid metric, or benchmark success.

## Artifact hashes (do not commit the ZIP or USD trees)

- ZIP `sha256:b5e572f7cb6cdc8054c2e1674d0bc2105b663b456762f1593425c3770a172df3`
- closeup quad `sha256:5747d2c422e0b594d36e026ec505df97f3db1f00d0e8699e8bb170b53659506d`
- overview quad `sha256:7590020288f47bbe633c01ec00ae8a6dfba772b616e50b123fc4439204bf192b`
- fill20 manifest `sha256:0a1df2ff86c6606a601a71df343210fe9384e8095a7b21b965864c1aafa8fcf3`
- fill40 manifest `sha256:d4296543ac5a059ed5a410da9d7a8979bc60dfc01b57b751c8dbcf3835760cf3`
- fill60 manifest `sha256:b0610e83b9389b231a35eb7b5c94de2f2cb4eff4345716fd0bd85429815e29f6`
- fill80 manifest `sha256:ebbcd5866d01cb9119d0f6e4a076d9c56b87bce4ae2f9e9abcd2a6969f36276d`

The final ZIP passed CRC validation and all 2,106 package-internal SHA-256
entries. Publication uses a sibling temporary archive plus `os.replace`, so an
interrupted rebuild cannot destroy the previous published ZIP.

Inputs: r9 rich base
`outputs/scientific_workbench_tasks_02_07_08_r9_20260816/rich_bases/scientific_workbench_r9_task02_pour_cylinder_to_beaker__background_modern_wet_chemistry`
and ConvertAsset
`/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task02_gpu_pbd_fill_sweep_20260817_r60/final_packages/{fill20,fill40,fill60,fill80}/`.
