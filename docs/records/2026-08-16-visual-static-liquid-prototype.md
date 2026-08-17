# Visual-static liquid prototype

Date: 2026-08-16

## Outcome

Scenario Forge now has a standalone, non-task prototype for making admitted
glass vessels look filled without adding PBD particles or any other liquid
physics:

```text
outputs/visual_static_liquid_prototype_20260816/
```

The prototype contains two beakers and two conical flasks with independently
configured colors and volume fractions. It provides a neutral review scene and
a full-room review scene. It has deliberately not been added to Tasks 02, 07,
08, or any benchmark package.

## Method and boundary

The generator solves liquid height from the configured vessel axial profile and
requested volume fraction, then authors an open-sided body mesh plus a shallow
concave meniscus under the vessel transform. Each liquid prim declares
`scenarioForge:role = visual_static_liquid` and has no collision, rigid-body,
mass, particle-system, or metric role.

This is intentionally a background-appearance technique. When a vessel moves or
tilts, the visual liquid rigidly follows it. It does not remain level, slosh,
pour, spill, or transfer. Interactive task vessels must continue to use the
existing dynamic liquid path.

The admitted beaker, conical-flask, table, and room packages are copied without
modification. Both USD entry scenes use package-relative references, and the
Isaac Sim 4.1 closure check found zero missing or external dependencies.

## Reproduction

Generate the self-contained prototype without launching a simulator:

```bash
/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  scripts/generate_visual_static_liquid_prototype.py
```

Generate it and render the evidence through the EOS-managed Isaac Sim 4.1
environment:

```bash
/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  scripts/generate_visual_static_liquid_prototype.py --render
```

Configuration is in
`configs/prototypes/visual_static_liquid_v1.yaml`. The output manifest records
source-package hashes, generated-file hashes, the visual-only physics contract,
and the render-evidence hash.

## Runtime and visual review

Isaac Sim 4.1 generated four 1920x1080 stills and an eight-second, 30 fps H.264
tilt demonstration. The runtime inspection found no physics API or particle
system below any `VisualLiquid` prim. The video contains 240 frames.

Local human-style visual QA verdict:

- Beakers: **PASS**. Blue and green liquid surfaces, different fill heights,
  transparent vessel walls, and contained geometry are identifiable.
- Full-room placement: **PASS**. All four vessels sit on the central table and
  read as background dressing at room scale.
- Conical flasks: **WARN**. The liquid color and rigid-follow behavior are clear,
  especially while tilted, but the source flask is a transparent analytic cone;
  nested transparency produces visibly faceted bands in some static views.
- Overall prototype: **PASS WITH CAVEAT** for optional background dressing, not
  for close-up evidence or interactive-liquid claims.

The review was performed locally rather than as an independent blind review.
The renderer emits a Replicator render-product cleanup message during headless
shutdown after all artifacts and manifests are complete; the process exits zero
and the recorded closure/runtime gates pass.

