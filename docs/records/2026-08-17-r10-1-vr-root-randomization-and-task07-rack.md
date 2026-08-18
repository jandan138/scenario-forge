# r10.1 VR root, tabletop randomization, and Task 07 rack

Date: 2026-08-17

## Outcome

The coordinated Task 02/07/08 r10.1 release contains ten independent dual-consumer
packages: four Task 02 liquid levels, five Task 07 backgrounds, and one Task 08
background. Each package has an eBench export and a VR export.

The VR source contract now has `/World` as `defaultPrim`, with no authored
`/World/_scene`. The loader owns that runtime mount. The source has direct
`background`, `table`, `obj_*`, and `vr_direct_open_light` children. The light is
a texture-free white DomeLight at intensity 750 and exposure 0, so the USD remains
visible when opened directly without adding an environment map dependency.

Every tabletop task object and context prop is named `obj_*`, appears exactly once
in `obj_prim_list`, and participates in local XY randomization of ±0.01 m with yaw
fixed to zero. The room, table, and light are excluded. PBD particles are excluded
from the object list but move in the same randomization group as their source
graduated cylinder. Rack populations are grouped so their relative placement is
preserved.

## Task 07 change

Task 07 now starts with the 300 mm glass rod inserted into the middle 14 mm hole
of the qualified transparent acrylic rack. The semantic sequence is: hold the
beaker, take the rod from that hole, stir at least one accumulated revolution,
return it to the same hole, release the rod, and release the beaker.

ConvertAsset owns the source-bound fixture package and collision/insertion
qualification. Scenario Forge only consumes its asset, named frames, and manifest;
it does not add a rack-specific collider or physics patch.

## Evidence

- All ten VR exports passed the Isaac Sim 4.1 direct-open smoke, including root,
  light, `obj_prim_list`, and randomization checks.
- All six newly compiled Task 07/08 eBench packages passed reset plus 960
  zero-action steps and the initial-scene geometry/visual gate.
- The four Task 02 packages retain their prior visual and product-smoke evidence.
- Human-style review of all Task 07/08 overview renders found no scale, placement,
  room-fit, robot/table intersection, or floating-object blocker. The transparent
  acrylic rack is intentionally subtle. The small red Task 08 cap was confirmed
  tabletop-supported in the close-up.

## Task-directory publication

The public task directory now has an explicit `r10.1 · 玻璃棒架` view. Task 07
uses the `teaching_research` task-object close-up as its card image so the glass
rod, transparent rack, beaker, and both robot arms remain legible at card size.
The variant disclosure retains the room-overview evidence for all five r10.1
backgrounds: teaching research, modern wet chemistry, bioclean, analytical
instrumentation, and example4.

The site still defaults globally to r11. Because Task 07 has no r11 package, its
r11 card says that it is displaying the latest valid r10.1 candidate. This is a
display fallback only and does not promote the package or add robot-success
evidence.

## Claim boundary

This release proves portable package closure and the attached initial-state,
zero-action, and direct-open checks. It does not add a robot oracle, policy success,
task completion rate, liquid metric, headset/controller launch, or benchmark claim.
