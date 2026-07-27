# Workspace profile-3 candidate 067 validation (2026-07-26)

> Historical profile-3 validation. ConvertAsset subsequently supplied
> profile-4, which marks 067 `not_applicable` after measuring every
> rule-compliant placement option. See
> `docs/records/2026-07-27-workspace-profile-4-067-closure.md` for closure.

Scenario Forge regenerated only `scientific_environment_067` after consuming
the ConvertAsset profile-3 sidecar from producer revision
`2026-07-26-workspace-integration-profile-3`
(`53bc8ebcd49770a171ea308c94243c108fe3d22b`). The profile selects the
north-wall fume-hood pair `/World/group_223` and `/World/group_225`, maps the
source-composed anchor with `2.676258376688719e-05` metres per source unit, and
keeps the fixed eBench workspace unchanged.

The regenerated package is structurally valid:

- `scenario_forge.cli package check --require-asset-lock`: passed;
- GenManip `visual_ready_gate.yaml`: passed;
- Isaac Sim 4.1 render evidence: passed at the runtime/required-prim level;
- workspace closeup: visually passes and shows the unchanged table, robot, and
  both vessels.

The strict combined-overview gate does **not** pass. In
`adapters/ebench/genmanip/evidence/initial_scene/scene_overview.png`, the
profile-3 north-wall geometry remains a large foreground occluder. The fixed
table, robot, and two vessels cannot be read together with the laboratory
context. This is a source/profile placement problem, not a GenManip runtime
failure and not a reason to add a local collider, hide list, or camera hack.

Evidence:

```text
outputs/scientific_workbench_workspace_profiled_variants_20260726/
  scientific_environment_067/adapters/ebench/genmanip/evidence/initial_scene/
    scene_overview.png
    workspace_closeup.png
    render_manifest.json
    visual_ready_gate.yaml
```

The generated manifest records the exact profile path, source hash, anchor,
inactive roots, and producer commit. No source USD/MDL, ConvertAsset package,
eBench table, robot/task pose, or GenManip checkout was modified.

## Decision

Keep candidate 067 as a structural and closeup-only diagnostic. Do not call it
a visually accepted room/workspace variant. Ask ConvertAsset to either mark
067 `not_applicable` for this fixed-workspace integration or deliver a new
source-bound profile whose replacement/anchor leaves a clear line of sight to
the unchanged eBench workcell (with the complete occluding assembly roots
identified and a source-side before/after render). Scenario Forge should then
consume that profile without adding candidate-specific physics or occlusion
workarounds.
