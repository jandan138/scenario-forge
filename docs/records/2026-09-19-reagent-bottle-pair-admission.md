# Reagent bottle 90×55 and matched 45/40 plug admission

Date: 2026-09-19.

规范依据：当前 `docs/standards` 资产接入与验证正文。
涉及规则：ASSET-001、ASSET-002、ASSET-003、VAL-001、VAL-002、VAL-005。
变化：**规范无需变更**。本次只把已有 `manual_glassware_v1` 成对刚体接入来源绑定，
不新增通用磨口、液体容纳或插拔资格。
验证：ConvertAsset `normalize-asset` static+Isaac 4.1 runtime smoke `pass`；
Scenario Forge 绑定测试 `tests/test_reagent_bottle_pair_handoff.py`。
限制：4.1 准入不等于 4.5 插合测试、倒液或机器人策略成功；瓶+塞仍是两件独立刚体。
同步内容：来源绑定、本记录、ConvertAsset 生产者记录。未改 `docs/standards` 规则正文。

## Bindings

`configs/source_bindings/scientific_workbench_reagent_bottle_pair_20260919.yaml`

| Asset ID | Package |
|---|---|
| `scientific_workbench_reagent_bottle_90x55_original_simready` | ConvertAsset `scientific_workbench_glass_web_standard_20260819` 已准入瓶 |
| `scientific_workbench_reagent_bottle_plug_45_40_original_simready` | ConvertAsset `scientific_workbench_reagent_bottle_pair_20260919` 新准入塞 |

两者都是 `rigid_object_unqualified_task_instance`，根 prim `/ObjectRoot`。
塞子与 `ground_glass_stopper_29_42` 不是同一件；29/42 是锥形瓶/平底烧瓶配套。

## Purchase dimensions

Authoritative millimetre values come from `manual_glassware_v1` `model_spec.json`
and the Blender lathe profiles. Shop for a **500 mL 白色广口试剂瓶，磨口玻璃塞，无螺纹**。
Exact NS 45/40 is better than a 29/42 flask stopper.

### Bottle `reagent_bottle_90x55`

| 参数 | 数值 | 采购怎么用 |
|---|---|---|
| 标称容量 | 按 **500 mL** 搜 | 内腔圆柱段约 511 mL，不是 250 mL |
| 瓶身最大外径 | **90 mm** | 圆柱段外径，最重要 |
| 瓶口外径 | **55 mm** | 广口，不是细口 |
| 瓶口内径（顶） | **45.4 mm** | 2×22.7 mm |
| 磨口内径（底） | **41.2 mm** | 1:10 锥孔下端 |
| 瓶高（含口） | **180 mm** | 底座到瓶口顶 |
| 磨口长度 | **40 mm** | 标准 45/40 的“40” |
| 壁厚 / 底厚 | 2.5 mm / 5.0 mm | 普通厚壁试剂瓶即可 |
| 质量 | 0.280 kg | 仅仿真用 |

### Plug `reagent_bottle_plug_45_40`

| 参数 | 数值 | 采购怎么用 |
|---|---|---|
| 磨口规格 | **约 NS 45/40，锥度 1:10** | 问商家“45/40 磨口玻璃塞” |
| 塞芯底径 | **40.5 mm** | 插入端 |
| 塞芯顶径 | **44.7 mm** | 40 mm 高度处 |
| 磨口段长 | **40 mm** | 与瓶口配套 |
| 塞帽最大外径 | **68 mm** | 扁圆蘑菇帽，不是桨形把手 |
| 塞总高 | **58.5 mm** | 芯底到帽顶 |
| 质量 | 0.085 kg | 仅仿真用 |

### 淘宝 / 京东搜索词

- `500ml 白色广口试剂瓶 磨口玻璃塞`
- `广口试剂瓶 500ml 玻璃塞 磨砂口 白色`

对照卖家图：圆柱瓶身、短磨砂颈、扁圆玻璃帽塞。不要蓝盖/红盖螺纹试剂瓶，不要锥形瓶 29/42 塞。

若商家不标 45/40，把这四个数发给客服核对：瓶身外径 90 mm、瓶高 180 mm、瓶口外径 55 mm、塞帽外径约 68 mm。

## Pictures

Producer pair renders and the physical reference photograph:

- `/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/scientific_workbench_reagent_bottle_pair_20260919/purchase_views/reagent_bottle_reference.jpg`
- `/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/scientific_workbench_reagent_bottle_pair_20260919/purchase_views/blender_assembled.png`
- `/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/scientific_workbench_reagent_bottle_pair_20260919/purchase_views/blender_exploded.png`

Admitted Isaac 4.1 package views:

- bottle `.../reagent_bottle_90x55_original_simready/evidence/runtime_smoke/material_views/orbit_3q.png`
- plug `.../reagent_bottle_plug_45_40_original_simready/evidence/runtime_smoke/material_views/orbit_3q.png`
