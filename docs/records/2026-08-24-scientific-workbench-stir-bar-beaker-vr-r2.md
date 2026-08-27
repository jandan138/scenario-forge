# Stir-bar/beaker VR r2 steel-tray layout

Task 04's reduced VR scene places the admitted 29.77 mm magnetic stir bar on a
30 cm stainless-steel tray instead of directly on the workbench. The tray is a
non-scoring context object; the beaker and stir bar remain the task objects.

## Layout and package

- package: `outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r2_20260824/`;
- tray root: `/World/obj_steel_plate`, initial XYZ `(0.09, -0.17, 0.755) m`;
- stir-bar root: `/World/obj_stir_bar`, initial XYZ `(0.09, -0.17, 0.760) m`;
- tray and stir bar share one local XY randomization group with `+/-0.01 m`;
- the five rear context objects randomize independently and do not participate
  in task metrics.

The source archive
`external_artifacts/incoming/from_xinyu/steel_plate_30cm_simready_v1.tar.gz`
declares `validation_status=ok`, 0.55 kg mass, 97 collision pieces, passing drop
and basin-containment checks, and approximately `0.300 x 0.300 x 0.030 m`
dimensions. Scenario Forge copies the SimReady package without authoring a
local collider or physics-material patch.

## Evidence

Isaac Sim 4.1 retained three eight-second static runs and three non-robot drop
runs. All six reports pass with no selected hard errors. The tray's final pose
is stable and its measured final-second displacement is `0 m`; every drop run
places the stir bar inside the beaker.

Three fixed views show the stir bar supported inside the tray, the tray on the
table, and the beaker upright. Local human-style visual QA verdict is PASS. The
second white capsule visible in the shiny tray is the stir bar's reflection,
not a duplicate object. This review was local rather than independently blind.

The handoff ZIP is
`handoff/scientific_workbench_insert_stir_bar_into_beaker_vr_r2.zip`, SHA-256
`1b100951f44a59a5a6828989cc1f291cb3e35cd1bd49e56e87b943085beea852`.
After extraction, `vr/scene.usd` composes 52 layers and 17 assets with zero
unresolved dependencies.

## Claim boundary

The package proves scene opening, static stability and non-robot drop into the
beaker. It does not include liquid or the canonical Task 04 closure step, and it
does not claim Lift2 robot-policy, canonical-task or benchmark success.
