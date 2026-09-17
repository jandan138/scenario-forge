# Task09 r5.8：120 Hz 粉粒线性阻尼不能压静止蠕动

日期：2026-09-15。r5.7 舀取量已接近 r4，但瓶内静止粉粒仍以约 4.8 mm/s 蠕动。r5.8 锁 120 Hz，只把 10240 颗 `linearDamping` 从 0 改到 1.0。

## 规范与范围

规范依据：同次工作的 [standards 入口](../standards/README.md) 案例行；规则正文无通用变更。
涉及规则：ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
变化：**规范无需变更**。`grain_linear_damping=1` 是本任务 120 Hz 夹具试验，不是全仓库默认。
验证：Isaac Sim 4.5 settle 15 s `report.json` 与 `states.npz` 的 `summarize_rest_motion`。
限制：未跑舀取；未替换 r4 交付头。阻尼几乎不改变 PGS 每步纠穿透造成的位移。
当前交付头仍指向 r4。

## 结果

- 来源：`outputs/task09_powder_bottle_r5_7_20260915/prep_h1/`。
- 试验：`outputs/task09_powder_bottle_r5_8_20260915/prep_d1/`。
- 15 s settle：**passed**。10240；床深约 11.79 mm；内托下 0。
- 静止：中位速度 **4.83 mm/s**，15 s 漂移 **6.53 mm**（r5.7 为 4.84 / 6.60；r4 为 1.5 / 0.61）。`meets_r4_rest_gate=false`。
