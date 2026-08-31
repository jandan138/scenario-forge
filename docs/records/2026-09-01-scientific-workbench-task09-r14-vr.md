# Scientific Workbench Task 09 r14 VR

Final archive:

`outputs/scientific_workbench_task09_r14_20260831/handoff/scientific_workbench_task09_r14_vr.zip`

r14 uses the ConvertAsset materialized dual-knob oven. The new left knob is the
default temperature/start control; the original right knob remains functional.
Both knobs are physically independent and share logical state. The door uses
angular-drive damping 9 and a 60-degree upper limit.

`/World/obj_oven` and `/World/obj_oven_cart` remain independent roots. Both now
author Translate, Orient, and Scale so the standard Isaac property panel can
edit them directly. Supported scale is uniform XYZ from 0.85 to 1.15. To keep
the station assembled, apply the same scale and XY delta to both roots and set
`oven_z = cart_z + 0.755 * scale`.

The final scene passed Isaac Sim 4.1 static Play, dependency closure, four-view
rendering, and local visual QA. The accepted control-panel render shows the new
knob between the mains rocker and bezel without visible overlap. Physical
dual-knob, scale endpoint, and door-limit claims remain bound to the bundled
ConvertAsset receipt. Robot-policy and benchmark success are not claimed.
