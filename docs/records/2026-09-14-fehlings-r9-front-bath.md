# Fehling r9: front-on in-bath color and video

## Scope and standards

The user rejected r8 stills: looking straight through the beaker wall and fake
water, later orange-red / brick-red was still not visible, and there was no
acceptance video. r9 keeps r8 fill/contact/tube/8 mL/five-layer reaction.
规范依据 MAT-001–006、VAL-001–006。规范无需新增通用规则：嵌套透明层必须用正确
观察视角验收已有正文。本次只改任务级案例：正视 `front_bath` 和试管留在水里的
视频才是隔杯验收，不能用出水图或掠射 `through_wall` 代替。

Design: [front bath lining](../design/fehlings-front-bath.md).
Operations: [r9 guide](../operations/fehlings-r9-front-bath-guide.md).

## Why r8 failed this observation

Source r8 scene SHA:
`9c883fcbe447db017df5524db0954b6292222528cfc7b9095384512c3ae2ee46`.

r8 `through_wall` is `sample+(0.22,0.02,0.01)`, aimed at the waterline through
the cylinder. Front diagnostic stills on frozen r8 (`diagnostic_front_bath/`)
show orange-red above the waterline and a near-black round bottom. r7 demo MP4
is a withdrawn-keyframe slideshow, not this view.

## Representation

Final r9 scene SHA:
`cc08d9b073e73ae1701136be89c509cab50c70407fde7c1b7a7349eb2e2161e9`.

`VisualWater` keeps `water:profile_m` and `fill_height_ratio=0.8`. `body` is an
open lining (inner radius ≈ 33.7 mm, thickness 1.5 mm). `surface` is a
meniscus ring, not a full disk. OmniGlass recipe otherwise matches r8. No
collision. Physics and the r7/r8 controller stay identical.

## Runtime, renders, video

Three independent Isaac Sim 4.5.0 runs, process IDs **1153797 / 1198199 /
1213691**, each pass, bound to the r9 scene SHA.

Six official `front_bath` frames (`t3/t9/t15/t21/t27/t30`). Render manifest SHA:
`ec0fc8b8f39fbc9d5ba39cddbbee3cf223f4695e027577de14a4b50078e11d31`.
Local review: **WARN / usable**. Blue/green/yellow-green stay nameable below the
waterline, including the tip at 3–15 s. Orange/orange-red is readable on the
immersed column; the last millimetres of the round bottom still darken at
21–30 s. Not independent review.

Video: `outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9_20260914/r9_front_bath.mp4`
(20.034 s, 1920×1080, H.264, 30 fps, 601 frames, 1,291,255 bytes). SHA256
`ab51123a2071d7a8d6ad02a31584d2df8e210c7ee88adcf2d246188e908fdf87`.
Assembled by `scripts/assemble_fehlings_r9_front_bath_video.py` from the six
in-bath fronts; tube stays in the bath. Not live robot capture. MP4 stays out
of Git.

## Delivery

Output:
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9_20260914/`.
Package:
`handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9/`.
Canonical ZIP SHA256
`f812cc3a034a0e1d548b650bf4277252984d20a2564f431772a54196862aa3c1`
(**106,864,228 bytes**; remade after syncing `COLOR_GUIDE_CN.md` to the
operations guide).
The `vr_open_tube_positive_visual_reaction` head pointed at r9 at closeout;
r8 remains the OmniGlass source on disk. Later the user required the 8 mL
column under the waterline; r9 heating only dipped about 6 mm.
[r10](2026-09-16-fehlings-r10-deep-immerse.md) supersedes that playback pose.
r9 bytes are not rewritten.

## Closeout checks

```bash
make check SMOKE_OUT=/tmp/scenario-forge-fehlings-r9-smoke SMOKE_SUITE_OUT=/tmp/scenario-forge-fehlings-r9-suite PHASE10X_SUITE_OUT=/tmp/scenario-forge-fehlings-r9-phase10x
```

**1039 passed, 1 skipped** in 302.16 s; Ruff, package-smoke, phase10x-smoke and
`git diff --check` all passed. This includes currently present independent worktree
tests and is not a claim that unrelated uncommitted work has been submitted.
