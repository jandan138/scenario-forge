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

## r10.1 source-root and randomization contract

The deliverable `scene.usd` is directly openable. Its `defaultPrim` is `/World`
and it does not author `/World/_scene`. Direct children use these names:

- `background` for the room;
- `table` for the static workbench;
- one `obj_*` prim for every tabletop task object and context prop;
- `vr_direct_open_light`, a texture-free white DomeLight with intensity `750`.

`/World/_scene` is a runtime mount created by the VR loader. Therefore paths in
`task_config.py` are runtime paths such as `/World/_scene/obj_beaker`, even though
the source USD contains `/World/obj_beaker`. Do not pre-author the mount wrapper
in the source file.

Every `obj_*` entry appears exactly once in `obj_prim_list` and exactly once in
`layout_randomization.objects`. Randomization is local-frame XY translation only:
`x` and `y` are both `[-0.01, 0.01]` metres and yaw is fixed to zero. Items that
must preserve their internal arrangement share one group—for example a rack and
its tubes. Task 02 similarly groups the PBD runtime with its graduated cylinder,
although `fluid_runtime` itself is not an `obj_*` entry.

Give the entire directory to the VR engineer. `scene.usd` is the file to open;
its USD, MDL, mesh, and texture references are package-relative under `deps/`.
`task_config.py` is a valid standalone Python module containing one `TASKS`
mapping. Merge that one entry into the VR plugin's existing mapping. Its task ID is
`scientific_workbench_pour_flask_to_cylinder`, so the deployed directory must be
placed at `_ASSETS_DIR/scenes/scientific_workbench_pour_flask_to_cylinder/` unless
the plugin owner deliberately changes that root convention.

## Physics and collider ownership

The table is the same ConvertAsset `static_support` package used by eBench. Neither
the VR scene nor Scenario Forge authors a local slab. If a downstream stronger USD
layer needs to replace support collision, it must explicitly disable the delivered
collider before enabling the replacement. Layering a second active collider on top
is invalid.

Both adapters use `manip/lift2/R5a_isaac41_vr600_v1`, derived from the Feishu VR
contract revision 600. It fixes Isaac Sim 4.1 PhysX scene values, robot material,
contact offset `0.05`, and rest offset `0.001`. The only accepted parity exception
is robot joint initialization: the current VR task config exposes base pose but no
joint-position field. This exception is explicit in `parity_manifest.json`; it
does not authorize any other asset, physics, or semantic drift.

## Acceptance boundary

Scenario Forge validates package closure, relative paths, shared-profile parity,
the table's passing six-probe static-support certificate, and—when Isaac 4.1
evidence is attached—the source root, direct-open light, object list, and local
randomization mapping. The VR plugin runtime is not present in this repository,
so actual headset/controller loading and a VR episode launch remain the VR owner's
acceptance test. The export does not claim policy success, liquid transfer, or
benchmark success.
