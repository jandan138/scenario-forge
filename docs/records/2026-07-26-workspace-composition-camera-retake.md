# Workspace composition and camera retake (2026-07-26)

The first profile-2 overview renders exposed two different issues:

- `scientific_environment_083` used a source row whose wall sat immediately
  behind the fixed eBench anchor.  The room itself was valid, but the old
  runtime-bounds camera pointed into the wall.
- `scientific_environment_067` had a valid structural package and closeup, but
  its profiled anchor leaves the fixed workspace at a room edge.  Retargeting
  the source camera still produces a blank-wall view and does not establish a
  usable combined room/workspace image.

Scenario Forge now has a small, explicit composition-layer policy:

1. If a visual-static package carries a source Perspective camera, preserve its
   direction and retarget only its target to the unchanged eBench workspace.
2. Candidate `scientific_environment_083` receives a reviewed +90° yaw around
   its source-bound anchor.  The generated scene layer preserves the anchor
   mapping, while the table, robot, vessels, poses, and task contract remain
   unchanged.
3. Candidate `scientific_environment_067` is not promoted by camera tricks. It
   remains a structural/closeup-only diagnostic until ConvertAsset supplies a
   better source-bound placement or assembly profile.

The generator records `composition_yaw_deg` in the background placement and
uses preview camera policy `scenario-forge/runtime-workspace-context-v8` for
the retargeted view. The source USD, MDL, mesh, physics, GenManip checkout,
and policy observation camera are not modified. The image review is evidence
only; it does not claim dynamic background behavior, grasp success, or liquid
transfer.

Current clean-room outcome:

| Candidate | Closeup | Combined overview |
| --- | --- | --- |
| `083` | pass | pass after +90° composition yaw |
| `067` | pass | fail; producer/profile follow-up required |
