# Round 07 — structure-A rebuild (2026-09-17)

Full layout rebuild after the author rejected round 06 as a recolor of the
same box row. The communication job is unchanged; the semantic graph
(nodes, edge order, meaning strings, spec payload strings) is
byte-identical to round 06 — only presentation changed.

Design (user-approved structure A):

- One IKA OVEN 125 instance threads the whole figure: closed-door
  catalog photo (Request) -> open-door catalog photo (Search, new
  staged asset source/ika_catalog_open.png from image2) -> spec
  contract card (Spec) -> admitted-scene USD render (Build, reuses the
  fig23-staged fig3_oven_usd.png) -> PASS outline pill (Admit) -> the
  OVEN 125 tile in the gallery.
- The agent lives in a #F5F7FA container band with four teal numbered
  step dots; the three in-band connectors render as internal-scope
  chevrons so the band never paints over them; zone connectors keep
  >=3.6 px clearance from every panel.
- Results are a 2x2 gallery of 375x224 cells (5.8% cover crop vs ~30%
  before); each label binds to its own tile (30 px above and below).
- DejaVu Sans, exactly four sizes (44/34/32/28), sentence case except
  the OVEN 125 product name.

Review-loop repairs (07.1): spec step gained an "asset spec" caption
for rhythm; the bottom gallery row shifted down so labels bind
unambiguously; the OVEN r2 hero's documented global brightness lift
went 1.25 -> 1.40 (script, hashes, provenance, tests updated together).
Independent clean-room review: PASS (first round) with five Minors,
re-verified PASS after the three repairs, no Critical/Major.

Evidence: fig1-hero-round07.png, fig1-hero.svg,
lab2sim-hero.figure-spec.json (snapshot), ../qa/fig1-hero-grayscale.png,
../qa/paper-page-2.png, ../../qa-report.json,
../../rendered/pptx-final/qa-report.json; verdict recorded in
../qa/final-review.md.
