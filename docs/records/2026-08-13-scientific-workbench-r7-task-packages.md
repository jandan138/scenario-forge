# Scientific Workbench r7 task packages

Scenario Forge r7 publishes seven immutable package variants for Feishu tasks
2, 7, and 8. The task and metric assets come only from `实验室资产库.zip`;
backgrounds, the eBench robot, the standard 2000 × 800 × 755 mm table, and
non-scored dressing remain separately admitted inputs.

- Task 2: one modern-wet-chemistry package using the 250 mL graduated cylinder
  and 325 mL beaker. It is a prototype with score ceiling 0.60 because no liquid
  contained-volume evaluator is qualified.
- Task 7: five background variants using the 325 mL beaker and 300 mm glass rod.
  Example4, teaching-research, and bioclean each add one source-scale aluminum
  rack populated at authoritative medium sockets 1, 3, and 6. Modern wet
  chemistry and analytical instrumentation intentionally add no rack.
- Task 8: one bioclean package with exactly one rack. Socket 3 contains the open
  task tube, sockets 1 and 6 contain closed context tubes, and the task cap is
  separate on the table. Context objects have no metric or VR-object-list role.
  The 0.70 ceiling records the missing threaded-closure interaction.

All seven packages pass portable package closure, the scientific tabletop
placement policy, eBench export, VR export, and Isaac Sim 4.1 initial-scene
rendering at 1920 × 1080 across seven views. R7 deliberately records IK as
`not_run`; it does not modify EOS/GenManip or claim reachability, robot policy,
liquid transfer, threaded closure, or benchmark success.

Primary artifacts:

- `outputs/scientific_workbench_asset_expansion_20260813_r7_full/manifest.yaml`
- `outputs/scientific_workbench_usd_handoff_r7_20260813/scientific_workbench_tasks_02_07_08_r7_20260813.zip`
- `docs/task-directory/index.html`
