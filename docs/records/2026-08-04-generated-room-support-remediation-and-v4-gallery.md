# Generated-room support remediation and v4 gallery

The five Code-as-Room scientific backgrounds were rebuilt under a support
relation contract after visual review found floating decoration groups in the
modern wet-chemistry and bioclean rooms.

## Source correction

Code-as-Room revision `d186186` inventories all non-floor small roots named
`MinorPlace_*`, `Orphan_*`, or `*__top__*`. It records a support prim, relation
kind, before/after bounds, correction, removal reason, and engineering review
in `support_relations.json`, bound to the exact exported USD hash.

- modern wet chemistry: 43 relations; the wash-bottle/dispenser group moved
  0.215 m onto the east bench; one unsupported overhead bottle group was
  removed;
- bioclean: 27 relations; the wash-bottle/soap group moved 0.203 m onto the
  east sink bench and down 0.005 m; one unsupported orphan drying-rack holder
  was removed;
- example4, analytical instrumentation, and teaching research were audited by
  the same rule. Small contact corrections were applied where required; no
  decoration was removed.

## Independent admission and consumer gate

ConvertAsset revision `79608d5` independently recomputes the declared
footprint and contact relationships from composed USD geometry. All five
packages under
`/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/generated_scientific_labs_v2_20260804/`
passed static/runtime admission and their support audit. Workspace profiles
carry the reviewed support closure.

Scenario Forge intake is now v0.2. Generated backgrounds require the producer
support sidecar and a matching passing ConvertAsset certificate. Source hash,
relation count, and removal count are checked again before compilation. The
portable asset metadata carries the certificate summary; Scenario Forge does
not reimplement USD geometry conversion or the independent geometry audit.

## Rebuilt task packages and visual review

Five fixed-workspace packages are under
`outputs/scientific_workbench_background_gallery_v4_20260804/packages/`. The
room changes between packages; the eBench robot, table, conical bottle,
graduated cylinder, task steps, and metric stay fixed. Each package produced
seven 1920 × 1080 Isaac Sim 4.1 / GenManip views and a passing v0.3 visual-ready
gate.

A local human-style review inspected all 35 images for floating decorations,
support/contact errors, geometry intersections, room/workcell placement,
missing assets, and unusable framing. No release-blocking defect remained. The
review was local because independent reviewer delegation was not enabled.

The gallery was served locally and audited in real Chromium at 1440 × 1000,
834 × 1112, and 390 × 844. It contains five cards, 40 image elements referring
to 35 unique 1920 × 1080 files, no missing image, and no visible responsive
layout failure. Browser evidence is in
`/tmp/background-gallery-browser-audit-v4/`.

## Claim boundary

This work establishes generated-room source support integrity, independent
visual-static admission, package compilation, reset/load visibility, and
seven-view visual readiness. It does not establish robot reachability,
collision-free motion, bimanual pouring, liquid transfer, policy success, or
benchmark success.
