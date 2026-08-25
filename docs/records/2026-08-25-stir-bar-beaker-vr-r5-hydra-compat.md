# Stir-bar/beaker VR r5 Hydra compatibility

r5 keeps the r4 task layout, source-bound SDF beaker, transparent-blue liquid,
tray, stir bar, magnetic stirrer, room, table, and object poses. It replaces
only the liquid producer package so the ParticleSet no longer authors Hydra-
incompatible `displayColor` or `displayOpacity` primvars. Particle color is
provided by the shared liquid material with diffuse color `(0.32, 0.72,
0.95)` and opacity `0.34`.

Both `vr/scene.usd` and `vr/scene_liquid_edit.usd` were exercised for 60
rendered physics steps in Isaac Sim 4.1 and 4.5. Both runtimes reported zero
target Hydra primvar errors, 100% particle retention, and zero below-floor
particles. The frozen entry retained 969 particles; the editable entry
resampled 1407 particles from its height-only cylinder sampler.

Isaac Sim 4.1 is the formal runtime. Isaac Sim 4.5 is recorded as a
compatibility gate because that is where the original Hydra error was
observed. The task does not claim robot-policy success, magnetic stirring,
heating, liquid-transfer success, benchmark success, or all-scene warning
freedom. A pre-existing warning about the SDF collision proxy's authored
normal count remains outside this narrowly scoped fix.
