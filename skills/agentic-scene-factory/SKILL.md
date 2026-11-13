---
name: agentic-scene-factory
description: Orchestrate out-of-domain and Real-to-Sim agentic scene generation in Scenario Forge aligned with NVIDIA SAGE, Scenethesis, Isaac Lab-Arena, and SimReady contracts — combining Scenario Forge's internalized room-source-v2 exporter & 6-view gate, Real-to-Sim 1:1 Texture Twin Ledger & metric pose grounding, Lab2Sim manufacturer-grounded multi-DOF articulated asset synthesis (GEN-001..008 + ART-001/ART-005 fixed-base v2), cross-host Independent Visual Critic verification, relational tabletop layout solving, and multi-stage GenManip predicate canary verification.
---

# Agentic Scene Factory Skill

<!-- local amendment 2026-11-13: internalized room-source-v2 exporter, Real-to-Sim 1:1 ledger/pose modules, and cross-host visual critic -->

Use this skill when generating a **brand-new out-of-domain or Real-to-Sim robot evaluation scenario** (outside wet-lab `scientific_workbench`) that requires:
1. Room environment generation & verification via Scenario Forge's **internalized** Blender 4.4.3 pipeline (`verify_and_render_room_pack.py` $\rightarrow$ `export_room_source_v2.py` $\rightarrow$ `ConvertAsset` `visual_static_environment`),
2. Optional **Real-to-Sim 1:1 reconstruction** from photographs or walkaround video (`texture_twin_ledger.py` + `spatial_pose_grounding.py` + camera-matched reprojection gate),
3. On-demand synthesis & qualification of **manufacturer-grounded multi-DOF articulated appliances** (`Lab2Sim` `GEN-001..008` + `ART-001`/`ART-005` fixed-base v2, including `G1..G8 + G9a + G9b` IKA-grade acceptance) and domain-tailored legged worktables / companion rigid assets,
4. Relational tabletop layout solving with explicit **multi-DOF sweep & drawer corridor exclusion**,
5. **Cross-Host Independent Visual Critic** + **Dual-Critic** automated audit and closed-loop repair across Antigravity, Claude Code, Codex CLI, and OpenCode, and
6. **Multi-Stage State-Teleport Predicate Canary** verification in GenManip (`MetricsManager` `0.0 -> ... -> 1.0`) prior to downstream privileged trajectory synthesis (`Astra` / *Embodied First Exam* §2.1).

## Hard Architectural Boundaries

- **Never** add episode runners, VLA/RL policy loops, CuRobo motion-planning search, or leaderboards inside `src/scenario_forge/`.
- **Never** import simulator SDKs (`isaacsim`, `omni.*`, `pxr`, `bpy`) in pure `src/scenario_forge/` layers.
- **Never** reimplement `ConvertAsset` normalization or promotion logic; always invoke `"${CONVERT_ASSET_ROOT:-../ConvertAsset}/main.py"` (e.g. `/cpfs/user/zhuzihou/dev/ConvertAsset/main.py` on shared CPFS) and its qualification scripts.
- Keep all binary USDs, renders, and qualification bundles under git-ignored `external_artifacts/`, referenced via SHA-256 digests (`GEN-007`).

## End-to-End 5-Stage Pipeline

### Stage 1: Domain Pack & Relational Task Planning (SAGE / Scenethesis Alignment)
1. Author or select a domain pack under `configs/domain_packs/<domain_id>/layout_constraints.yaml` (`domain-layout-pack/v0.1`).
2. Author a relational task draft (`out-of-domain-task-draft/v0.1`) under `configs/out_of_domain_tasks/<task_slug>.yaml` paired with a `relational-layout-spec/v0.1` section declaring:
   - `table` (`x_range_m`, `y_range_m`, `surface_z_m: 0.755`, `min_edge_clearance_m: 0.10`),
   - `objects` with `footprint_xy_m`, `region`, `facing`, `stacked_on` (for initial tray/coaster stacking), and **`kinematic_clearance_volumes`** for every prismatic drawer corridor or lateral lever sweep,
   - `relations` (`left_of`, `right_of`, `in_front_of`, `behind`, `near`, `far_from`, `aligned_x`, `aligned_y`),
   - Multi-stage `steps` and `success.predicates` (`articulation_joint_state_reached` + `relative_pose_reached` with `sequence_index: 0..K-1`).

