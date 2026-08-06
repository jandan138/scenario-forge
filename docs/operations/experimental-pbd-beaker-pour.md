# Experimental PBD beaker pour

This temporary task is deliberately outside the formal wet-experiment catalog
and catalog statistics. It exercises the LabUtopia 3,600-particle source scene
through the same Scenario Forge package and two consumer adapters.

Generate it with:

```bash
PYTHONPATH=src python scripts/generate_experimental_pbd_beaker_pour.py \
  --handoff-package /path/to/qualified/labutopia/package \
  --out outputs/experimental_lab001_pbd_beaker_to_beaker_pour_20260806_r3
```

The producer package must have id
`lab001_pbd_beaker_to_beaker_step600_v1` and qualified `native`, `genmanip` and
`vr` endpoints. The generator writes:

- `scene/main.usda`: neutral/native composition;
- `adapters/ebench/genmanip/`: GenManip collected package at 600 Hz;
- `adapters/vr/scene.usd` and `task_config.py`: VR handoff at 60 Hz.

The left arm operates `beaker2`; the right arm remains idle; `beaker1` stays on
the table. The primary success contract is staged geometric pour pose followed
by return to the initial source pose. Release is an instruction-only inactive
rubric item because GenManip has no native release success metric. Liquid
transfer is also inactive until a particle-transfer scorer is separately
qualified.

The package is internal and non-redistributable. Do not extract its LabUtopia
assets for public delivery, and do not add consumer-side collider or physics
patches.

For initial-scene evidence, producer-composed PBD scenes use eight zero-action
physics steps, matching the producer qualification window. Camera warmup after
that point refreshes rendering without advancing physics. All task views keep
the inseparable producer scene visible; the overview reuses the workcell camera
instead of fitting to distant non-task geometry below the producer table prim.
These images remain visual evidence only and do not establish stable grasp,
liquid transfer or task success.
