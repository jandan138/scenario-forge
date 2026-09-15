# Task09 r5.6：120 Hz 只加勺碗摩擦，抬离后仍是 221 粒

日期：2026-09-15。r5.5 挖深后规定舀取过门，舟内 221 粒 / 0.48 g。r5.6 锁 120 Hz，只给勺碗新建独立接触材质，不改粉面目标、时间轴或瓶壁/内托偏移。

## 规范与范围

沿用 ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
**规范无需变更**：勺碗 0.9/0.7 是本任务 120 Hz 夹具参数，不是全仓库默认。
当前交付头仍指向 r4，没有改 [current_task_heads.v1.json](../../configs/artifact_retention/current_task_heads.v1.json)。

## 候选

- 来源：`outputs/task09_powder_bottle_r5_5_20260915/prep_s1/`。
- 试验：`outputs/task09_powder_bottle_r5_6_20260915/prep_b1/`。
- `revision=r5.6`，`physics_hz=120`，`solver=PGS`，`status=candidate`。
- 新建 `/World/obj_sampling_spoon/BowlContact` 0.9/0.7，只重绑碗 mesh。`/World/PowderLooks/Contact` 仍是 0.65/0.5，绑定瓶壁、内托、舟和 10240 粒。
- `/World/obj_sampling_spoon/PhysicsMaterial` 0.4/0.3 只绑两侧握代理，舀取用不上。
- 克隆脚本：`scripts/clone_task09_powder_r5_6.py`。

## 运行证据（Isaac Sim 4.5.0）

未跑 calibration。`engine_errors` 为空。

| 试验 | 结果 |
|---|---|
| settle2 8 s | **passed**。10240 粒全程在瓶内；内托下 0，桌下 0。沉降中位床深 **11.68 mm**，median headspace **4.32 mm** |
| scoop 50 s | **passed**。去皮成功。舟内 **221** 粒、净重约 **0.476 g**，LCD **0.48 g**。搬运窗勺上持续 221 粒；勺区高峰 **1102**。内托下全程 **0**。全部 scoop checks 为 true。墙钟约 19.3 min |

逐秒抬离与 r5.5 同形：t=28 勺上 1096（高峰 1102），t=29 为 673，t=30 为 228，t=31 起稳住 221。留存约 20%。

对照 r5.5：221 / 0.48 g，高峰 1119。碗摩擦没有提高抬离留存。

## 视频

未渲。量未接近 r4，GPU 转给 r5.7。

未打 ZIP，未改当前任务头。

## 结论

120 Hz 下单独提高勺碗摩擦不能把 221 粒拉回 r4 的 253。下一版不改摩擦/挖深/内托，只在锁定的 50 s 时间轴内给 t=28–32 加早期抬离停顿。
