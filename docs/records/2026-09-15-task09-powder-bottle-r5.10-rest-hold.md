# Task09 r5.10：120 Hz 静止段位姿冻结

日期：2026-09-15。r5.8 阻尼和 r5.9 sleep 都不能压 GPU PGS 蠕动（两者逐粒重合）。r5.10 锁 120 Hz，在勺插入前把粉粒世界坐标钉住。

## 规范与范围

规范依据：同次提交的 [standards 入口](../standards/README.md) 案例行；规则正文无通用变更。
涉及规则：ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
变化：**规范无需变更**。`grain_rest_kinematic_from_s` / `until_s` 是本任务 120 Hz 夹具参数，缺省不写时旧 revision 不冻结，不是全仓库默认。
验证：Isaac Sim 4.5 settle/scoop `report.json`；`summarize_rest_motion`；50 s overview/close 与瓶口帧；同机位目视 `video/visual_review.json`。
限制：GPU 上 kinematic+CCD 会被 PhysX 拒绝，中途改 kinematic 也不冻，因此用 validator 回写位姿，不是刚体 sleep。未替换 r4 交付头。
同步内容：README 案例与变更记录、本记录、r5.10 操作说明、design r5.8–r5.10 段、docs/index。
当前交付头仍指向 r4，没有改 [current_task_heads.v1.json](../../configs/artifact_retention/current_task_heads.v1.json)。

## 候选

- 来源：`outputs/task09_powder_bottle_r5_9_20260915/prep_e1/`。
- 试验：`outputs/task09_powder_bottle_r5_10_20260915/prep_f1/`。
- `revision=r5.10`，`physics_hz=120`，`solver=PGS`，`status=candidate`。
- `grain_rest_kinematic_from_s=0.5`，`grain_rest_kinematic_until_s=18`。抬离停顿、粉面目标、BowlContact、瓶壁/内托偏移同 r5.7。
- 克隆脚本：`scripts/clone_task09_powder_r5_10.py`。协议：`scripts/compact_powder_protocol.py`。

## 运行证据（Isaac Sim 4.5.0）

未跑 calibration。`engine_errors` 为空。

| 试验 | 结果 |
|---|---|
| settle6 15 s（from=1） | **passed**。10240 粒全程在瓶内；内托下 0。床深 **11.82 mm**。冻结后速度 0；从 t=0 起 15 s 漂移 **1.31 mm**（第一秒压实） |
| scoop 50 s（from=0.5） | **passed**。去皮成功。舟内 **245** 粒、区域 **0.528 g**，LCD **0.52 g**。搬运窗勺上持续 245 粒；勺区高峰 **1081**。内托下全程 **0**。插入前瓶内仍 10240。墙钟约 31.9 min |

静止（scoop 0–15 s）：中位速度 **0**，15 s 漂移 **0.90 mm**，`meets_r4_rest_gate=true`。对照 r4 约 1.5 mm/s / 0.61 mm，r5.7 约 4.8 mm/s / 6.6 mm。

逐秒抬离：t=28 勺上 1081，t=29 为 883，t=30 为 531，t=31 为 246，t=32 起稳住 **245**。

| 版 | t=28 | t=29 | t=30 | t=31 起 | 舟内 | 静止 0–15 s |
|---|---|---|---|---|---|---|
| r4 240 Hz | 813 | 413 | 253 | 253 | 253 / 0.55 g | 1.5 mm/s，0.61 mm |
| r5.7 120 Hz | 1096 | 890 | 531 | **252** | **252 / 0.54 g** | 4.8 mm/s，6.6 mm |
| r5.10 120 Hz | 1081 | 883 | 531 | **245** | **245 / 0.53 g** | **0 mm/s，0.90 mm** |

## 视频

同机位、30 fps、1280×800、50 s：

- `outputs/task09_powder_bottle_r5_10_20260915/video/overview.mp4`
- `outputs/task09_powder_bottle_r5_10_20260915/video/close.mp4`
- 瓶口帧：`bottle_0000.png`、`bottle_0210.png`、`bottle_0750.png`、`bottle_0900.png`

目视：`video/visual_review.json`。实现者同机位对可见瓶身 **PASS**（无外侧贴粒），初态近满 **PASS**。`bottle_0000` 与 `bottle_0210` 粉面锁定。`bottle_0900` 勺碗看起来空，是因为 t=30 仍是 6 mm 停顿、碗口朝粉；抬离后的堆在 `close_0960`。LCD 0.52 g。

未打 ZIP，未改当前任务头。

## 结论

120 Hz 下阻尼和 sleep 压不住 GPU PGS 蠕动。插入前 0.5–18 s 回写位姿可以把静止速度压到 0、15 s 漂移 0.90 mm，并保住冷启动 10240、不漏内托、可见瓶身无贴粒、舀取约 245 粒 / 0.53 g。overview/close/瓶口帧已出。未打 ZIP，未改当前任务头。
