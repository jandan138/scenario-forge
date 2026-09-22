# Funnel pour then place flask on stirrer VR r1.2

Date: 2026-09-20.

规范依据：当前 `docs/standards` USD 组织、资产接入、材质/液体、验证与交付正文。
涉及规则：ASSET-001、ASSET-005、ASSET-006、USD-003、USD-004、USD-005、USD-006、MAT 液体声明、VAL-001、VAL-002、VAL-003、VAL-005、VAL-006。
变化：**规范无需变更**。去掉任务内扁圆柱底座后，不再需要 ASSET-006 底座例外。
r1 / r1.1 在 Isaac 4.5 Play 后锥形瓶仍在可交互底座上晃，按约定去掉底座，瓶子直接坐桌面。
验证：`tests/test_funnel_pour_flask_to_stirrer_vr_r1.py`（无底座、桌面落点、986 粒静止 PBD、物化闭包、claim 边界）。
限制：Isaac 4.1/4.5 实倒、漏斗过流、headset 加载均为 `not_run`。
同步内容：生成器、测试、本记录、操作说明、薄 `scenario.yaml`、`current_task_heads.v1.json`。未改 `docs/standards` 规则正文。

## Identity

- `task_id`: `scientific_workbench_funnel_pour_flask_to_stirrer`
- artifact family: `funnel_pour_flask_to_stirrer`
- 输出根: `outputs/scientific_workbench_funnel_pour_flask_to_stirrer_vr_r1_2_20260920`
- 替换 r1.1 作为当前 candidate。

## Layout

漏斗从 `obj_funnel_rack` 拿取并放回同一槽。锥形瓶初始在桌面 `(-0.11, -0.16, 0.755)`。
倒完把锥形瓶放到磁力搅拌器上。不做塞子，不放扁圆柱底座。
