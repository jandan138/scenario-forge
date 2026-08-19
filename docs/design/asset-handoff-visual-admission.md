# Asset handoff visual-admission modes

`scenario-forge-asset-handoff/v0.2` accepts either of two explicit visual
admission modes from an already admitted ConvertAsset package.

1. `visual_material_override`: the manifest contains a passing
   `aan.visual_material_profile.v2` result and the package contains a passing
   `evidence/visual_material_only_audit.json`.
2. `original_material_visual_preservation`: no visual material profile was
   requested and the ConvertAsset manifest contains a passing
   `visual_preservation_fingerprint`.

Both modes still require overall admission pass, no blocked reasons, and a
passing target-runtime result. The archive manifest records
`visual_admission_mode` and `visual_evidence` for every package; consumers do
not infer which route was used from a filename.

This contract lets Scenario Forge distribute a mix of explicit visual
overrides and producer-original SimReady materials without inventing USD/MDL
conversion logic. It does not promote the asset to a task-qualified object and
does not change any existing task package.
