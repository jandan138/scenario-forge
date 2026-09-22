# Generate boat-pour-then-stir VR r1

Rebuild the relocatable Isaac 4.5 VR collection handoff from the `scene_usds`
task_14 workbench, 30 r5.7 rigid grains, the task_04 cylinder PBD recipe, and
the task_02 rest tray.

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_boat_pour_stir_vr.py \
  --out outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920
```

Open `scene.usd` in Isaac Sim 4.5. Merge `task_config.py` into the VR plugin
`TASKS` map. Deploy the directory at
`_ASSETS_DIR/scenes/scientific_workbench_boat_pour_stir/` unless the plugin
owner changes that convention.

This generator clones composed USD; it is not the v0.2 compiler path and not
the Isaac 4.1 VR600 exporter. Claims are in
[the r1 record](../records/2026-09-20-boat-pour-stir-vr-r1.md).
Do not treat a successful generate as pour, dissolve, headset, or LCD live
evidence.

Isaac 4.5 short physics smoke (headless, 3 s):

```bash
/isaac-sim/python.sh scripts/smoke_boat_pour_stir_vr_r1.py \
  --root outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920 \
  --seconds 3 \
  --out outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920/evidence/isaac45_runtime_smoke.json
```

The 2026-09-20 run is recorded as blocked: LCD live `5.02 g` (untared), 30 grains
stayed in the boat, authored PBD stayed in the cylinder, no engine crash.
