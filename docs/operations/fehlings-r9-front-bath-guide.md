# 斐林水浴 r9：正对隔着烧杯清水看清浸入变色

从 r8 派生。目标运行时 Isaac Sim 4.5。规范依据 MAT-001～006。
假水 `water:profile_m` 与 `fill_height_ratio=0.8` 不变，无碰撞。试管、8 mL 五层和 30 秒策略不变。

## 问题

r8 把假水换成 OmniGlass 后，斜俯视 closeup 仍主要看见**水面以上**的颜色。
掠射 `through_wall` 和后来的正视 `front_bath` 里，水面以下圆底（砖红该出现的位置）仍是近黑。
r8 没有正视浸入变色视频。出水图不能当隔杯验收。

## 假水视觉

几何属性仍在 `/World/obj_beaker/VisualWater`。`fill_height_ratio=0.8` 与 `water:profile_m` 与 r8 相同。
`body` 改成约 1.5 mm 贴壁薄壳，中间留空。`surface` 是贴壁液面环，不是挡住管底的实心圆盘。
视线穿过杯壁 + 薄水膜 + 试管，而不是实心水柱。Shader 仍是包内 OmniGlass 近无色清水。

## 验收

必须看正视 `t3/t15/t21/t30_front_bath.png` 和试管**留在水里**的变色 MP4。
水面以下整段（含圆底）要能叫出蓝/绿/黄/橙红/砖红。出水图只作不回退。
掠射 `through_wall` 和斜俯视 closeup 不是本任务的隔杯验收镜头。

视频（Git 外）：`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r9_20260914/r9_front_bath.mp4`

后来核对加热回放：管底只低于液面约 6 mm，8 mL 大半在空气里。深插姿态改到 r10，本包不改写。
