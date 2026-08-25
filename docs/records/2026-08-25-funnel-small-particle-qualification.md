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

The 15 mL receiver is not promoted. Multiple source-bound Hollow-SDF + bottom-
Cube candidates improved static retention to about 92.7%, but did not meet the
99% reservoir threshold; gravity-feed integration therefore retained 0% in the
tube even though the funnel again delivered 100% legally. This receiver blocker
does not invalidate the qualified funnel conduit claim.
