# Experimental PBD beaker pour

This temporary task is deliberately outside the formal wet-experiment catalog
and catalog statistics. It exercises the LabUtopia 3,600-particle source scene
through the same Scenario Forge package and two consumer adapters.

Generate it with:

```bash
PYTHONPATH=src python scripts/generate_experimental_pbd_beaker_pour.py \
  --handoff-package /path/to/qualified/labutopia/package \
  --out outputs/experimental_lab001_pbd_beaker_to_beaker_pour_20260806_r4
```

The producer package must have id
`lab001_pbd_beaker_to_beaker_step600_v2` and qualified `native`, `genmanip` and
`vr` endpoints. The generator writes:

- `scene/main.usda`: neutral/native composition;
- `adapters/ebench/genmanip/`: GenManip collected package at 600 Hz;
- `adapters/vr/scene.usd` and `task_config.py`: VR handoff at 60 Hz.

The left arm starts open above `beaker2`; the right arm starts open in a clear
idle pose; both vessels remain on the source table. The initial 16-joint Lift2
state is explicit in `scenario.yaml` and is copied to GenManip episode metadata.
The primary success contract is staged geometric pour pose followed by return
to the initial source pose. Release is an instruction-only inactive
rubric item because GenManip has no native release success metric. Liquid
transfer is also inactive until a particle-transfer scorer is separately
qualified.

The package is internal and non-redistributable. Do not extract its LabUtopia
assets for public delivery, and do not add consumer-side collider or physics
patches.

For initial-scene evidence, producer-composed PBD scenes use eight zero-action
physics steps, matching the producer qualification window. Camera warmup after
that point refreshes rendering without advancing physics. All task views keep
the inseparable producer scene visible; the overview fits the recovered source
table and complete Lift2 workcell.
These images remain visual evidence only and do not establish stable grasp,
liquid transfer or task success.

The v0.2 handoff records the composed position, quaternion, local scale and
world AABB of the source vessel, target vessel and support table for every
entrypoint. Scenario Forge treats those records as recovery authority. In
particular, it must not replace the source table's non-unit local scale with an
identity transform. The older r3 output did that during GenManip recovery and
is superseded by r4.
