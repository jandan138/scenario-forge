# Fehling r6: five fixed layers and 30-second multicolor development

## Agreed visual target

The user requested richer colors than r5, using
`external_artifacts/incoming/from_xinyu/菲林试剂.mp4` as a visual reference.
Frame inspection identified blue, green/olive, yellow/yellow-brown, orange and
orange-red development, with the upper region lagging the body. At video times
53.5–54 s the final experimental view is broadly orange-red, not a small pellet
under a large clear upper region. Earlier 52 s footage still has a dark upper
patch. The final patch therefore must not be frozen as the endpoint. The bright
line across the tube is the beaker water surface, not another sample interface.

The clip lasts 57.44 s, includes preparation/shaking and an outro, and labels
the heating footage ×3. It provides visual keyframes, not measured kinetics.

Decisions: five equal **height** regions; moderately enhanced readability;
each layer follows blue→green→yellow→orange→orange-red at staggered times;
all converge at **30 s cumulative valid contact**. Leave-water pause/resume,
upright stable observation for 3 s and reset remain. At 30 s the task permits
withdrawal, so visual completion and the heating gate stay consistent.

## Architecture review

The implementation is task-local: pure r6 policy, thin embedded USD writer,
versioned generation/validation/finalization scripts. Core package/schema APIs
are unaffected. Source is the qualified r5 package; r5's actual contact and
compute functions are embedded unchanged. Its state advance is replaced with
the same observation/latch structure and a 30-second completion constant.

Five Meshes share coincident boundary rings, with normals computed from the
same cavity profile. They partition the exterior surface; only the global
bottom and top have caps. No internal disks are needed for these non-physical
visual regions, avoiding five fake liquid surfaces at initial uniform color.
Runtime only writes diffuseColor, opacity and roughness on five shaders and
task telemetry; mesh points, topology, normals, extent and visibility are fixed.

Ordered `layerMeshes` / `layerShaders` relations and `layer_bounds_m` /
`layer_progress` replace r5's two-region relations and sediment-height fields.
These are task-versioned visual regions rather than independent liquid phases.
The policy version `visual_five_layers_v6` distinguishes this contract from r5.

## Completeness review

Tests cover five matching blue initial states, the hue path in every layer,
continuous monotonic development, different simultaneous layer progress,
uniform orange-red completion, clamping, the 30 s gate, early withdrawal,
paused heating, interrupted observation, success latch and pose-independent
reset. Actual embedded code is exercised on a real USD Stage. All new geometry
is fitted to the source cavity, equal height, bound to existing input types and
free of internal caps. Tests compare source physical contents and non-liquid
world transforms and check the inherited contact/compute functions structurally.

Task YAML, VR hold/color/onset times, step ID and portable metric references
must all use the new 30 s rule. Finalization dispatches by the new policy.
Runtime snapshots capture every shader input and all layer progresses. A hash
of all non-Looks visual properties and bindings verifies fixed geometry across
the full path and reset. Geometry need not be rewritten during render replay.

## Risk review

Main risks are unintended gray interpolation and transparent-interface artifacts.
Explicit green/yellow/orange keyframes avoid a direct blue-to-brown blend;
capless internal boundaries reduce artificial interfaces. Material colors are
validated through the actual glass and water; same-pose withdrawn runtime
snapshots expose color changes obscured by the water bath. Image crops retain
the same scale and no post-hoc recoloring. The darker tapered region and
discrete intermediate colors remain documented limitations.

New source/output identities prevent overwriting prior packages. Three fresh
Isaac Sim 4.5 processes qualify the final scene, plus closure, relocation and ZIP
CRC/hash checks. No producer physical repair, dependency conversion or new
external service is introduced. No true chemistry, thermal solution, fluid
mixing, human/robot success or cross-runtime qualification is inferred.

## Standards and operations

This is an explicit spatial-rendering use under [MAT-005](../standards/materials-and-liquids.md#mat-005):
five non-overlapping portions of one sample, not five overlapping complete
liquids switched by color stage. It adds no universal layer count or time rule.

- [Operating guide and numeric curves](../operations/fehlings-r6-color-guide.md).
- [Dated evidence](../records/2026-09-11-fehlings-r6-five-layer-color-development.md).
