# Hand off Scientific Workbench Task 05 / Task 09 r11

Give the receiving engineer this ZIP as one file:

`outputs/scientific_workbench_task05_task09_r11_20260817/handoff/scientific_workbench_task05_task09_r11.zip`

After extraction, keep each task directory intact.  Do not mix its `assets/`,
`deps/`, evidence, or configuration with another task.

## Task 05

- eBench USD and config: read the paths in
  `task05/remove_vessel_closure/ebench/package_manifest.json`;
- VR USD: `task05/remove_vessel_closure/vr/scene.usd`;
- VR config: `task05/remove_vessel_closure/vr/task_config.py`.

## Task 09

- eBench USD and config: read the paths in
  `task09/oven_load_start/ebench/package_manifest.json`;
- VR USD: `task09/oven_load_start/vr/scene.usd`;
- VR config: `task09/oven_load_start/vr/task_config.py`.

Use Isaac Sim 4.1.  The USD files do not embed the eBench robot; eBench or the
VR collection runtime inserts it from the corresponding config.  VR source USD
uses `/World` as defaultPrim and is mounted under `/World/_scene` only by the
runtime.

These packages are suitable for USD/config integration review and downstream
robot-policy work.  They do not yet claim a successful end-to-end robot task.
