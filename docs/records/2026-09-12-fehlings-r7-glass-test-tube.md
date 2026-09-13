# Fehling r7: plain rolled-rim glass tube, eight-mL fixed sample

## Scope and standards

User approved nominal18×150 mm generic borosilicate-style glass, 1 mm engineering
wall, gentle rolled rim, round bottom, no printing, 8 mL visual sample and rack
scaling only if fit requires it. The r6 five-layer/30-second reaction is retained.
Design review: [glass tube integration](../design/fehlings-glass-test-tube.md).
Operations: [r7 guide](../operations/fehlings-r7-glass-tube-guide.md).

Standards read: current ASSET-001/002/003, USD-002/004, MAT-001–006,
STATE-001–006 and VAL-001–006. 规范无需新增通用规则：本次是获授权的生产者资产替换，
不是消费者修生产者碰撞；现有接入、物化、材质、状态与证据规则已经覆盖。
同批补充设计、操作、当前标准案例引用、生产者记录和交付证据，不把尺寸或8 mL推广为通用要求。

## Producer and source

ConvertAsset output:
`outputs/chemistry_test_tube_18x150_r1_20260912/package/`.
Entry `asset.usd`, root `/World/TestTube`, sole glass mesh
`/World/TestTube/Visual/GlassShell` and local OmniGlass material closure.

- Blender4.4.3 actual creation, bmesh manifold/winding/positive-volume/open-lumen
  checks, CPU Cycles overview/mouth previews and an independent reopen pass.
- 38,146 vertices, 76,288 triangles, OD18/ID16 mm, height150 mm, maximum rim OD20 mm.
- Inner/outer round-bottom radii8/9 mm share z9 mm centre; floor z1 mm.
- Density2230 kg/m³ is an engineering assumption. Signed-solid mass:
  **0.01800892040135455 kg**, COM z0.07610319835919559 m.
- SDF resolution512, contact offset0.25 mm, rest offset0. No lumen-filling proxy.
- Material: local OmniGlass, neutral white, IOR1.47, roughness0.02, real transmission.
- Producer geometry/package tests:7 passed. Promotion plus producer tests:
  **46 passed** after matching the actual `process_id` report schema; Ruff passed.
  Promotion tests use disposable copies/synthetic reports and separate read-only
  parsing of the actual final reports. They are not extra simulator runs.

Frozen asset SHA256:
`4f7129da98db6d3307bb924834e97f001f6d7ce9e3fba95273bb95d6788cd757`.
Blender SHA256:
`96ed8e1a6c627317fe9a6afd7d78f84c3a024cf86fdfc6881eb3cfdc64ca3547`.
Geometry JSON SHA256:
`504b510d27610beaf59b1e2732990209d46cec582bb085df5570f920e176db67`.

Supplier search results support nominal18×150 mm sizing; full product-page
retrieval was unreliable. Wall/lip/density/optical values remain explicit
engineering choices. The model is not a manufacturer replica or a thermal test.

## Scene integration and rack result

Source r6 scene SHA:
`2835c2b541c5f2db5008653345f4ace86d3780c82beac664d4aff0e7c30de3d4`.

Final r7 scene SHA:
`71e38a115fc2b1e5fa8294224d16a3cc17474bc6015196e319c7d431ed460098`.

Source materialization uses Scenario Forge's existing VR object materializer,
retaining relative local asset paths and no composition arcs under the tube.
New glass asset is copied to `deps/chemistry_test_tube_18x150_r1/`; prior
dependencies remain as historical inputs. Other physics is unchanged.

Five-region mesh volume is **7.999999861264258 mL**. Sample bottom z1.1 mm,
top43.78056203 mm, height42.68056203 mm, each layer8.53611241 mm. The solver
uses the source cavity and compensates actual mesh discretization/meniscus.
Tube radius/mouth/sample-profile metadata changes with the geometry; the
embedded r6 state/contact script remains byte-identical.

Rack measured guide diameter≈20.46 mm, body radial clearance≈1.23 mm.
**Scale remains (1,1,1)**. In each final run, the tube starts around
`(0.12148709,-0.14615604,0.77847803)` m after settlement and ends the reinsert
around `(0.12147991,-0.14631884,0.77847636)` m. Dynamic extraction clears the
upper plate; reinsertion returns within the configured stability tolerance.
These are velocity-guided dynamics, not a gripper or robot-policy result.

## Diagnostics and corrections

