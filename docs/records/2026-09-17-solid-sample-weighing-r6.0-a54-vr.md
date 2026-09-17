# 固体样品称量：r6.0 a54 PBD VR 数采候选包

日期：2026-09-17。把 `prep_a54` 冻成可编译的 v0.2 任务包，给 VR 数采加载。过程分仍是去皮后终帧 LCD `1.00 g`。不替换 r4 当前交付头，也不替换 r5.7 1 g 正式 USD。

## 规范与范围

规范依据：同次提交的 [standards 入口](../standards/README.md) 案例行。
涉及规则：ASSET-001/003、USD-002、STATE-004/007、VAL-001/002/003/005/006。
变化：**规范无需变更**。LCD `1.00 g` 仍是本任务过程分，不是全仓库仪器默认。a54 是本任务 VR 候选，不是近满合格夹具，也不是全仓库粉末默认。
验证：`tests/test_solid_sample_weighing_r6_0_package.py` 加载 scenario、校验 JSON Schema、编译 stub 包并 `validate_package`；真实 USD 走 `package compile` + `package check`（`asset_locked`）。
限制：本包证明合同可编译、场景闭包可复制。不证明 10–12 mm 近满，不证明规定一勺就是 `1.00 g`，不证明机器人策略成功，不做 `scene_fixture_verified`。评测运行时仍是 transport_only。
同步内容：r6.0 示例合同、本记录、数采操作说明、index、CHANGELOG、`current_task_heads` 候选行。

## 场景与一勺证据

- 冻住 USD：`outputs/task09_powder_bottle_r6_0_20260917/vr_a54/`（从 `prep_a54` 原样拷贝，SHA `74cdd778fb67fb8ddedf538af3023899ea8be2438b339f26a6ec4648d579fede`）
- 3125 粒干 PBD，单粒 `2.155132560362598e-6` kg
- settle：留存 3125 / 散粒 0，床 8.90→7.05 mm
- 官方 50 s scoop：船内 126 / 0.27 g / LCD `0.27 g` / 散粒 30；t=32 勺上 155 / 碗心 69 / 沿圈 36.1%
- 近摄：`outputs/task09_powder_bottle_r6_0_20260917/prep_a54_video/close.mp4`

## 包

- 合同：`examples/scientific_workbench/solid_sample_weighing_r6_0/scenario.yaml`
- `scenario_id`: `scientific_workbench_solid_sample_weighing_r6_0`
- `composition_mode`: `producer_entrypoint`，资产 `task09_powder_bottle_r6_0`
- 编译目录：`outputs/scientific_workbench_solid_sample_weighing_r6_0_a54`
- ZIP：`outputs/task09_powder_bottle_r6_0_20260917/handoff/scientific_workbench_solid_sample_weighing_r6_0_a54.zip`
- ZIP SHA256：`56e8319b2936f144e4794f278094c608cc3a1759eb1585595cf6a1419c9554dc`
- 包状态：`asset_locked` 候选，不是 `scene_fixture_verified`

未改 r4 `current_delivery`。
