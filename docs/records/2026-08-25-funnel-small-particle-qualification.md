# Funnel small-particle qualification

The 76 x 120 mm generated funnel passed three process-isolated Isaac Sim 4.1
conduit runs with `scientific_workbench_small_gpu_pbd_v2`. Every run measured
legal outlet ratio 1.0, zero structural leaks and zero hard PhysX/CUDA errors.
The package uses the visual hollow mesh as SDF and the webpage-standard thick-
wall ClearBorosilicate material.

The exact colleague v1 recipe remains preserved. It loaded and stepped without
hard errors, but 0 of 9750 particles crossed the 7 mm throat because its 5 mm
rest offset jammed above the stem. v2 changed only particle contact/rest offsets
to 0.7/0.55 mm for the successful funnel qualification.

The final 15 mL receiver removes the Cube and uses one connected watertight
visual-topology collision copy with a thickened bottom and a source-bound inner-
wall retention profile. Three Isaac 4.1 runs passed at 0.99237 static retention,
0.96004 motion retention, 0.98801 pour outflow and zero structural leaks. The
funnel-to-tube gravity fixture then measured 1.0 legal funnel outlet ratio and
0.98632 tube capture with zero structural leaks. Robot and benchmark success
remain unclaimed.
