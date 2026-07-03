# USD Scene Compiler Design

Status: Phase 0 product contract draft. This document is normative for the
v0.2 USD compiler direction, not evidence that a compiler is implemented.

The USD Scene Compiler turns structured scene instances and resolved assets into
the standard USD scene entry point for a package: `scene/main.usda`.

## Purpose

Scenario Forge should not require task generators to hand-write USD. Generators
produce structured scene instances, layout constraints, robot spawn information,
and asset requirements. The compiler translates that portable contract into a
simulator-friendly USD reference stage.

The source of task semantics remains YAML or JSON schema. USD is the scene
transport format, not the only truth source.

## Inputs

Required inputs:

- `scene/instances.yaml`;
- `locks/asset_lock.yaml`;
- `assets/asset_manifest.yaml`;
- `robot/robot.yaml`;
- package root and output path.

Optional inputs:

- `scene/layout.yaml`;
- task predicates for binding checks;
- metrics for success binding checks;
- camera and lighting presets.

## Scene Instances

`scene/instances.yaml` should describe package-level scene semantics:

```yaml
schema_version: scene-instances/v0.2
coordinate_system:
  units: meters
  up_axis: Z
instances:
  - id: sample_bottle_001
    asset_id: sample_bottle_50ml_v1
    role: manipulated_object
    pose:
      xyz: [0.45, 0.0, 0.92]
      wxyz: [1.0, 0.0, 0.0, 0.0]
    semantic_tags:
      - bottle
      - pickable
      - container
    initial_state:
      upright: true
      contains_liquid: false
```

Instance IDs must be unique within the package. Task predicates must bind to
instance IDs, not asset IDs.

## Output

`scene/main.usda` should include:

- root Xform;
- meters and up-axis metadata;
- one prim per scene instance;
- references to locked asset USD files;
- pose transforms;
- custom metadata for instance ID, asset ID, role, and semantic tags;
- robot spawn metadata or prim reference;
- basic lights;
- optional cameras;
- optional physics scene metadata.

The first compiler implementation may write a conservative USDA reference stage.
It must not depend on Isaac, Omniverse, CUDA, Habitat, ManiSkill, OmniGibson, or
other simulator SDK imports in pure package layers.

## Validation

The compiler must report structured blockers for:

- unresolved `asset_id`;
- missing referenced USD file;
- USD reference outside package root without a lock entry;
- duplicate instance ID;
- predicate reference to missing instance;
- pickable object without collision metadata;
- manipulated object without physics profile;
- robot spawn missing or outside declared workspace;
- layout constraints that cannot be satisfied by the generated instance poses.

Static USD validation should confirm that `scene/main.usda` exists and that all
declared asset references are resolver-managed. Runtime load, reset, and physics
smoke tests belong to adapter or downstream runtime checks.

## Boundaries

The compiler may generate USD reference stages and metadata. It must not:

- reimplement ConvertAsset conversion logic;
- repair meshes, MDL materials, or texture packages;
- import simulator SDKs in pure package layers;
- decide model evaluation success;
- mutate adapter outputs into the portable manifest.

ConvertAsset remains responsible for USD/MDL/mesh/GLB conversion and normalized
asset packages. Simulator-specific scene exports remain under
`adapters/<simulator>/`.

## Phase 0 Decisions

- `scene/main.usda` is the v0.2 scene entry point.
- `scene/instances.yaml` is the portable scene instance source.
- USD references must be generated from asset resolver results.
- Task predicates bind to scene instance IDs.
- USD existence is not proof of runtime executability.

## Future Work

- `scene/instances.yaml` JSON Schema.
- Static USDA writer for reference stages.
- USD reference validation without simulator SDK imports.
- Predicate-to-instance binding checks.
- Optional parser checks isolated from pure package layers.
- Runtime smoke validation through adapters or downstream runtimes.
