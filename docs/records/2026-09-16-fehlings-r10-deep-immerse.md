# Fehling r10: deep upright in-bath playback

## Scope and standards

The user kept fill `0.8` and asked to lower the tube until the sample is under
the fake water, then watch color through the beaker. r9 optics (lining +
meniscus ring) stay; r9 heating pose does not. 规范依据 MAT-001–006、VAL-001–006。
规范无需新增通用规则：隔杯验收必须用正确姿态和视角已有正文。本次只改任务级案例：
颜色回放须让 8 mL 样液顶低于液面，不能用液面下 6 mm 的浅插代替。

Design: [deep immerse](../design/fehlings-deep-immerse.md).
Operations: [r10 guide](../operations/fehlings-r10-deep-immerse-guide.md).

## Why r9 failed this observation

Source r9 scene SHA:
`cc08d9b073e73ae1701136be89c509cab50c70407fde7c1b7a7349eb2e2161e9`.

r9 color playback used `surface−0.006` (t3–t15 also at 55°). t3 `tube_xyz.z` was
about 0.910 against `water_world_surface_z` about 0.916. The 8 mL top
(`sample_top_m≈0.044`) sat in air.

## Representation

Final r10 scene SHA:
`5243d9752fa753e4c1d98e8647ab2b43328dec9d1100fbe1f6c9b959cb5c89d5`.

Visual water fill, lining meshes, OmniGlass, tube, 8 mL and controller match r9
except the package task id. Heating style is `deep`: local xy centered, tilt 0,
origin ≈ water floor + 1.5 mm. Runtime t3: tube z ≈ 0.831, water z ≈ 0.916,
sample top ≈ 0.874 (about 42 mm below the waterline, about 86 mm of glass
immersed). Mouth still above water.

## Runtime, renders, video

Three independent Isaac Sim 4.5.0 runs, process IDs **1567313 / 1573657 /
1579960**, each pass, `heating_style=deep`, `color_sample_below_waterline=true`,
bound to the r10 scene SHA.

Six official `front_bath` frames (`t3/t9/t15/t21/t27/t30`). Render manifest SHA:
`d1a5fde06db687c71436c95e0f3b92be05b770c4edc1a46831dc457f3ac86718`.
Local review: **WARN**. Pose is the requested deep insert. Hue through nested
beaker/lining/tube glass is still muted gray; blue→brick-red is not nameable in
this front view. Not independent review. Not a claim that underwater color is
solved.

Video: `outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10_20260914/r10_front_bath.mp4`
(20.034 s, 1920×1080, H.264, 30 fps, 601 frames, 1,230,864 bytes). SHA256
`e1b86fbd9d678a2bf264f2636bbd698b7fdca5b50f26879141ba7f9fccec0425`.
Assembled by `scripts/assemble_fehlings_r10_front_bath_video.py`. Tube stays
near the floor. Not live robot capture. MP4 stays out of Git.

## Delivery

Output:
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10_20260914/`.
Package:
`handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r10/`.
Canonical ZIP SHA256
`7aacf3c594045e91e42eaf5fecab8942a2549a6472f0e64fb1bf0fe5d140fd7c`
(**106,530,994 bytes**).
The `vr_open_tube_positive_visual_reaction` head advances to r10; r9 remains on
disk as the lining-water source. No chemistry, heat, spill, robot or CPU/4.1 claim.

## Closeout checks

```bash
make check SMOKE_OUT=/tmp/scenario-forge-fehlings-r10-smoke SMOKE_SUITE_OUT=/tmp/scenario-forge-fehlings-r10-suite PHASE10X_SUITE_OUT=/tmp/scenario-forge-fehlings-r10-phase10x
```

**1110 passed, 1 skipped** in 347.04 s; Ruff, package-smoke, phase10x-smoke and
`git diff --check` all passed. This includes currently present independent worktree
tests and is not a claim that unrelated uncommitted work has been submitted.
