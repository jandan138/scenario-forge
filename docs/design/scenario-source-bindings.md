# Scenario Source Bindings

`scenario-source-bindings/v0.1` is the local build-input contract between a
portable `ScenarioSpec` and the USD closures used to compile it. It keeps machine
paths and ConvertAsset delivery locations out of `scenario.yaml` while preserving
the asset IDs used by the scenario.

The dependency flow is:

```text
ScenarioSpec asset IDs + local source bindings
  -> LocalUSDAssetSource values
  -> portable scenario-package/v0.2
  -> optional GenManip collected-package export
```

The bindings file is an operational input, not package identity and not an asset
registry. It may contain absolute paths. Relative paths are resolved against the
directory containing the bindings file. Generated manifests and provenance retain
portable source URIs, upstream package identities, revisions, and content hashes;
they do not retain the local paths used for the build.

## Contract

The `bindings` keys are the asset IDs referenced by `scene.asset_id`,
`scene.overlay_asset_ids`, and object bindings in the ScenarioSpec. The first
version supports two resolvers.

`local_usd` maps one already usable USD closure directly into the neutral asset
source contract:

```yaml
schema_version: scenario-source-bindings/v0.1
bindings:
  scientific_workbench_environment:
    resolver: local_usd
    source_usd: ./lab_001/lab_001.usd
    role: environment
    license: CC-BY-NC-4.0
    source_uri: LabUtopia:lab_001_localized_20260707
    attribution:
      - "LabUtopia data assets: CC BY-NC 4.0"
    redistributable: false
    exclude_relative_paths: [_reports]
    root_prim_path: /World
    expected_sha256: sha256:...
```

`convert_asset_package` validates an existing source-bound ConvertAsset delivery
through the existing inbound adapter, then maps it to a scene-overlay source:

```yaml
  scientific_workbench_dryingbox_03_dynamic:
    resolver: convert_asset_package
    source_usd: ./lab_001/lab_001.usd
    package_dir: ./convert_asset_delivery/package
    manifest_path: ./convert_asset_delivery/manifest.json
    producer_revision: 324ce6e6d4395ccfda1e59e5ae89de9389cdf225
    expected_scope_prims: [/World/DryingBox_03]
    license: CC-BY-NC-4.0
    attribution:
      - Dynamic physics package normalized by ConvertAsset
    redistributable: false
    exclude_relative_paths: [evidence]
```

The resolver calls `load_convert_asset_package_handoff`; it does not convert USD,
author physics, copy ConvertAsset implementation code, or weaken the producer's
source/hash/runtime gates. A replacement calibrated profile is selected by changing
the external binding to a new delivery, not by changing the ScenarioSpec.

## Compile command

```bash
scenario-forge package compile \
  --spec examples/scientific_workbench/bimanual_pour/scenario.yaml \
  --source-bindings /path/to/source_bindings.yaml \
  --out /tmp/scientific_workbench_bimanual_pour \
  --export-genmanip
```

`--export-genmanip` is explicit and optional. The command is a static compiler: it
does not start Isaac Sim, render previews, execute an oracle, or run an episode.
Those operations stay in the existing preview workflow and downstream EOS/GenManip.

The compiler derives `asset_lock.yaml` identity from `scenario_id`, so identical
specs, bindings, and unchanged source closures produce identical package contents
even when compiled under different output directory names. The standalone
`generate_asset_lock` API keeps its historical output-basename default unless a
caller supplies a stable `lock_id`.
