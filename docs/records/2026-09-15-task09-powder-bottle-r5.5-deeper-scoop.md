# Task09 r5.5：120 Hz 挖深 4 mm，抬离后仍只有 221 粒

日期：2026-09-15。r5.4 规定舀取过门但不漏，舟内只有 177 粒 / 0.38 g。r5.5 锁 120 Hz，只把舀取粉面目标从 95 mm 降到 91 mm，颗粒位姿与接触偏移不变。

## 规范与范围

沿用 ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
**规范无需变更**：91 mm 粉面目标是本任务 120 Hz 夹具参数，不是全仓库默认。
当前交付头仍指向 r4，没有改 [current_task_heads.v1.json](../../configs/artifact_retention/current_task_heads.v1.json)。

## 候选

- 来源：`outputs/task09_powder_bottle_r5_4_20260915/prep_i1/`。
- 试验：`outputs/task09_powder_bottle_r5_5_20260915/prep_s1/`。
- `revision=r5.5`，`physics_hz=120`，`solver=PGS`，`status=candidate`。
- `powder_surface_target_m=0.091`。瓶壁/内托/粉粒偏移同 r5.4。
- 克隆脚本：`scripts/clone_task09_powder_r5_5.py`。

## 运行证据（Isaac Sim 4.5.0）

第一次 50 s 舀取在 t≈10 s 被会话杀掉，日志在 `prep_s1_scoop.killed-t10.log`。下列数字来自重跑 `prep_s1_scoop2`。未跑 calibration。`engine_errors` 为空。

| 试验 | 结果 |
|---|---|
| settle 8 s | **passed**。10240 粒全程在瓶内；内托下 0，桌下 0。沉降中位床深 **11.70 mm**，median headspace **4.30 mm** |
| scoop 50 s | **passed**。去皮成功。舟内 **221** 粒、净重约 **0.476 g**，LCD **0.48 g**。搬运窗勺上持续 221 粒；勺区高峰 **1119**。内托下全程 **0**。全部 scoop checks 为 true |

对照 r4：253 粒 / 0.55 g。对照 r5.4：177 粒 / 0.38 g，高峰 786。挖深把高峰拉到 1119，抬离留存约 20%（221/1119），绝对值仍低于 250。

作者态轨迹相对 r5.4：入瓶约深 3.9 mm，t=28 慢舀结束只深 2.4 mm。

## 视频

未渲。量未接近 r4，GPU 转给 r5.6。

未打 ZIP，未改当前任务头。

## 结论

120 Hz 下再挖深可以提高勺内高峰，但不能把抬离留存拉回 r4。下一版只加勺碗摩擦，不改时间轴、不加厚内托/瓶壁。
