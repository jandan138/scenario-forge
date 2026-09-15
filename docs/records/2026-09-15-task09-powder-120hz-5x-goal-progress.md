# Task09 120 Hz 近满瓶 5.x 目标进度

日期：2026-09-15。这是当前进行中的目标快照，不是合格交付说明。数字来自本机 `outputs/` 报告，不是记忆。

## 目标原文

锁死 **120 Hz**，视觉继续接近 r4 近满瓶；针对 r5.2 暴露的问题不断迭代新的 5.x，直到：

1. 冷启动不丢粒（10240 仍在瓶内）
2. 规定舀取不漏进内托板缝
3. 瓶身外侧不再明显贴粒
4. 舀取量接近 r4（约 **250 粒 / 0.55 g**）
5. 有 overview / close 50 s 视频和瓶口帧

**未授权把 r4 当前交付头换成 5.x**，除非某一版通过现有包装门禁（settle + scoop，必要时 calibration）。

对照基准仍是 240 Hz 的 r4：`outputs/task09_powder_bottle_r4_20260911/`，当前头 `revision=r4`、`status=current_delivery`。

## 现在算不算完成

**算完成（交付头仍是 r4）。** r5.7 锁 120 Hz：冷启动 10240、规定舀取不漏、舟内 **252 粒 / 0.54 g**，overview / close 各 50 s 加瓶口帧已落盘。独立目视：可见瓶身无贴粒，初态近满接近 r4。未改 `current_task_heads`。

| 要求 | 状态 | 依据 |
|---|---|---|
| 锁 120 Hz | 已做到 | r5.0 起 `authored_physics_hz=120`，PGS，未改回 240 |
| 近满瓶观感（床深 10–12 mm，距口约 3–7 mm） | 从 r5.2 起做到 | 见下表沉降床深 |
| 冷启动不丢粒 | r5.3 起做到 | r5.3/r5.4/r5.5 settle `retained=true`，10240 |
| 舀取不漏内托 | r5.4 做到 | r5.4 scoop `no_leak_below_insert=true`，全程 0 |
| 瓶外不贴粒 | 已做到（可见壁） | r5.7 独立 clean-room：可见肩/壁无黄粒。同机位 r5.2 `bottle_0750` 能看见贴粒，本版没有。无专用侧拍 |
| 舀取接近 250 粒 / 0.55 g | 已做到 | r5.7 scoop：**252 粒 / 0.54 g**（r4 为 253 / 0.55 g） |
| overview + close + 瓶口帧 | 已做到 | `outputs/task09_powder_bottle_r5_7_20260915/video/`：两支 50 s / 1500 帧，四张瓶口帧 |
| 替换 r4 交付头 | 未做 | `current_task_heads.v1.json` 仍指向 r4 |

## 一句话对照

| 版 | Hz | 做了什么 | 8 s 沉降 | 50 s 舀取 | 视频 |
|---|---|---|---|---|---|
| r4 | 240 | 合格近满瓶 | 约 10.28 mm，通过 | **253 粒 / 0.55 g**，通过 | 有 |
| r5.0 | 120 | 只改频率 | 约 7.53 mm，失败 | 31 粒 / 0.07 g，失败 | 有（失败对照） |
| r5.1 | 120 | 粉粒 vmax 0.15 | 仍约 7.53 mm，失败 | 未跑 | 无 |
| r5.2 | 120 | 加大粉粒/内托偏移并重固化 | 11.54 mm，丢 3 粒 | 170 粒 / 0.37 g，内托下 1 | 有 |
| r5.3 | 120 | 加厚瓶壁 1.0 / 0.2 mm | **通过**，10240 | 167 粒 / 0.36 g，内托下 2 | 无 |
| r5.4 | 120 | 内托再加到 3.0 / 0.6 mm | **通过**，10240 | **通过**，177 粒 / 0.38 g，内托下 0 | 有 |
| r5.5 | 120 | 舀取粉面目标 95→91 mm（挖深） | **通过**，10240 | **通过**，221 粒 / 0.48 g，漏 0 | 未渲 |
| r5.6 | 120 | 勺碗 BowlContact 0.9/0.7 | **通过**，10240 | **通过**，221 粒 / 0.48 g，漏 0 | 未渲 |
| r5.7 | 120 | t=30 早期抬离停顿 6 mm | **通过**，10240 | **通过**，252 粒 / 0.54 g，漏 0 | 有 |

r5.0/r5.1 证明：不能直接拿 r4 的 240 Hz 位姿降频。r5.2 证明：要在 120 Hz 下把接触间隙加大并重固化，粉面才能回到近满。之后每一版只改一个变量。

## 物理参数（作者态）

共同锁定：Isaac Sim 4.5、PGS、32 次位置迭代、CCD、10240 粒、规定勺轨迹时间轴不变。

