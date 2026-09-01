# Long-neck threaded 15 mL tube asset readiness

## Outcome

Scenario Forge now registers the independently admitted long-neck tube body and
sealed cap from ConvertAsset. The bindings are in
`configs/source_bindings/scientific_workbench_tube15_long_neck_threaded_v1_20260901.yaml`.
The explicit readiness card is
`configs/asset_readiness/scientific_workbench_tube15_long_neck_threaded_v1_20260901.yaml`.

The two consumer assets are:

- `scientific_workbench_tube15_long_neck_threaded_body_v1`, rooted at
  `/World/Tube15LongNeckThreadedBody`;
- `scientific_workbench_tube15_long_neck_threaded_closed_cap_v1`, rooted at
  `/World/Tube15LongNeckThreadedClosedCap`.

Both bindings point directly to immutable ConvertAsset package entries. Scenario
Forge does not copy or modify their mesh, SDF collision, physics material, mass,
or inertia.

## Readiness boundary

Geometry, three-cold-start dynamic runtime, and SDF collision are ready. The
body and cap may therefore be placed independently as provisional rigid assets.

Thread interaction and Task 08 remain blocked. ConvertAsset observed thread
geometry and some rotation-coupled descent, but the two physical protocols did
not demonstrate stable reversible screw engagement. Liquid qualification was
not requested. The registry therefore forbids a thread-task claim and forbids
consumer-side physics overrides.

No scenario package, pre-closed assembly, robot rollout, or benchmark result is
created by this admission.

## Validation

`tests/test_long_neck_threaded_tube15_asset_admission.py` checks that:

- both bindings resolve as separate rigid USD assets;
- both entry roots are identity dynamic bodies with MassAPI;
- each package preserves exactly one SDF collider;
- producer manifests pass geometry/runtime while keeping thread readiness false;
- the readiness card blocks Task 08 and liquid claims.

```text
python -m pytest -q tests/test_long_neck_threaded_tube15_asset_admission.py
# 3 passed
```

## Follow-up

A later task revision may consume these objects only after ConvertAsset publishes
a thread-capable collider/contact revision and qualifies forward tightening plus
reverse loosening. Liquid containment, if needed, remains a separate admission.
