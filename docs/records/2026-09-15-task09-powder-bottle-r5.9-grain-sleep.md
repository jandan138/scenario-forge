# Task09 r5.9：120 Hz 粉粒 sleep 对 GPU PGS 无效

日期：2026-09-15。r5.8 线性阻尼不能压静止蠕动。r5.9 锁 120 Hz，只把 10240 颗 `sleepThreshold`/`stabilizationThreshold` 改到 PhysX 默认 5e-5 / 1e-5，并让 runtime 不再每步叫醒粉粒。

## 规范与范围

变化：**规范无需变更**。sleep 阈值是本任务夹具试验，不是全仓库默认。
验证：Isaac Sim 4.5 settle 15 s。作者态阈值已写入并被 validator 读回。
限制：未跑舀取；未替换 r4 交付头。

## 结果

- 来源：`outputs/task09_powder_bottle_r5_8_20260915/prep_d1/`。
- 试验：`outputs/task09_powder_bottle_r5_9_20260915/prep_e1/`。
- 15 s settle：**passed**。10240；床深约 11.79 mm。
- 静止：中位速度 **4.83 mm/s**，15 s 漂移 **6.53 mm**，与 r5.8 **逐粒终态完全重合**（中位差 0 μm）。
- 结论：GPU PGS + CCD 粉粒不走 sleep。下一刀改为勺插入前 kinematic 冻结。
