# Neutral workbench background VR scene

The neutral VR delivery reuses the admitted room, standard workbench and five
non-operational context props. The amber bottle, tip box, pipette carousel,
clear bottle and wash bottle form one rear row at table-local `y = 0.25 m`.
There is no task target, robot, liquid, beaker, stir bar, tray, magnetic
stirrer, task graph or benchmark claim.

The scene applies the standard VR presentation rule: the composed
`/World/table/table/Surface/Source/mesh` is invisible while its collision stays
enabled. Isaac Sim 4.1 produced the packaged fixed-view evidence render without
scene-load errors. `scene_config.yaml` lists the five runtime object paths and
the standard 1 cm local XY randomization range; no `task_config.py` is emitted.

Delivery:
`outputs/scientific_workbench_neutral_background_vr_20260825/handoff/scientific_workbench_neutral_background_vr.zip`.
