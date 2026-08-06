# Producer-composed interactive scenes

Scenario Forge normally composes a scene from separately admitted assets. Some
interactive scenes cannot be safely decomposed without changing their physical
meaning. A PBD liquid scene is one example: particle owners, collision groups,
container colliders, materials and authored particle state form one coupled USD
composition.

`scenario-spec/v0.7` therefore adds a narrow generic contract:

- `scene.composition_mode: producer_entrypoint` selects a producer-owned scene
  entrypoint instead of reconstructing the scene.
- `objects[].instance_mode: embedded_scene_prim` registers semantic objects that
  already exist in that entrypoint. The compiler and adapters must not re-instance
  them or author pose, collider, rigid-body, mass or material overrides.
- The embedded object's `asset_id` must equal `scene.asset_id`.

The source binding remains outside the portable scenario recipe.
`scenario-source-bindings/v0.4` adds `producer_package` with usage
`interactive_composed_scene`. The current adapter admits a hash-bound LabUtopia
handoff only when native, GenManip and VR entrypoints are independently qualified,
the required hidden-cube overlay is applied, the closure is intact and the
license remains non-redistributable.

This does not turn Scenario Forge into a simulator or asset converter. The pure
package layer copies the admitted closure and records provenance. Target adapters
select their named producer entrypoint. GenManip receives the 600 Hz entrypoint;
VR receives the 60 Hz entrypoint. Either adapter registers existing object paths
and never patches producer physics.

Runtime qualification is transport evidence only. Robot grasp, release, liquid
transfer, policy success and benchmark success require separate evaluators and
must not be inferred from scene qualification.