| 项 | r4 | r5.2 | r5.3 | r5.4 | r5.5 | r5.6 | r5.7 |
|---|---|---|---|---|---|---|---|
| 粉粒 contact/rest | 0.03 mm / 0 | 0.25 / 0.15 mm | 同 r5.2 | 同 r5.2 | 同 r5.2 | 同左 | 同左 |
| 粉粒 vmax | 未写 | 0.15 m/s | 同左 | 同左 | 同左 | 同左 | 同左 |
| 内托 contact/rest | 默认约 0.05 mm | 2.0 / 0.4 mm | 同 r5.2 | **3.0 / 0.6 mm** | 同 r5.4 | 同左 | 同左 |
| 瓶壁 contact/rest | 0.05 mm / 0 | 同 r4 | **1.0 / 0.2 mm** | 同 r5.3 | 同 r5.3 | 同左 | 同左 |
| 舀取粉面目标 | 95 mm | 95 mm | 95 mm | 95 mm | **91 mm** | 同 r5.5 | 同 r5.5 |
| 勺碗摩擦 | Contact 0.65/0.5 | 同左 | 同左 | 同左 | 同左 | **BowlContact 0.9/0.7** | 同 r5.6 |
| 早期抬离停顿 | 无 | 无 | 无 | 无 | 无 | 无 | **t=30，+6 mm** |
| 初态来源 | 240 Hz 预沉降 | r4 位姿再沉降固化 | 克隆 r5.2 | 克隆 r5.3 | 克隆 r5.4 | 克隆 r5.5 | 克隆 r5.6 |

不要跑 ConvertAsset 高塔 HCP 来复现：120 Hz 下该路径过慢，r5.2 已弃用。

## 沉降数字（冷启动 8 s）

门禁：中位床深 10–12 mm，中位距口 3–7 mm，10240 粒留下，内托下 0，桌下 0。

| 版 | status | 沉降中位床深 | 中位距口 | 瓶内末粒数 | 内托下最大 |
|---|---|---|---|---|---|
| r5.2 | failed（仅丢粒） | 11.54 mm | 4.46 mm | 10237 | 0 |
| r5.3 | **passed** | 11.50 mm | 4.50 mm | 10240 | 0 |
| r5.4 | **passed** | 11.70 mm | 4.30 mm | 10240 | 0 |
| r5.5 | **passed** | 11.70 mm | 4.30 mm | 10240 | 0 |
| r5.6 | **passed**（settle2） | 11.68 mm | 4.32 mm | 10240 | 0 |
| r5.7 | **passed** | 11.68 mm | 4.32 mm | 10240 | 0 |

r5.5 粉床与 r5.4 相同：只改了勺子用的粉面目标，没有重写颗粒位姿。

## 舀取数字（规定 50 s）

门禁能舀：去皮、舟内 ≥32、搬运窗勺上 ≥32、受力为正且稳定。包装另要求全程内托下 0。

| 版 | status | 舟内 | 净重 | LCD | 搬运窗勺上 | 勺区高峰 | 内托下最大 | 墙钟 |
|---|---|---|---|---|---|---|---|---|
| r4 | passed | 253 | ≈0.545 g | 0.55 g | ≥32 | — | 0 | — |
| r5.0 | failed | 31 | 0.067 g | 0.07 g | 31 | 488 | 29 | 8.2 min |
| r5.2 | failed（漏 1） | 170 | 0.366 g | 0.37 g | 170 | 767 | 1 | 26.9 min |
| r5.3 | failed（漏 2） | 167 | 0.360 g | 0.36 g | 167 | 762 | 2（t≈10.7 s 起） | 20.0 min |
| r5.4 | **passed** | 177 | 0.381 g | 0.38 g | 177 | 786 | 0 | 24.6 min |
| r5.5 | **passed** | **221** | 0.476 g | **0.48 g** | 221 | **1119** | 0 | scoop2 |
| r5.6 | **passed** | **221** | 0.476 g | **0.48 g** | 221 | 1102 | 0 | 19.3 min |
| r5.7 | **passed** | **252** | 0.543 g | **0.54 g** | 252 | 1114 | 0 | 19.3 min |

r5.4 的诊断：粉里高峰 786，抬离后只剩 177。缺的不是“挖不到”，而是 **120 Hz 下抬勺留不住**。r5.5 把勺子挖深 4 mm，是在测“更满的勺头抬起来会不会多剩”。

逐秒对照（同一时间轴）：掉粒几乎全在 `lift_powder` 的前 2 s，t=30 之后两边都稳住。

| 版 | t=28 勺上 | t=29 | t=30 起 | 留存 |
|---|---|---|---|---|
| r4 240 Hz | 813 | 413 | 253 | 31% |
| r5.4 120 Hz | 777 | 399 | 177 | 23% |
| r5.5 120 Hz（scoop2 日志） | **1115** | 697 | **221** | 20% |
| r5.6 120 Hz（BowlContact） | 1096 | 673 | **221** | 20% |
| r5.7 120 Hz（early hold） | 1096 | 890 | **252** | 23% |

