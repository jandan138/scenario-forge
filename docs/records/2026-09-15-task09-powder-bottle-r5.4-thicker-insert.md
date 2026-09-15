# Task09 r5.4：120 Hz 再加厚内托，舀取不再漏板缝

日期：2026-09-15。r5.3 冷启动保留 10240 粒，但规定舀取内托下最多 2 粒，第一粒在 t≈10.7 s、勺尚未入瓶时就出现。r5.4 锁 120 Hz，从 r5.3 把 `Insert_*` 从 2.0 / 0.4 mm 加到 3.0 / 0.6 mm。

## 规范与范围

沿用 ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
**规范无需变更**：内托 3.0 / 0.6 mm 是本任务 120 Hz 夹具参数，不是全仓库默认。
当前交付头仍指向 r4，没有改 [current_task_heads.v1.json](../../configs/artifact_retention/current_task_heads.v1.json)。

## 候选

- 来源：`outputs/task09_powder_bottle_r5_3_20260915/prep_w1/`。
- 试验：`outputs/task09_powder_bottle_r5_4_20260915/prep_i1/`。
- `revision=r5.4`，`physics_hz=120`，`solver=PGS`，`status=candidate`。
- 内托：`contactOffset=0.003`，`restOffset=0.0006`。
- 瓶壁保持 r5.3：1.0 / 0.2 mm。粉粒保持 r5.2：0.25 / 0.15 mm，vmax 0.15。
- 克隆脚本：`scripts/clone_task09_powder_r5_4.py`。

## 运行证据（Isaac Sim 4.5.0）

未跑 calibration。`engine_errors` 均为空。

| 试验 | 结果 |
|---|---|
| settle 8 s | **passed**。墙钟 202.3 s。10240 粒全程在瓶内；内托下 0，桌下 0。沉降中位床深 **11.70 mm**，median headspace **4.30 mm** |
| scoop 50 s | **passed**。墙钟 1474.5 s。去皮成功。舟内 **177** 粒、净重约 **0.3815 g**，LCD **0.38 g**。搬运窗勺上持续 177 粒；勺区高峰 786。内托下全程 **0**。全部 scoop checks 为 true |

对照 r4：253 粒 / 0.55 g。对照 r5.2/r5.3：170/167 粒且舀取漏内托。本版防漏和近满瓶已过包装门禁，转移量仍明显低于 r4。

## 视频

`outputs/task09_powder_bottle_r5_4_20260915/video/`：`close.mp4`、`overview.mp4`（1280×800、30 fps、50 s），瓶口帧 `bottle_0000/0210/0750/0900.png`。overview 缺 `overview_1470.png`。独立 clean-room 目视未完成；实现者尚未把瓶外贴粒写成正式 verdict。

未打 ZIP，未改当前任务头。

## 结论

加厚内托后，120 Hz 规定舀取不再漏进板缝，冷启动仍近满。下一版应提高抬离后留勺量，而不是再拧内托。
