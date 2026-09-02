# Scientific Workbench Task 12 dual-glassware oven unload

The Task 09 r14 visual station was reused through the later r15 articulated
layout, so the oven keeps the required `/World/obj_oven/Instance/...` subtree.
The new Task 12 variant starts after heating has completed and asks the operator
to remove an empty SDF beaker and conical flask, place both on the main table,
close the door, and switch off the oven.

The static oven cart keeps its original XY footprint and uses Z scale `0.7`.
Its top is therefore at `0.5285 m`, and the unscaled oven root is translated to
the same height. Both vessels start 1 mm above the actual `Shelf_0` collision
proxy, not above the taller decorative front lip. Isaac Sim 4.1 measured about
1 mm of settling and no lateral drift for either vessel.

The initial control state is mains on, setpoint and actual temperature 65 C,
heating disabled, operating state `complete`, and chamber light enabled. The
Isaac Sim 4.1 device smoke opened the door to 60 degrees, returned it to within
0.04 degrees of closed, and used the physical mains-rocker drive to reach the
`off` state; the chamber light also turned off. This is device-level evidence,
not a robot-policy or benchmark-success claim.

The final evidence contains a closed station overview, a completed-panel close
view, and two open-door views showing both vessels on the lower shelf. Package
dependencies are copied under `deps/`; finalization rejects unresolved or
absolute external assets.
