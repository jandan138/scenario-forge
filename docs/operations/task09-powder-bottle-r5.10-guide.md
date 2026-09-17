# Task09 粉末瓶 r5.10：120 Hz 静止段位姿冻结（Isaac Sim 4.5）

在 r5.9 上只给 validator 加可选静止段位姿冻结。物理步频仍锁 120 Hz，总时间轴仍是 0–50 s。当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。

## 和 r5.9 的预定差异

| 项 | r5.9 | r5.10 |
|---|---|---|
| 物理步频 | 120 Hz | 120 Hz |
| 粉粒 sleep / 阻尼 | sleep 5e-5 / stab 1e-5，damping 1 | 同左，作者态保留 |
| 勺插入前粉粒 | 动态 PGS | **0.5–18 s 回写世界坐标** |

缺省不写 `grain_rest_kinematic_from_s` / `until_s` 时，旧 revision 不冻结。GPU 上 kinematic+CCD 会被 PhysX 拒绝，因此冻结是 validator 回写，不是刚体 kinematic。

## 已观察到的结果

- 冷启动 15 s：**通过**。10240 粒；床深约 **11.82 mm**。
- 规定舀取 50 s：**通过**。舟内 **245** 粒，LCD **0.52 g**；高峰 1081；内托下 0。静止中位速度 **0**，15 s 漂移 **0.90 mm**（过 r4 静止门）。
- 视频：`outputs/task09_powder_bottle_r5_10_20260915/video/overview.mp4`、`close.mp4`，以及四张瓶口帧。同机位目视：可见瓶身无贴粒；`bottle_0000` 与 `bottle_0210` 粉面锁定。

## 复跑

```bash
python scripts/clone_task09_powder_r5_10.py \
  --source outputs/task09_powder_bottle_r5_9_20260915/prep_e1 \
  --out outputs/task09_powder_bottle_r5_10_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_10_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_10_YYYYMMDD/settle --mode settle --seconds 15
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_10_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_10_YYYYMMDD/scoop --mode scoop --seconds 50
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_10_YYYYMMDD/candidate \
  --states outputs/task09_powder_bottle_r5_10_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_10_YYYYMMDD/video --view close --video
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_10_YYYYMMDD/candidate \
  --states outputs/task09_powder_bottle_r5_10_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_10_YYYYMMDD/video --view overview --video
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_10_YYYYMMDD/candidate \
  --states outputs/task09_powder_bottle_r5_10_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r5_10_YYYYMMDD/video --view bottle --frames 0,210,750,900
```
