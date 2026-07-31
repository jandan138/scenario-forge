# Generate Scientific Workbench Tube Prototypes

This workflow builds two integration prototypes:

- `scientific_workbench_prototype_centrifuge_load_start`;
- `scientific_workbench_prototype_bimanual_rack_insert`.

They exercise an articulated centrifuge, a test tube, a tube rack, the eBench
dual-arm workcell, and the Code-as-Room `center_open_floor` background. They are
not canonical rows from the live Feishu Task Design:

- live task 7 is `scientific_workbench_glass_rod_stir`;
- live task 10 is `scientific_workbench_centrifuge_load_start`;
- live task 11 is `scientific_workbench_centrifuge_unload_shutdown`.

The centrifuge prototype starts with the lid open and ends after insertion,
lid closing, and start-button press. It omits task 10's lid-open action and
setting-button press. The rack prototype is a useful two-arm insertion
integration case, but is not task 11, which requires centrifuge unloading,
lid-open-button press, shutdown-button press, and an observable off-state.

## Inputs

Use the accepted source-bound packages for:

- Code-as-Room visual environment;
- static eBench worktable;
- centrifuge r9 as `articulated_object`;
- test tube as `rigid_object`;
- tube rack r4 as `rigid_object`.

The generator consumes producer-qualified mounting, socket, insertion, and
grasp frames. Scenario Forge must not add asset-specific colliders, mass,
inertia, joint drives, scale fixes, or PhysX-warning suppression.

## Static compile

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_tube_prototypes.py \
  --bindings <accepted-five-asset-bindings.yaml> \
  --prototype all \
  --out <output-root> \
  --static-only
```

Generate one prototype with either:

```text
--prototype centrifuge_load_start
--prototype bimanual_rack_insert
```

Each result contains a portable Scenario Forge package and a GenManip collected
package. Compilation and loader acceptance do not run an episode or establish
task success.

## Isaac 4.1 initial-scene preview

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_tube_prototypes.py \
  --bindings <accepted-five-asset-bindings.yaml> \
  --prototype all \
  --out <output-root> \
  --isaac-python /cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python \
  --genmanip-root /cpfs/user/zhuzihou/dev/worktrees/genmanip-runtime-contract-20260714
```

Review each image at:

```text
<scenario-id>/adapters/ebench/genmanip/evidence/initial_scene/scene_overview.png
```

The preview verifies package/input hashes, runtime prims, tabletop containment,
support placement, and producer-versus-runtime extents. Visual review is a
separate gate. Neither result may be reported as Feishu task 7, 10, or 11.

## Historical outputs

Outputs whose scenario IDs begin with `wetlab_` are immutable historical
prototype evidence. Do not rename them in place or hand them to eBench as
canonical Task Design packages. Rebuild from this runbook to obtain the corrected
prototype identities.
