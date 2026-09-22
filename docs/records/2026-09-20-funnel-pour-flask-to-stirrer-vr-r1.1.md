# Funnel pour then place flask on stirrer VR r1.1

Date: 2026-09-20.

规范依据：当前 `docs/standards` USD 组织、资产接入、材质/液体、验证与交付正文。
涉及规则：ASSET-001、ASSET-005、ASSET-006、USD-003、USD-004、USD-005、USD-006、MAT 液体声明、VAL-001、VAL-002、VAL-003、VAL-005、VAL-006。
变化：**规范无需变更**。本包仍是任务内扁圆柱底座例外，不改通用桌板、漏斗喉口或 PBD 默认配方。
r1 Play 后锥形瓶在动态底座上晃；r1.1 保持底座可交互（非 kinematic），瓶子抬高 2 mm 再落下，底座质量改为 0.5 kg 并加线/角阻尼。
未做 Isaac Play 静止证明，不当 pass。
验证：`tests/test_funnel_pour_flask_to_stirrer_vr_r1.py`（布局、986 粒静止 PBD、动态底座、物化闭包、claim 边界）。
限制：Isaac 4.1/4.5 实倒、漏斗过流、headset 加载、Play 后无晃均为 `not_run`。
同步内容：生成器、测试、本记录、操作说明、薄 `scenario.yaml`、`current_task_heads.v1.json`。未改 `docs/standards` 规则正文。

## Identity

- `task_id`: `scientific_workbench_funnel_pour_flask_to_stirrer`
- artifact family: `funnel_pour_flask_to_stirrer`
- 输出根: `outputs/scientific_workbench_funnel_pour_flask_to_stirrer_vr_r1_1_20260920`
- 替换 r1 作为当前 candidate。r1 布局声明仍见 [r1 记录](2026-09-20-funnel-pour-flask-to-stirrer-vr-r1.md)。

## Stability change

底座仍是 `RigidBodyAPI` 动态刚体，`physics:kinematicEnabled=false`，VR 可抓。
锥形瓶 translate z 从 0.770 改为 0.772。底座碰撞用 cylinder + `convexHull`。
不把底座改成 kinematic/static；若 Play 后仍明显晃，下一版去掉底座，瓶子直接放桌面。
