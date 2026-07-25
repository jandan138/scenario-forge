# Workspace profile-2 package and render status (2026-07-26)

ConvertAsset profile-2 is consumed from
`outputs/scientific_workbench_workspace_profiles_20260724/workspace_profiles_manifest.json`.
The producer revision is `47d64148f7f5f4cc585ca0b43fb450eb21c6fda5`.
Scenario Forge generated five fat packages at
`outputs/scientific_workbench_workspace_profiled_variants_20260726/`.

The exact source-composed mappings used by the generator are:

| Candidate | metres per source-composed unit | Placement policy |
| --- | ---: | --- |
| 059 | `0.09044044496698923` | preserve profiled workspace metric |
| 066 | `0.05223023085762039` | preserve profiled workspace metric |
| 067 | `0.00002676258376688719` | preserve metric; profile-2 corrected the bench-local estimate |
| 083 | `1.0` | preserve profiled workspace metric |
| 084 | existing reviewed anchor; legacy envelope fit | visual envelope fit |

All five packages pass `scenario_forge.cli package check --require-asset-lock`.
All five GenManip exports have a structural `visual_ready_gate.yaml`; the gate
only proves that the post-reset renderer produced both required images and that
the expected runtime prims were present. It does not prove on-camera visibility,
task success, physics fidelity, or liquid transfer.

Evidence locations are, for each candidate,
`adapters/ebench/genmanip/evidence/initial_scene/scene_overview.png` and
`workspace_closeup.png`. The closeups consistently show the fixed dual-arm
workspace and both vessels. The overview images for 059, 066, 084, and the
retaken 083 show useful room context at different quality levels. Candidate
083 now uses a reviewed +90° composition-layer yaw and source-authored camera
direction retarget, so its closeup and combined overview are visually
accepted. Candidate 067's closeup is usable, but its combined overview remains
a visual FAIL: the fixed workspace is against a blank wall and the target
vessels are not readable. Do not describe 067 as a complete room/workspace view
until ConvertAsset provides a better source-bound placement/profile.

No GenManip source or ConvertAsset asset was modified. No dynamic task rollout,
metric score, grasp success, or pour success is claimed by this record.
