# Titration r1.7: open downward nozzle and reference object placement

## Scope and ownership

r1.7 derives from the retained r1.6 scene. ConvertAsset owns the visual nozzle
repair in `traditional_titration_station_r4`; Scenario Forge imports only the
two qualified visual prim specs at their existing scene paths and applies five
reference root translations. It does not implement conversion logic or modify
producer physics. The source background, object tree, material paths, links,
joints, collider shapes and r1.6 task controller are retained.

The only allowed prim-type change is
`/World/obj_titration_station/Instance/Burette/body_link/Visual/delivery_tip`:
Cone becomes Mesh at the same path. No prim is added or removed. The existing
`liquid_precharge` stays a Mesh and receives the matching distal profile.

## Root cause and corrected geometry

The original standard Cone had axis Z with no rotation, so its apex pointed up.
The authored `asset:tip_radius2_m` metadata did not make it a truncated or hollow
cone. The previous precharge audit checked containment within the source outer
primitive envelopes; it did not establish a correctly oriented hollow outlet.

The producer repair removes the old 10 mm overlap with the glass outlet: the
new nozzle runs from body-link z=-0.23 to -0.28 m, while its prim translate stays
at z=-0.25 m. The outlet endpoint stays fixed. Outer radii are 2/0.8 mm and inner
radii 1.55/0.4 mm at top/bottom. Inner/outer walls and annular ends form the glass
solid while leaving an open axial lumen. Winding and face-varying normals are
checked for all faces.

The distal precharge follows the lumen with 0.05 mm radial clearance and ends
0.2 mm above the exit. Upstream precharge, the 25 mL metered column, meniscus and
all material parameters remain unchanged. There are no external drops or new
liquid physics. The producer has its own shape tests, static audit, three
standalone Isaac 4.5 runs and promotion receipt.

## Reference placement

The immutable input ZIP is
`external_artifacts/incoming/from_xinyu/task_10_titration_experiment.zip`, SHA
`a68ab0cefeec96cee73e4f511c6ee3199027e753ad6a4f3f6cdaf2e893cb63a9`.
Its embedded scene SHA is
`1cbf81d6c0499cd9e4045b86a4e65750a2654261ac00d84e470ec9a8d8ddffcb`.

Both scenes use meters and Z-up. The five common task objects have identity
root rotation/scale and unchanged internal transforms. Their exact world
matrices are read into `evidence/initial_pose_reference.json`; rounded values
are not used as build inputs. Background/material/physics content from the ZIP
is not imported.

The station and receiver move to y=-0.17674479517291017 m; the stirrer moves to
y=-0.1898312215769973 m. The sample beaker and context flask move to y values
0.023255204827089843 and 0.013255204827089834 m respectively. Original x/z and
randomization groups remain. The ceramic plate's center is offset from its root,
so the different stirrer/receiver root y values are not themselves a centering
error; final support/alignment checks use composed bounds and runtime state.

## Evidence and standards

The change audit compares every prim path/type, applied schema, relationship,
attribute value/type/time samples and attribute connections. It allows only the
specified geometry properties and five root translations. A negative test
changes mass and requires rejection. The scene controller string must match r1.6
exactly. Final runtime checks add pre-run reference matrices, fixed station
placement and flask support to the existing linear-flow and single-material tests.

Rendering follows the new task placement and includes dedicated side/outlet
macros at initial, mid-scale and end-scale states. These are explicitly static
visual snapshots; runtime timing comes from the separate exact-scene reports.
Consumer finalization requires matching producer, pose, structure, runtime and
render/visual-review evidence, then dependency closure and ZIP CRC/SHA.

The general lesson belongs to MAT-003: inspect primitive direction and aperture
semantics, and validate liquid against the actual lumen, not merely the outer
AABB or a custom metadata label. The standards are updated after the new
geometry and runtime verification; historical records keep their original scope.

Build: `python -m scripts.generate_traditional_titration_vr_r17`.
Output: `outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_7_20260908/`.
The delivered color guide explains the type change and current paths.

## Final validation

Producer asset SHA:
`6b9101c118c2ddbcc2d635c41d8fb1cbdd476e39f1cdc97fe3202dbb5b5502cb`.
Four focused producer tests, Ruff and three independent Isaac Sim 4.5 cold
starts pass; the promoted receipt is embedded in the consumer package.

Consumer scene SHA:
`d190860a6641629f4f61e661a8af93c79e6fb55b9e5f070e54a83738f302e132`.
Three cold starts pass, including reference placement, fixed-root stability,
support/alignment, the unchanged flow/color policy and single-material behavior.
All 2579 prim paths remain; the only type change is delivery_tip. The allowed
attribute diff contains the five root translations and two visual geometries.

`make check` passes with 949 tests and one skip; all 18 focused consumer tests
pass. The new external-artifact tests are marked local_artifacts for portable CI.
Twenty-one 1920×1080 static images cover full/mid/end scale, including side and
outlet macros. Local visual review accepts the corrected taper and opening,
with the retained clear-liquid/dark-reflection contrast caveat; not an independent
review. Geometry/normal tests establish lumen clearance in addition to the views.

ZIP CRC/SHA and closure pass; current VR head advances to r1.7. The original
input ZIP and r1.6 package remain unchanged. No source background, materials or
physics are imported from the reference ZIP.

## 2026-09-11 Git closeout recheck

The r1.7/r1.6/r1.5 focused consumer tests pass: **17 passed**. The retained
r1.7 scene hash still matches the final value above; all packaged runtime
reports pass the current evaluator and contain passing r1.7-specific checks.
ZIP CRC, SHA and extraction into a fresh directory pass, with **19 package-local
dependencies** and no unresolved or external paths. The three original startup
logs remain under the output's `runtime/` directory; this closeout did not rerun
the simulator or change the qualified scene.

Canonical ZIP: **31,604,694 bytes**, SHA256
`cbaed136cb9bbb545fad35bba93674bf8bcedabc4d92493bd625d047309398ff`.
The related MAT-003 clarification and r1.7 task head are committed with this
consumer revision. Producer sources remain owned by ConvertAsset; its promoted
asset and receipt are retained in the existing delivery.
