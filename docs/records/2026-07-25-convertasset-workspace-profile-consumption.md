# ConvertAsset workspace-profile consumption (2026-07-25)

ConvertAsset delivered source-bound workspace integration profiles under
`outputs/scientific_workbench_workspace_profiles_20260724/`. Scenario Forge
consumes them only as visual composition metadata: no source USD, MDL, mesh,
collider, rigid-body, mass/inertia, PhysX, or GenManip code is modified.

The profile source hashes and `/World` scopes match the batch-admission YAML,
the admitted package manifests, and the local source USDs. ConvertAsset
profile-2 (`main@47d64148f7f5f4cc585ca0b43fb450eb21c6fda5`) has supplied the
machine-readable coordinate mapping for the four new integrations. Scenario
Forge consumed that sidecar and generated the five integrated packages under
`outputs/scientific_workbench_workspace_profiled_variants_20260726/`.

| Candidate | Required inactive source roots |
| --- | --- |
| 059 | `/World/group_063`, `064`, `073`, `241` |
| 066 | `/World/group_111` |
| 067 | `/World/group_205`, `206` |
| 083 | `/World/group_025`, `026`, `027` |
| 084 | existing separately reviewed Scenario Forge anchor `/World/group_078` |

`081` and `085` remain explicitly excluded. The profile explains that either
case would require anonymous loose-mesh masking or an undersized source island;
Scenario Forge does not substitute an envelope-centred placement for those
results.

## Coordinate adaptation correction

The first consumer implementation treated profile `anchor_xyz_m` values as
source-composed coordinates convertible with the admitted package stage
`meters_per_unit`. A real post-reset GenManip render of `066` disproved that
assumption.

`066` declares an approximately 19.15 source-units-per-metre workcell scale in
its human-readable note, while the source USD stage declares
`metersPerUnit = 0.001`. Applying the latter and the generic 4 m minimum
visual-envelope fit shrank the profile's source clearance
`46.90 x 52.66 x 58.58` to only about `0.210 x 0.235 x 0.262 m`; it could not
possibly contain the fixed `2.45 x 2.75 m` eBench workbench. The retained room
shell then crossed the workcell and obscured the overview image.

Scenario Forge now rejects a `profiled` profile unless it supplies this
machine-readable contract:

```yaml
coordinate_mapping:
  frame: source_composed
  source_composed_meters_per_unit: <exact positive number>
```

The consumer maps raw source-composed anchors and bounds with this value and
sets `fit_factor = 1.0` for a workspace profile. Preserving this metric is
necessary: an arbitrary visual-envelope fit would scale the producer-audited
clearance and invalidate it. The existing field names `anchor_xyz_m` and
`clearance_aabb_m` are misleading for 059/066/067 because their supplied
numbers are source-composed units, not metres; ConvertAsset should correct
those names in its next schema revision, but an exact mapping sidecar is the
minimal unblocker. Profile-2 also corrected 067's bench-local scale from the
profile-1 estimate `31417` to `37365.6` source units per metre and regenerated
its anchor and clearance audit; the other three mappings were unchanged.

## Evidence boundary

The producer's source-side before/after images establish which complete source
assemblies were selected. Their framing is not sufficient to accept a final
eBench composition: image review found occlusion, overexposure, or incomplete
workspace framing in all four source-side previews.

The old 066 post-reset image remains rejected: its generic envelope fit shrank
the audited clearance. The new profile-mapped package preserves the workspace
metric and has a fresh post-reset render. Fresh renders are also available for
059, 067, 083, and 084; 067 required a reverse camera retake, while 083 is being
retaken with the room included in the overview camera anchors. The remaining
acceptance step is clean-room visual review plus the structural visual-ready
gate; none of these images claim task success, physics fidelity, or liquid
transfer.

## Provenance follow-up

The delivered profile YAML, index, and consumer manifest agree on ConvertAsset
`main@47d64148f7f5f4cc585ca0b43fb450eb21c6fda5`. Scenario Forge binds
consumption to that provenance and the verified source hashes; the remaining
uncertainty is visual framing, not asset ownership or coordinate provenance.
