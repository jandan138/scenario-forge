# Task09 120 Hz 静止粉粒振动 5.x 目标进度

日期：2026-09-15。这是当前进行中的目标快照，不是合格交付说明。数字来自本机 `outputs/` 报告，不是记忆。

## 目标原文

锁死 120 Hz，迭代尝试 5.x，把瓶内静止粉粒的振动/蠕动压到接近 r4（勺插入前中位速度 ≲ 1.5 mm/s，15 s 漂移 ≲ 1.3 mm），并保住 r5.7 已过的门：冷启动 10240、不漏内托、瓶外不贴粒、舀取约 250 粒 / 0.55 g，以及 overview / close 50 s 和瓶口帧。

未授权把 r4 当前交付头换成 5.x。不改回 240 Hz，不回退接触偏移。一版只改一个变量。

对照基准：`outputs/task09_powder_bottle_r4_20260911/final_scoop/states.npz`（插入前约 1.5 mm/s，15 s 漂移约 0.61 mm）。r5.7 同段约 4.8 mm/s、6.6 mm。

## 现在算不算完成

**完成。** r5.10 scoop **passed**：静止中位速度 **0**，15 s 漂移 **0.90 mm**，过 r4 静止门；舟内 **245** 粒 / LCD **0.52 g**（区域 0.528 g）；内托下 0；冷启动 10240。overview/close 各 50 s、瓶口四帧已出；同机位目视无贴粒。未改交付头。

## 一版一刀

| 版 | 改动 | 静止 0–15 s | 沉降 | 50 s 舀取 | 视频 |
|---|---|---|---|---|---|
| r4 | 240 Hz 交付 | 1.5 mm/s，漂移 0.61 mm | 通过 | 253 / 0.55 g | 有 |
| r5.7 | 120 Hz 量已过门 | 4.8 mm/s，漂移 6.6 mm | 通过 | 252 / 0.54 g | 有 |
| r5.8 | 只加粉粒 `linearDamping=1` | **4.83 mm/s，漂移 6.53 mm**，未过门 | 15 s **通过**，10240 | 未跑 | 无 |
| r5.9 | 粉粒 sleep 5e-5 / stab 1e-5 | **4.83 mm/s，与 r5.8 逐粒相同** | 15 s **通过** | 未跑 | 无 |
| r5.10 | 0.5–18 s 位姿冻结 | scoop 0–15 s：**0 mm/s，漂移 0.90 mm**（过门）；settle6 from=1 为 1.31 mm | **passed**，10240，床深 11.82 mm | **passed**，245 / 0.53 g，LCD 0.52 g，漏 0 | **有** |

## 路径

- 场景：`outputs/task09_powder_bottle_r5_10_20260915/prep_f1/`
- 克隆：`scripts/clone_task09_powder_r5_10.py`
- 沉降：`outputs/task09_powder_bottle_r5_10_20260915/prep_f1_settle6/`
- 舀取：`outputs/task09_powder_bottle_r5_10_20260915/prep_f1_scoop/`
- 视频：`outputs/task09_powder_bottle_r5_10_20260915/video/`
