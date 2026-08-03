# Four generated laboratory backgrounds

> Superseded for gallery camera coverage by
> [`2026-08-03-full-room-seven-view-gallery.md`](2026-08-03-full-room-seven-view-gallery.md).
> The source rooms and task packages remain the same; the newer record adds a
> uniform seven-view, 1080p runtime evidence contract to all five backgrounds.

Date: 2026-08-03

## Outcome

The existing Code-as-Room `example4` center-open-floor package remains the
visual baseline. Four additional rooms were generated and carried through the
same owner-separated pipeline:

1. Code-as-Room produced traceable Blender/USD source deliveries;
2. ConvertAsset produced source-bound `visual_static_environment` packages,
   dependency closure evidence, Isaac Sim 4.1 runtime smoke evidence, and full
   3.8 m by 4.0 m workcell profiles;
3. Scenario Forge consumed those handoffs and compiled four independent eBench
   bimanual-pour packages with the same Lift2 robot, workbench, conical flask,
   graduated cylinder, task definition, and metric references.

The public comparison page is
[`docs/background-gallery/`](../background-gallery/). It shows the historical
baseline plus the four new room overviews. Each new room also includes the
workspace and task-object closeups introduced by the preview v0.2 contract.

## Accepted backgrounds

| Background | Profile | Optional inactive assemblies | Result |
| --- | ---: | --- | --- |
| `scientific_environment_code_room_wet_chemistry_v1` | yaw 0° | none | profiled; package check passed |
| `scientific_environment_code_room_analytical_instrumentation_v1` | yaw 90° | three complete movable stool roots | profiled; package check passed |
| `scientific_environment_code_room_bioclean_v1` | yaw 90° | none | profiled; package check passed |
| `scientific_environment_code_room_teaching_research_v1` | yaw 0° | none | profiled; package check passed |

An earlier analytical-instrumentation candidate was rejected because the full
workcell clearance intersected perimeter equipment. The retained analytical
room is a separately generated fallback whose center aisle passes the same
clearance contract after removing only the three declared stool assemblies.
The rejected candidate is not presented as a successful package.

## Reproducible environment boundary

No ad-hoc Python or simulator environment was created. Pure package commands
used the EOS managed Python interpreter. Code-as-Room used its existing managed
interpreter and external Blender 4.4.3. Runtime rendering used the EOS managed
Isaac Sim 4.1/GenManip interpreter. Scenario Forge did not modify GenManip and
did not add room-specific collider, mass, inertia, scale, material, or PhysX
suppression patches.

## Evidence

The compact, hash-bound evidence index is retained at
[`evidence/2026-08-03-four-generated-lab-backgrounds/manifest.yaml`](evidence/2026-08-03-four-generated-lab-backgrounds/manifest.yaml).
Each generated task package contains:

```text
adapters/ebench/genmanip/evidence/initial_scene/
  scene_overview.png
  workspace_closeup.png
  task_object_closeup.png
```

All four packages passed `scenario-forge package check --require-asset-lock`
and their visual-ready gates. Visual review found no room/workcell intersection
or missing task component in the retained overviews. The fixed overview camera
keeps the workcell large enough to compare object placement; it is not intended
as an architectural room survey.

The final static page was served locally from `docs/` and audited in the EOS
managed Playwright environment with the existing shared Chromium. Desktop
(1440 × 1000), tablet (834 × 1112), and mobile (390 × 844) all returned HTTP
200 with 18/18 images loaded, no document-level horizontal overflow, no console
or page errors, and no failed requests. The local review screenshots and JSON
log were written to
`/tmp/scenario-forge-background-gallery-browser-audit-20260803-final/`; they
are reproducible QA artifacts rather than repository inputs.

## Claim boundary

This delivery proves source-bound static-background admission, complete package
composition, post-reset initial-scene rendering, and background interchange at
the package-generation boundary. It does not prove robot reachability,
collision-free motion, grasp or pour execution, liquid transfer, policy
performance, or benchmark success.
