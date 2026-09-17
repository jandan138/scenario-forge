---
name: hunyuan-isaac-articulation-assets
description: "Create or validate Hunyuan3D-derived USD assets in Isaac Sim, including Blender cleanup, PhysX setup, and a single ArticulationRootAPI per complex asset. Use for articulated asset generation, conversion, or physics acceptance; do not use for ordinary static meshes or browser-game GLB packaging."
---

# Hunyuan Isaac Articulation Assets

Use this skill for a Hunyuan3D-to-Isaac Sim asset workflow when the deliverable needs USD, PhysX joints, or articulated interaction. Treat the generated mesh as source geometry, not as an automatically valid physical asset.

## Required outcome

Produce a self-contained, reopenable USD asset with explicit units/orientation, separated visual and collision geometry, and a documented validation result. For every complex articulated asset, build one articulation per asset scope and exactly one `UsdPhysics.ArticulationRootAPI`.

## Default articulation contract

- Default to a fixed-base articulation for appliances and other world-supported objects.
- Put the single root API on the root fixed joint that connects `Links/Base` to the world. The base must be a rigid-body root link; do not leave it as a separate world-anchored static body.
- Connect every dynamic child link through a supported joint with `body0=parent` and `body1=child`. Do not give child links independent world joints.
- Use a floating-base mode only when explicitly selected; in that mode put the root API on the selected root body and state the choice in the report.
- Keep the included articulation graph connected and tree-shaped. A loop, unsupported joint, or separate mechanism is an exception: redesign it, use an articulation-supported mimic/tendon where appropriate, or exclude the closing joint with a non-empty documented reason and a stability test.
- Set initial joint positions through articulation joint state APIs. Do not set non-root link poses after playback starts.

## Workflow routing

1. Classify the input as a Hunyuan mesh, an existing mesh, or an existing USD.
2. Read [hunyuan-isaac-workflow.md](references/hunyuan-isaac-workflow.md) for generation, repair, scale/orientation, and USD authoring decisions.
3. Read [articulation-physics.md](references/articulation-physics.md) for the single-root topology, joint drives, collision proxies, variants, and exception policy.
4. Read [validation-and-acceptance.md](references/validation-and-acceptance.md) before claiming physics or interaction success.
5. Run `scripts/check_articulation_usd.py` in Isaac Kit Python for the static contract. Use Isaac Sim 4.5 for runtime acceptance; report Isaac 4.1 as static-only unless a runtime is actually available.
6. Read [oven125-legacy-case-study.md](references/oven125-legacy-case-study.md) only when comparing with the historical oven implementation. It is evidence and a migration reference, not the new topology default.

## Source route fallback (local amendment 2026-09-17)

Hunyuan3D is the preferred but not the only geometry source. If Hunyuan is unavailable (model access, environment, or licensing), build the mesh procedurally in Blender alone, driven by the asset spec's frozen dimension table and evidence images. See "Source route fallback" in [hunyuan-isaac-workflow.md](references/hunyuan-isaac-workflow.md). This is a repo-local amendment: re-apply it after any wholesale skill update.

## Non-negotiable authoring rules

- Do not assume Hunyuan topology is watertight. Inspect and repair before conversion.
- Prefer procedural USD geometry when exact cavities, dimensions, support surfaces, or collision behavior matter.
- Keep collision meshes low-complexity and separate from visual meshes; use hidden support proxies where a visual rail or shelf cannot provide a reliable contact surface.
- Model viscous resistance with `UsdPhysics.DriveAPI` damping and rigid-body damping. Do not add `physxJoint:jointFriction` to non-articulation joints.
- Use positive-scale mirrored variants for physical geometry. Clear direct USD opinions before authoring VariantSet values when composition precedence could mask a change.
- Parameterize Isaac, Hunyuan, server, and output paths; never copy the historical oven's machine-specific paths into a reusable asset.
- Measure actual composed USD world bounds for every frozen dimension. Do not use configuration values as a substitute for a stage-bound measurement.
- Export authored root layers directly when distributing binary USD if the toolchain can flatten variant opinions; reopen the binary and enumerate every VariantSet/selection.
- Treat state-machine math, scripted angle sweeps, and AABB/clearance checks as portable evidence only. Mark G1--G3 `NOT_TESTED` until PhysX joint state, contact, and drift playback is recorded.

## Isaac 4.5 environment compatibility

- When direct Kit Python can import `pxr` but fails to register PhysX schema plugins, run authoring/validation from Isaac's `python.sh` after starting one `SimulationApp({"headless": True})`; this loads `omni.usd.schema.physx` and `omni.graph.core` before USD authoring.
- USD 0.22 bindings shipped with Isaac Sim 4.5 may not expose `Usd.Prim.GetDescendants()` or `Sdf.Path.IsPrefixOf()`. Use `stage.Traverse()` and explicit string/path-prefix filtering in portable checkers.
- Blender is an optional preprocessing tool. Probe the configured host for `blender`/`bpy` and keep Blender-specific cleanup separate from the Isaac USD authoring environment; do not assume `/root/blender-4.0.2-linux-x64/blender` exists.

## Reporting

Report the asset root, articulation mode, root prim, body/joint counts, static-check result, runtime Isaac version, tests run, known limitations, and any articulation exception. Distinguish direct-force smoke tests from robot grasp/contact validation.
