# Articulated Instance Layout

Every newly generated scenario package must mount an articulated object's
complete device subtree at:

`<existing-prefix>/<obj_root>/Instance/<device-relative-path>`.

The prefix and `obj_*` placement root remain unchanged. `Instance` is a
case-sensitive `UsdGeomScope`, not an Xform: a new Xform layer can disable
non-articulation DriveAPI controls even when its matrix is identity. Placement,
randomization and GUI scale stay on the `obj_*` root.

ConvertAsset owns the producer facade. It materializes the complete subtree
under `Instance`, retargets joints and runtime paths, and qualifies controls
under canonical, arbitrary-prefix and VR `_scene` namespaces. Scenario Forge
never repairs a legacy articulated hierarchy. Its final-scene validator requires
every RigidBodyAPI link and every internal joint body target to remain under
`Instance`; violations block package generation.

Historical packages are immutable. A future scenario that needs a legacy
articulated asset must first consume a new ConvertAsset Instance revision.
