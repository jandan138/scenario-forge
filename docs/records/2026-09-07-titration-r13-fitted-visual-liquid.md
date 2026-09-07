# Titration r1.3: receiver liquid fitted to the inner cavity

## Scope

The r1.2 receiver contained an unbound, opaque-looking cylinder above the actual
inner floor. r1.3 replaces only `/World/obj_receiver_flask/VisualLiquid` and its
rendering connections. The original r1.2 delivery remains unchanged.

This is a visual liquid, not a PBD upgrade. The liquid level is fixed at 89 mm
in the flask's local frame; reported titrant volume does not raise the mesh.
Container geometry, SDFs, mass, joints, device flow rates, success thresholds,
task placement and producer dependency files are unchanged.

## Geometry

`measure_titration_receiver_cavity.py` calls ConvertAsset's existing triangle and
ray-intersection helpers, rather than implementing another mesh converter.
The profile is bound to the source scene SHA and records the helper SHA.
It samples 64 azimuths at uniform heights plus source vertex heights.

- Actual inner floor: 3.684 mm above the flask origin.
- Visual liquid bottom: 3.834 mm; nominal inner-wall clearance: 0.15 mm.
- Maximum sampled wall gap: 0.3523 mm, including the source's polygonal surface.
- Four phase meshes share one fitted axial profile and a closed top surface.
- Smooth side normals avoid the obvious faceted refraction of the first candidate.
- The visual magnetic bar sits at the inner floor, not inside a floating cylinder.

These are sampled geometric measurements, not a general proof for arbitrary vessels.
No CollisionAPI, rigid body or particle system is added to the visual subtree.

## Color and runtime

The initial water tint is `(0.97, 0.99, 1.0)`, endpoint tint `(1.0, 0.80, 0.88)`.
The package-local OmniGlass recipe uses IOR 1.333, roughness 0.02, absorption
depth 0.05 m and `thin_walled=false`. Only the visual liquid has
`primvars:doNotCastShadows=true`: the realtime opaque-shadow approximation was
turning the submerged white magnetic bar black. This is a documented visual
approximation, not physically solved water optics. Increasing refraction
bounces, using a thin-walled shader, and reducing IOR did not improve the
comparison, so none of those diagnostic overrides enters the delivery.
The original dark cabinets and stirrer plate still produce strong dark reflections;
the revision does not relight the room or change the flask glass material.
The existing controller now writes `inputs:glass_color` as well as its older
diffuse/base-color interfaces. It still controls phase visibility and retains
the same OPEN → FINE → DRIP → CLOSED sequence, volume window and hold duration.
Reset must restore the initial material color as well as the volume and phase.

The VR baseline is **Isaac Sim 4.5**. An early test incorrectly used the 4.1
robot environment; it failed because that is not the original VR runtime.
That report remains outside the handoff and is not counted as acceptance.
No environment or runtime compatibility conversion was made.

## Evidence and reproduction

Output root:
`outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_3_20260907/`

Scripts:

1. `measure_titration_receiver_cavity.py`: source-bound profile via ConvertAsset.
2. `python -m scripts.generate_traditional_titration_vr_r13`: candidate generation.
3. `python -m scripts.audit_titration_visual_revision`: non-visual/dependency comparison.
4. `render_titration_liquid_comparison.py`: separate Isaac 4.5 processes for before/after.
5. `validate_traditional_titration_vr_r1.py`: three cold starts, including material reset.
6. `finalize_traditional_titration_vr_r1.py`: dependency closure, ZIP CRC and SHA.

Render comparisons use the same scene lighting, camera and renderer. Endpoint
stills are explicitly labeled visual-state snapshots, not robot execution.
The state-machine regression prescribes device joint positions; it does not
claim robot contact or robot-policy success. No old robot video is relabeled r1.3.

Local visual review (not independent) accepts the geometry and transparency,
with a WARN for strong dark room reflections. The four-panel comparison is
`handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_3/evidence/initial_scene/liquid_before_after.png`.
Only final renders enter the handoff; exploratory material renders are retained
separately under `diagnostic_renders/` in the output root.

## Final acceptance

- Three fresh Isaac 4.5 processes passed on the exact scene SHA
  `f0617fed47b5e3f460773bf976f7ad6aae922edc8fad201d9d39697945df95bd`.
- Each reached 15.000164 mL, held closed for 3.216664 s, and restored the initial
  water tint on reset. All material, state and stability checks passed.
- Non-visual content audit: no unexpected scene changes, no changed producer
  dependencies, no physics added to the liquid.
- Package dependency closure and ZIP CRC passed; a `.zip.sha256` is provided.
- `make check`: 920 passed, 1 skipped; Ruff and package/phase10x smoke passed.
- Current VR long-handle delivery points to r1.3. The separate r1.2 robot
  validation branch remains unchanged; nothing is archived or deleted here.
