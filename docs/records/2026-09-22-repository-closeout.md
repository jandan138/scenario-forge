# Repository closeout: 2026-09-22

Baseline: `5d4b13af86736fe70a3d3535d587c4d1fa1c9808`, `main` tracking `origin/main`.
The user authorized closing out the entire repository and pushing to the existing
remote. This includes work beyond the current Figure 1 thread.

## Included work

- Reagent-bottle/plug source bindings and admission record.
- Funnel-to-stirrer and weighing-boat pour/stir tasks, generators, examples,
  tests, operations guidance and current-candidate head entries.
- Colleague scientific-experiment package builder and source/qualification record.
- Lab2Sim and LabBench figure tooling, current editable/portable outputs, all
  historical PPTX presentations, specs, source manifests and visual QA records.
- Portable/local figure-test separation and deferred optional rendering imports.

## Retention decision

The initial worktree contained 735 untracked files (325,271,601 bytes), predominantly
historical image-embedded SVG, PPTX and PDF variants. The user explicitly selected
**all historical PPTX also committed**. The final inventory contains 91 presentations,
including the already tracked hero, totaling 122,162,692 bytes before Git compression.
All remain at their original local paths and are included in Git.

129 untracked historical SVG/PDF projections and render logs (186,524,429 bytes)
remain on disk and are indexed by path, size and SHA-256 in
`paper/artifact-retention-20260922.json`. Narrow ignore rules cover these historical
projections/caches, not the whole figure directories or their PPTX files. Current
canonical SVG/PDF deliverables and existing tracked historical files remain tracked.
Raw USD/media trees and `outputs/` continue to use the established external-artifact
policy. No local history is deleted or moved, and this local index is not an OSS upload.

Normative update: scoped author-directed paper retention under VAL-005, with the
operations entry and this record synchronized. Package/schema/API and simulator
qualification contracts are unchanged; this does not broaden asset admission.

## Portable verification

A new regression reproduces importing the v2 layout from a clean tree with neither
its ignored reference raster nor python-pptx. It initially failed on the eager PPTX
import. PPTX imports now occur only inside the exporter; the reference image is
resolved only when rendering, before a new round directory is created. Pure layout,
archive and manifest checks stay in portable CI. Actual image/font/Sharp/Office
render checks use the existing `local_artifacts` marker and still run in `make check`.

The repository is checked both in the managed workspace (`make check`) and in a
clean temporary Git checkout exported from the intended staged files (`make ci-check`),
without ignored local images or generated output trees. The first clean run exposed
17 failures/errors in older titration and Fehling integration tests that lacked local
markers; an additional robot-bundle test used an absolute generated-source path.
Those 18 asset-backed cases now use the existing marker. Pure state/geometry/finalizer
checks in the mixed test modules remain portable.

The managed run also found the colleague shared source directory unavailable at
closeout time. The nine affected new task-integration cases now bind test-local
source constants to retained packaged copies only when the original is absent.
Each replacement must match the original task handoff manifest SHA-256; missing
or mismatched copies fail. Production generator defaults, source files and test
assertions are unchanged. The fixture is inactive in portable CI. Final results are recorded
below once those checks finish. No generated presentation is rebuilt merely to change
its test/import plumbing.

## Git transport

Normal GitHub HTTPS initially returned `Proxy CONNECT aborted`. The existing
`using-github-proxy` skill supplied a one-command proxy configuration; authenticated
read-only remote inspection and push dry-run succeeded. No global Git configuration
or proxy credential is added to the repository. Push uses the existing `main` branch
with ordinary fast-forward updates, followed by remote SHA and GitHub CI verification.

## Final local validation

- managed: **1204 passed, 1 skipped in 509.37s (0:08:29)**. Log SHA-256: `e6d3f89dce51e42d4cb5b2fe0a16c675402e579ba8f5da0283c764a85af348e3`.
- clean_portable: **1100 passed, 1 skipped, 104 deselected in 58.42s**. Log SHA-256: `cdf66a8ab684b36fa6d518796f7ef18765fbf0ad79d1efa0826642936ded46d2`.
- retained_source_regression: **11 passed in 184.40s (0:03:04)**. Log SHA-256: `e6608dacf957c61c0b73b06106f009761cda95d4cabc5b293f7f46640a9241da`.

Both complete make targets passed lint, package smoke, phase10x smoke and diff-check.
All 91 PPTX and all 129 indexed local artifacts were rehashed unchanged before commit.
The clean snapshot omits ignored images, simulator trees and generated outputs.
A separate import probe confirmed the legacy PPTX builder's pure geometry/image helpers
work without python-pptx; no rendering or core runtime dependency was added.
