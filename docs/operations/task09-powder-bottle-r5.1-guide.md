# Task09 粉末瓶 r5.1：120 Hz 粉粒限速对照（Isaac Sim 4.5）

这是 r4 近满瓶场景的**限速试验**，不是当前交付。物理步频锁在 120 Hz，并给每颗粉末加上 `maxLinearVelocity = 0.15` m/s；`maxDepenetrationVelocity` 保持 0.2 m/s。PGS、几何、预沉降位姿和勺轨迹与 r4 相同。

当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。本版 settle 未通过近满瓶门禁，不要当 `scene_fixture_verified` 使用。50 s 舀取按 2 s 烟测门未跑。

## 和 r5.0 的预定差异

| 项 | r5.0 | r5.1 试验 |
|---|---|---|
| 求解器 | PGS | PGS |
| 物理步频 | 120 Hz | 120 Hz |
| 粉粒 `maxDepenetrationVelocity` | 0.2 m/s | **0.2 m/s（不降低）** |
| 粉粒 `maxLinearVelocity` | 未写 | **0.15 m/s** |
| 颗粒 / 初态 | 10,240 预沉降 | 同一份 USD 位姿 |

大固体 `obj_grain_01..05` 仍是各自的 `maxLinearVelocity = 1`。

## 已观察到的结果

不要把这些数字读成合格验收：

- 冷启动第一帧中位床深约 **8.09 mm**（r5.0 约 7.55 mm）；2 s / 8 s 后约 **7.51 / 7.53 mm**（门禁 10–12 mm）。
- 8 s：内托下最多 **2** 粒，桌下 0，未穿到玻璃瓶底；1 粒在轮廓外。
- 无引擎错误。未跑 scoop / calibration。

## 复跑

从仓库根目录，输出目录必须是新的：

```bash
python scripts/clone_task09_powder_r5_1.py \
  --source outputs/task09_powder_bottle_r4_20260911/handoff/task09_powder_bottle_r4 \
  --out outputs/task09_powder_bottle_r5_1_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_1_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_1_YYYYMMDD/settle2s --mode settle --seconds 2
```

2 s 中位床深仍低于 9.5 mm 且与 r5.0 的 7.5 mm 同类时，不要跑 50 s scoop。若要对照 8 s 漏粒：

```bash
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_1_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_1_YYYYMMDD/settle --mode settle --seconds 8
```

验收看 `report.json` 的 `status`、checks、`authored_grain_max_linear_velocity` 和空 `engine_errors`，不能只看进程退出码。
120 Hz 限速场景不能拿 r4 的 240 Hz 报告来资格化。
