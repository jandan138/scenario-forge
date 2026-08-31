# IKA OVEN 125 interactive v3 relocatability diagnosis

## Outcome

The incoming `ika_oven_125_interactive_v3.7z` is a strong standalone producer
asset, but it is not yet a relocatable articulated-object input for Scenario
Forge.  The attempted consumer-side coordinate workaround was rejected.  The
asset must first pass a ConvertAsset-owned relocatable-articulation admission.

The source archive and primary USD remain unchanged:

- archive SHA-256:
  `c3549ad1ed967e79b5ec3612e04da1acb70479d6528a8a0b144ad93acf379de1`
- primary USD SHA-256:
  `8bbd61f9d987a38fc582d218d01c33dd23cfe006ebaa4a1776b18b6b6d63e310`
- source entry: `/World/Oven125`

## Reproduced blockers

The source has 16 joints: 3 revolute, 11 prismatic and 2 fixed.  Only one joint
authors `physics:body0`; the other 15 use a world anchor plus `body1`.  This is
valid when the standalone asset stays at the producer world origin, but is not
portable under a consumer root transform.

When the oven wrapper was placed on the standard workbench at `z = 0.755 m` in
Isaac Sim 4.1:

- PhysX reported disjoint body transforms for the door, ten buttons, rocker,
  knob press carrier and both shelf fixed joints;
- the lower shelf snapped to another height;
- the empty SDF beaker and conical flask both dropped by approximately
  `0.128 m`;
- the inline Controller ScriptNode repeatedly queried rigid bodies under the
  missing hard-coded namespace `/World/Oven125` after the consumer had mounted
  the asset at `/World/obj_oven`.

The controller source contains one root constant:

```python
ROOT = "/World/Oven125"
```

All downstream button, knob, light and page paths are derived from that value.
The Graph therefore also needs instance-relative root discovery; fixing only
the joints would not restore functional parity.

## Rejected workaround

Keeping the oven at the producer world origin and shifting the table, neutral
floor, vessels and robot down by `0.755 m` removed the disjoint-joint warnings.
In that diagnostic only, both vessels retained the lower shelf for 300 frames:

- beaker horizontal drift: `1.34e-7 m`; vertical settling: `0.0009998 m`;
- conical flask horizontal drift: `5.69e-7 m`; vertical settling:
  `0.0009972 m`.

This proved the attribution, but it is not an acceptable product design.  It
would break the shared table/robot/world coordinate contract and would still
leave the OmniGraph namespace hard-coded.  No handoff ZIP was promoted from
this experiment.

## Required producer boundary

ConvertAsset owns the next step:

1. preserve the original archive and USD byte-for-byte;
2. emit an identity-root source-bound facade with a relocatable mount body;
3. convert world-anchored joints into mount-local body0/body1 relationships;
4. make the inline ScriptNode derive its root from its own OmniGraph node path;
5. prove independent controller state under `/World/Oven125`,
   `/World/obj_oven`, and `/World/_scene/obj_oven` in Isaac Sim 4.1;
6. prefer full functional parity, with an explicitly bounded Task 09 + Task 12
   subset package allowed only when failures are isolated to non-task UI
   branches.

Scenario Forge must consume the final package and manifest without adding
joint, controller, collider, world-origin, table-height or robot-pose patches.

## Final scoped delivery

Generic relocation was not promotable: the Isaac 4.1 non-articulation DriveAPI
stopped moving controls whenever the oven was parent-wrapped, translated,
renamed or mounted below a VR `_scene` prim.  The user-approved fallback was
therefore applied.

ConvertAsset promoted:

`/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/ika_oven_125_task0912_fixed_benchtop_r1_20260831/`

The package keeps `/World/Oven125`, bakes the 0.755 m standard-benchtop height,
and passes the producer's complete 12-branch physical-input/OmniGraph smoke in
Isaac Sim 4.1.  Its claim covers Task 09 + Task 12 in direct-stage mode only;
parent Xforms, rename, oven randomization and VR `_scene` mounting remain
forbidden.

Scenario Forge then added the standard table and empty liquid-ready SDF flask
and beaker directly to the same root layer.  The final composed scene also
passed the complete 12-branch smoke.  Handoff ZIP:

`outputs/ika_oven_125_task0912_direct_scene_r1_20260831/handoff/ika_oven_125_task0912_direct_scene_r1.zip`

ZIP SHA-256:

`807cead1fadbd30ef60761fc0eab68718033648a2a7905ef3072190124ea3fd4`

The ZIP includes a closed runnable `scene.usd`, a static 100-degree
`scene_open_preview.usd`, source-bound evidence, the final Isaac 4.1 report and
two review renders.  It is not a standard VR teleoperation package and claims
no robot-policy or benchmark success.