规定勺轨迹总时间轴不变。r5.6 只加勺碗摩擦：第一次稿写错了 `/World/obj_sampling_spoon/PhysicsMaterial`（只绑握代理）；碗、瓶壁、舟和 10240 粒共用 `/World/PowderLooks/Contact` 0.65/0.5。直接改 Contact 会连带加瓶壁摩擦。正式候选新建 `/World/obj_sampling_spoon/BowlContact` 0.9/0.7，只重绑碗。scoop **passed**，舟内仍是 221。挖深和碗摩擦都提高不了留存。r5.7 在 t=30 插入 filled+6 mm 中间路点，t=32 仍到原来的 carry。缺省无 `lift_early_hold_m` 时旧轨迹不变。

## 视频在哪

同机位、30 fps、1280×800、50 s（与 r4 同一套 `overview` / `close` / `bottle`）。

| 版 | 目录 | 文件 |
|---|---|---|
| r4 | `outputs/task09_powder_bottle_r4_20260911/video/` | `overview.mp4`、`close.mp4`、`bottle_0000/0210/0750/0900.png` |
| r5.2 | `outputs/task09_powder_bottle_r5_2_20260914/video/` | 同上；另有 `video_validation.json`、`visual_review.json`（实现者本地 WARN） |
| r5.4 | `outputs/task09_powder_bottle_r5_4_20260915/video/` | `close.mp4`、`overview.mp4`、四张瓶口帧；overview 缺 `overview_1470.png` |
| r5.7 | `outputs/task09_powder_bottle_r5_7_20260915/video/` | `close.mp4`、`overview.mp4`、四张瓶口帧；`visual_review.json` |
| r5.3 / r5.5 / r5.6 | — | 还没有回放片 |

r5.2 实现者目视：`bottle_0000` 接近 r4 近满；入粉后瓶身外侧有贴粒，LCD 0.37 g。r5.4 实现者本地 `video/visual_review.json`：**WARN**（非独立 clean-room）。r5.7 独立目视：可见瓶身无贴粒，LCD 0.54 g。

## 场景和脚本

| 版 | 场景目录 | 脚本 |
|---|---|---|
| r5.2 | `outputs/task09_powder_bottle_r5_2_20260914/candidate/` | `scripts/prepare_task09_powder_r5_2.py`（HCP 补丁；实际候选来自 r4 位姿重固化） |
| r5.3 | `outputs/task09_powder_bottle_r5_3_20260915/prep_w1/` | `scripts/clone_task09_powder_r5_3.py` |
| r5.4 | `outputs/task09_powder_bottle_r5_4_20260915/prep_i1/` | `scripts/clone_task09_powder_r5_4.py` |
| r5.5 | `outputs/task09_powder_bottle_r5_5_20260915/prep_s1/` | `scripts/clone_task09_powder_r5_5.py` |
| r5.6 | `outputs/task09_powder_bottle_r5_6_20260915/prep_b1/` | `scripts/clone_task09_powder_r5_6.py`（BowlContact 0.9/0.7 只绑碗） |
| r5.7 | `outputs/task09_powder_bottle_r5_7_20260915/prep_h1/` | `scripts/clone_task09_powder_r5_7.py`（`lift_early_hold_m=0.006`） |

单版记录：

- [r5.0](2026-09-14-task09-powder-bottle-r5.0-120hz.md)
- [r5.1](2026-09-14-task09-powder-bottle-r5.1-velocity-cap.md)
- [r5.2](2026-09-15-task09-powder-bottle-r5.2-120hz.md)
- [r5.3](2026-09-15-task09-powder-bottle-r5.3-wall-offset.md)
- [r5.4](2026-09-15-task09-powder-bottle-r5.4-thicker-insert.md)
- [r5.5](2026-09-15-task09-powder-bottle-r5.5-deeper-scoop.md)
- [r5.6](2026-09-15-task09-powder-bottle-r5.6-bowl-friction.md)
- [r5.7](2026-09-15-task09-powder-bottle-r5.7-early-lift-hold.md)

## 过程里中断过什么

对话链路多次 `deadline_exceeded` / connection interrupted，Isaac 作业本身多数已跑完并写进 `outputs/`。因此进度以磁盘报告为准，不以某次聊天是否说完为准。

## 下一步（目标仍未结束）

1. 目标条目已齐：120 Hz、近满、不丢粒、不漏内托、可见瓶身不贴粒、252 / 0.54 g、50 s overview/close + 瓶口帧。
2. 交付头仍指向 r4，未跑 calibration，未打 ZIP。
3. `bottle_0900` 不能当 r4 同秒堆高对照：r5.7 该秒还在早期停顿。
