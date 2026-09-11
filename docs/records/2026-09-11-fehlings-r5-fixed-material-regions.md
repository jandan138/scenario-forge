# Fehling r5: fixed sample/sediment regions, material-only development

## Scope and standards

Standards baseline: current scene-authoring standards established 2026-09-08,
with task-applicable updates read on 2026-09-11. Rules: ASSET-001/002,
USD-001/002, MAT-001–006, STATE-001–006, VAL-001–006.

The user approved derivation **directly from r3**, using its Isaac Sim 4.5
GPU/SDF physics and contact/task logic. Existing r4 CPU-collider work is a
separate variant. r5 replaces growing visual geometry with two fixed material
regions; the lower region is one third of initial liquid-column height. See
[design review](../design/fehlings-fixed-material-regions.md) and
[operating guide](../operations/fehlings-r5-color-guide.md).

规范无需新增通用规则：这是 MAT-005/006 允许的分区视觉表达和可解释参数策略，
不改变真实液体能力或跨任务契约。本次只在规范中补充已验证案例引用，
同期新增设计说明、操作指南、证据记录，并更新该 variant 的任务头。

## Exact geometry and policy

- Original liquid floor z: 4 mm; liquid top z: 32.608117 mm.
- Fixed interface z: 13.536039 mm; lower height: 9.536039 mm.
- r3 final .3 mL visual bed was 10.111986 mm high. The confirmed one-third
  fraction is slightly thinner, not thicker; implementation reported this fact
  and followed the explicit fraction rather than silently increasing it.
- Two semantic regions, two materials, four retained body/surface Mesh paths.
  Side boundaries touch exactly. Only the lower top caps the internal interface;
  the upper bottom cap is removed to avoid coplanar double surfaces.
- Runtime writes only diffuseColor, opacity and roughness on the two shaders,
  plus task telemetry. No geometry/extent/topology/visibility updates remain.
- 0–30 s identical blue materials; 30–45 s upper clouding; 45–60 s upper clearing.
  Lower color/opacity/roughness develop linearly over 30–60 s to opaque matte
  brick-red. Reset restores both initial materials without needing readable pose.
- Policy: `visual_fixed_regions_v5`; source contact policy remains
  `visual_water_contact_v3`. `sediment_progress` is material progress;
  `sediment_height_m` is fixed including initial/reset.

## Provenance and artifacts

Source scene SHA256:
`8902bdc2062bc1a9d3d8fcace0ead2c7d86c2c45beae6848e4f702141bfb300b`.

r5 scene SHA256:
`b96cb7dd241cf15f592744e9b2f4ae9c7f7104c746f55e1a2fe0eddeb6fc1d30`.

Output root:
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r5_20260911/`.
Package under `handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r5/`,
with canonical sibling `.zip` and `.zip.sha256`. Source r3 remains a retained
build dependency. No source assets or old task outputs were replaced.

## Validation

1. TDD: `python -m pytest -q tests/test_fehlings_r5.py` first failed during
   collection because the new policy did not exist; five behavioral tests then
   passed after implementation. They cover curve continuity and clamping,
   matching initial materials, solid-red endpoint, actual embedded Shader writes
   with invariant geometry, r3 physical/state/contact equivalence, versioned
   config finalization, and reset/missing-pose paths on a real USD Stage.
2. Runtime: three independent Isaac Sim **4.5.0** processes, IDs 4018493,
   4033945 and 4049453. Each has **25 passing checks** and **19 snapshots**,
   bound to the r5 scene above. Reports: `final_cold_start_{1,2,3}.json` at the
   output root and `evidence/runtime/cold_start_{1,2,3}.json` in the package.
   Checks include dynamic low-speed insertion/bottom/wall contact, positive and
   negative contact cases, tilted contact, moving bath, pause/resume, 60 s
   completion, 3 s observation, reset, both materials and fixed geometry/height.
3. Log review: final cold-start logs have no `[Error]`, Traceback or Fatal
   entries. Early diagnostic runs exposed inherited fixture writes of dynamic
   velocity on a kinematic tube. The fixture now clears velocity only for dynamic
   bodies; three final runs and the final render were regenerated afterward.
   The early `cold_start_*` reports/logs remain outside delivery as diagnostics.
4. Visual: **15 final replay images**, with all three inputs of both shaders
   restored from retained runtime snapshots. Render manifest SHA256:
   `693c4da60d449da736961b25303696dcd132c9ce1435500e72aecdb36deef7a6`.
   Local implementer review is **WARN / usable**, not independent review.
   Full-image initial/final comparison and all-stage contact sheet inspected;
   detailed findings are in `evidence/initial_scene/visual_review.json`.
5. Closure, ZIP CRC and SHA checked by `scripts.finalize_fehlings_water_bath_r5`.
   Config finalization dispatch preserves r5 rather than restoring an old policy.
6. Repository check: initial full run had **995 passed, 1 skipped** and then
   stopped on two pre-existing unused imports in the r4 generator. Those imports
   were removed without changing its behavior; lint and both smoke targets then
   passed. The final complete `make check` passes: **995 passed, 1 skipped**,
   ruff, package-smoke, phase10x-smoke and diff-check all successful. Log:
   `make_check.log` at the output root (test duration 312.62 s).

Final delivery verification (`delivery_verification.json` at the output root)
also confirms all **1709 world transforms** match r3, all **441 copied source
dependency files** are byte-identical, all retained Mesh topologies and material
bindings are valid, and task config differs only in identity/scene path/reaction
policy. Extracting the ZIP into a new temporary directory retains **70 package-local
dependencies**, no unresolved/external paths, and a working relative scene entry.
The packaged color guide matches the repository guide; documentation links pass.

Canonical ZIP: **118,791,432 bytes**, SHA256
`63a160e96efc6c3d3af3c7305e7ea014687df9b6bf260599d316b34cde441fa9`.

Reproduction:

```bash
python -m scripts.generate_fehlings_water_bath_r5
/isaac-sim/python.sh -m scripts.validate_fehlings_water_bath_r5 --root <package> --out <report.json>
/isaac-sim/python.sh -m scripts.render_fehlings_water_bath --root <package> --report <report.json>
python -m scripts.finalize_fehlings_water_bath_r5 --root <package> --report <run1.json> --report <run2.json> --report <run3.json>
make check SMOKE_OUT=/tmp/opencode/fehlings-r5-smoke SMOKE_SUITE_OUT=/tmp/opencode/fehlings-r5-suite PHASE10X_SUITE_OUT=/tmp/opencode/fehlings-r5-phase10x
```

Finalization requires a real visual-review record bound to the final render
manifest; it does not create an automatic visual approval.

## Visible limits and evidence boundaries

The withdrawn view identifies initial blue liquid, cloudy orange-brown
mid-reaction liquid and a brick-red final tapered base with a clearer upper
region. An initial faint interface contour remains. Glass, water, rack and
reflection darken colors, especially inside the bath; the overview is for layout
and dynamic-insertion frames are not color-readability evidence. Provided
withdrawn closeups and before/after sheet are the color-inspection entrypoints.

The material is not granular and the sediment front does not rise. Liquids are
rigidly attached visual meshes without free surfaces/spilling, temperature or
real chemistry. Controlled kinematic trajectory and low-speed collision fixtures
do not establish human/robot grasp success or unrestricted impact robustness.
No Isaac Sim 4.1 compatibility or r4 CPU-collider qualification is claimed.
