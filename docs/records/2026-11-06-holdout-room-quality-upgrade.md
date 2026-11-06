# Holdout room quality upgrade — sample in progress

The user requested a full-room visual-quality upgrade after reviewing the first five backgrounds. Existing delivery remains unchanged. Priority is complete-room geometry, furnishing, materials and lighting rather than maximizing background visibility in fixed task cameras. Task foreground, physics, cameras, metrics and initial states remain fixed.

The first sample is teaching chemistry, using its retained source reference. The user selected normal prior Gemini-style pipeline execution with bounded existing retries, not budget-driven repeated iteration. Geometry/material retries remain capped at three; existing layout iteration limit is five. Detailed small-object stages are enabled to address the previous simplified furnishings.

DeepSeek official model discovery succeeded; `deepseek-flash` and `deepseek-v4-pro` were available. A small vision/JSON probe using the reference image succeeded. `deepseek-flash` is selected for the normal vision/text pipeline, including explicit replacement of the Stage 2 Gemini override. Credentials are stored outside repositories with restricted permissions, never in manifests or command arguments.

Producer: Code-as-Room, existing dedicated Python environment and Blender executable. Run: `/cpfs/user/zhuzihou/dev/Code-as-Room/runs/holdout_deepseek_20261106/run_teaching_chemistry`. Orchestration/evidence: `external_artifacts/holdout_room_upgrade_20261106`. Stages 1–10 run first; Stage 11 uses existing/procedural material resources and builtin image generation for missing texture imagery as needed. The unavailable Gemini image endpoint is not called. Render preparation, Blender execution, ConvertAsset admission and Isaac integration remain pending.

The sample must be shown in full-room, detail and existing task views for user direction confirmation before expanding to all five rooms. No runtime or aesthetic pass is claimed yet. Later integration requires a new version, fresh scene evidence and a manually reviewed PR, with no automatic merge.

Applicable standards: ASSET-001–005, MAT-002/004 and VAL-001–006. No general rule or core API change; this is a producer-side quality improvement. This record will retain phase-specific evidence and limits.

## Sample implementation and correction log

The initial provider probe passed, but constructor-level hardcoded Stage 5/6 model overrides still selected Gemini/GPT model IDs at the DeepSeek endpoint. The first pipeline summary misleadingly reported all stages successful despite zero generated detailed geometry. That attempt is archived, not accepted. The task launcher now pins all text/vision model slots after construction; rerunning stages 5–10 produced 77 detailed objects/914 parts and 21 of 22 detailed small items/70 parts. One wash bottle retains its simple representation.

The initial preview runner omitted `run_name='__main__'`, so it rendered Blender's default cube and only unguarded small-object calls. After correcting the runner, a generated helper signature lacked its `show_direction` parameter; the producer script was corrected and an explicit overview camera added. These failed previews remain diagnostic evidence, not valid room renders.

A builtin imagegen base-color map supplements procedural materials. Final prompt: “single seamless tileable square base-color texture, orthographic flat surface scan of clean light-medium neutral gray laboratory safety vinyl flooring with fine subtle mineral speckles; uniform diffuse illumination; no shadows, highlights, objects, perspective, room, grout, text or border; restrained realistic microtexture.” Saved in the producer run at `textures/lab_floor_albedo.png`; it is an albedo map, not generated normal/roughness data. Lighting/exposure were reduced to reveal surfaces. Stools were tucked toward their perimeter benches; the sample has a separately profiled central 3.8 × 4 m region, not the previous rooms' larger clearance claim.

Close views exposed a duplicated lower cabinet inside the upper fume-hood assembly. Revision r2 removes those duplicate parts, extends the upper chamber down to worktop height and removes duplicate sash geometry. Existing foreground task assets are untouched. Source r1/r2 and their respective admission evidence are kept separately.

ConvertAsset source support correction records 16 corrected and 12 unchanged supported small roots; two oversized cabinet-stock groups were removed by the producer support policy. This is a visible-content limitation, not a claim that the entire initial object inventory was retained. The final task integration runs in isolated worktree `/mnt/data/zhuzihou/GenManip-Sim-deliveries/holdout-room-quality-20261106`; receiver data is read-only baseline input.

## Sample r2 completed

Source export and ConvertAsset normalization/runtime admission pass for `holdout_teaching_chemistry_deepseek_r2`. The central 3.8 × 4 m profile passes for this source. Source and normalized asset were reviewed in full-room renders; Blender near views cover the hood, bench equipment and interior. RTX glass reflections/transparency differ from Blender and remain a stated limitation. The normalized source itself is not claimed photometrically identical across renderers.

The representative task01 `holdout_test_mixed_1` completed reset and a 20-step hold with eight four-camera initial/final images. `final_native_audit.json` binds final config/metadata/scene hashes, exact foreground metadata preservation and YAML equivalence except scene path. Reviewed retained worker/server/client logs have no matches for the listed fatal patterns. Eight producer lights are disabled in the task-only composition to avoid excessive glass highlights, while its native ambient light is inherited. This is one representative task check, not 136-case acceptance or policy success.

Delivery and canonical ZIP: `external_artifacts/holdout_room_upgrade_20261106/delivery/teaching_chemistry_sample_r2` and the adjacent `.zip`/`.zip.sha256`. The bundle contains source .blend/USD/textures/provenance, the normalized package, preview images and selected evidence; files have SHA-256 records and the ZIP CRC is checked. The isolated task composition requires existing receiver baseline assets and is not advertised as a standalone task delivery.

No installed holdout_test asset or receiver code was replaced. No PR was opened or merged for the quality sample. The requested single-sample sequence is complete; expansion to the other four rooms awaits the previously agreed user direction confirmation. No general standard or core schema/API changed; the producer and task-specific limitations above are not generalized into new rules.
