# Task09 粉末瓶 r6.0：GPU-PBD 干粉（Isaac Sim 4.5）

从 [r5.7](task09-powder-bottle-r5.7-guide.md) 拷场景，删掉 10240 个刚体 ico 粒，在原粒心铺 `fluid=False` 的 PBD 点。物理步频仍锁 120 Hz，规定勺轨迹仍是 0–50 s（含 `lift_early_hold_m=0.006`）。当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)；1 g 正式 USD 仍是 r5.7。a54 干 PBD 是 [VR 数采候选](solid-sample-weighing-r6.0-a54-guide.md)，不是近满合格夹具。

## 和 r5.7 的预定差异

| 项 | r5.7 | r6.0 |
|---|---|---|
| 粉末表示 | `obj_powder_grain_*` 刚体 ico | `/World/powder_pbd` Points，`physxParticle:fluid=false` |
| 几何对齐 | 等体积直径 1.4 mm | 自碰 1.04 mm、墙碰 0.7 mm（1.0 mm 墙距会加重爬壁）；阻尼 0.4、maxVel 0.06；`gravityScale` 2 会把床压到 7.6 mm |
| 第一阶段过门 | 秤盘接触力交叉检查 | 区域内粒子数 × 写死单粒质量 |
| 交付头 | 不替换 r4 | 不替换 r4 / r5.7 |

## 复跑

```bash
python scripts/clone_task09_powder_r6_0.py \
  --source outputs/task09_powder_bottle_r5_7_20260915/prep_h1 \
  --out outputs/task09_powder_bottle_r6_0_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r6_0_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r6_0_YYYYMMDD/settle --mode settle --seconds 8
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r6_0_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r6_0_YYYYMMDD/scoop --mode scoop --seconds 50
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root outputs/task09_powder_bottle_r6_0_YYYYMMDD/candidate \
  --states outputs/task09_powder_bottle_r6_0_YYYYMMDD/scoop/states.npz \
  --out outputs/task09_powder_bottle_r6_0_YYYYMMDD/video --view close --video
```

验证器对 PBD 必须打开 `/physics/updateToUsd` 和 `/physics/updateParticlesToUsd`，位置读 `physxParticle:simulationPoints`（没有才退回 `points`）。床深用视觉半径 0.7 mm，不用 r5.7 ico 外接半径；自碰 rest 是 1.04 mm。

同机位视频仍走 `scripts/render_task09_powder.py`。PBD 回放用 0.7 mm 视觉半径球体做 PointInstancer 原型，不再拷刚体粒 Mesh。

不要用全局 `adhesionOffsetScale>0`，也不要在入瓶前打开勺碗外沿。中途改勺沿 `physics:collisionEnabled` 或独立运动学笼子都不是纯物理舀取。干粉默认仍是 `fluid=False`。若要让 cohesion 生效，可另开 `pbd_viscous` 试验：`fluid=True`、关掉 isosurface、外观仍用粒子。此近满干装上 `fluidRestOffset` ≤0.65 mm 才能零漏（床会矮到约 6 mm），0.78 mm 起慢漏。近满要用 `fill_pbd_cavity_lattice` 按流体间距重装，不能只改 rest。a34 的 1.10 mm / 11 mm / 17957 在瓶口慢漏；a37 用 1.16 mm / 10.5 mm / 瓶颈墙距 3.5 mm 留存 13597、床 7.58 mm。a38 同间距加高到 14 mm / 18137：留存、床 9.17 mm。a39 16 mm / 20458：留存、床 9.88 mm。a40 17 mm / 21696：留存、沉降床 10.27 mm，近满沉降过门。未沉降晶格会偏高，scoop 仍可能卡 `near_full_initial_state`。
要把勺速压到不超过 `maxVelocity`，设 `spoon_max_speed_m_s`：只拉长超速的关键帧，空间路点不变，总时长会超过 50 s，这是试验，不是 r5.7 规定轨迹。粘稠粉出瓶口被刮到勺沿时，可设 `carry_pitch_deg`（如 25）让出瓶后碗口朝上、到船再放平；`carry_pitch_through_transfer` 会提前滴，不要默认开。默认 0 仍是官方放平。近满晶格（a40/a44）settle 能留、scoop 会从瓶口漏，不能当沿圈基线。粘稠糊上把勺碗 `BowlContact` 降到 0.25/0.18（a45）沿圈不变，不要再用碗摩擦修远端挂条。官方 50 s + `carry_pitch_deg=25`（a46）终局散粒 4、远端 6.7%，优于 71 s 慢勺的 a41。同一套接到 a39 床（a47）仍漏 95，不要再加高晶格指望官方钟自己不漏。约 3000 粒粗粉试验：`fill_pbd_cavity_lattice` 间距 1.8 mm / 作者态 9 mm（3125 粒），视觉半径 1.0 mm，`fluidRest` 0.93 mm；勺内高度用 `spoon_local_z_max_m`（如 18 mm）。a48 官方 50 s 移送 156 / 散粒 0，LCD `0.61 g`；近摄 `prep_a48_video/close.mp4` 出瓶后是单列 C 圈，不是堆，粗粒零散粒基线可以是 a48，勺上堆仍看 a46。2.0 mm × 156 已接近一勺单层；再缩到 1.6 mm 仍卡约 3000 粒只会更薄。a49 同装、`lift_hold_pitch_deg=30`（默认仍 20）加上出瓶 35°：t=32 勺上 143 / 碗心 52 / 沿圈 43.4%，比 a48 更差，不作沿圈对照。a50 同装、规定 20° 抬离、无出瓶倾角，只把 cohesion 0.02 / viscosity 0.2：t=32 仍是 156 / 碗心 57 / 沿圈 46.2%（a48 为 156/58/42.9%），移送掉 34 粒，船内 122 / LCD `0.61 g`。降内聚不能甩沿留心，只会在 0° 移送掉台面；不要再降 cohesion 修 C 圈。a51 把 a48 粘稠晶格直接改回干 PBD：settle 就胀漏（t=8 散粒 311），终局散粒 815 / 船内 75，不要再拿粘稠晶格当干粉。干粉粗装必须按固体 rest 重铺。a52 从 a9 重铺 3074 粒（1.63 mm / 7 mm / 瓶颈 4.5 mm）：t=8 仍漏 281、床 14.3 mm，不要再铺到 7 mm。a53 同偏移、作者态 5 mm、2556 粒：scoop t=32 勺上 132 / 碗心 64 / 沿圈 32.6%，船内 68 / 散粒 417 / LCD `0.42 g`。干粗晶格 a51–a53 都会胀漏，不要再浅铺。a54 从 a9 位姿抽 3125 粒：settle 留存 3125 / 散粒 0，床塌到 7.05 mm。官方 50 s scoop t=32 勺上 155 / 碗心 69 / 沿圈 36.1%，船内 126 / 散粒 30 / LCD `0.27 g`。干粉少散粒基线可以看 a54（30 vs a9 187），零散粒仍看 a48，勺上堆仍对 r5.7 252/168/15.5%。不要再铺干粗晶格，也不要把 a54 7.05 mm 床当近满。勺上有堆对 r5.7 t=32：252 粒、碗心 168、沿圈 15.5%，不要把 a46/a48 糊圈当成原样。10–12 mm 近满门先不改。不加勺沿、不用运动学笼子。近摄回放按录到的阶段对齐官方 50 s 拍法（倒粉锁在 `slow_pour` = 36–40 s 机位），不要用重定时关键帧推时钟：船位变化会让倒粉段对到 LCD。
