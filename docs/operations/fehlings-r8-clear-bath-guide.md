# 斐林水浴 r8：透过烧杯清水看清试管内变色

从 r7 派生，目标运行时 Isaac Sim 4.5。规范依据：`docs/standards/materials-and-liquids.md`
的 MAT-001～006。本次只改烧杯假水光学，不改假水总量、接触几何、试管、8 mL 五层或 30 秒策略。

## 问题

r7 出水近景已经能看清蓝→绿→黄→橙→红。浸在烧杯里、透过杯壁和假水看时，水面以下会变成近黑空管。
露出水面的同色样液仍然清楚，所以不是五层策略或试管玻璃把颜色写丢了。

r3 起的假水是 UsdPreviewSurface，`opacity=0.12`，body/surface 双面。渲染里整杯水像烟灰体积，
嵌套透明层把水下样液吃掉。验收不能只看出水图。

## 假水光学

几何仍是 `/World/obj_beaker/VisualWater` 的 `body` 与 `surface`，`water:profile_m` 与
`water:fill_height_ratio=0.8` 与 r7 相同，无碰撞、无质量。

Shader 换成包内 `deps/objects/obj_beaker/deps/mdl/OmniGlass.mdl`：

| 输入 | 值 |
|---|---|
| `glass_color` | `(0.97, 0.99, 1.0)` 近无色，不是教学蓝 |
| `glass_ior` | `1.333` |
| `thin_walled` | `true` |
| `enable_opacity` | `false` |
| `frosting_roughness` | `0.02` |
| `depth` | `0.002` |
| body/surface `doubleSided` | `false` |

这是滴定接收液已经用过的「透过玻璃看颜色」路线。参数是本任务的教学可读性配方，不是通用清水默认值。

## 样液与任务

试管、8 mL、五层、`visual_five_layers_v6`、接触判定和重置沿用 r7。运行时仍只写五套样液的
`diffuseColor` / `opacity` / `roughness`。不要把烧杯假水改回 PreviewSurface alpha。

## 验证

```bash
PYTHONPATH=src python -m scripts.generate_fehlings_water_bath_r8 --out <全新输出目录>
/isaac-sim/python.sh -m scripts.validate_fehlings_water_bath_r8 --root <包目录> --out <报告.json>
/isaac-sim/python.sh -m scripts.render_fehlings_water_bath --root <包目录> --report <报告.json>
PYTHONPATH=src python -m scripts.finalize_fehlings_water_bath_r8 --root <包目录> --report <报告1.json> --report <报告2.json> --report <报告3.json>
```

必须看浸入态 `t3/t15/t30_closeup.png` 与 `*_through_wall.png`：水面以下要能叫出当时的蓝/绿/黄/橙/红。
出水图不得回退。材质 RGB 不是截图像素。

浸入近景当时被当作水下颜色的验收视角。斜穿杯壁的 `through_wall` 在掠射角下仍会压暗管底。
后来在冻结 r8 上用正视 `front_bath` 看，圆底砖红仍近黑；隔杯验收改到 r9。本包配方与体积不改写。
