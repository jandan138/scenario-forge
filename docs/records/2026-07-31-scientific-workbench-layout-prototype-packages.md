# 2026-07-31 Scientific Workbench Layout Prototype Packages

## Decision

Compile Feishu Task Design rows 2, 13, and 16 as
`layout_validated_prototype` packages using the Code-as-Room center environment,
the eBench worktable, and source-bound ConvertAsset rigid-object packages.
Keep row 6 blocked until a source-identifiable magnetic stirrer exists.

The authoritative source snapshot is
`configs/task_catalogs/scientific_workbench_phase1.yaml`, pinned to document
revision 1576 and sheet revision 564.

## Asset selection

The user authorized the task archive assets for public redistribution under
`LicenseRef-Team-Owned-Public-Redistribution` on 2026-07-31. The source archive
is:

```text
external_artifacts/incoming/valid_with_json_by_final_category_usd.zip
SHA-256 89f7248e223588fe0a584bdb5033b3b30ff4e055227ec1f40fa03d2531d0f5ea
```

Selected archive members:

- `beaker/data_buy_BCI762450811977342-6.usd`;
- `funnel/data_buy_EEG3939408195047-3.usd`.

The canonical graduated cylinder and conical flask are identity-entry facades
over the previously qualified LabUtopia source-bound packages. Scenario Forge
does not add object-specific scale, collider, mass, inertia, or PhysX-warning
suppression.

The producer-side facade/profile implementation and source-bound task-object
records are committed and pushed in ConvertAsset `main@db71fde`.

The archive's two magnetic-stirrer-labelled candidates were rejected by visual
identity review. One is a scale; the other is a stand-mounted heating apparatus.
This is an honest asset blocker, not an admission waiver.

## Contract changes

`scenario-spec/v0.6` transports the v0.5 general predicate set together with a
progress rubric and adds rubric conditions for relative pose, return-to-initial
pose, and configured motion trajectories. Derived artifacts are `task/v0.5`,
`metrics/v0.4`, and
`scenario-forge-genmanip-runtime-contract/v0.6`.

ConvertAsset interaction profiles v1 and v2 are both accepted. v2 allows a
producer to declare the exact named frames required by a non-vessel object,
instead of forcing every object to pretend that it has vessel opening, grasp,
and support semantics.

## Generated packages

Output root:

```text
outputs/scientific_workbench_layout_validated_prototypes_20260731/
```

Completed:

- `scientific_workbench_pour_cylinder_to_beaker`, active ceiling 0.60;
- `scientific_workbench_funnel_pour_cylinder_to_flask`, active ceiling 0.60;
- `scientific_workbench_two_sample_mix`, active ceiling 0.70.

All liquid-transfer items are retained with `active: false`,
`normalization: declared_sum`, and `inactive_treatment: zero`.

## Validation and evidence

The three portable packages pass the package checker, and their GenManip
collected-package exports contain the v0.6 semantic runtime contract. Isaac 4.1
authored-state previews are stored under:

```text
<scenario-id>/adapters/ebench/genmanip/evidence/authored_key_states/
```

Ten authored states render successfully. Every render manifest is hash-current,
reports `stage_meters_per_unit: 1.0`,
`authored_static_physics_disabled: true`, and contains non-black-frame
luminance evidence. The camera packet contains one task-object close-up and two
room/table overview views.

A local human-style visual review used only the rendered contact sheets and task
expectations; it was not an independently delegated review. Verdicts:

| Task | Verdict | Visible evidence |
|---|---|---|
| Row 2 cylinder-to-beaker | PASS | both vessels are identifiable at realistic tabletop scale; the authored tilted opening projects over the beaker; overview views retain the full centered table |
| Row 13 funnel pour | PASS | funnel, graduated cylinder, and conical flask are distinct; insertion and pour-alignment states are visible in close-up; the complete room remains visible |
| Row 16 two-sample mix | PASS | both source vessels and the beaker are distinct; both alignment states and the lifted shake pose are visible; no room-scale or support-placement anomaly is visible |

Minor ray-tracing noise on transparent vessels is visible in some overview
views but does not prevent object identification or layout review.

The runtime USD/USDA/MDL files in all three packages were scanned for `/cpfs/`
and `file://` references; none were found. Producer evidence manifests retain
absolute machine paths as provenance records, but those strings are not runtime
asset dependencies.

Repository verification:

```text
make check
531 passed; ruff, package smoke, Phase 10.x strict smoke, and diff check passed

scripts/validate_package.py <package>
Package OK (all three packages)
```

The evidence is deliberately labelled `execution_status: not_executed`. It is
not evidence of robot reachability, collision-free paths, physical pouring,
liquid transfer, policy success, benchmark success, or task completion.
