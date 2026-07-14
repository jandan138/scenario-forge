# Scene Asset Overlays

`scenario-spec/v0.2` adds the optional `scene.overlay_asset_ids` field for
composing already prepared USD packages over one base environment:

```yaml
schema_version: scenario-spec/v0.2
scene:
  asset_id: scientific_workbench_environment
  root_prim_path: /World
  overlay_asset_ids:
    - scientific_workbench_dryingbox_03_dynamic
```

The list is ordered from strongest to weakest. Every overlay is stronger than
`scene.asset_id`, and every overlay must declare exactly the same
`root_prim_path` as the base scene. Overlays therefore contribute opinions to one
shared USD namespace; they are not independently placed scene instances. IDs must
be unique, must not repeat the base asset ID, and cannot simultaneously be used as
object-asset sources.

Scenario Forge's generated scene layer remains stronger than all referenced or
sublayered assets. Consequently, task-owned `scene.pose` and
`scene.inactive_prim_paths` opinions win over both overlays and the base. The
portable compiler and the GenManip adapter preserve this same strength contract,
even though one emits sublayers and the other emits references with local room
overrides.

This feature is a composition contract, not an asset-repair API. An inbound
adapter may validate an upstream package/manifest and map it to a Scenario
Forge-owned asset source. Conversion, material repair, and physics-profile
authoring remain upstream. The robot profile and injection contract are separate
from scene overlays; adding an overlay does not replace or modify the configured
EBench robot.
