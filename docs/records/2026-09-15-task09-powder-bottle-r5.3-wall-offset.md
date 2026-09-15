# Task09 r5.3：120 Hz 加厚瓶壁防侧漏

日期：2026-09-15。r5.2 冷启动丢 3 粒、瓶身外侧贴粒；舀取仍能转到 170 粒。判断侧漏来自 256 块 `Wall_*` 仍只用 0.05 mm 接触偏移。r5.3 锁 120 Hz，从 r5.2 候选加厚瓶壁，不改粉粒/内托偏移。

## 规范与范围

沿用 ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
**规范无需变更**：瓶壁 1.0 / 0.2 mm 偏移是本任务 120 Hz 夹具参数，不是全仓库默认。
当前交付头仍指向 r4。

## 候选

- 来源：`outputs/task09_powder_bottle_r5_2_20260914/candidate/`。
- 试验：`outputs/task09_powder_bottle_r5_3_20260915/prep_w1/`。
- `revision=r5.3`，`physics_hz=120`，`solver=PGS`，`status=candidate`。
- 瓶壁 `Wall_*`：`contactOffset=0.001`，`restOffset=0.0002`。
- 粉粒/内托保持 r5.2：0.25 / 0.15 mm，内托 2.0 / 0.4 mm，vmax 0.15。
- 克隆脚本：`scripts/clone_task09_powder_r5_3.py`。

## 运行证据（Isaac Sim 4.5.0）

| 试验 | 结果 |
|---|---|
| settle 8 s | **passed**。墙钟 175.8 s。10240 粒全程在瓶内；内托下 0，桌下 0。作者态/沉降中位床深 **11.75 / 11.50 mm**；median headspace **4.25 / 4.50 mm**。全部近满瓶与 `retained` 门禁通过 |
| scoop 50 s | **failed**（`no_leak_below_insert=false`）。墙钟 1202 s。去皮成功。舟内 **167** 粒、净重约 **0.3599 g**，LCD **0.36 g**。搬运窗勺上持续 167 粒。内托下最多 **2** 粒：第一粒在 t≈10.7 s（`extract_from_beaker`，勺尚未入瓶），第二粒在慢舀。`tare`/`transfer`/`sustained_carry` 为 true |

对照 r5.2：沉降丢 3 粒已消除；舀取内托漏从 1 增到 2，转移量几乎同级（170→167）。瓶壁加厚解决侧向丢粒，不能挡住延迟的内托板缝。

未跑 calibration，未打 ZIP，未改当前任务头。舀取视频尚未回放。

## 结论

120 Hz 下加厚瓶壁，可以把冷启动保持在 10240 粒近满瓶。下一版应加厚内托，而不是再拧瓶壁。
