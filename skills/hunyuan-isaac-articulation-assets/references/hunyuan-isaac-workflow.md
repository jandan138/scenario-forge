# Hunyuan3D → Blender → Isaac USD workflow

Read this reference for any asset that starts as a Hunyuan3D mesh or that needs a repeatable mesh-to-USD handoff. The skill's main contract remains authoritative for articulation topology.

## Input and output contract

Record these inputs before generating anything:

- `asset_id` and intended asset root prim.
- Hunyuan model/revision, prompt or reference images, seed, steps, guidance, resolution, and whether shape or paint was used.
- Blender version and cleanup operations.
- Isaac Sim/Kit version, stage units, up axis, and output USD path.
- Whether the asset is fixed-base or floating-base, and the intended interaction links and degrees of freedom.

The deliverable is a self-contained USD (or a deliberately documented package of self-contained layers) that can be reopened without the generation process, has an explicit default prim, embeds or resolves all materials and textures, and contains the validated visual/collision/physics graph. Keep provenance metadata in a sidecar JSON or custom namespaced attributes; do not hard-code machine-specific paths in reusable instructions.

## 1. Choose the source route

Use Hunyuan shape generation when a fast silhouette or a reference mesh is useful. Use Hunyuan paint only when generated textures materially improve the deliverable. A Hunyuan result is not automatically a final CAD model, collision mesh, or watertight shell.

If the request requires exact dimensions, cavities, wall thickness, shelves, hinges, or stable contact surfaces, author those features procedurally in USD (or rebuild them in Blender) and use the Hunyuan mesh as visual/reference input. Preserve the original candidate in a clearly named reference layer or provenance record rather than silently presenting it as authoritative geometry.

## Source route fallback (local amendment 2026-09-17)

If Hunyuan3D is unavailable (no model access, environment down, or licensing), select the Blender-only procedural route instead of blocking the asset:

- The asset spec's frozen dimension table and evidence images become the sole geometric authority. Never invent dimensions the spec grades as unknown; unresolved values go back to the spec's open-measurements list.
- Budget more iteration rounds than the Hunyuan route: silhouette/proportions → frozen dimensions → functional details (cavities, shelves, handles) → materials, with each round checked against the spec before proceeding.
- All other contracts are unchanged: articulation topology, collision/visual separation, static gate, and validation apply exactly as for a Hunyuan-derived asset.
- Record `source_route: blender_procedural` (versus `hunyuan`) plus the Blender version and iteration count in the provenance sidecar.

This is a repo-local amendment: re-apply it after any wholesale skill update.

## 2. Generate in a reproducible environment

Run Hunyuan with the project-selected model and isolated environment. Record the full invocation, seed, and output hashes. Run Isaac authoring scripts with Isaac Kit's Python/Kit runtime so `pxr`, USD schemas, and PhysX extensions resolve from the target Isaac installation; do not assume an ambient conda Python is equivalent.

Use parameterized variables such as `HUNYUAN_ROOT`, `ISAAC_ROOT`, `ASSET_ROOT`, and `OUTPUT_DIR`. Never copy a personal server path or credential into a skill, generated USD, or report.

## 3. Inspect and repair the mesh

Before USD conversion, inspect:

- units, bounding box, axis orientation, origin, transforms, and scale;
- non-manifold edges, holes, inverted normals, self-intersections, degenerate faces, and disconnected islands;
- material slots, texture references, UVs, and texture color space;
- whether the intended cavity/interior is actually modeled rather than visually implied.

Repair only what is necessary and record each operation. For collision, create separate low-complexity proxies (boxes, capsules, convex decomposition, or an appropriate SDF/mesh approximation) instead of using a detailed Hunyuan surface as the sole collider. For open vessels and appliances, verify that the shell and interior floor are closed enough for the selected collision method.

## 4. Blender handoff

Use Blender for deterministic cleanup, scale/orientation normalization, decimation or retopology, material consolidation, and export. Apply transforms before export when the target pipeline requires baked scale; preserve a copy of the unmodified candidate for comparison. Verify that mirrored parts use positive scale, especially for physical geometry and collision meshes.

Export an intermediate GLB/OBJ only as an auditable handoff. Reopen the exported file and compare its bounds, orientation, material count, and mesh count with the repaired source before authoring USD.

## 5. Isaac USD authoring

Create a new standalone layer or asset stage rather than mutating the source candidate. Use a stable asset root such as `/World/<AssetId>`, set it (or its designated component root) as the default prim, and author `kind=component` when the target asset convention supports it. Keep visual meshes under their link and collision proxies under a separate, consistently named collision scope. Add stable interaction frames (hinge, grasp, support, opening, sample-floor, sensor) as child Xforms with documented local coordinates.

Apply explicit USD/PhysX schemas for rigid bodies, mass/inertia, colliders, joints, limits, drives, and material properties. For open vessels, chambers, or ovens, verify that the cavity/interior floor is modeled and that the selected shell/collision representation is closed enough for the chosen mesh or SDF method. Use the articulation topology and root placement in [articulation-physics.md](articulation-physics.md); do not invent a second world-anchored mechanism tree as a shortcut.

For fixed-base assets, the base link is a rigid-body link attached to the world by the single root fixed joint. Visual-only details may be children of a link without their own rigid body. Any independently moving or load-bearing part must be a link in the same articulation tree.

## 6. Materials and self-containment

Prefer embedded Preview Surface/MDL-compatible material data or package texture references relative to the asset. Scan the reopened stage for unresolved asset paths, missing textures, unexpected external references, duplicate default prims, and unit/up-axis drift. A successful export is not complete until a fresh process can open the USD and enumerate the same links, joints, colliders, and materials.

## 7. Validation handoff

Run the static checker from Isaac Kit Python:

```text
python check_articulation_usd.py --usd <file> --asset-root <prim> --mode fixed --json-out <report.json>
```

Then follow [validation-and-acceptance.md](validation-and-acceptance.md). Isaac 4.5 is the full runtime target for this skill. Isaac 4.1 results must be labeled `static_audit_only` unless a real 4.1 runtime test was executed.

## Common failure modes

- **Looks correct but falls apart:** the Hunyuan mesh was used as a collider without checking topology or contact surfaces. Rebuild proxies and test under gravity.
- **Correct in Blender, wrong in Isaac:** units, up axis, unapplied scale, or transform order changed at export. Reopen and compare bounds before adding physics.
- **A mechanism is not controlled as an articulation:** a link or joint was left world-anchored or the root API was placed outside the intended asset scope. Run the static checker and inspect body0/body1 relationships.
- **Materials disappear on another machine:** the USD still references an absolute texture path. Package or embed the material and rerun the self-containment scan.
- **A variant appears unchanged:** a direct opinion overrides the VariantSet value. Clear the direct opinion before selecting and validating the variant.
