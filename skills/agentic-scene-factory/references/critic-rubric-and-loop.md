# Dual-Critic Rubric & Closed-Loop Repair Protocol

This reference defines the exact failure taxonomy, quantitative thresholds, and automated repair operators used by Stage 4 (`scripts/run_out_of_domain_scene_gate.py`) of `agentic-scene-factory`.

## 1. Critic 1 — Physical & Kinematic Critic

| Check ID | Scope | Quantitative Pass Threshold | Failure Diagnostic Code | Automated Repair Operator |
| :--- | :--- | :--- | :--- | :--- |
| `C1-EDGE` | Static Tabletop | All dynamic & articulated object footprints keep $\ge 0.10\text{ m}$ inward margin from table $X\in[-1.0,1.0]\text{ m}, Y\in[-0.40,0.40]\text{ m}$ edges | `EDGE_MARGIN_VIOLATION` | Clamp region sampling window inward and re-solve with incremented `min_edge_clearance_m` |
| `C1-AABB` | Static Tabletop | Pairwise 2D AABB clearance $\ge 0.025\text{ m}$ for all non-stacked objects | `FOOTPRINT_OVERLAP` | Advance deterministic solver `seed` or split crowded `region` (`center` $\rightarrow$ `left`/`right`) |
| `C1-SWEEP` | Kinematic Corridor | Zero intersection between any rigid/context object footprint and any articulated machine's `kinematic_clearance_volumes` (e.g. pull-out drawer corridor, eccentric lever side sweep) | `SWEEP_CORRIDOR_INTRUSION` | Inject/expand `kinematic_clearance_volumes` on the articulated object and relocate intruding object out of front/side sweep zone |
| `C1-SETTLE` | Isaac 4.1 Runtime (`120` zero-action steps after `reset_scene` + `recovery_scene`) | Root translation drift $< 0.005\text{ m}$, root tilt $< 3.0^\circ$, all objects $z > 0.70\text{ m}$ (zero fall-off), fixed-base joint drift $< 0.002\text{ rad/m}$ | `RUNTIME_SETTLE_DRIFT` | For stacked objects: align child initial $z$ to carrier recess floor (`surface_z + recess_z + 0.001 m`); for colliding neighbors: increase pairwise clearance and re-solve |

## 2. Critic 2 — Visual & Framing Critic (`v0.3` 7-View Bundle)

Rendered via `scripts/ebench/render_genmanip_initial_preview.py` (`workspace_closeup`, `scene_overview`, `task_object_closeup`, `room_topdown`, `room_corner_a`, `room_corner_b`, `room_entrance_eye_level`):

| Check ID | Scope | Quantitative Pass Threshold | Failure Diagnostic Code | Automated Repair Operator |
| :--- | :--- | :--- | :--- | :--- |
| `C2-COMPLETENESS` | Render Bundle | All 7 PNGs exist, `render_evidence.yaml` matches `input_digest` | `MISSING_PREVIEW_VIEW` | Re-export collected package and re-run `render_genmanip_initial_preview.py` |
| `C2-EXPOSURE` | Image Luma | Mean luminance $\in [18, 235]$ (8-bit scale) and pixel std-dev $> 8.0$ across `workspace_closeup`, `scene_overview`, `task_object_closeup` | `BAD_EXPOSURE_OR_BLANK` | Verify DomeLight fallback / studio lighting and re-render |
| `C2-OCCLUSION` | Workspace Framing | `context_prop` objects remain in `far_context` (`y > +0.08 m`) and never sit directly between robot `(0, -1.02)` and primary `task_object`s | `FOREGROUND_CONTEXT_OCCLUSION` | Force `context_prop` `region: far_context` and add `behind` relation relative to hero appliance |

## 3. Bounded Repair Loop (`max_iterations = 3`)

```text
Draft v0 -> Critic Pre-Check / Solve -> Compile & Export -> Critic 1 (Runtime) -> Critic 2 (7-View)
   ^                                                              |                   |
   |__________________ Apply Deterministic Repair Delta __________|___________________|
                               (up to 3 iterations; fail-closed if unresolved)
```

Every iteration logs its input draft digest, diagnostic codes, applied repair delta, and resulting placement coordinates in `gate_summary.json` so repairs are 100% auditable and reproducible.
