# Code-as-Room generated environment integration

Date: 2026-07-30

## Outcome

Scenario Forge can now consume a producer-declared Blender room source through
ConvertAsset and compile selectable eBench task packages without importing
Blender or simulator SDKs into its pure package layers.

The first source is
`run_20260729_175041_example4_detail_small_r2`. Code-as-Room r2 removes the
undeclared Blender backup, records only a package-relative export path, includes
the source/reference and seven Blender render images in the declared closure,
and authors `/Room/env_light.inputs:texture:format = latlong`.

## Bindings

- Code-as-Room commit: `837641ce5431f6e552a73cd16c4c1207bb654d17`
- r2 `room_source.usdc` SHA-256:
  `b8dd5954a317ec0f7cacad608a0eb154ed6a67cd4c809433de49e4a6231243f3`
- producer manifest SHA-256:
  `462847bf84616465fc2ac3048f0c44ac7dc191217f751e3b7ddbb4ebb8da0a04`
- declared source closure SHA-256:
  `5f7ed3bc9ffff53e66d9103d84ecfdc6f517f82cb7d5f51273ed81831936b199`
- ConvertAsset facade SHA-256:
  `b24683e2210ee8e2a8b29dfac20772ceddb30981a841fbb081ceedbf5a37e0a9`
- admitted package `asset.usd` SHA-256:
  `c36508887ad8859bde6eea14e957e21b761908ccef87187e40f3047f7f4f7160`

ConvertAsset reported `overall_status: pass`, no blocked reasons, no missing or
remote dependencies, an Isaac Sim 4.1 runtime-profile pass, a finite 120-frame
step, and deterministic reset for the empty rigid-body set. The legacy
`MirroredBall environment format not supported yet` warning is absent.

## Workspace variants

The fixed bimanual-pour workcell passed geometric clearance in four placements:

- `center_open_floor`: retains every room Zone;
- `north_workbench_opening`: replaces the complete north Zone;
- `east_wet_lab_opening`: replaces the complete east Zone;
- `west_containment_opening`: replaces the complete west Zone.

All four generated packages passed the GenManip initial-scene visual-ready gate.
Visual review ranks west and center highest, north next, and east lowest because
the east replacement exposes a relatively blank wall.

## Human-style visual QA

The final r2 `scene_overview.png` images were reviewed without consulting
implementation details during the visible-image judgment:

| Variant | Verdict | Visible evidence |
| --- | --- | --- |
| `center_open_floor` | PASS with framing caveat | Complete room context, robot, both vessels, and retained background workbench are identifiable; the foreground task table occupies a large fraction of the image. |
| `east_wet_lab_opening` | WARN | Task elements are readable and no crossing is visible, but the removed east assembly leaves a broad blank wall and weaker laboratory context. |
| `north_workbench_opening` | PASS | Robot and vessels are clear against a retained equipment-filled side bench; no wall or furniture penetration is visible. |
| `west_containment_opening` | PASS | Strongest laboratory context, with multiple retained benches, stools, and instruments while the task remains readable. |

The review was performed locally because no independent reviewer was requested.
It is a visual judgment, not additional geometric or runtime evidence.

## Compatibility fixes

Two reusable boundary fixes were required:

- ConvertAsset now preserves explicit `.usdc` binary format when rewriting
  package-local dependencies; writing USDA text into a `.usdc` filename had
  caused Isaac to report a corrupt crate.
- Scenario Forge now factors a proper Blender root +Z basis yaw (the delivered
  room uses 180 degrees) into instance placement while keeping positive scale.
  Reflection, tilt, and shear remain rejected.

## Claim boundary

This record proves source intake, visual-static admission, four reviewed
placements, package compilation, and post-reset initial-scene rendering. It
does not prove physical interaction with background furniture, oracle rollout,
grasp success, liquid transfer, or benchmark success.
