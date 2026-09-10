# Export the bimanual pour for VR collection

The VR handoff is compiled from the same canonical Scenario Forge package as the
eBench/GenManip handoff. It is not a separately arranged scene. The environment,
table, vessel assets, world poses, robot model/base pose, static-support physics,
PhysX scene settings, robot material, and contact/rest offsets therefore stay in
one recipe.

## Export

```bash
PYTHONPATH=src python scripts/export_vr_teleop_package.py \
  outputs/scientific_workbench_bimanual_pour_static_support_v1_20260806 \
  --out outputs/scientific_workbench_bimanual_pour_vr_r2_20260806
```

The result is one relocatable directory:

```text
scientific_workbench_bimanual_pour_vr_r2_20260806/
  scene.usd
  task_config.py
  parity_manifest.json
  object_materialization.json
  deps/
    environment/
    table/
    source_container/
    target_container/
```

For generalized tabletop tasks, `deps/objects/<object-id>/` replaces the two
legacy vessel roles. Since the r10.1 contract, `task_config.py` lists every
tabletop task object and context prop in canonical scenario order. This lets the
VR collector randomize scene dressing without silently leaving background props
fixed. The table, room, light, and PBD particle set are deliberately excluded.
The legacy bimanual-pour shape above remains unchanged for compatibility.

## r10.1 export checklist and options

The current authoring requirements are maintained in
[USD scene organization](../standards/usd-layout.md) and
[Articulation standards](../standards/articulation.md).
This runbook provides the procedure and exporter options, not a second normative
copy of the hierarchy, registration or randomization rules.

1. Select the source and target profiles, then check USD-003 for the direct-open
   root, loader mount paths, object registration and local randomization scope.
2. For fixed-base articulated devices, use ART-001 through ART-004 for structure,
   complete link registration and root-level randomization. See the
   [design rationale](../design/articulated-instance-layout.md) for its history.
3. Run the common exporter/materialization route and inspect
   `object_materialization.json` and `parity_manifest.json` against USD-004.
   Their source/runtime paths, transform-equivalence result and content
   fingerprints explain which composition arcs were removed and what was kept.
4. Apply the standard-table VR presentation policy (USD-005) before hashing.
   The evidence includes `vr_presentation_policy` and confirmation of preserved
   collision. This policy is specific to its standard-table VR route.

Callers may set `include_robot_physics_overrides=False` when the collection
runtime owns Lift2 material/contact/rest-offset configuration. It omits
`set_robot_physics_material`, `set_robot_contact_offset` and
`set_robot_rest_offset` while retaining shared PhysX scene configuration;
the default remains enabled for existing exports.

The supported `metadata.vr_presentation_visibility: invisible` option authors
visibility for a support object's reference when the environment already supplies
its visual presentation. It does not replace or disable the qualified collider.

Give the entire directory to the VR engineer. `scene.usd` is the file to open.
Tabletop object geometry is inline; any remaining room/table USD and material or
texture dependencies are package-relative under `deps/`.
`task_config.py` is a valid standalone Python module containing one `TASKS`
mapping. Merge that one entry into the VR plugin's existing mapping. Its task ID is
`scientific_workbench_pour_flask_to_cylinder`, so the deployed directory must be
placed at `_ASSETS_DIR/scenes/scientific_workbench_pour_flask_to_cylinder/` unless
the plugin owner deliberately changes that root convention.

## Physics and collider ownership

The table consumes the same ConvertAsset `static_support` package as eBench.
Follow [ASSET-005](../standards/asset-intake.md#asset-005) for collider ownership
and the boundary between visibility overrides and collision replacement.

Both adapters use `manip/lift2/R5a_isaac41_vr600_v1`, derived from the Feishu VR
contract revision 600. It fixes Isaac Sim 4.1 PhysX scene values, robot material,
contact offset `0.05`, and rest offset `0.001`. The only accepted parity exception
is robot joint initialization: the current VR task config exposes base pose but no
joint-position field. This exception is explicit in `parity_manifest.json`; it
does not authorize any other asset, physics, or semantic drift.

## Acceptance boundary

Scenario Forge validates package closure, relative paths, shared-profile parity,
the table's passing six-probe static-support certificate, tabletop-object
materialization and transform preservation, and—when Isaac 4.1
evidence is attached—the source root, direct-open light, object list, and local
randomization mapping. The VR plugin runtime is not present in this repository,
so actual headset/controller loading and a VR episode launch remain the VR owner's
acceptance test. The export does not claim policy success, liquid transfer, or
benchmark success.
