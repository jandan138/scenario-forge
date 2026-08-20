# Build a simple-SDF multi-liquid package

Set the producer checkout and the EOS-managed Isaac Sim 4.1 Python:

```bash
export SCENARIO_FORGE_CONVERTASSET_ROOT=/cpfs/user/zhuzihou/dev/ConvertAsset
export EEOS_ISAACSIM41_PYTHON=/path/to/eos-managed-isaac41/python
```

## 1. Review and build container collision

Generate a review file without changing the source:

```bash
scenario-forge fluid-asset simple-sdf-propose \
  --source /abs/path/scene.usd \
  --container /World/obj_tube15 \
  --visual-mesh /World/obj_tube15/Visual/Mesh \
  --particle-scale small_required \
  --out /abs/path/review
```

Inspect `review/proposal.yaml`. A proposed bottom Cube remains blocked until a
human verifies its size and local pose and changes `approved` to `true`. Build
the source-bound package:

```bash
scenario-forge fluid-asset simple-sdf-build \
  --spec /abs/path/review/proposal.yaml \
  --out /abs/path/collision_package
```

## 2. Add independent liquid sets

Create a request such as:

```yaml
schema_version: aan.multi_liquid_sample_request.v1
scene: /abs/path/collision_package/asset.usda
validation: quick
sets:
  - id: reagent_bottle_liquid
    container_prim: /World/obj_reagent_bottle
    sampler_usd: /abs/path/samplers.usda
    sampler_mesh_prim: /World/Samplers/ReagentBottle
    particle_scale: task02_compatible
  - id: tube15_liquid
    container_prim: /World/obj_tube15
    sampler_usd: /abs/path/samplers.usda
    sampler_mesh_prim: /World/Samplers/Tube15
    particle_scale: small_required
```

Then run:

```bash
scenario-forge liquid sample-add \
  --spec /abs/path/liquid.yaml \
  --out /abs/path/liquid_package
```

Open `liquid_package/scene.usda`. Keep the entire directory together; all
dependencies are package-relative. The command also writes a deterministic
same-name ZIP. Inspect `manifest.json` and
`evidence/runtime_validation/report.json` before handoff.

Use `validation: qualified` for the three-cold-start, eight-second gate. Do not
promote a quick package as qualified evidence.
