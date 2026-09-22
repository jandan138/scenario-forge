# Generate funnel-pour-then-stirrer VR r1.2

Rebuild the relocatable VR collection handoff from the `scene_usds` task_04
funnel scene, the task_01 90×35 flask, and the task_10 magnetic stirrer.
The flask sits on the table; there is no task-local puck.

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_funnel_pour_flask_to_stirrer_vr.py \
  --out outputs/scientific_workbench_funnel_pour_flask_to_stirrer_vr_r1_2_20260920
```

Open `scene.usd` in Isaac Sim 4.1. Merge `task_config.py` into the VR plugin
`TASKS` map. Deploy the directory at
`_ASSETS_DIR/scenes/scientific_workbench_funnel_pour_flask_to_stirrer/` unless
the plugin owner changes that convention.

This generator clones composed USD; it is not the v0.2 compiler path. Claims
are in
[the r1.2 record](../records/2026-09-20-funnel-pour-flask-to-stirrer-vr-r1.2.md).
Do not treat a successful generate as pour or headset evidence.
