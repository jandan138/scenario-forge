# Task09 粉末瓶 r5.3：120 Hz 加厚瓶壁（Isaac Sim 4.5）

在 r5.2 近满瓶上只加厚 256 块 `Wall_*` 碰撞，物理步频仍锁 120 Hz。当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。

## 和 r5.2 的预定差异

| 项 | r5.2 | r5.3 |
|---|---|---|
| 物理步频 | 120 Hz | 120 Hz |
| 粉粒 contact/rest | 0.25 / 0.15 mm | 同 r5.2 |
| 内托 contact/rest | 2.0 / 0.4 mm | 同 r5.2 |
| 瓶壁 contact/rest | 0.05 mm / 0 | **1.0 / 0.2 mm** |

## 已观察到的结果

- 冷启动 8 s：**通过**。10240 粒保留；床深约 **11.50 mm**，距口约 **4.50 mm**。
- 规定舀取 50 s：舟内 **167** 粒，LCD **0.36 g**；内托下最多 2 粒（约 10.7 s 起）。能舀，包装未过。

## 复跑

```bash
python scripts/clone_task09_powder_r5_3.py \
  --source outputs/task09_powder_bottle_r5_2_20260914/candidate \
  --out outputs/task09_powder_bottle_r5_3_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_3_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_3_YYYYMMDD/settle --mode settle --seconds 8
```