### Stage 2: Internalized Room Synthesis, Real-to-Sim Grounding & Admission (`scenario-forge` $\rightarrow$ `ConvertAsset`)
Read [internalized-room-exporter-and-critic.md](references/internalized-room-exporter-and-critic.md):
1. **For Real-to-Sim scenes from photos/video**:
   - Extract 1:1 perspective-rectified crops, delight/tile macro surfaces, and Reinhard LAB color-lock seamless textures via `skills/agentic-scene-factory/scripts/build_texture_twin_ledger.py` (`scenario_forge.adapters.texture_twin_ledger`), then validate CIE76 $\Delta E^*_{ab} \le 12.0$ and independent patch critique (`>= 8.0/10`) via `skills/agentic-scene-factory/scripts/verify_texture_patch_pairs.py`.
   - Recover metric camera pose (`fov_deg`, `eye_xyz`, `target_xyz`), tabletop `(x, y, z)` poses, and `rests_on`/`stacked_on` support hierarchy from standard scale anchors (`385 mm` 98-key keyboard, `360 mm` 15.6" laptop, `612 mm` 27" monitor, `750 mm` desk) via `scenario_forge.adapters.spatial_pose_grounding`.
2. **Deterministic Room Verification & 6-View Cycles `AgX` Gate**:
   - Run `skills/agentic-scene-factory/scripts/verify_and_render_room_pack.py` in Blender 4.4.3 to enforce assembly/prop density, 100% file-backed non-packed PNG textures, flat `Z <= 0.003 m` central floor, and `--clearance-xy` open-floor bounds, emitting `room_gate_report.json` + 6 canonical views (`corner_ne/nw/se/sw`, `entrance_eye_level`, `topdown_floorplan`).
   - Obtain independent blind visual critic `PASS` (`>= 8.0/10`) via `skills/agentic-scene-factory/scripts/run_independent_visual_critic.py` (`--driver {validate_only,codex_cli,opencode_cli}`, Antigravity swarm critic, or Claude Code `.claude/agents/visual-critic.md`).
3. **Native `room-source-v2` Export & Admission**:
   - Export in Blender 4.4.3 via `skills/agentic-scene-factory/scripts/export_room_source_v2.py` (emitting `producer.repo: "scenario-forge"` + `support_relations.json` via `scenario_forge.adapters.room_support_relations`).
   - Run `scripts/intake_generated_environment.py` and qualify via `"${CONVERT_ASSET_ROOT:-../ConvertAsset}/main.py"` (`visual_static_environment`, `isaac41`, `gates=static,runtime`).
4. **Camera-Matched Reprojection Verification (Real-to-Sim)**:
   - Composite `[real_photo | virtual_render | 50%_edge_overlay]` via `skills/agentic-scene-factory/scripts/render_reprojection_comparison.py` and pass independent blind reprojection critique (`>= 8.0/10`).

