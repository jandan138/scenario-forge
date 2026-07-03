# Adapter Boundaries

Adapters translate portable packages into simulator or tool-specific artifacts.

Rules:

- Adapters consume portable packages; they do not mutate `manifest.yaml` in place.
- Adapters report blockers as structured issues.
- Heavy imports stay lazy or out-of-process.
- Optional simulator dependencies must not be required for `scenario-forge package check`.

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
