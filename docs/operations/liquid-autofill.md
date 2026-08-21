# Add initial liquid to a USD container

Use the EOS-managed Isaac Sim 4.1 Python and a ConvertAsset checkout:

```bash
export SCENARIO_FORGE_CONVERTASSET_ROOT=/path/to/ConvertAsset
export EEOS_ISAACSIM41_PYTHON=/path/to/eos-managed-isaac41/bin/python
```

Inspect candidate prims without changing the source:

```bash
scenario-forge liquid inspect --scene /path/to/scene.usd
```

Choose the exact intended prim, then produce one fill:

```bash
scenario-forge liquid add \
  --scene /path/to/scene.usd \
  --container /World/obj_graduated_cylinder \
  --fill 0.40 \
  --out /path/to/delivery
```

For a standalone interaction-qualified dynamic container with no table in the
input USD, keep the delivered rigid body dynamic but isolate liquid containment
in an evidence-only fixed-container fixture:

```bash
scenario-forge liquid add \
  --scene /path/to/dynamic_container_package/asset.usd \
  --container /World/Flask \
  --fill 0.40 \
  --fixed-container-validation \
  --initial-particle-count 731 \
  --out /path/to/delivery
```

This route copies the selected visual hollow mesh into an invisible
Task-02-derived `convexDecomposition` PBD proxy while preserving the source SDF.
For a non-cylindrical axisymmetric vessel, particle generation follows the
measured inner-radius curve instead of treating the vessel as a straight tube.
An explicit particle count is accepted only on this profiled standalone route
and must be backed by retained failed/pass evidence; it does not alter particle
size, velocity, rest/contact offsets, or source physics. Temporary fixed-container
USD fixtures are excluded from the final self-contained ZIP.

When the container comes from a promoted fluid-interaction asset package, bind
its evidence explicitly with
`--fluid-profile /path/to/package/interaction/fluid_profile.json`. Only a
qualified `reservoir` profile is accepted; funnel (`conduit`) and glass-rod
(`surface_guide`) profiles do not represent a loaded liquid start.

The output basename is
`<scene>__liquid__<container>__fillNN`. Keep the alias USD and matching `_deps/` directory
together, or hand off the same-name ZIP. Open the alias USD in Isaac Sim 4.1.

## What is inherited from Task 02 r10.3

- 5.82 mm particle spacing and 5.94 mm rendered width;
- 5 mm contact offset, effective 9 mm rest offset, and 5 mm grid smoothing;
- blue `UsdPreviewSurface`: diffuse `(0.32, 0.72, 0.95)`, IOR `1.333`, opacity `0.34`, roughness
  `0.02`;
- SDF walls/rim plus convex-hull solid bottom/base/connector;
- live `points`, not authored `simulationPoints`, as runtime evidence.

## Failure handling

Read `<basename>_diagnostics/logs/` and the producer manifest. A rejection is expected for geometry
whose cavity cannot be proved, containers tilted beyond 15°, multiple ambiguous cavities,
articulations/deformables, more than 10,000 required particles, Isaac version mismatch, leakage,
or drift. Do not patch the scene locally to suppress a rejection; repair/admit the asset in
ConvertAsset.
