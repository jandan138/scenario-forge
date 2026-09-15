# Task09 粉末瓶 r5.7：120 Hz 早期抬离停顿（Isaac Sim 4.5）

在 r5.6 上只给规定勺轨迹加可选 `lift_early_hold_m`。物理步频仍锁 120 Hz，总时间轴仍是 0–50 s。当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。

## 和 r5.6 的预定差异

| 项 | r5.6 | r5.7 |
|---|---|---|
| 物理步频 | 120 Hz | 120 Hz |
| t=30 勺头 | 按 28→32 插值抬向 carry | **filled + 6 mm，pitch 20°** |
| t=32 | carry | 同左，时间不变 |

缺省不写 `lift_early_hold_m` 时，旧 revision 轨迹不变。

## 已观察到的结果

- 冷启动 8 s：**通过**。10240 粒；床深约 **11.68 mm**，距口约 **4.32 mm**（与 r5.6 相同：只改轨迹，未改颗粒）。
- 规定舀取 50 s：**通过**。舟内 **252** 粒，LCD **0.54 g**；高峰 1114；内托下 0。接近 r4（253 / 0.55 g）。
- 视频：`outputs/task09_powder_bottle_r5_7_20260915/video/overview.mp4`、`close.mp4`，以及四张瓶口帧。独立目视：可见瓶身无贴粒。

## 复跑

```bash
python scripts/clone_task09_powder_r5_7.py \
  --source outputs/task09_powder_bottle_r5_6_20260915/prep_b1 \
  --out outputs/task09_powder_bottle_r5_7_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_7_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_7_YYYYMMDD/settle --mode settle --seconds 8
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_7_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_7_YYYYMMDD/scoop --mode scoop --seconds 50
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_7_YYYYMMDD/candidate \
  --states outputs/task09_powder_bottle_r5_7_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_7_YYYYMMDD/video --view close --video
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_7_YYYYMMDD/candidate \
  --states outputs/task09_powder_bottle_r5_7_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_7_YYYYMMDD/video --view overview --video
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_7_YYYYMMDD/candidate \
  --states outputs/task09_powder_bottle_r5_7_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_7_YYYYMMDD/video --view bottle --frames 0,210,750,900
```
