# 固体样品称量：1 g 过程分与 r5.7 任务包

日期：2026-09-16。把飞书任务 15 的过程分改成以去皮后终帧 LCD `1.00 g` 为最大项，并写成 v0.2 规范任务包。场景 USD 用粉末瓶 **r5.7**（120 Hz），不替换 r4 当前交付头。

## 规范与范围

规范依据：同次提交的 [standards 入口](../standards/README.md) 案例行；[progress rubric](../design/progress-rubric.md) 增加条件类型 `instrument_display_matches`。
涉及规则：STATE-004/007、VAL-001/002/003/005。
变化：**规范无需变更** 通用成功模型。LCD `1.00 g` 是本任务过程分，不是全仓库仪器默认。
验证：`tests/test_solid_sample_weighing_r5_7_package.py` 加载 scenario、校验 JSON Schema、编译 stub 包并 `validate_package`。
限制：评测运行时仍是 transport_only，不在本仓库打 episode 分。勺数不计分。未改 [current_task_heads](../../configs/artifact_retention/current_task_heads.v1.json)。
同步内容：scenario、schema、progress-rubric、本记录、操作说明、index。

## 过程分（合计 1.00）

| 项 | 权重 | 时间 |
|---|---|---|
| 舟在秤上 | 0.08 | instant |
| 去皮触发 | 0.08 | instant |
| 勺离座 | 0.06 | instant |
| 勺入粉 | 0.08 | instant |
| 带料出瓶 | 0.12 | instant |
| 舟内有粉 | 0.10 | instant |
| **终帧 LCD 1.00 g** | **0.35** | terminal |
| 勺放回 | 0.05 | terminal |
| 终帧舟仍在秤上 | 0.08 | terminal |

过门文本与天平 `balance:lcd_readout` 一致，含单位：`1.00 g`（净重大约 0.995–1.005 g）。权威是屏，不是颗粒计数。

## 包

- 合同：`examples/scientific_workbench/solid_sample_weighing/scenario.yaml`
- `scenario_id`: `scientific_workbench_solid_sample_weighing`
- `composition_mode`: `producer_entrypoint`，资产 `task09_powder_bottle_r5_7`
- 预定 VR USD：`outputs/task09_powder_bottle_r5_7_20260915/prep_h1/scene.usda`
- `primary_metric_id`: `terminal_lcd_1_00_g`
- 总交付 ZIP：`outputs/task09_powder_bottle_r5_7_20260915/handoff/task09_powder_bottle_r5_7.zip`
- 场景 SHA：`db849664e0f8c8162d1cf37db3d7c3071fa3ebb6779c93e16c5a57518910dd70`
- 包状态：`scene_fixture_verified`（settle + scoop + calibration + video PASS）

ZIP SHA256：`8e1a7a1cc5e94a58c0ef370da567c1225070103bfad30691b2b158081802b755`（旁路 `.zip.sha256`）。未改当前任务头。
