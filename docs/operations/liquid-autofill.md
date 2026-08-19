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
