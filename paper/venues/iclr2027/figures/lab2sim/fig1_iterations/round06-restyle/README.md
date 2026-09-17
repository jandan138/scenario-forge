# Round 06 — visual-language restyle (2026-09-17)

Slate + single-teal restyle of the approved semantic graph, plus a
clean-room-review repair round (06.1). No change to nodes, edges,
meanings, or provenance claims. The spec payload strings now use the
spaced product naming of the source spec doc (OVEN 125 / DOOR 180° /
SHELF ×6).

Round 06 (initial restyle):

- Palette harmonized to the fig2/3 `compose_galleries.py` hex values
  (ink #172033, muted #3F4855, teal #0E7C6B, orange #C96A0A, hairline
  #C5CFDA, spec tint #FFF8EE); the three colored section rule bars were
  replaced by one full-width hairline.
- Font unified to DejaVu Sans, two weights (Book/Bold only); all labels
  sentence case except the OVEN 125 product name.
- Stage panels unified, spec keeps the fig3 contract-card tint and
  accent stroke; icons recolored to monochrome slate and re-sanitized.

Round 06.1 (independent visible-only review repairs):

- All cards joined one y170-430 band; canvas trimmed to 2000x470,
  eliminating the orphaned Video row and the dead bottom band.
- All connectors now span 20 px gutters, including the Admit → gallery
  payoff handoff (the review's M1); one slate solid width-4 family.
- Type ramp consolidated to four sizes (46 headers / 36 stage titles +
  gallery labels / 34 stage bodies / 30 spec payload, modality labels,
  PASS), keeping the PPTX audit's max-font-sizes gate green.
- PASS demoted from a filled teal pill to a teal outline pill so the
  spec contract card is the single warm accent.
- Video icon redrawn as a camcorder with attached lens and record dot
  (no longer reads as a form checkbox); search-icon stroke normalized.
- Gallery label casing unified with the spec payload (OVEN 125).
- OVEN r2 hero's documented global brightness lift raised 1.12 → 1.25
  to balance the gallery row (script, hash manifest, provenance, and
  tests updated together; no local retouching, no crop).
- Fehling tan wall and the icon rhythm (icons on Search/Build only)
  were reviewed and kept: the wall is real scene content consistent
  with Figure 2, and Spec/Admit carry their content (contract fields,
  admission verdict) instead of glyphs.

Evidence: fig1-hero-round06.png (standalone), fig1-hero.svg (canonical),
../qa/fig1-hero-grayscale.png, ../qa/paper-page-1.png,
../qa/paper-page-2.png (figure inline), ../../qa-report.json,
../../rendered/pptx-final/qa-report.json. The independent clean-room
review loop ran WARN → repairs (06.1) → WARN → repairs (06.2: payoff
arrow span, cube build icon, modality list rhythm; 06.3: unmasked the
payoff arrow tip by starting the invisible result-region after it) →
final PASS with no Critical/Major, recorded in ../qa/final-review.md.
