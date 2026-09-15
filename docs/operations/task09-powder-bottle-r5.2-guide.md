# Task09 粉末瓶 r5.2：120 Hz 近满瓶重固化（Isaac Sim 4.5）

这是 r4 近满瓶在 **120 Hz** 下重新沉降并固化的可用对照，不是当前交付。PGS、32 次位置迭代、10240 粒和规定勺轨迹保持；粉粒与内托碰撞偏移相对 r4 加大，初态按 120 Hz 平衡重写。

当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。本版 settle/scoop 的包装 `status` 未通过（丢粒 / 内托下 1 粒），不要当 `scene_fixture_verified` 使用。

## 和 r4 / r5.1 的预定差异

| 项 | r4 | r5.1 | r5.2 候选 |
|---|---|---|---|
| 求解器 | PGS | PGS | PGS |
| 物理步频 | 240 Hz | 120 Hz | **120 Hz** |
| 位置迭代 | 32 | 32 | 32 |
| 粉粒 contact/rest | 0.03 mm / 0 | 同 r4 | **0.25 / 0.15 mm** |
| 粉粒 vmax | 未写 | 0.15 m/s | **0.15 m/s** |
| 内托 contact/rest | 默认 | 默认 | **2.0 / 0.4 mm** |
| 初态 | r4 240 Hz 预沉降 | 同一份 r4 位姿 | **120 Hz 再沉降后固化** |

不要跑 ConvertAsset 高塔 HCP `prepare` 来复现本版：120 Hz 下该路径过慢。本候选已写在
`outputs/task09_powder_bottle_r5_2_20260914/candidate/`。

## 已观察到的 120 Hz 结果

不要把这些数字读成替换 r4 的合格验收：

- 冷启动 8 s：代表性床深约 **11.54 mm**（门禁 10–12 mm），距口约 **4.46 mm**（门禁 3–7 mm）；瓶内 10240→10237；内托下 0；桌下 0。
- 规定舀取 50 s：舟内 **170** 粒，净读数约 **0.3664 g**，LCD **0.37 g**（r4 为 253 粒 / 0.55 g；r5.0 为 31 粒 / 0.07 g）。搬运窗勺上持续 170 粒。内托下最多 1 粒。
- 无引擎错误。未跑 calibration。

视频：

- `outputs/task09_powder_bottle_r5_2_20260914/video/overview.mp4`
- `outputs/task09_powder_bottle_r5_2_20260914/video/close.mp4`

## 复跑已固化候选

从仓库根目录，输出目录必须是新的：

```bash
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_2_20260914/candidate \
  --out outputs/task09_powder_bottle_r5_2_YYYYMMDD/settle --mode settle --seconds 8
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_2_20260914/candidate \
  --out outputs/task09_powder_bottle_r5_2_YYYYMMDD/scoop --mode scoop --seconds 50
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_2_20260914/candidate \
  --states outputs/task09_powder_bottle_r5_2_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_2_YYYYMMDD/video --view close --video
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_2_20260914/candidate \
  --states outputs/task09_powder_bottle_r5_2_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_2_YYYYMMDD/video --view overview --video
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_2_20260914/candidate \
  --states outputs/task09_powder_bottle_r5_2_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_2_YYYYMMDD/video --view bottle --frames 0,210,750,900
```

验收看 `report.json` 的 `status`、checks 和空 `engine_errors`，不能只看进程退出码。
120 Hz 场景不能拿 r4 的 240 Hz 报告来资格化。
`scripts/prepare_task09_powder_r5_2.py` 只给 ConvertAsset `prepare` 打 120 Hz/偏移补丁；本候选不是那条高塔路径的产物。
