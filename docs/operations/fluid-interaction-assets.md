# Fluid-interaction asset workflow

Set the producer and the managed Isaac Sim 4.1 runtime:

```bash
export SCENARIO_FORGE_CONVERTASSET_ROOT=/cpfs/user/zhuzihou/dev/ConvertAsset
export EEOS_ISAACSIM41_PYTHON=/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-isaacsim41-py310/bin/python
```

Prepare a proposal from a raw or already admitted USD:

```bash
scenario-forge fluid-asset prepare \
  --source /path/to/asset.usd \
  --prim /World/Funnel \
  --out reviews/funnel
```

Review `proposal.yaml` and its two SVG evidence files. Confirm the behavior and
set `review.status: approved` plus a named reviewer. For a funnel, verify the
inlet, outlet and throat; the outlet is the only permitted exit. Then qualify:

```bash
scenario-forge fluid-asset qualify \
  --proposal reviews/funnel/proposal.yaml \
  --out packages/funnel
```

Only a pass directory is promoted and zipped. A blocked candidate is moved to a
`*_diagnostics` directory. A glass-rod `not_applicable` result is also retained
as diagnostics and cannot enter a task as a qualified guide.

If the direct visual-mesh SDF closes an opening or fails retention, generate the
bounded fallback instead of tuning offsets blindly:

```bash
scenario-forge fluid-asset derive-partitions \
  --proposal reviews/funnel/proposal.yaml \
  --out reviews/funnel_round2
```

This creates package-local convex wall segments from measured axial stations.
It preserves the visual mesh and requires a second named approval before the
normal `qualify` command can consume it.

Batch preparation uses `scenario-forge-fluid-asset-batch/v0.1`; batch
qualification uses `scenario-forge-fluid-asset-qualification-batch/v0.1` and
lists approved proposal paths. The commands are `batch-prepare` and
`batch-qualify` respectively. Every item remains independently reviewable and
independently promotable.

Do not edit collision, SDF, mass or PhysX parameters in Scenario Forge after
handoff. If qualification exposes leakage or an unusable throat, return the
proposal and evidence to ConvertAsset. Do not solve it with a scene-local patch.
