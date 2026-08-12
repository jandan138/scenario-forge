# Scientific workbench r6 dynamic dressing

Scenario Forge r6 adds five fixed background-specific tabletop dressing
presets while retaining all r5 packages unchanged. The release contains 14
packages for 10 task types; Task 7 is rendered in all five backgrounds.

Each context prop is a real ConvertAsset-owned dynamic package, but has no
metric participation. eBench loads the package-authored physics with local
collider/rigid-body authoring disabled. VR includes the prop in `scene.usd` and
`deps/context/`, but keeps the task `obj_prim_list` limited to task objects.

The supplied source archive contains 29 geometry-validated items. Geometry
validation is not dynamic admission. This release deliberately reuses the
already source-bound interaction/static-support packages needed by the five
presets; it does not claim that all 29 source items are dynamically qualified.
ConvertAsset now has the narrower `aan.dynamic_context_profile.v1` path for
future context-only admissions without inventing grasp or task claims.

Runtime preview evidence was produced in Isaac Sim 4.1 at 1920 × 1080 with
seven views per package. All 14 visual-ready gates passed. This evidence covers
initial scene loading, reset and rendering; it does not establish policy or
benchmark success.

Artifacts:

- `outputs/scientific_workbench_asset_expansion_20260812_r6_full/manifest.yaml`
- `outputs/scientific_workbench_usd_handoff_r6_20260812/`

The handoff contains two tested archives:

- `scientific_workbench_task01_bimanual_pour_r6_20260812.zip`
  (`sha256:0a6f474f6452e2c8e35bf739bbcc7d1f33191c559512c843530c20d7f1eecca1`);
- `scientific_workbench_regular_tasks_r6_20260812.zip`
  (`sha256:e5f6e21d69402c92ae6a2b13a1f1710bb7304227408fb4f0f472e476c984a4a3`).

The published task directory defaults to r6 and provides an explicit r5
switch. A real-browser audit covered 1440×1000, 900×1000, and 390×844: no
broken images, page/console/request errors, or document-level horizontal
overflow were observed, and switching to r5 replaced all 20 versioned image
and release-label nodes.
