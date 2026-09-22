# Boat pour then stir VR r1

Date: 2026-09-20.

规范依据：当前 `docs/standards` USD 组织、资产接入、材质/液体、Articulation、交互状态、验证与交付正文。
涉及规则：ASSET-003、USD-001、USD-003、USD-004、USD-005、USD-006、ART-003、MAT-001、STATE-001、VAL-001、VAL-002、VAL-003、VAL-005、VAL-006。
变化：**规范无需变更**。本包是第一份 4.5 受力天平 + r5.7 刚体细粉 + task_04 液体 PBD 的任务级混合场景，不把该组合升格为仓库默认，也不改粉末 PGS、液体 TGS 或天平资格。
验证：`tests/test_boat_pour_stir_vr_r1.py`（30 粒、无干 PBD、舟上盘、去皮属性、986 粒平移 PBD、托盘边距、物化闭包、claim 边界）。Isaac 4.5 冷启动烟雾见 `outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920/evidence/isaac45_runtime_smoke.json`。
限制：倒粒、倒液、搅拌、headset 加载未跑，不当 pass。颗粒倒进烧杯后不溶解。force_r1 OmniGraph 启动会重置去皮，因此开局属性 `0.06 g` 不是 live LCD。PBD 仍是 authored `points`，没有 `simulationPoints` 回读。
同步内容：生成器、测试、本记录、操作说明、薄 `scenario.yaml`、`current_task_heads.v1.json`。未改 `docs/standards` 规则正文。

## Identity

- `task_id`: `scientific_workbench_boat_pour_stir`
- artifact family: `boat_pour_stir`
- variant: `isaac45_vr` / r1 / `current_candidate`
- 输出根: `outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920`
- 不是同事 catalog 的 `task_14_fixed_weight_weighing` stub，也不替换该 stub。
- 不是 1.00 g / 30 g 称量任务。

## Sources

| 角色 | 路径 |
|---|---|
| 4.5 工作台 + 天平 + 空 SDF 烧杯/量筒 | `/cpfs/shared/simulation/chenjiantong/scene_usds/scientific_experiments/task_14_fixed_weight_weighing/seen_scene_1/scene.usd` |
| 30 粒刚体粉原型 | `outputs/task09_powder_bottle_r5_7_20260915/handoff/task09_powder_bottle_r5_7/scene.usda` 的 `/World/obj_powder_grain_00000` |
| 986 粒量筒 PBD | 同树 `task_04_pour_liquid_with_funnel` |
| 玻璃棒用完托盘 | 同树 `task_02_pour_liquid_and_stir` 的 `obj_plate` |

删掉 task_14 的 `/World/powder_pbd`（12500 干 PBD）。量筒粒子按两场景量筒中心差平移，不能原样粘贴。ParticleSet 去掉 `displayColor` / `displayOpacity`。

## Layout

开局称量舟在秤盘上，离盘面 2 mm，`tare_g=10`、`tared=true`、`lcd_readout="0.06 g"`，`resolution_g=0.01`。`balance:target_g=1.0` 只给 force_r1 `BalanceState` 构造用，不是 1 g / 30 g 称量任务。托盘放在原称量舟空位 `(-0.34, -0.20, 0.755)`。棒+架保持 task_14 现位。其余 task_14 物体原位保留。PowderProxy 接触从 20 mm 收到 0.5 mm，避免 SDF 底板嵌进秤盘后把舟打飞。场景写入单一 `/World/PhysicsScene`（GPU / TGS / 120 Hz），ParticleSystem `simulationOwner` 指向它。

随机化：天平+舟固定；量筒固定；棒+架共组；托盘、烧杯、粉末瓶、药勺、称量瓶、各 r9 ±0.01 m。30 粒不进 `obj_prim_list`。天平按 ART-003 注册根和三个刚体 link；该天平是 force_r1 自由基座，不是固定基座 v2。

PhysX 剖面：Isaac 4.5、GPU、TGS、120 Hz。过程分四步各 0.25，只看动作序列。

## Isaac 4.5 physics smoke

Host: `/isaac-sim` 4.5.0, RTX 4090, `scripts/smoke_boat_pour_stir_vr_r1.py --seconds 3`.
Scene sha256: `4245a0ec0685f785adcddd50b11f9e415c51b8f856f9fab851feeaae8f8c5e57`.
Evidence: `outputs/scientific_workbench_boat_pour_stir_vr_r1_20260920/evidence/isaac45_runtime_smoke.json`.

| check | result |
|---|---|
| engine crash | no |
| LCD | `5.02 g` (`valid`/`stable`, `tare_g=0`, not `0.06 g`) |
| grains in boat | 30/30 |
| boat stayed on pan | yes; live xform ≈ `(0.056, -0.152, 0.930)` (slid +X ≈ 6 cm from authored) |
| PBD in cylinder | 986 authored points; `used_simulation_points=false` |
| World dt | Isaac World kept 60 Hz fallback (`0.01666 s`) |

Status: **blocked**. Do not treat this as pour, dissolve, headset, or `scene_fixture_verified`.
The first two harnesses either never ticked the balance OG (`------`) or launched the boat (20 mm PowderProxy SDF contact into the pan, plus a missing PhysicsScene). Those were harness/package bugs, not a runtime pass.
