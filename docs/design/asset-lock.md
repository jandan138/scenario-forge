# Asset Lock Design

Status: Phase 1 local package scope implemented. This document remains normative for the
v0.2 asset reproducibility direction; registry, resolver cache, and suite dedupe remain future work.

Asset reproducibility is part of the package contract. Scenario Forge packages
must not depend on informal local paths or mutable registry state when they are
used as EBench export inputs or benchmark suite members.

## Concepts

- `asset_id` is a semantic identifier used by tasks and scene instances.
- `asset_digest` or `sha256` is the content identity.
- `asset_manifest.yaml` describes assets available inside a package.
- `asset_lock.yaml` records exactly how each external or materialized asset was
  resolved.
- Formal v0.2 packages always include `locks/asset_lock.yaml`.
- Fat packages materialize assets under `assets/` and still include a lock.
- Locked packages may keep assets external, but the lock must be sufficient to
  restore them from a registry, cache, or documented source.

## Required Asset Metadata

Each formal asset entry must include:

- `asset_id`;
- role or asset type;
- canonical USD path after resolution;
- license;
- content checksum;
- normalized status;
- provenance;
- physics readiness for interactive assets;
- EBench export eligibility.

Example:

```yaml
schema_version: asset-manifest/v0.2
assets:
  - asset_id: sample_bottle_50ml_v1
    role: manipulated_object
    asset_type: bottle
    canonical_usd: assets/objects/sample_bottle_50ml_v1/model.usd
    collision_usd: assets/objects/sample_bottle_50ml_v1/collision.usd
    license: CC-BY-4.0
    sha256: sha256:...
    normalized: true
    normalized_by: convert_asset
    affordances:
      - pickable
      - container
    physics:
      rigid_body: true
      mass_kg: 0.08
      collision: convex_decomposition
```

## Lock File

`locks/asset_lock.yaml` records resolver decisions and checksums:

```yaml
schema_version: asset-lock/v0.2
lock_id: workbench_pick_place_0001_asset_lock
created_by: scenario-forge
assets:
  sample_bottle_50ml_v1:
    source_kind: curated_registry
    source_uri: registry://scenario-forge/workbench_assets/sample_bottle_50ml/v1
    resolved_path: assets/objects/sample_bottle_50ml_v1/model.usd
    content_sha256: sha256:...
    metadata_sha256: sha256:...
    license: CC-BY-4.0
    normalized_package_sha256: sha256:...
    resolver_version: scenario-forge-asset-resolver/0.2.0
```

Rules:

- Package compilers should provide a stable `lock_id` derived from package
  identity, not from the output directory name. The low-level lock generator keeps
  the output-basename-derived ID only as a backwards-compatible default.
- Every locked asset must have a checksum.
- Every locked asset must have a license.
- External assets must include source URI, version or immutable digest, resolver
  version, and resolved package path.
- Package-local asset paths must stay inside the package root.
- USD scene references must point to package-local paths or resolver-managed
  paths recorded in the lock.
- EBench export should prefer fat packages. Locked packages require the EBench
  runner to have the same resolver or cache snapshot.

## Fat Package Rules

A fat package must satisfy:

- every USD reference in `scene/main.usda` resolves to an existing package-local
  file;
- materials, textures, collision files, and metadata referenced by assets exist;
- every `assets/asset_manifest.yaml` entry has local files;
- every `locks/asset_lock.yaml` checksum can be recomputed;
- every asset has a license;
- manipulated objects have physics profiles;
- pickable objects have collision metadata;
- simulator-specific asset exports remain under `adapters/<target>/`.

## Reconstructed And External Pipeline Assets

SimFoundry-style real-to-sim outputs and LabBuilder-style asset selections are
external inputs until Scenario Forge locks them.

Rules:

- Raw videos, scans, depth maps, Gaussian splats, reconstruction intermediates,
  and generated mesh dumps stay outside git and outside the portable package
  unless a tiny fixture is explicitly needed for tests.
- Reconstructed assets must record source media or dataset reference, upstream
  pipeline name/version, reconstruction method, normalization status, license or
  use restriction, checksum, and physics/collision readiness.
- Non-redistributable or research-only assets can be referenced only through a
  locked external source with explicit provenance; they must not be silently
  bundled into public fat packages.
- ConvertAsset remains the normalization boundary for USD/MDL/mesh/GLB closure.
  Scenario Forge may record command plans and outputs but must not reimplement
  conversion internals.
- Asset checks must fail closed when license, checksum, source URI, or package
  path evidence is missing.

## Resolver Boundary

Asset resolution belongs in `scenario_forge/assets`. The resolver may create
ConvertAsset command plans, but it must not import or reimplement ConvertAsset
USD, MDL, mesh, or GLB conversion logic.

The task and layout generators should request assets by `asset_id`, `asset_type`,
affordance, semantic tags, physics profile, license policy, and version
constraints. They should not directly construct filesystem paths.

## Validation

Phase 1 implements these checks:

- `scenario-forge assets lock <package>` reads `assets/asset_manifest.yaml` and writes
  `locks/asset_lock.yaml`;
- `scenario-forge assets check <package>` checks lock file shape, license, package-local paths,
  local asset existence, checksums, and package-local USD references. It also
  cross-checks each lock entry's canonical path, checksum, and license against the
  current asset manifest;
- `scenario-forge package check <package> --require-asset-lock` fails when the lock is missing or
  invalid;
- missing `asset_lock.yaml` fails when `--require-asset-lock` is set;
- checksum mismatch fails;
- license missing fails;
- unresolved package-local asset path fails;
- USD reference not present in the lock fails;
- assets outside the package root fail unless they are locked external assets;
- `not_run` asset checks cannot be reported as passed checks.

Phase 1 intentionally does not implement a hosted registry, external resolver cache,
content-addressed suite dedupe, or simulator runtime smoke checks.

## Artifact Policy

The repository should commit schemas, manifests, tiny fixtures, and evidence
reports. It should not commit raw USD asset trees, converted asset packages,
videos, rendered frames, depth arrays, or simulator dumps. Large assets belong in
external artifact storage with a checked-in index.

## Future Work

- Asset lock JSON Schema and Python helpers.
- Registry and resolver implementations.
- Content-addressed dedupe for suite-level asset stores.
- License policy validation.
- Physics metadata completeness checks.
- ConvertAsset normalization command planning from resolver output.