### Stage 3: On-Demand Multi-DOF Articulated & Rigid Asset Production (`Lab2Sim` / SimReady Alignment)
1. Follow `skills/hunyuan-isaac-articulation-assets/SKILL.md` (`references/ika-grade-acceptance-and-visual-critic.md`) and `GEN-008`:
   - Collect real manufacturer datasheet dimensions (`E`-grade closed envelope & total mass) in `external_artifacts/asset_evidence/<slug>/datasheet_evidence.json`.
   - Write the 14-section `GEN-001..008` spec in `docs/design/asset-specs/<slug>.md` (including Section 9.1 declarative `G1..G9b` acceptance config) with explicit `E`/`F`/`D`/`U` labels and non-convex cavity clearance math (chutes, pin-nests, pull-out cassettes, hollow tunnels).
   - Author canonical fixed-base v2 USD via `skills/hunyuan-isaac-articulation-assets/scripts/cad_usd_kit.py` (`PhysicsArticulationRootAPI` + `PhysxArticulationAPI` on `/AssetRoot/Joints/BaseToWorld`, `PhysxRigidBodyAPI` on every link, BFS-depth ordered `Joints/*`, non-convex compound `Cube` colliders, `stiffness=0` + viscous detent `damping>0` drives) and pass `skills/hunyuan-isaac-articulation-assets/scripts/check_articulation_usd.py --mode fixed`.
   - Render 4-view Cycles `AgX` studio sheets via `skills/hunyuan-isaac-articulation-assets/scripts/blender_usd_studio_render.py`, obtain independent blind-review `PASS` (`>= 8.0/10` on all 5 dimensions, `critic_agent != author_agent`), and pass all 10 gates (`G1..G8 + G9a + G9b`) in `scripts/verify_ika_grade_hero_acceptance.py --spec-config`.
   - Wrap in a consumer facade (`/World/<AssetId>` with `rel physics:body0 = </World/<AssetId>>` on `BaseToWorld`), run `ConvertAsset` `normalize-asset` (`isaac41`), bootstrap & verify `qualify_articulated_benchtop_stability.py` (`50` warmup + `240` settle frames), and promote via `finalize_articulated_package.py`.
2. Promote companion rigid task objects (`--interaction-profile`, `aan.object_interaction_profile.v2`) and dynamic context props (`--context-profile`, `aan.dynamic_context_profile.v1`).
3. Register all packages in `configs/source_bindings/<batch>.yaml`.

### Stage 4: Relational Layout Solve + Dual-Critic Closed-Loop Gate
Read [critic-rubric-and-loop.md](references/critic-rubric-and-loop.md) and run `scripts/run_out_of_domain_scene_gate.py`:
1. Solve tabletop layout (`solve-layout` / `compose-from-layout`), compile package, and export GenManip collected bundle (`validate_package` + `check_asset_lock`).
2. **Critic 1 (Physical & Kinematic Critic)**:
   - Static check: tabletop `>= 0.10 m` margin, zero AABB overlap, zero intrusion into `kinematic_clearance_volumes`.
   - Runtime check: 120-frame GenManip zero-action cold-reset settling (`drift < 0.005 m`, `tilt < 3.0 deg`, zero tabletop fall-off).
3. **Critic 2 (Visual & Framing Critic)**:
   - Render 7-view `v0.3` preview (`scripts/ebench/render_genmanip_initial_preview.py`) and audit framing/exposure/occlusion.
4. **Bounded Repair Loop** (`<= 3` iterations): map Critic diagnostics back to relational deltas (e.g., adding missing `kinematic_clearance_volumes`, increasing clearance margin, shifting `region`, or advancing deterministic `seed`) and re-solve until PASS.

### Stage 5: Multi-Stage State-Teleport Predicate Canary & Downstream Handoff
1. Run `scripts/verify_genmanip_predicate_canary.py` in `isaac41` + GenManip:
   - Assert `t=0` post-warmup `MetricsManager` score `== 0.0` **and** every leaf predicate individually evaluates to `False` (anti-false-positive gate).
   - Sequentially execute all `K` task stages via joint-state + cavity pose teleportation (`30` physics steps per stage), asserting zero cavity pop-out/depenetration, monotonic intermediate stage progression, and final `MetricsManager` score `== 1.0`.
2. Emit hash-bound `evidence/predicate_canary_report.yaml` and hand off the verified collected package (`scene.usda` + `meta_info.json` + `scenario_forge_runtime_contract_v05`) to downstream privileged trajectory synthesis (`Astra` / *Embodied First Exam* §2.1).
