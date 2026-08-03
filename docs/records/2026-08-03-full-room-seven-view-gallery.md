# Full-room seven-view gallery

The historical `example4` room and four generated scientific rooms were
re-rendered through the actual Isaac Sim 4.1 / GenManip collected-package path.
Each package uses preview request/evidence/gate v0.3 and contains seven
1920 × 1080 images.

Output root:

`outputs/scientific_workbench_background_gallery_v3_20260803/packages/`

Packages:

- `example4`
- `modern_wet_chemistry`
- `analytical_instrumentation`
- `bioclean`
- `teaching_research`

All five `evidence/initial_scene/visual_ready_gate.yaml` receipts report
`status: passed`. Each gate verifies the four room views, three task views,
runtime object presence, exact PNG resolution/hash, room visibility policy,
and projected room/workcell framing.

Clean-room local visual review inspected contact sheets for all 20 room views
and all 15 task views. No blank render, wall-clipped camera, missing workcell,
unusable lighting, or obvious geometry/material failure remained. The review
was local because delegated reviewers were not enabled for this task.

The page preview was served from `docs/background-gallery/` and audited with a
real Chromium browser at 1440 × 1000, 834 × 1112, and 390 × 844. All three
returned HTTP 200, loaded 40/40 images, had zero failed requests, console/page
errors, broken images, or document-level horizontal overflow. Temporary audit
artifacts were written to `/tmp/background-gallery-browser-audit/`.

Claim boundary: this evidence establishes visual package readiness only. It
does not establish reachability, collision-free motion, manipulation success,
liquid transfer, policy success, or benchmark success.
