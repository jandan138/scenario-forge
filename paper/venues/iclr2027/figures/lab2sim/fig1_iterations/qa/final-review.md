# Figure 1 final visual review

Date: 2026-09-17

## Evidence

- Canonical standalone: `../../fig1-hero.png`
- Canonical SVG/PDF: `../../fig1-hero.svg`, `../../fig1-hero.pdf`
- Grayscale: `fig1-hero-grayscale.png`
- Editable roundtrip: `../../rendered/pptx-final/fig1-hero-slides/slide-001.png`
- Paper placement: `paper-page-1.png`

## Independent visible-only verdict

PASS, high confidence. No Critical, Major, or Minor finding remains after
rebuilding from the hash-staged source assets.

- The text/image/video input is one compact card.
- Search, Spec, Build, and Admit survive paper-scale rendering.
- The Spec and ConvertAsset/PhysX meanings remain visible.
- Fehling, Powder, Titration, and OVEN 125 are equal, independent result cards.
- Grayscale preserves hierarchy and connector direction.
- The PPTX roundtrip has no material topology or content drift.
- The final ICLR page has no title, prose, figure, or caption collision.

## Machine checks

- Strict figure-spec validation: zero errors and zero warnings.
- `scripts/prepare_lab2sim_fig1_assets.py --check`: five external sources and
  five selected assets match the committed source/asset hash manifest.
- PPTX audit: 62 shapes, 19 text shapes, 26 words, three font sizes, no external
  relationships, paths, shadows, or theme effects.
- Paper compile: five pages; Figure 1 sits after its first textual reference on
  page 1.
