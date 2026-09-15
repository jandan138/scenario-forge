# Task09 r5.0：r4 场景锁定 120 Hz 的对照试验

日期：2026-09-14。用户确认 r4 可用后，要求后续物理步频定死 120 Hz，先只改频率、其余不变，看效果和视频。

## 规范与范围

沿用 ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
**规范无需变更**：120 Hz 是本任务后续目标配置，不是全仓库 PhysX 默认；本次失败结果不能提炼成通用时间步规则。
当前交付头仍指向 r4，没有改 [current_task_heads.v1.json](../../configs/artifact_retention/current_task_heads.v1.json)。

生产者几何未重建。SF 从 r4 交付目录克隆场景，只改 `physxScene:timeStepsPerSecond` 与 `scene_config.physics_hz`/`revision`。

## 候选

- 来源：`outputs/task09_powder_bottle_r4_20260911/handoff/task09_powder_bottle_r4/`（240 Hz，`scene_fixture_verified`）。
- 候选：`outputs/task09_powder_bottle_r5_0_20260914/candidate/`。
- 场景 SHA-256：`d8091c77e560f06ac46aeb5c94513904b9347cb0606c5341f6adc19e935105f5`。
- `revision=r5.0`，`physics_hz=120`，`solver=PGS`，`status=candidate`。
- 克隆脚本：`scripts/clone_task09_powder_r5_0.py`。

## 运行证据（Isaac Sim 4.5.0）

未跑 calibration。两份报告 `engine_errors` 均为空，`authored_physics_hz=120`，`physics_dt=1/120`。

| 试验 | 结果 |
|---|---|
| settle 8 s | **failed**。墙钟 59.5 s。初始/沉降床深 median **7.55 / 7.53 mm**（门禁 10–12 mm）；median headspace **8.45 / 8.47 mm**（门禁 3–7 mm）。瓶内由 10240 降至 10234；`below_insert_count=2`；桌下 0。checks：`near_full_*`、`deep_powder_bed`、`retained`、`no_leak_below_insert` 为 false |
| scoop 50 s | **failed**。墙钟 490.8 s。去皮成功。舟内 **31** 粒、约 0.0668 g，LCD **0.07 g**。抬离后勺上持续 31 粒（门禁 ≥32）。内托下最多 **29** 粒。无桌下漏粒。`transfer`/`sustained_carry`/`no_leak_below_insert`/`near_full_initial_state` 为 false；`tare`/`positive_force`/`valid_stable`/`force_region_agreement` 为 true |

对照 r4 规定舀取：253 粒、净重约 0.545 g、LCD 0.55 g、内托下 0。勺在粉中区域计数高峰 488，但抬离只剩 31，说明 120 Hz 下接触步长变大后留料掉落。

## 视频与目视

`outputs/task09_powder_bottle_r5_0_20260914/video/`：

- `overview.mp4`、`close.mp4`：1280×800、30 fps、1500 帧、50 s，ffmpeg 全片解码通过。
- 瓶口帧 `bottle_0000/0210/0750/0900.png`。
- `video_validation.json`、`visual_review.json`。

选帧目视（实现者本地审核，**不是独立 clean-room**）：整体 **FAIL**。同机位下 r5 粉面略低于 r4；25 s 入粉不如 r4 埋入；38 s 倾倒勺上只有一小撮；49 s LCD 清晰为 **0.07 g**。视频作为 120 Hz 对照可用，不能当作合格交付画面。

## 代码与检查

测试先行：r5.0 近满瓶门禁、拒绝 240 Hz 证据/TGS、打包认 `r5.0`。
`pytest -q tests/test_full_powder_protocol.py tests/test_task09_powder_evidence.py tests/test_clone_task09_powder_r5_0.py` 在实现后通过。

未把 r5.0 打成 ZIP，也未改当前任务头。

## 结论

只改 120 Hz、沿用 r4 预沉降位姿，**不能**通过现有近满瓶和舀取门禁。若 120 Hz 必须保留，需要在 120 Hz 下重新沉降/固化初态，并可能放慢勺的运动学，而不是宣布本候选合格。
