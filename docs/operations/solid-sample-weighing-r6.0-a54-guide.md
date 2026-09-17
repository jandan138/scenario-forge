# 固体样品称量：r6.0 a54 PBD VR 数采候选

权威合同是 [scenario.yaml](../../examples/scientific_workbench/solid_sample_weighing_r6_0/scenario.yaml)。当前合格粉末交付头仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。1 g 正式 USD 仍是 [r5.7](solid-sample-weighing-r5.7-1g-guide.md)。本包指定 VR 数采用 a54 干 PBD 场景，分数仍看去皮后终帧 LCD `1.00 g`。

解压目录：`outputs/scientific_workbench_solid_sample_weighing_r6_0_a54`。
ZIP：`outputs/task09_powder_bottle_r6_0_20260917/handoff/scientific_workbench_solid_sample_weighing_r6_0_a54.zip`。
校验和见旁路 `.zip.sha256`。冻住的生产者 USD 在 `outputs/task09_powder_bottle_r6_0_20260917/vr_a54/scene.usda`。

## 编译任务包

```bash
PYTHONPATH=src python -m scenario_forge.cli package compile \
  --spec examples/scientific_workbench/solid_sample_weighing_r6_0/scenario.yaml \
  --source-bindings examples/scientific_workbench/solid_sample_weighing_r6_0/source_bindings.yaml \
  --out outputs/scientific_workbench_solid_sample_weighing_r6_0_a54
PYTHONPATH=src python -m scenario_forge.cli package check \
  outputs/scientific_workbench_solid_sample_weighing_r6_0_a54
```

下游读 `metrics/metrics.yaml`。`terminal_lcd_1_00_g` 权重 0.35，是 primary metric。本仓库不评价回合，只运输 rubric。验证级别是 `asset_locked`，**不是** `scene_fixture_verified`。

## 数采怎么用

- Isaac Sim 4.5 + GPU PBD（`physxParticle:fluid=false`）。不要当 r5.7 刚体 ico 包加载。
- 去皮后往称量舟里加到 LCD 显示 `1.00 g`。勺数不限；最后一勺可以点着倒，不必一次倒完。
- 规定 50 s 一勺大约 126 粒 / 0.27 g（单粒 2.155 mg）。到 `1.00 g` 大约 3–4 勺，再补几颗。
- 床深约 7.05 mm，**不是** 10–12 mm 近满。瓶外可能剩约 30 粒。近满门不改。
- 近摄参考：`outputs/task09_powder_bottle_r6_0_20260917/prep_a54_video/close.mp4`。没有独立 `visual_review.json`，不要写成目视 PASS。
