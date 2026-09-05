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

## Generated-output retention

The current local task heads are declared in
`configs/artifact_retention/current_task_heads.v1.json`. A head is keyed by
task family and variant, not by the numerically largest release suffix. Distinct
VR/eBench, liquid-fill, layout, and validation-evidence variants may therefore
have separate heads.

For each declared head, retain both the complete generated directory and its
canonical handoff ZIP. Classify every other generated directory explicitly as
one of:

- `KEEP_HEAD`: current deliverable for one task/variant;
- `KEEP_SOURCE`: active source binding or current-head build dependency;
- `ARCHIVE_SUPERSEDED`: replaced by a named head;
- `ARCHIVE_DIAGNOSTIC`: valuable but inactive diagnostic evidence;
- `DELETE_REBUILDABLE`: cache or mechanically reproducible scratch data;
- `HOLD`: unresolved; never archive or delete automatically.

OSS archival is additive and immutable. Uploads use a project-owned
`artifact-history-v1/<family>/<variant>/<revision>/<batch>/` namespace, retain
per-file and tree hashes, run a restore sample, and pass repository validation
before local quarantine is removed. Source material under
`external_artifacts/incoming`, Git history, and ambiguous worktrees are outside
this generated-output policy.
