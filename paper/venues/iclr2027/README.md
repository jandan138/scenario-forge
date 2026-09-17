# Lab2Sim (ICLR 2027 two-layer draft)

Anonymous ICLR 2027 draft: about three pages of main narrative (introduction
through conclusion) with three full-width figures, followed by references and
an appendix.

Compile from this directory:

```bash
latexmk -pdf main.tex
```

PDF: `build/main.pdf` (also copied to `Lab2Sim.pdf`).

Figures live in `figures/lab2sim/`.

- Figure 1 is built from `lab2sim-hero.figure-spec.json` with the
  scientific-figures skill.
- Figures 2 and 3 are composed by `figures/lab2sim/compose_galleries.py`
  (Matplotlib, laid out at the 5.5 in text width with 7–8.5 pt type; SVG,
  PDF, and 600 dpi PNG). Their figure contract is `fig23-contract.md`.
- Provenance for all figures, including render manifests, scene hashes, and
  ConvertAsset promotion receipts for Figure 3, is in
  `figures/lab2sim/provenance.json`.

The raster sources are intentionally ignored by git. With the indexed external
artifacts present, stage and verify the inputs before rendering:

```bash
python ../../../scripts/prepare_lab2sim_fig1_assets.py          # Figure 1 (5 inputs)
python ../../../scripts/prepare_lab2sim_result_assets.py        # Figures 2-3 + appendix (14 inputs)
python ../../../scripts/prepare_lab2sim_fig1_assets.py --check
python ../../../scripts/prepare_lab2sim_result_assets.py --check
python figures/lab2sim/compose_galleries.py                     # regenerates fig2/fig3 svg/pdf/png
```

The open-oven frame in Figure 3 is a camera-only retake of the admitted Task 12
scene (`scripts/render_lab2sim_oven_retake.py`, run with
`/isaac-sim/python.sh`); its manifest lives under
`outputs/lab2sim_fig3_retake_20260917/oven_r2/`.
