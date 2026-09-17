# Oven 125 legacy case study

This is a validated historical example and a source of reusable lessons. It is deliberately marked **Legacy** for topology: the final oven v3 asset uses a self-contained USD/PhysX joint graph and sets `oven:usesArticulationRoot=False`. It must not be used as the default topology for new complex articulated assets.

## What was successful

- Hunyuan3D-2.1 shape output was retained as an auditable silhouette/reference candidate. The authoritative oven geometry was procedurally authored in Isaac USD because exact dimensions, chamber cavities, materials, supports, and collision behavior mattered.
- The final asset is self-contained and reopenable, uses meters and Z-up, and has no external references, payloads, textures, or runtime controller paths.
- The final v3 package contains 16 rigid bodies, 3 revolute joints, 11 prismatic joints, 2 shelf fixed joints, and 100 colliders.
- Isaac Sim 4.5 structure, PhysX regression, interactive smoke, rendering, and NVIDIA Asset Validator all passed. Isaac 4.1 received a static API/schema audit only; no 4.1 runtime was available.

## Mechanical patterns worth reusing

- Door: independent rigid body, Z-axis revolute motion, explicit limits, authored handle interaction frame, and mirrored left/right hardware variants using positive-scale geometry.
- Knob: independent prismatic press carrier plus an independent revolute rotor, allowing simultaneous press and rotation.
- Buttons: separate prismatic links with spring-return drives and explicit rest/pressed clearance checks.
- Rocker: explicit revolute axis and hard limits.
- Shelves: fixed/removable modes, six level variants, and invisible support colliders for actual load-bearing contact.
- Resistance: DriveAPI damping plus rigid-body angular damping. The implementation removed ineffective `physxJoint:jointFriction` opinions from non-articulation joints and avoided the resulting ignored-friction warning.

## The support-collider failure and repair

The original shelf proxy and cylindrical rails had conservative AABB gaps of approximately `6.7 mm` in X and `0.2 mm` in Z. With removable mode selected, shelves fell by about `123 mm` and `333 mm` before extraction. The repair added two invisible support boxes at each of six levels, each `0.014 × 0.430 × 0.004 m`, positioned to provide coplanar support and measurable overlap.

Post-fix Isaac 4.5 acceptance used two independent `30 kg` load blocks for `600` frames per shelf, with zero measured shelf drift. Force-driven extraction was approximately `38.9 mm` and `39.1 mm`, with zero post-extraction support drop. This is the general lesson: infer support from actual proxy overlap and gravity behavior, not from visual proximity or nominal rail geometry.

## Acceptance evidence

- Both hinge variants opened to approximately `180°` under direct `220 N` handle force and returned near closed with zero body drift.
- Eight closed-door seal/frame AABB pairs passed without conservative penetration.
- Ten buttons passed rest and pressed checks across `90` button-pair tests; minimum pair gap was approximately `7 mm`, and pressed-to-fascia gap was approximately `4.3 mm`.
- The interactive controller passed `12/12` branches, restored all `13` temporary drives, and ended at event sequence `242`.
- NVIDIA Asset Validator reported `0 failures / 0 warnings / 0 errors / 0 infos`.

## What must not be generalized blindly

- The oven's dimensions, masses, force values, server paths, model paths, and UI/thermal behavior are asset-specific.
- Direct world-space forces at authored handles and shelf application points do not prove a particular robot grasp, planner, controller, or per-contact impulse behavior.
- The oven's disconnected/world-anchored mechanism organization is the reason it is a legacy joint-graph example. New assets should consolidate the mechanisms under one base link and one root articulation whenever the target PhysX topology supports it.
- The remaining 4.1 runtime, robot integration, triangle-level signed-distance penetration, and calibrated appliance behavior were not established by this case.
