# Task09 粉末瓶 r5.5：120 Hz 挖深舀取（Isaac Sim 4.5）

在 r5.4 上只降低 `powder_surface_target_m`。物理步频仍锁 120 Hz。当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。

## 和 r5.4 的预定差异

| 项 | r5.4 | r5.5 |
|---|---|---|
| 物理步频 | 120 Hz | 120 Hz |
| 舀取粉面目标 | 95 mm | **91 mm** |

## 已观察到的结果

- 冷启动 8 s：**通过**。10240 粒；床深约 **11.70 mm**，距口约 **4.30 mm**。
- 规定舀取 50 s：**通过**。舟内 **221** 粒，LCD **0.48 g**；高峰 1119；内托下 0。仍低于 r4（253 / 0.55 g）。

## 复跑

```bash
python scripts/clone_task09_powder_r5_5.py \
  --source outputs/task09_powder_bottle_r5_4_20260915/prep_i1 \
  --out outputs/task09_powder_bottle_r5_5_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_5_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_5_YYYYMMDD/settle --mode settle --seconds 8
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_5_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_5_YYYYMMDD/scoop --mode scoop --seconds 50
```
