# Internalized Room Exporter, Real-to-Sim Modules & Cross-Host Visual Critic

This reference documents Scenario Forge's native room-generation delivery contract (`room-source-v2`), Real-to-Sim 1:1 reconstruction toolchain, and host-agnostic Independent Blind-Review Visual Critic workflow across **Antigravity**, **Claude Code**, **Codex CLI**, and **OpenCode**.

## 1. Internalized Room Gate & `room-source-v2` Exporter (Zero External Repo Dependency)

Room scenes authored in Blender 4.4.3 are verified and exported directly inside Scenario Forge without any external repository dependency:

1. **Deterministic Room Gate + 6-View Cycles `AgX` Inspection Pack**:
   ```bash
   "${BLENDER_BIN:-blender}" --background \
     --python skills/agentic-scene-factory/scripts/verify_and_render_room_pack.py -- \
     --source-script <work_dir>/render_output.py \
     --out-dir <work_dir>/renders_round_1 \
     --clearance-xy 4.2 4.0
   ```
   - Hard-checks multi-part assembly density (`>= 18` assemblies or `>= 200` meshes), domain prop richness (`>= 25`), 100% unpacked file-backed textures on disk, flat floor (`Z <= 0.003 m` inside the central workcell), and zero polygon intrusions inside `--clearance-xy` (customizable e.g. `--clearance-xy 2.4 2.2` or `--clearance-center-xy CX CY` for compact open-office bays).
   - Renders `corner_ne.png`, `corner_nw.png`, `corner_se.png`, `corner_sw.png`, `entrance_eye_level.png`, and `topdown_floorplan.png` at `1280x960` (`64` samples, `AgX`, OIDN denoising), hiding ceiling occluders to camera rays on overhead views and entrance door leaves on `entrance_eye_level.png`.
   - Emits `room_gate_report.json` (`scenario-forge-room-gate-report/v1.0`) and exits non-zero on any gate failure.

2. **Native `room-source-v2` Delivery Export & Portable Intake**:
   ```bash
   "${BLENDER_BIN:-blender}" --background \
     --python skills/agentic-scene-factory/scripts/export_room_source_v2.py -- \
     --run-dir <work_dir> \
     --source-script <work_dir>/render_output.py \
     --delivery-dir <deliveries_dir>/<room_id> \
     --background-asset-id <asset_id> \
     --source-image <reference_image.png> \
     --support-reviewer <reviewer_id> \
     --workspace-clearance-xy 3.8 4.0

   PYTHONPATH=src "${SCENARIO_FORGE_PYTHON:-python3}" \
     scripts/intake_generated_environment.py \
     --asset-id <asset_id> \
     --delivery-root <deliveries_dir>/<room_id> \
     --out <intakes_dir>/<room_id>_intake.yaml
   ```
   - Uses `scenario_forge.adapters.room_support_relations` (`Box3`, `OrientedSupport`, `apply_resting_correction`, `validate_support_sidecar`) to snap or prune small unsupported props and write SHA-256-bound `support_relations.json`.
   - Auto-detects `git rev-parse HEAD` in `scenario-forge` and writes native `producer: {"repo": "scenario-forge", "commit": "<hash>", "exporter": "skills/agentic-scene-factory/scripts/export_room_source_v2.py"}` in `source_manifest.json` (while `generated_environment.py` retains full backward compatibility with legacy manifests).

## 2. Real-to-Sim 1:1 Texture Twin Ledger & Spatial Pose Grounding

Pure-Python core modules live under `src/scenario_forge/adapters/` (stdlib + `numpy` + `PIL` + `yaml` only):

- **`scenario_forge.adapters.texture_twin_ledger`**:
  - `rectify_perspective_patch(image, src_quad_xy, output_size)`: 4-point SVD homography rectification for screens, UI panels, QR tags, and planar surfaces.
  - `enhance_macro_texture_photo(image, tile_size=512)`: LAB low-frequency illumination delighting, toroidal raised-cosine seamless tile synthesis, and roughness/normal map derivation.
  - `lock_color_to_reference_lab(source_image, reference_image)`: Reinhard CIE L\*a\*b\* mean/std color transfer locking repeated seamless textures to ground-truth photo crops (`CIE76 delta_e_ab <= 6.0` typical, hard gate `<= 12.0`).
  - Wrapped by CLIs:
    - `skills/agentic-scene-factory/scripts/build_texture_twin_ledger.py` (emits `[ref_crop | twin_tex | shaded_swatch]` strips, `contact_sheet_all.png`, and `ledger_manifest.json`).
    - `skills/agentic-scene-factory/scripts/verify_texture_patch_pairs.py` (re-verifies SHA-256 digests, live CIE76 $\Delta E^*_{ab}$, and `patch_critique_report.json`).
    - `skills/agentic-scene-factory/scripts/render_reprojection_comparison.py` (composites `[real_photo | virtual_render | 50%_edge_overlay]` boards + edge IoU / $\Delta E^*_{ab}$ metrics).

- **`scenario_forge.adapters.spatial_pose_grounding`**:
  - `STANDARD_ANCHOR_CATALOG` (`keyboard_98key` `385x140x38 mm`, `laptop_15_6_in` `360 mm`, `monitor_27_in_landscape` `612 mm`, `pet_bottle_500ml` `Ø66x225 mm`, `standing_desk_standard` `750 mm` height).
  - `solve_camera_and_tabletop_poses(...)`: damped Gauss-Newton solver recovering metric virtual camera (`fov_deg`, `eye_xyz`, `target_xyz`), 3D tabletop `(x, y, z)` poses, and `rests_on` / `stacked_on` support hierarchy from 2D image boxes.
  - `build_ffmpeg_keyframe_command(...)` + `average_multiview_object_poses(...)`: uniform walkaround video keyframe extraction and MAD-filtered multi-view pose fusion.

## 3. Host-Agnostic Independent Visual Critic Contract

Every visual gate (`GEN-008` `G9b` hero studio pack, 6-view room Cycles pack, 1:1 texture patch-pair ledger, camera-matched reprojection board, and composed Isaac RTX 7-view pack) enforces **strict author/critic isolation** (`author_agent != critic_agent`, `verdict == "PASS"`, every dimension `>= 8.0`) validated via `skills/agentic-scene-factory/scripts/run_independent_visual_critic.py`:

| Agent Host | Independent Critic Mechanism | Validation Command |
| :--- | :--- | :--- |
| **Antigravity** | Dedicated swarm critic worker (`swarm{action:"add", name:"visual-critic", ...}`) with read-only code policy | `python skills/agentic-scene-factory/scripts/run_independent_visual_critic.py --driver validate_only --report <report.json>` |
| **Claude Code** | Isolated subagent `.claude/agents/visual-critic.md` invoked via Task tool (fresh context, read-only tools + JSON report output) | `python skills/agentic-scene-factory/scripts/run_independent_visual_critic.py --driver validate_only --report <report.json>` |
| **Codex CLI** | Fresh non-interactive `codex exec --image ...` critic process driven directly by the harness | `python skills/agentic-scene-factory/scripts/run_independent_visual_critic.py --driver codex_cli --images <pngs...> --prompt-file <rubric.md> --report <report.json>` |
| **OpenCode** | Fresh `opencode run` critic session driven directly by the harness | `python skills/agentic-scene-factory/scripts/run_independent_visual_critic.py --driver opencode_cli --images <pngs...> --prompt-file <rubric.md> --report <report.json>` |
