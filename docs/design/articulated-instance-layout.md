# Articulated Instance Layout

## Canonical v2 layout

Every newly generated articulated-object scenario package uses this hierarchy:

```text
<existing-prefix>/<obj_root>                         # placement Xform + Articulation Root
└── Instance                                         # identity Xform
    ├── Body                                         # non-kinematic rigid base link
    ├── <other rigid links>                          # non-kinematic
    └── Joints
        └── BaseFixed                                # obj_root -> Instance/Body
```

The existing prefix and `obj_*` placement root remain unchanged. The object root
owns placement, GUI transform, uniform asset scale, and scene randomization.
`Instance` must be an identity `Xform`; no placement transform may be authored on
it or on individual links.

The `obj_*` root must have `PhysicsArticulationRootAPI` and an enabled PhysX
articulation. Every `RigidBodyAPI` link must remain below `Instance` and be
non-kinematic. `Instance/Joints/BaseFixed` connects body0 at the object root to
body1 at `Instance/Body`. All other internal joint body targets stay below
`Instance`.

## VR registration and randomization

VR `task_config.py:obj_prim_list` registers both the runtime object root and every
rigid link, in deterministic USD traversal order:

```text
/World/_scene/obj_device
/World/_scene/obj_device/Instance/Body
/World/_scene/obj_device/Instance/<link>...
```

Joints, visual meshes, material prims, and collider children are not links and
are not registered separately. Registration does not grant transform ownership:
only `obj_device` appears in `layout_randomization`. Links follow the articulation
root and must never be randomized independently. A support cart and its device
may share one root-level randomization group; their child links still do not.

## Ownership and admission

ConvertAsset owns the producer facade and fixed-base physics authoring. It
materializes the complete subtree under `Instance`, preserves existing link,
joint, control, and runtime-graph paths, and qualifies canonical, arbitrary-prefix,
and VR `_scene` mounts. Scenario Forge consumes the promoted package, expands the
VR registration list, and validates the final scene. It never adds an articulation
root, toggles kinematic state, adds a fixed joint, or repairs asset physics.

The v2 validator blocks a missing or disabled articulation root, a Scope or
non-identity `Instance`, missing/kinematic links, an invalid `BaseFixed`, and
internal joint targets outside `Instance`.

## Legacy boundary

The former v1 layout used a `Scope` and could retain a kinematic chassis. It is a
legacy compatibility shape for immutable historical outputs only. New exports
must not reuse it. A legacy asset must receive a new ConvertAsset revision before
entering a newly generated VR or eBench task package.
