# Stir-bar/beaker VR r4

r4 replaces the task beaker with the source-bound WebStandard SDF beaker and
adds a dual liquid delivery. `vr/scene.usd` contains 969 settled transparent-
blue particles for repeatable collection. `vr/scene_liquid_edit.usd` retains a
hidden height-only cylinder sampler for manual liquid-volume editing.

The task keeps the r3 tray, stir bar, magnetic stirrer, room, table, and object
poses. Both entries expose one ParticleSet named `beaker_liquid`, one shared
ParticleSystem, and one active `/World/physicsScene`. Isaac Sim 4.1 observed
100% retention, zero below-floor particles, stable foreground objects, a valid
sampler relationship, and no selected hard errors. Robot policy, magnetic
stirring, heating, and benchmark success remain unclaimed.

Local visual QA rejected the first mouth-drop freeze because it showed a
column above the cup. The producer now freezes post-validation settled points.
It also binds the transparent-blue material to the ParticleSystem, fixing the
black isosurface fallback. The final overview and closeups show liquid inside
the glass beaker with no floating sampler geometry.
