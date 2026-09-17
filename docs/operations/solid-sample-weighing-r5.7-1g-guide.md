# 固体样品称量：r5.7 场景 + 1 g 过程分

权威合同是 [scenario.yaml](../../examples/scientific_workbench/solid_sample_weighing/scenario.yaml)。当前合格粉末交付头仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。本包指定 VR / 智能体用 r5.7 USD，分数看去皮后终帧 LCD `1.00 g`。

总交付 ZIP（r4 同形，含本任务合同）在
`outputs/task09_powder_bottle_r5_7_20260915/handoff/task09_powder_bottle_r5_7.zip`。
解压后读 `task/scenario.yaml`；`task/source_bindings.yaml` 的 `source_usd` 是同包 `../scene.usda`。校验和见旁路 `.zip.sha256`。

## 编译任务包

把 r5.7 `scene.usda` 当作 `task09_powder_bottle_r5_7` 的 producer entrypoint，用仓库编译器写出 v0.2 包：

```bash
PYTHONPATH=src python -m scenario_forge.cli package compile \
  --spec examples/scientific_workbench/solid_sample_weighing/scenario.yaml \
  --source-bindings examples/scientific_workbench/solid_sample_weighing/source_bindings.yaml \
  --out outputs/scientific_workbench_solid_sample_weighing_r5_7_1g
PYTHONPATH=src python -m scenario_forge.cli package check \
  outputs/scientific_workbench_solid_sample_weighing_r5_7_1g
```

下游读 `metrics/metrics.yaml`。`terminal_lcd_1_00_g` 权重 0.35，是 primary metric。本仓库不评价回合，只运输 rubric。
