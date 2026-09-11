# 水浴显色 r5：两块固定假液体，材质随加热时间变化

r5 严格由 r3 派生，目标运行时为 Isaac Sim 4.5。它保留 r3 的接触、计时、观察和重置规则。
规范依据：MAT-001～006（仓库 `docs/standards/materials-and-liquids.md`）、
STATE-001～006（仓库 `docs/standards/task-state.md`）。

## 1. 固定区域与外观

样液最底端至原液面的高度分为上部 2/3、下部 1/3。两块分别使用一套 UsdPreviewSurface 材质，
各自包含侧壁和表面 Mesh；运行时不改 `points`、`extent`、拓扑、变换或 `visibility`。
分界侧壁精确相接；只保留下块的上表面，去掉上块底盖，避免两个共面界面。
上液面仍保持原约 3 mL 样液的高度。高度比例不是体积比例，也不是化学产率。
当前管腔底端局部 z 为 4 mm，液面为 32.608 mm，固定分界为 13.536 mm；下块高度为 9.536 mm。
r3 最终视觉沉淀高约 10.112 mm，因此三分之一比例实际略薄于 r3；本版以用户确认的高度比例为准，
不宣称比 r3 更厚。辨识主要依靠砖红、不透明、偏哑光与上部变清的对比。

| 累计触水仿真时间 | 上块 | 下块 |
|---|---|---|
| 0–30 s | 蓝色、半透明 | 同样蓝色、半透明 |
| 30–45 s | 连续变为橙棕浑浊 | 连续变红，增加不透明度和粗糙度 |
| 45–60 s | 连续变为近无色、较透明 | 继续变为砖红、不透明、偏哑光 |
| ≥60 s | 保持完成态 | 保持完成态 |

上块沿用 r3 颜色曲线：30 s RGB `(0.40,0.72,0.95)`、opacity `0.55`；
45 s `(0.65,0.30,0.14)`、`0.80`；60 s `(0.94,0.97,1.00)`、`0.25`。roughness 为 `0.08`。
下块在 30–60 s 线性插值：RGB 从同样的蓝色到 `(0.70,0.18,0.07)`，opacity 从 `0.55` 到 `1`，
roughness 从 `0.08` 到 `0.65`。无额外纹理、颗粒几何或发光。
30 s 前进度为零，60 s 后夹取到一。显色是沉淀外观增强，不是沉淀层长高。

## 2. 操作与任务逻辑

样液下段与假水体积相交就累计仿真时间，浅浸、倾斜和部分接触均可；离水暂停，重入继续。
仅上段碰水、只碰杯外壁、仍在水面以上或杯外不累计。完整几何窄相位和实际刚体位姿读取沿用 r3。
累计60秒后，取出水面、近竖直（20°内）并在2 cm半径内稳定观察3秒才成功；成功锁定到重置。
重置当步恢复零计时、未成功、两块相同的蓝色材质；当步不继续加热，不改变物理位姿或固定几何。
同样保留无位姿时暂停和不依赖物理位姿的材质重置。

## 3. 属性与读取

试管根为 `/World/obj_sample_tube`，VR挂载后可能增加 `/World/_scene/` 前缀，优先用关系找目标：

- `fehlings:sampleShader` → `VisualLiquid/Looks/Sample/Shader`（上块）。
- `fehlings:sedimentShader` → `VisualLiquid/Looks/Sediment/Shader`（下块）。
- 两者更新 `inputs:diffuseColor`（color3f）、`inputs:opacity`（float）、`inputs:roughness`（float）。
- `sampleBody` / `sampleSurface` / `sedimentBody` / `sedimentSurface` 仍指向固定几何。
- `fehlings:sediment_progress` 在 r5 表示材质显现进度，不再表示体积增长。
- `fehlings:sediment_height_m` 是恒定下块高度，初始和重置也不为零。
- `fehlings:sediment_height_fraction` 固定为 `1/3`。
- 其余 `heated_seconds`、`color_progress`、`reaction_stage`、`bath_contact`、`immersed`、
  `observation_seconds`、`stage`、`success`、`reset_requested` 的意义沿用 r3。
- `fehlings:policy_version` 为 `visual_fixed_regions_v5`。

在 Isaac Sim Script Editor 读取运行中的 Stage：

```python
import omni.usd

stage = omni.usd.get_context().get_stage()
if stage is None:
    raise RuntimeError("请先打开 r5 场景")
for tube in stage.Traverse():
    if not tube.GetRelationship("fehlings:sampleShader"):
        continue
    print(tube.GetPath(), tube.GetAttribute("fehlings:heated_seconds").Get())
    for name in ("sampleShader", "sedimentShader"):
        target = tube.GetRelationship("fehlings:" + name).GetTargets()[0]
        shader = stage.GetPrimAtPath(target)
        print(name, {key: shader.GetAttribute("inputs:" + key).Get()
                     for key in ("diffuseColor", "opacity", "roughness")})
```

控制节点仍为 `ReactionRuntime/FehlingsGraph/FlowController`；包内嵌入完整运行代码，不依赖仓库 Python 模块。
手动改运行材质可能在下一步被自动控制器覆盖。

## 4. 验证与局限

几何、材质数值、运行结果和渲染分别验收。图片回放实际保留的运行快照，恢复两套材质全部三个属性；
不是机器人/人类操作录像。初始、浑浊、分层、完成、重置以及水浴内外分别观察。
透明容器、刻度、反射和水浴遮挡会影响可见颜色，不能把截图像素等同于 RGB 输入。
当前近景中，初始蓝色和最终管尖砖红可辨，初始内部界面有轻微轮廓；架内和水浴内颜色更暗。
观察前后优先对照 `evidence/initial_scene/appearance_before_after.png`，浑浊出水态见
`pause_begin_closeup.png`；全景用于定位设备，不用于判断沉淀颜色。
假液体随试管刚性运动，不保持水平、不晃动或洒出；无真实化学、传热或沉淀颗粒动力学。
保留 r3 的 GPU/SDF 物理基线；此包的证据范围为 Isaac Sim 4.5，不继承 r4 的 CPU 碰撞改造。

生成入口：`python -m scripts.generate_fehlings_water_bath_r5`。
验证入口：`/isaac-sim/python.sh -m scripts.validate_fehlings_water_bath_r5 --root <包目录> --out <报告.json>`。
渲染入口：`/isaac-sim/python.sh -m scripts.render_fehlings_water_bath --root <包目录> --report <报告.json>`。
完成三次独立冷启动及视觉检查后，用 `scripts.finalize_fehlings_water_bath_r5` 完成闭包、归档和校验。
