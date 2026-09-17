# Changelog

## Unreleased

- Start Task09 r6.0: replace r5.7 rigid ico grains with a `fluid=False`
  GPU-PBD set at 0.7 mm `solidRestOffset`. Scoop gates use region count ×
  authored mass; the r4 / r5.7 delivery heads stay put. Live PBD readout
  uses `/physics/updateParticlesToUsd` and `physxParticle:simulationPoints`.
  `prep_a9` keeps 10240 grains at a 10.67 mm bed; neck climb is the
  remaining settle gate. Wall rest 1.0 mm and gravityScale 2 both failed
  (climb worse / bed crushed to 7.6 mm).   Replay uses a 0.7 mm sphere
  prototype instead of copying a missing grain Mesh. `prep_a9_scoop` passed
  the region-count gates (142 grains / 0.31 g in the boat; LCD 0.29 g).
  Mid-sim spoon-weir `collisionEnabled` (a26) did not hold the transfer
  heap and zeroed the scale LCD callback. A kinematic carry cage was
  rejected; later rounds stay on bowl-only rigid friction from a9.
  Optional `pbd_viscous` (`fluid=True`, particle display): rest 0.65 mm
  retains 10240 but crushes the bed to 6.3 mm; scoop holds 383→355 with
  28 loose (a9 shed to 142 / 187 loose). Rest ≥0.78 mm leaks on this pack.
  `fill_pbd_cavity_lattice` rebuilds a fluid-spacing cavity pack so a
  viscous rest can stay near-full without reusing the dry 10240 layout.
  Optional `spoon_max_speed_m_s` stretches only those spoon keyframes
  whose smoothstep peak would exceed the cap; the r5.7 50 s timing stays
  the default. `prep_a36` (maxVel 0.04, spoon cap 0.04, damping 3 /
  viscosity 2) held 380 through a 14 s transfer with 0 exclusive loose.
  Cavity lattice can take a larger `neck_wall_margin_m` above `neck_z_m`
  so a refill does not pack the rim the way a34 (17957 / 1.10 mm) leaked.
  Close-camera replay maps a stretched `spoon_max_speed_m_s` clock back
  onto the official 50 s key times so lift heap and LCD stay in frame.
  Optional `carry_pitch_deg` keeps the bowl pocketed through neck exit
  so a viscous rim ridge can slump back into the bowl; default stays 0°.
- Add progress-rubric condition `instrument_display_matches` (scenario-spec/v0.6
  and v0.7). The solid-sample weighing package scores a tared terminal LCD of
  `1.00 g` at weight 0.35 on the r5.7 powder-bottle producer scene.
- `package_task09_powder.py` can stage that 1 g contract into `task/` and write
  a `<zip>.sha256` sidecar when the fixture is verified.
- Add `success.progress_rubric` (scenario-spec/v0.4, task/v0.4, metrics/v0.3,
  GenManip runtime contract v0.4): weighted progress-score rubric transport with
  aggregation semantics, activation flags, capability requirements, temporal
  kinds, and pinned upstream source refs. Rubric items are transported, not
  runtime-evaluated (`transport_only`).
- Align the golden bimanual-pour spec with the upstream five-item Progress
  Score; liquid items declared inactive pending the liquid measurement adapter
  contract.
- Static EBench export resolves the primary metric via
  `aggregation.primary_metric_id` when no `primary_success` role exists.

## 0.1.0 - 2026-07-03

- Bootstrap Scenario Forge as a portable scenario package compiler.
- Add starter package scaffold and structural package validation.
- Add ConvertAsset command-plan adapter boundary.
- Add architecture tests preventing simulator imports in pure package layers.
