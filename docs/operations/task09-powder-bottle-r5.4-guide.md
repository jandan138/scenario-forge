# Task09 粉末瓶 r5.4：120 Hz 加厚内托（Isaac Sim 4.5）

在 r5.3 上只加厚 32 块 `Insert_*`。物理步频仍锁 120 Hz。当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。

## 和 r5.3 的预定差异

| 项 | r5.3 | r5.4 |
|---|---|---|
| 物理步频 | 120 Hz | 120 Hz |
| 瓶壁 contact/rest | 1.0 / 0.2 mm | 同 r5.3 |
| 内托 contact/rest | 2.0 / 0.4 mm | **3.0 / 0.6 mm** |

## 已观察到的结果

- 冷启动 8 s：**通过**。10240 粒；床深约 **11.70 mm**，距口约 **4.30 mm**。
- 规定舀取 50 s：**通过**。舟内 **177** 粒，LCD **0.38 g**；内托下 0。能量低于 r4（253 / 0.55 g）。

视频：`outputs/task09_powder_bottle_r5_4_20260915/video/overview.mp4`、`close.mp4`。

## 复跑

```bash
python scripts/clone_task09_powder_r5_4.py \
  --source outputs/task09_powder_bottle_r5_3_20260915/prep_w1 \
  --out outputs/task09_powder_bottle_r5_4_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_4_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_4_YYYYMMDD/settle --mode settle --seconds 8
```