Initial candidate and diagnostics are retained at
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7_20260912_diagnostic_v1/`.

1. Underpowered upward velocity did not overcome gravity during the native step;
   the fixture now commands0.25 m/s upward and records actual positions.
2. The old inverted negative-test height let a150 mm tube touch the beaker floor.
   The r7 upper-only pose was raised. Wall-only negative cases can move a dynamic
   beaker, so each independent contact case re-seats it before placement.
   No beaker physics change is authored into the package.
3. Actual glass shadows caused black stripes on near-wall fake liquid. The
   diagnostic no-shadow render removed them. The final scene authors only
   `primvars:doNotCastShadows=true` on the new glass shell, matching the task's
   prior readability policy. Producer mesh/material/source/MDL bytes stay fixed.
4. Failed fixture runs now retain partial checks and snapshots, rather than
   losing the useful pre-failure evidence.

All final reports and final renders were regenerated after the scene-level
shadow opinion. Early diagnostic reports/images are not delivery qualifications.

## Final runtime and visual evidence

Three independent **Isaac Sim4.5.0** runs, process IDs
**2841658 / 2846800 / 2851656**, each **35 passing checks and38 snapshots**.
They cover rack seating/extraction/reinsertion, body mass, bath contacts,
positive/negative semantic cases, moved bath, 30 s reaction, observation,
reset, all five materials, sample identity and fixed geometry.

Producer qualification was promoted only after those exact passes, with scope:
**`Isaac Sim 4.5 Fehling r7 rack and bath prescribed fixtures`**.
Source/asset/MDL/scene bytes are frozen; only compact runtime summaries and
qualification metadata were synchronized. Robot, heat and PBD claims remain false.
Finalizer rejects report triplets other than the promoted originals.

**29 final replay images** cover full tube, rim/mouth, rounded sample bottom,
rack cycle, bath views, all colors and reset. Final render manifest SHA:
`17f39cbdd9149ba82cf405dc48db42c328e8227c023071771cb6fd6858c94d2b`.
Local implementer review: **WARN / usable**, no blocking defects; not independent review.
The 0/9/15/21/27/30 s sheet uses identical crops, with source hashes and no recoloring.
Rack/background reflections, rim occlusion, bright mouth reflections and discrete
intermediate layer transitions remain documented limits.

## Delivery and checks

Output:
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7_20260912/`.
Package:
`handoff/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r7/`.
Editable Blender source is embedded at `deps/chemistry_test_tube_18x150_r1/source/tube.blend`.
## Closeout checks

SF focused r7/r6/r5/r3 tests: **24 passed**, including the regression requiring
the same report triplet used in producer promotion; targeted Ruff passes.

```bash
make check SMOKE_OUT=/tmp/opencode/fehlings-r7-smoke SMOKE_SUITE_OUT=/tmp/opencode/fehlings-r7-suite PHASE10X_SUITE_OUT=/tmp/opencode/fehlings-r7-phase10x
```

Full working-tree result: **1022 passed, 1 skipped** in332.34 s, Ruff,
package-smoke, phase10x-smoke and diff-check all pass. Log: `make_check.log`
at the r7 output root. This includes the currently present independent worktree
tests and is not a claim that unrelated ongoing work has been submitted.

`delivery_verification.json` confirms:

- **1657 non-tube world transforms** and all non-tube physics match r6.
- All **441 retained r6 dependency files** and **14 new producer files** match
  their source bytes, including the qualified metadata and editable Blender source.
- Actual serialized USD sample volume **7.9999927038443275 mL**; the tiny difference
  from the recipe's double-precision mesh value is float32 serialization.
- Config keeps GPU dynamics and the30-second policy, with the correct r7 identity,
  glass-container semantics and8 mL sample.
- ZIP CRC, SHA256 and a fresh-directory extraction pass. **71 package-local USD
  dependencies**, no unresolved/external paths; transitive MDL bytes also match
  the producer audit. The relocated config resolves its local scene entry.
- Three final runtime logs and the final render log have no Error/Traceback/Fatal entries.
- Packaged guide matches the repo guide; local documentation links resolve.

Canonical ZIP: **138,214,173 bytes**, SHA256
`f8340b4c61aeda7efabc161fb4ee926bea6c49631091664cc7b72c4acc405fcd`.
The current `vr_open_tube_positive_visual_reaction` head advances to r7;
r6 remains the retained source and the separate CPU-r4 candidate is not reused.
