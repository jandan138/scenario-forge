# Task09 r5.1：120 Hz 粉末限速对照

日期：2026-09-14。r5.0 只改 120 Hz 后床深塌到约 7.5 mm、内托漏粒。本次在同一 120 Hz / PGS / r4 预沉降位姿上，给 10240 颗 `obj_powder_grain_*` 加上 `maxLinearVelocity = 0.15` m/s，并保持已有 `maxDepenetrationVelocity = 0.2` m/s。大固体、瓶、勺、舟不改。

## 规范与范围

沿用 ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
**规范无需变更**：0.15 m/s 线速度上限是本任务 120 Hz 夹具试验，不是全仓库粉末默认。
当前交付头仍指向 r4，没有改 [current_task_heads.v1.json](../../configs/artifact_retention/current_task_heads.v1.json)。

## 候选

- 来源：`outputs/task09_powder_bottle_r4_20260911/handoff/task09_powder_bottle_r4/`（240 Hz）。
- 候选：`outputs/task09_powder_bottle_r5_1_20260914/candidate/`。
- 场景 SHA-256：`ccb74d1aec96075f56a484f9d912e4a97fa37115daa2eaf755088ca1808f8800`。
- `revision=r5.1`，`physics_hz=120`，`solver=PGS`，`status=candidate`。
- `grain_max_linear_velocity_m_s=0.15`，`grain_max_depenetration_velocity_m_s=0.2`。
- 克隆脚本：`scripts/clone_task09_powder_r5_1.py`。

0.15 m/s 对应每步最多约 1.25 mm，低于 2 mm 内托一帧穿板阈值 0.24 m/s。

## 运行证据（Isaac Sim 4.5.0）

未跑 calibration。两份沉降报告 `engine_errors` 均为空，`authored_physics_hz=120`，作者态粉粒速度上限已核对。

| 试验 | 结果 |
|---|---|
| settle 2 s 烟测 | **failed**（也短于 5 s 门禁）。墙钟 11.8 s。第一帧/2 s 中位床深 **8.09 / 7.51 mm**。瓶内 10240，内托下 0，桌下 0。 |
| settle 8 s | **failed**。墙钟 64.1 s。第一帧/8 s 中位床深 **8.09 / 7.53 mm**；median headspace **7.91 / 8.47 mm**。瓶内 10240→10237；`below_insert_count` 最大 **2**（t≈3.98 s 起）；桌下 0；穿到玻璃瓶底 **0**。`grain_06707` 在粉面高度挤出内轮廓。checks：`near_full_*`、`deep_powder_bed`、`retained`、`no_leak_below_insert` 为 false |
| scoop 50 s | **未跑**。2 s 中位床深已落到 7.51 mm，与 r5.0 的 7.55 mm 同类（门禁 &lt; 9.5 mm 则停舀取）。 |

对照 r5.0 同 8 s 沉降：床深同样约 7.53 mm；r5.0 内托下 2、穿瓶底 2、轮廓外 2。r5.1 第一步只比 r5.0 浅塌约 0.5 mm（8.09 vs 7.55），8 s 后仍回到同一平衡。内托下仍是 2 粒卡在板厚（`grain_02926`、`grain_03290`，局部 z≈82.5 mm，径向约 26.3 mm），没有穿到瓶底。

未打 ZIP，未改当前任务头。

## 代码与检查

测试先行：r5.1 近满瓶门禁、120 Hz、速度上限写入 scene_config、拒绝错误 vmax/depen 或 240 Hz 证据；USDA float32 容差；打包认 `r5.1`。
`pytest -q tests/test_clone_task09_powder_r5_1.py tests/test_task09_powder_evidence.py tests/test_full_powder_protocol.py` 在实现后通过。

## 结论

120 Hz 上给粉粒加 0.15 m/s 线速度上限，**不能**把冷启动床深拉回 10–12 mm；8 s 平衡仍约 7.5 mm。防漏只去掉了穿到玻璃底的路径，内托板缝仍漏 2 粒。下一步应在 120 Hz 下加高填料再烘初态，或很小的正 `restOffset`，而不是把 vmax 再拧紧。
