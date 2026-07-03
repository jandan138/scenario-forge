# Adapter Boundaries

Adapters translate portable packages into simulator or tool-specific artifacts.

Rules:

- Adapters consume portable packages; they do not mutate `manifest.yaml` in place.
- Adapters report blockers as structured issues.
- Heavy imports stay lazy or out-of-process.
- Optional simulator dependencies must not be required for `scenario-forge package check`.

## External Pipeline Integrations

LabBuilder-style and SimFoundry-style systems are external capability sources,
not Scenario Forge core dependencies.

Rules:

- LabBuilder-style integrations may produce protocol, required asset, layout,
  safety, and validation hints. They must enter Scenario Forge through
  `generation_plan.yaml`, `scene/layout.yaml`, `scene/instances.yaml`,
  `evidence/layout_checks.yaml`, `evidence/static_checks.yaml`, and provenance
  records.
- SimFoundry-style integrations may produce reconstructed assets, scene/object
  poses, physics metadata, task-cousin proposals, validation evidence, and source
  provenance. They must enter Scenario Forge through a real-to-sim importer under
  `src/scenario_forge/adapters/real2sim/`.
- External pipeline outputs must be normalized into Scenario Forge schemas before
  they appear in `manifest.yaml`; bespoke upstream pipeline schemas must not
  become package identity.
- External assets must go through `assets/asset_manifest.yaml` and
  `locks/asset_lock.yaml`. No adapter may bypass license, checksum, or provenance
  checks.
- Pipeline identity, versions, prompts, source media references, and model/tool
  versions belong in `locks/generator_lock.yaml`,
  `provenance/source_refs.yaml`, `provenance/generation_trace.jsonl`, or
  `evidence/*`, not in top-level package naming.
- Heavy reconstruction, simulator import, VLM/model calls, navigation evaluation,
  rollout collection, and benchmark reporting remain outside pure package layers.

Adoption gate:

1. Use a deterministic Scenario Forge baseline first.
2. Add an optional importer/adapter for an external pipeline only after its
   artifact contract, license terms, and dependency boundary are clear.
3. Compare external output against the baseline on package validity, asset-lock
   coverage, task predicate binding, reachability, collision/safety checks, and
   EBench adapter readiness.
4. Promote the external pipeline from reference to supported adapter only when it
   improves those checks without weakening portability.

## ConvertAsset

ConvertAsset integration uses command plans for its public CLI.

Preferred high-level path:

```text
ConvertAsset/scripts/isaac_python.sh ConvertAsset/main.py normalize-asset <source.usd> --package-dir <out>
```

Low-level commands such as `no-mdl`, `mesh-faces`, and `usd-to-glb` remain ConvertAsset-owned.

## Isaac

The planned Isaac adapter will write:

```text
adapters/isaac/scene.usd
adapters/isaac/run_config.yaml
```

It must keep `pxr` and `omni.*` imports out of pure package layers.
