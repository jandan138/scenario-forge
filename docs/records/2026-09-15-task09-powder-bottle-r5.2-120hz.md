# Task09 r5.2：120 Hz 近满瓶重固化与可舀视频

日期：2026-09-15。r5.0/r5.1 只改频率或粉粒限速后，10240 粒在 120 Hz 下塌到约 7.5 mm，不能舀。本次在 120 Hz / PGS / 32 次位置迭代下调整粉粒与内托碰撞偏移，从 r4 预沉降位姿重新沉降并固化初态。

## 规范与范围

沿用 ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
**规范无需变更**：grain `contactOffset`/`restOffset`、内托加厚偏移和 0.15 m/s 线速度上限是本任务 120 Hz 夹具参数，不是全仓库粉末默认。
当前交付头仍指向 r4，没有改 [current_task_heads.v1.json](../../configs/artifact_retention/current_task_heads.v1.json)。

ConvertAsset 的高塔 HCP `prepare` 在 120 Hz 下单步约 7 s，本轮放弃该路径。实际制作：克隆 r4 预沉降 USD，改 120 Hz 与偏移，沉降 8 s，把漏出的少量颗粒拨回粉面后写入新初态。

## 候选

- 来源位姿：`outputs/task09_powder_bottle_r4_20260911/handoff/task09_powder_bottle_r4/`（240 Hz）。
- 候选：`outputs/task09_powder_bottle_r5_2_20260914/candidate/`。
- 场景 SHA-256：`d537095c3e5e18f7e23067e4cefd97213b787a0fbce148038e98b47a568bfa3c`。
- `revision=r5.2`，`physics_hz=120`，`solver=PGS`，`status=candidate`，`initial_state=presettled`，`preparation_only=false`。
- 粉粒：`contactOffset=0.00025`，`restOffset=0.00015`，`maxLinearVelocity=0.15`，`maxDepenetrationVelocity=0.2`。
- 内托 `Insert_*`：`contactOffset=0.002`，`restOffset=0.0004`。
- 固化前将 5 粒漏出颗粒拨回粉面。

偏移扫描（同一 r4 位姿、8 s 沉降）：

| 试验 | 粉粒 contact/rest | 内托 contact/rest | 8 s 中位床深 | 内托下漏粒 |
|---|---|---|---|---|
| A0 | 0.15 / 0.05 mm | 默认 | 8.43 mm | 22 |
| A1 | 0.20 / 0.10 mm | 默认 | 9.70 mm | 33 |
| A2 | 0.25 / 0.15 mm + vmax 0.15 | 默认 | 11.09 mm | 50 |
| A3 | A2 + speculative CCD | 默认 | 9.98 mm | 66 |
| A4 | A2 | 1.0 / 0.2 mm | 11.27 mm | 9 |
| A5 | A2 | **2.0 / 0.4 mm** | **11.48 mm** | **2** |

A3 不用。最终 bake 取 A5。

## 运行证据（Isaac Sim 4.5.0）

未跑 calibration。两份报告 `engine_errors` 均为空，`authored_physics_hz=120`，`physics_dt=1/120`。

| 试验 | 结果 |
|---|---|
| settle 8 s | **failed**（仅 `retained=false`：10240→10237）。墙钟 142.4 s。作者态/沉降中位床深 **11.77 / 11.54 mm**（门禁 10–12 mm）；median headspace **4.23 / 4.46 mm**（门禁 3–7 mm）；最低头空 3.02 / 3.29 mm。内托下 0，桌下 0。checks：`near_full_initial_state`、`near_full_settled_state`、`deep_powder_bed`、`no_leak_below_insert`、`no_below_table` 为 true |
| scoop 50 s | **failed**（`no_leak_below_insert=false`：最多/末帧内托下 **1** 粒）。墙钟 1614 s。去皮成功。舟内 **170** 粒、净重约 **0.3664 g**，LCD **0.37 g**。抬离后搬运窗（33–35 s）勺上持续 **170** 粒（门禁 ≥32）；勺区高峰 767。瓶内剩余 10048。桌下 0。`tare`/`transfer`/`sustained_carry`/`positive_force`/`valid_stable`/`force_region_agreement`/`near_full_initial_state` 为 true |

对照 r4 规定舀取：253 粒 / LCD 0.55 g。对照 r5.0：31 粒 / 0.07 g。本版能舀，质量低于 r4，高于 r5.0。

## 视频与目视

`outputs/task09_powder_bottle_r5_2_20260914/video/`：

- `overview.mp4`、`close.mp4`：1280×800、30 fps、1500 帧、50 s，ffmpeg 全片解码通过。
- 瓶口帧 `bottle_0000/0210/0750/0900.png`。
- `video_validation.json`、`visual_review.json`。

选帧目视（实现者本地审核，**不是独立 clean-room**）：整体 **WARN**。`bottle_0000` 粉面接近 r4 近满瓶，头空略更小。25–30 s 勺上有可见堆料并完成倾倒，LCD 为 **0.37 g**。入粉后瓶身外侧可见数粒贴壁（r4 同帧没有）；7 s 肩部已有 1 粒，与 settle 丢失 3 粒一致。视频可作为 120 Hz 近满瓶可舀对照，不能当作替换 r4 的 `scene_fixture_verified` 交付。

## 代码与检查

测试先行：r5.2 近满瓶门禁、120 Hz、打包认 `r5.2`；prepare 补丁改 revision/Hz/粉粒偏移。
未把 r5.2 打成 ZIP，也未改当前任务头。

## 结论

120 Hz 下用更大的粉粒接触间隙、加厚内托偏移，并从 r4 位姿重固化初态，可以把床深拉回 10–12 mm，规定轨迹能舀到 170 粒 / 0.37 g。包装门禁仍因 settle 丢 3 粒、scoop 内托下 1 粒失败。当前合格交付仍是 r4。
