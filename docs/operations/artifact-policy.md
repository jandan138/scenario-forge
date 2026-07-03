# Artifact Policy

Commit:

- package manifests;
- schema files;
- tiny examples and fixtures;
- validation reports that support a design decision;
- dated records summarizing claim boundaries.

Do not commit:

- raw USD asset trees;
- converted asset packages;
- videos, rendered frames, depth arrays, or simulator dumps;
- raw real-to-sim source media, scans, Gaussian splats, segmentation masks,
  reconstruction intermediates, and generated mesh dumps;
- model checkpoints;
- large generated scenario outputs.

Use `external_artifacts/README.md` as an index for large artifacts stored outside git.

Source datasets should be treated as immutable. Generated outputs should go under a scratch root
such as `/tmp/scenario-forge-*` or a documented external artifact path.

For LabBuilder-style and SimFoundry-style integrations, commit only Scenario
Forge manifests, locks, provenance summaries, evidence summaries, schemas, and
tiny fixtures. Store upstream datasets, source media, generated assets, and
simulator outputs in external artifact storage with immutable references.
