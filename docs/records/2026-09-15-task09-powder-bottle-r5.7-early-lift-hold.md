# Task09 r5.7：120 Hz 早期抬离停顿，舟内回到 252 粒 / 0.54 g

日期：2026-09-15。r5.6 碗摩擦后规定舀取仍是 221 粒 / 0.48 g。r5.7 锁 120 Hz，只在锁定的 50 s 时间轴内给 t=30 加 filled+6 mm 中间路点，t=32 仍到原来的 carry。

## 规范与范围

规范依据：同次提交的 [standards 入口](../standards/README.md) 案例行；规则正文无通用变更。
涉及规则：ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
变化：**规范无需变更**。`lift_early_hold_m` 是本任务 120 Hz 夹具参数，缺省关闭时旧 revision 轨迹不变，不是全仓库默认。
验证：Isaac Sim 4.5 settle/scoop `report.json`；50 s overview/close 与瓶口帧；独立目视 `video/visual_review.json`。
限制：无专用侧拍；瓶内+舟内合计差 2 粒，可见壁上未见；未替换 r4 交付头。
同步内容：README 案例与变更记录、本记录、r5.7 操作说明、design r5.5–r5.7 段、docs/index。
当前交付头仍指向 r4，没有改 [current_task_heads.v1.json](../../configs/artifact_retention/current_task_heads.v1.json)。

## 候选

- 来源：`outputs/task09_powder_bottle_r5_6_20260915/prep_b1/`。
- 试验：`outputs/task09_powder_bottle_r5_7_20260915/prep_h1/`。
- `revision=r5.7`，`physics_hz=120`，`solver=PGS`，`status=candidate`。
- `lift_early_hold_m=0.006`。粉面目标、BowlContact、瓶壁/内托偏移同 r5.6。
- 克隆脚本：`scripts/clone_task09_powder_r5_7.py`。协议：`scripts/compact_powder_protocol.py`。

作者态 t=30 勺头比无停顿低约 12.7 mm，pitch 20°；t=32 高度与相位不变。

## 运行证据（Isaac Sim 4.5.0）

未跑 calibration。`engine_errors` 为空。

| 试验 | 结果 |
|---|---|
| settle 8 s | **passed**。10240 粒全程在瓶内；内托下 0，桌下 0。沉降中位床深 **11.68 mm**，median headspace **4.32 mm**（与 r5.6 相同） |
| scoop 50 s | **passed**。去皮成功。舟内 **252** 粒、净重约 **0.543 g**，LCD **0.54 g**。搬运窗勺上持续 252 粒；勺区高峰 **1114**。内托下全程 **0**。全部 scoop checks 为 true。墙钟约 19.3 min |

逐秒抬离：t=28 勺上 1096，t=29 为 890，t=30 为 531，t=31 为 253，t=32 起稳住 **252**。留存约 23%。

| 版 | t=28 | t=29 | t=30 | t=31 起 | 舟内 |
|---|---|---|---|---|---|
| r4 240 Hz | 813 | 413 | 253 | 253 | 253 / 0.55 g |
| r5.6 120 Hz | 1096 | 673 | 228 | 221 | 221 / 0.48 g |
| r5.7 120 Hz | 1096 | 890 | 531 | **252** | **252 / 0.54 g** |

对照 r4：253 粒 / 0.55 g。r5.7 在 120 Hz 下回到同一量级。

瓶内末粒 9986 + 舟内 252 = 10238，差 2 粒；不在内托下、不在桌下。贴粒要等瓶口/close 目视。

## 视频

同机位、30 fps、1280×800、50 s：

- `outputs/task09_powder_bottle_r5_7_20260915/video/overview.mp4`
- `outputs/task09_powder_bottle_r5_7_20260915/video/close.mp4`
- 瓶口帧：`bottle_0000.png`、`bottle_0210.png`、`bottle_0750.png`、`bottle_0900.png`

目视：`video/visual_review.json`。独立 clean-room 对可见瓶身 **PASS**（无外侧贴粒），初态近满 **PASS**。`bottle_0900` 勺碗看起来空，是因为 t=30 仍是 6 mm 停顿、碗口朝粉；抬离后的堆在 `close_0960`，与 r4 同帧接近。LCD 0.54 g。

未打 ZIP，未改当前任务头。

## 结论

120 Hz 下减慢抬离前 2 s 的上升，可以把留存从 221 拉回约 252，而不用改时间轴总长、挖深或摩擦。overview/close/瓶口帧已出；可见瓶身无贴粒。未打 ZIP，未改当前任务头。
