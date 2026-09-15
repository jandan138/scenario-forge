# Task09 粉末瓶 r5.0：120 Hz 对照（Isaac Sim 4.5）

这是 r4 近满瓶场景的**频率试验**，不是当前交付。只把物理步频从 240 Hz 改成 120 Hz；PGS、几何、粉粒和勺轨迹不变。

当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。本版 settle/scoop 未通过，不要当 `scene_fixture_verified` 使用。

## 和 r4 的唯一预定差异

| 项 | r4 | r5.0 试验 |
|---|---|---|
| 求解器 | PGS | PGS |
| 物理步频 | 240 Hz | **120 Hz** |
| 位置迭代 | 32 | 32 |
| 颗粒 / 初态 | 10,240 预沉降 | 同一份 USD 位姿 |

录像仍是 30 fps、50 s。变的是每步接触位移。

## 已观察到的 120 Hz 结果

不要把这些数字读成合格验收：

- 冷启动 8 s：代表性床深约 **7.53 mm**（门禁 10–12 mm），距口约 **8.47 mm**（门禁 3–7 mm）；2 粒在内托下。
- 规定舀取 50 s：舟内 **31** 粒，净读数约 **0.0668 g**，LCD **0.07 g**（r4 为 253 粒 / 0.55 g）；抬离后勺上只剩 31 粒；内托下最多 29 粒。
- 无引擎错误。未跑 calibration。

视频：

- `outputs/task09_powder_bottle_r5_0_20260914/video/overview.mp4`
- `outputs/task09_powder_bottle_r5_0_20260914/video/close.mp4`

## 复跑

从仓库根目录，输出目录必须是新的：

```bash
python scripts/clone_task09_powder_r5_0.py \
  --source outputs/task09_powder_bottle_r4_20260911/handoff/task09_powder_bottle_r4 \
  --out outputs/task09_powder_bottle_r5_0_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_0_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_0_YYYYMMDD/settle --mode settle --seconds 8
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_0_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_0_YYYYMMDD/scoop --mode scoop --seconds 50
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_0_YYYYMMDD/candidate \
  --states outputs/task09_powder_bottle_r5_0_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_0_YYYYMMDD/video --view close --video
```

验收看 `report.json` 的 `status`、checks 和空 `engine_errors`，不能只看进程退出码。
120 Hz 场景不能拿 r4 的 240 Hz 报告来资格化。
