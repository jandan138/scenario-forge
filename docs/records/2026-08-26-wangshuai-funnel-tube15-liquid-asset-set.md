# Wangshuai funnel/tube liquid-interactive asset directory

Scenario Forge imports the four promoted, exact-source ConvertAsset packages
into:

`outputs/scientific_workbench_funnel_tube15_liquid_asset_set_20260826/`

The pinned source is
`external_artifacts/incoming/from_wangshuai/lixinguan_funnel_liquid.usd`.

The directory contains the threaded 15 mL tube body, threaded closed cap,
small-v2 funnel, and a separate 1,948-particle liquid overlay. The three instrument
packages do not contain liquid. The overlay contains liquid but no PhysicsScene;
consumers provide one GPU scene.

The import copies each producer package byte-for-byte, verifies identity
defaultPrims and package-local USD/MDL dependencies, and retains the producer
source/runtime evidence. No Scenario Forge collider, SDF, mass, offset, material
parameter, or warning patch is authored.

Source and three recomposed Isaac Sim 4.1 runs all captured `1948/1948`
particles in the tube after 16 seconds with zero below-floor leaks. The source
and recomposition also match at eight seconds (`84.856%`), demonstrating that
the longer qualification window reflects the original `0.1 m/s` velocity cap
rather than consumer tuning.

Liquid and collision numbers for this threaded tube/funnel pair are recorded in
ConvertAsset `docs/operations/wangshuai-threaded-tube-funnel-pbd.md`.
Do not substitute `scientific_workbench_small_gpu_pbd_v2`. Authored overlay
values are `maxVelocity=0.1`, `particleContactOffset=0.002`, `restOffset=0.002`,
1948 frozen points, widths `0.002376 m`. The funnel and tube roots stay
kinematic; the consumer supplies one GPU PhysicsScene at 120 Hz TGS.

This is a directory-only delivery by user choice. It contains no complete-set
ZIP and no public demo scene. Robot, cap-tightening task, policy, and benchmark
success remain false. A separately requested funnel-only ZIP remains available
from the ConvertAsset output.
