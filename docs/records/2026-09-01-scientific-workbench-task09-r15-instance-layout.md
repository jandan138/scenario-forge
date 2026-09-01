# Scientific Workbench Task 09 r15 Instance layout

Task 09 r15 preserves the r14 scene and mechanics while adopting the global
articulated-object path contract. The placement root remains
`/World/obj_oven`; all oven-owned content is materialized below the non-Xform
Scope `/World/obj_oven/Instance`. VR therefore exposes links below
`/World/_scene/obj_oven/Instance` without changing `obj_prim_list`.

ConvertAsset qualifies all nineteen links, valid joint targets, both physical
knobs, press actions, controller state and the 60-degree door under canonical,
arbitrary-prefix and VR namespaces. Scenario Forge validates the final scene,
static Play, dependency closure and four fixed views. The r14 and r15 renders
are visually indistinguishable in the reviewed views.

The final handoff is
`outputs/scientific_workbench_task09_r15_20260901/handoff/scientific_workbench_task09_r15_vr.zip`.
Robot-policy and benchmark success remain outside the claim.
