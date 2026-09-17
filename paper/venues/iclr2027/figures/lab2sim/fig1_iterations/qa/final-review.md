# Figure 1 final visual review

Date: 2026-09-17 (round 06 restyle; supersedes the earlier same-day review below)

## Evidence

- Canonical standalone: `../../fig1-hero.png`
- Canonical SVG/PDF: `../../fig1-hero.svg`, `../../fig1-hero.pdf`
- Grayscale: `fig1-hero-grayscale.png`
- Editable roundtrip: `../../rendered/pptx-final/fig1-hero-slides/slide-001.png`
- Paper placement: `paper-page-2.png` (figure and caption inline)
- Round notes: `../round06-restyle/README.md`

## Independent visible-only verdict (round 06)

PASS, high confidence, from an independent clean-room reviewer after four
inspection rounds (WARN → repairs → WARN → repairs → PASS re-verification).
No Critical or Major finding remains. Three non-blocking Minors stand:
card borders are light gray in B/W print; two scene thumbnails clip
background objects at their top edge (only visible on close zoom); the
Image and Video modality icons share a rectangle-with-dot motif
(disambiguated by the camcorder lens).

Repairs made during the loop:

- All cards joined one 170-430 band; canvas trimmed to 2000x470; the
  orphaned Video row and dead bottom band are gone.
- All five connectors, including the Admit → gallery payoff handoff,
  render as one uniform full-size arrowhead family across 20 px gutters
  (the payoff tip had been painted over by the invisible result-region
  panel; the region now starts after the arrow tip).
- PASS demoted to a teal outline pill; the spec contract card is the
  single warm accent; payload strings use the source spec doc's spaced
  product naming (OVEN 125 / DOOR 180° / SHELF ×6).
- Build icon redrawn as an isometric cube; Video icon redrawn as a
  camcorder with attached lens and record dot; icon family is
  monochrome slate.
- OVEN r2 hero's documented global brightness lift raised 1.12 → 1.25
  to balance the gallery row (hash manifest, provenance, and tests
  updated together; no local retouching or crop).

## Machine checks (round 06)

- Strict figure-spec validation: zero errors and zero warnings.
- `scripts/prepare_lab2sim_fig1_assets.py --check`: five external sources and
  five selected assets match the committed source/asset hash manifest.
- PPTX audit: 58 shapes, 19 text shapes, 28 words, four font sizes, no external
  relationships, paths, shadows, or theme effects.
- Paper compile: five pages; Figure 1 sits after its first textual reference,
  inline on page 2.

## Earlier same-day review (pre-restyle, kept for history)

PASS, high confidence. No Critical, Major, or Minor finding remains after
rebuilding from the hash-staged source assets.

- The text/image/video input is one compact card.
- Search, Spec, Build, and Admit survive paper-scale rendering.
- The Spec and ConvertAsset/PhysX meanings remain visible.
- Fehling, Powder, Titration, and OVEN 125 are equal, independent result cards.
- Grayscale preserves hierarchy and connector direction.
- The PPTX roundtrip has no material topology or content drift.
- The final ICLR page has no title, prose, figure, or caption collision.

Machine checks at that time: strict validation clean; hash check clean;
PPTX audit 62 shapes, 19 text shapes, 26 words, three font sizes; paper
compiled to five pages with Figure 1 after its first reference.
