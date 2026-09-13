# Fehling r7: Blender glass tube, measured 8 mL and rack fit

## Approved design

The user selected a generic chemistry test tube with nominal body OD18 mm,
height150 mm, round bottom, small rolled rim, clear colorless glass and no
printed markings. The visual sample is8 mL, split into five equal-height
regions using r6's unchanged 30-second color/state policy. Rack scaling is
conditional on actual fit validation rather than a mandatory visual enlargement.

Indexed commercial 18×150 mm products support nominal sizing. Manufacturer
detail pages were not consistently accessible; wall1 mm, rolled-rim OD20 mm,
glass density2230 kg/m³ and the chosen optical inputs are explicitly engineering
parameters, not an exact vendor replica or measured physical-glass qualification.

## Architecture review

ConvertAsset owns the procedural Blender model, closed-solid geometry, normals,
physical moments, SDF collision, local OmniGlass material closure and producer
qualification. Scenario Forge consumes the frozen package and uses its existing
VR object materializer to replace the tube at `/World/obj_sample_tube`.
It preserves r6's controller string, object identity and other scene physics.
This adds task-local scripts, not conversion code or simulator imports in core.

The source `.blend` and geometry JSON remain in the embedded producer package.
Only a task-level `primvars:doNotCastShadows=true` opinion is applied to the
materialized glass mesh; this carries forward the reaction task's readability
policy. Source glass material, mesh, mass and MDL bytes remain producer-owned.

## Geometry and sample

Outer and inner round bottoms have radii9/8 mm about z9 mm, giving exterior
bottom z0 and inner floor z1 mm. The plain body is OD18 / ID16 mm and the lip
reaches OD20 mm. Glass solid mass is derived by signed tetrahedral integration:
about18.0089 g; the fake sample adds no separate physical-fluid mass.

The sample profile begins0.1 mm above the inner pole and follows the producer
cavity. r6's five-region mesh construction retains its0.02 mm radial inset.
The volume solver compensates for polygonal section, rounded-bottom sampling
and meniscus so the combined mesh encloses8 mL. Height is about42.68056 mm,
not8 mL divided by an assumed constant cylindrical area. Contact profile,
sample top, outer radius and mouth height are updated together.

## Rack fit and completeness review

Measure the actual occupied-slot guide rings rather than trusting the rack's
nominal metadata: the two guide levels have diameter about20.46 mm. Body18 mm
thus has about1.23 mm radial clearance; the lip remains above the rack while
seated. Check the existing support collider and curved visual seat separately.

Runtime qualification tests initial settling, dynamic upward extraction and
downward reinsertion, water entry and wall/bottom contact, semantic contact
positive/negative cases, all color stages, pause/resume, observation and reset.
Original rack scale1 passed all three final runs, so no rack resize was applied.

The longer tube requires an adapted test fixture: inverted upper-only contact
is placed higher to avoid the lip touching the bath floor; negative wall-contact
cases re-seat the dynamic beaker before the next independent case. The upward
velocity command exceeds per-native-step gravity loss. These are fixture
operations, not new runtime reset rules or proof of robotic grasping.

## Risk review and evidence boundaries

Thin glass/SDF validity, lumen closure, physical moments, namespace/path
remapping, near-wall shading and false inherited qualification are the main
risks. Producer creation/reopen/static tests, source-equivalence tests and
three exact-scene cold starts address these within Isaac Sim4.5 GPU/SDF scope.

An initial render exposed black striping from glass shadow rays on near-wall
visual liquid. Diagnostic images isolated the shadow effect; the final scene
restores the existing glass-shadow readability policy and is revalidated and
rerendered. Earlier failures remain in a separate diagnostic output. No image
recoloring is used to pass the visual review.

Producer promotion changes only evidence metadata after validating the frozen
asset, source, MDL closure, scene and distinct report process IDs. Finalization
requires the same promoted report hashes, final visual-review identity and
package closure. Future scenes cannot silently inherit this fixture-specific
qualification.

No actual chemistry, temperature, breakage, spill, robot or CPU/4.1 capability
is added. Five visual colors remain a teaching representation.

See [operation guide](../operations/fehlings-r7-glass-tube-guide.md) and
[dated evidence](../records/2026-09-12-fehlings-r7-glass-test-tube.md).
