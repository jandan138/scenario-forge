# Funnel pour then place flask on stirrer VR r1

Date: 2026-09-20.

规范依据：当前 `docs/standards` USD 组织、资产接入、材质/液体、验证与交付正文。
涉及规则：ASSET-001、ASSET-005、ASSET-006、USD-003、USD-004、USD-005、USD-006、MAT 液体声明、VAL-001、VAL-002、VAL-003、VAL-005、VAL-006。
变化：**规范无需变更**。本包是新任务 VR 数采 handoff，不改通用桌板、漏斗喉口或 PBD 默认配方。
扁圆柱底座是本任务场景内圆柱（ASSET-006 例外，不是桌子，也不是新 ConvertAsset 准入资产），
不写入 `usd-layout` / `asset-intake` 正文。
验证：`tests/test_funnel_pour_flask_to_stirrer_vr_r1.py`（布局、986 粒静止 PBD、物化闭包、claim 边界）。
限制：Isaac 4.1 实倒、漏斗过流、headset 加载均为 `not_run`，不当 pass。3 mm 粒子过漏斗喉口未资格化。
同步内容：生成器、测试、本记录、操作说明、薄 `scenario.yaml`、`current_task_heads.v1.json`。未改 `docs/standards` 规则正文。

## Identity

- `task_id`: `scientific_workbench_funnel_pour_flask_to_stirrer`
- artifact family: `funnel_pour_flask_to_stirrer`
- 输出根: `outputs/scientific_workbench_funnel_pour_flask_to_stirrer_vr_r1_20260920`
- 不是飞书目录 Task 04（磁子+瓶塞），也不是 Task 13 交付头。
- 源场景是 `scene_usds` 的 `task_04_pour_liquid_with_funnel`。

## Sources

| 角色 | 路径 |
|---|---|
| 桌面 + 漏斗架 + 量筒 + 986 粒 PBD | `/cpfs/shared/simulation/chenjiantong/scene_usds/scientific_experiments/task_04_pour_liquid_with_funnel/seen_scene_1/scene.usd` |
| 90×35 锥形瓶 | 同树 `task_01_pour_flask_to_cylinder` 的 `obj_conical_flask/ConicalFlask90x35Warp` |
| 磁力搅拌器 | 同树 `task_10_titration_experiment` 的 `obj_magnetic_stirrer` |
| 参考视频 | `external_artifacts/incoming/from_gaoxing/liangtong_loudou_shijiping.mp4` |

源 `scene.usd` SHA-256：task04 `ad5bd29a4827afcb213a201537233c7465d8540e071a40e9e1e14a5f31d2c924`；
task01 `35c707fd67a1a3552d5301922a645d53ed316483ba8a419968a8a51fee62e91c`；
task10 `ba056e7e17fe27c21ad88a877867ebbe9d30e29dde618b7cf9a2bfec1007107b`。

液体原样：986 点、`particleContactOffset/restOffset=3 mm`、`widths=3.564 mm`、青绿 PreviewSurface。不改粒径去迁就漏斗喉口。

## Layout

漏斗从 `obj_funnel_rack` 拿取并放回同一槽。锥形瓶坐在任务内扁圆柱底座上倒液。倒完只把锥形瓶放到磁力搅拌器上，底座留在桌上。不做塞子。

随机化：漏斗+架共组；瓶+底座共组；搅拌器单独；量筒固定（世界坐标烘焙粒子）。

标准桌视觉隐藏用 scene_usds 路径 `/World/table/obj_table/table/Surface/Source/mesh`。
`apply_standard_workbench_vr_presentation` 不认识该路径，本包直接设 visibility，不扩展通用 helper。

## Claims

`layout_authored` 与 `authored_pbd_at_rest` 为真。以下为假或 `not_run`：液体转移、漏斗 conduit、canonical Task 13 成功、Isaac 倒液运行、机器人/benchmark 成功。
