# 水浴显色 r3：颜色、透明度与沉淀高度教学

本任务模拟斐林还原糖阳性反应的外观。蓝色样液先逐渐浑浊，最后形成底部砖红沉淀、上层较清。
时间和颜色是教学演示参数，不是对真实化学动力学、温度或沉淀量的测量。

## 1. 操作和变化时间

这里的秒数是**样液下段接触水浴期间的累计仿真时间**。
只要该区域与假水体积相交就累计，不检查倾角、完整浸没或管口高度；离水暂停，重入继续。

| 时间 | 样液颜色 RGB | 样液 opacity | 沉淀 |
|---|---|---|---|
| 0–30 s | `(0.40, 0.72, 0.95)` | 0.55 | 隐藏 |
| 30–45 s | 连续渐变至 `(0.65, 0.30, 0.14)` | 连续增至0.80 | 从底部生长 |
| 45–60 s | 连续渐变至 `(0.94, 0.97, 1.00)` | 连续降至0.25 | 继续增厚 |
| ≥60 s | 保持近无色 | 保持0.25 | 达到最终砖红沉淀外观 |

30秒是变化起点，不在这一帧跳色。60秒完成后允许取出，近竖直且在2 cm半径内稳定观察3秒成功。
未满60秒提前取出不会成功。观察时移动超过范围会重新累计观察时间，成功后锁定结果至重置。

## 2. 两套材质分别表示什么？

它们分别表示**上层样液**和**固体沉淀**，不是为了切换阶段而准备的重复材质。

```text
/World/obj_sample_tube/VisualLiquid
├── Sample/body、Sample/surface       样液侧壁与表面几何
├── Sediment/body、Sediment/surface   沉淀侧壁与上表面几何
└── Looks
    ├── Sample/Shader                样液 Shader
    └── Sediment/Shader              沉淀 Shader
```

样液颜色完整属性路径：

```text
/World/obj_sample_tube/VisualLiquid/Looks/Sample/Shader.inputs:diffuseColor
```

这是 `UsdPreviewSurface` 材质，颜色使用 `inputs:diffuseColor`（RGB，类型 `color3f`），
透明度使用 `inputs:opacity`（0–1，类型 `float`）。两者都确实写入当前 Shader。
这与滴定任务的 `OmniGlass / inputs:glass_color` 不同。

RGB 三个数依次是红、绿、蓝。截图像素还受容器、背景和照明影响，不能直接等同于材质输入值。

## 3. 为什么先浑浊、后来变清？

我们用颜色和透明度一起表达悬浊程度：30–45秒颜色偏橙棕、opacity增大，表现浑浊；
45–60秒颜色回到近无色、opacity减小，表现上层逐渐变清。这是视觉近似，没有真实悬浮颗粒。

每段采用线性插值：`当前值 = 起始值 + 进度 × (目标值 − 起始值)`。

| 时刻 | RGB | opacity |
|---|---|---|
| 37.5 s | `(0.525, 0.51, 0.545)` | 0.675 |
| 45 s | `(0.65, 0.30, 0.14)` | 0.80 |
| 52.5 s | `(0.795, 0.635, 0.57)` | 0.525 |
| 60 s | `(0.94, 0.97, 1.00)` | 0.25 |

opacity=0.25并不表示液体消失；它比之前更透明，顶部液面仍保持在初始约3 mL样液的高度。

## 4. 沉淀不只是“显示出来”

沉淀颜色固定为 `(0.70, 0.18, 0.07)`，roughness为0.65。
30–33秒其opacity由0升至1，避免突然出现；之后保持为1。

30–60秒沉淀视觉体积从零连续增加至约0.3 mL。控制器根据原管腔截面重新计算顶面高度，
固定底部并改变 Mesh 的 `points`。上层样液的下边界随之提高，顶部液面保持不动。
两部分间保留极小的几何间隙，避免重叠或共面闪烁。

沉淀高度与体积不是简单线性关系，因为离心管底部是锥形。
0.3 mL只是沿用的视觉体积，不代表真实反应产物体积或化学产率。
没有沉淀时，沉淀 Mesh 隐藏；内部保留一个极薄、非退化的占位形状。

## 5. 当前进度和几何在哪里读？

以下属性都在 `/World/obj_sample_tube` 上。VR导入时根路径可能增加 `/World/_scene/`。

| 属性 | 意义 |
|---|---|
| `fehlings:heated_seconds` | 下段接触水体累计时间，最多60秒 |
| `fehlings:color_progress` | 30–60秒反应进度；前30秒为0，60秒为1 |
| `fehlings:reaction_stage` | `warming`、`clouding`、`settling`、`developed` |
| `fehlings:sediment_progress` | 沉淀体积增长进度，0–1 |
| `fehlings:sediment_height_m` | 沉淀顶面相对固定底部的高度，米 |
| `fehlings:stage` | 操作阶段，如加热、允许取出、观察、完成 |
| `fehlings:success` | 成功结果 |
| `fehlings:reset_requested` | 设置为true请求重置 |

关系 `fehlings:sampleShader`、`sedimentShader` 指向两套Shader；
`sampleBody`、`sampleSurface`、`sedimentBody`、`sedimentSurface` 指向四个几何节点。
集成时优先通过这些关系寻找目标，避免写死导入后的路径。

下面的代码在Isaac Sim Script Editor执行，每次读取当前时刻的一次快照，不修改场景：

```python
import omni.usd

stage = omni.usd.get_context().get_stage()
if stage is None:
    raise RuntimeError("请先打开水浴r3场景")
for tube in stage.Traverse():
    if not tube.GetRelationship("fehlings:sampleShader"):
        continue
    print("试管:", tube.GetPath())
    for name in ("heated_seconds", "reaction_stage", "color_progress",
                 "sediment_progress", "sediment_height_m", "stage", "success"):
        print(name, tube.GetAttribute("fehlings:" + name).Get())
    for name in ("sampleShader", "sedimentShader"):
        target = tube.GetRelationship("fehlings:" + name).GetTargets()[0]
        shader = stage.GetPrimAtPath(target)
        print(target, "RGB:", shader.GetAttribute("inputs:diffuseColor").Get(),
              "opacity:", shader.GetAttribute("inputs:opacity").Get())
```

离线可用 `Usd.Stage.Open("实际路径/scene.usd")` 读取文件，但它不会执行控制器，
也看不到另一个Isaac进程中未保存的变化；观察动态状态要读取正在运行的Stage。

## 6. 控制代码与证据边界

控制节点是 `/World/obj_sample_tube/ReactionRuntime/FehlingsGraph/FlowController`，
代码位于其 `inputs:script` 字符串属性中。包内已嵌入纯策略、几何计算和USD更新代码。
仓库源文件分别为 `scripts/fehlings_r2_state.py`（沿用颜色与沉淀策略）和
`scripts/fehlings_r3_contact.py`（接触数学）。r3生成器嵌入新的USD桥接代码。

重置在当步优先恢复零计时、浅蓝样液、隐藏沉淀和未成功状态；下一步才可重新累计。
重置不依赖当前物理位姿是否可读。位姿暂时不可读时不累计反应进度。
手动修改正在运行的颜色或几何可能被控制器覆盖，长期改变需更新策略并重新生成验证。

水浴声明已预热60°C，没有求解样液升温。管子仍是开口离心管教学替代容器。
真实斐林阳性反应产生氧化亚铜沉淀，可参考 [UCLA斐林反应说明](https://www.chem.ucla.edu/~harding/IGOC/F/fehlings_test.html)。
30/60秒和这里的RGB、opacity是可重复的演示规则。
包内图片回放保留的运行里程碑，不是机器人或人类VR操作成功录像。

## 7. r3 的假水与接触条件

烧杯下的 `/World/obj_beaker/VisualWater` 包含 `body`、`surface` 和 `Looks/Water/Shader`。
没有碰撞、刚体、质量或粒子API。整个场景移除了原PBD系统、粒子集合和禁用的PBD代理。
杯壁、杯口和杯底仍是实体，试管不会获得穿墙能力。

假水默认填充杯内有效高度的80%，不是标称容量的80%。
水位由实际内底、内壁和杯口几何计算，当前约为世界高度0.917 m，杯口下留约2 cm。
材质使用 `UsdPreviewSurface`，`inputs:diffuseColor=(0.95,0.98,1)`、
`inputs:opacity=0.12`、`inputs:ior=1.333`、`inputs:roughness=0.02`，零自发光。
水体显示和计时判定共用 `water:profile_m`；初始参数详见 `evidence/water_recipe.json`。

试管根上的 `fehlings:bath`、`fehlings:bathWater` 关系分别指向烧杯和假水。
`fehlings:bath_contact` 表示下段与水体相交，`fehlings:immersed` 作为兼容别名表示同一个接触结果，
不再表示完整浸没。`fehlings:water_surface_z` 仅作显示水位遥测，实际判定使用烧杯局部坐标。

控制器读取试管、烧杯的实际物理位姿，将初始含样液下段（也包含之后的沉淀区域）变换到烧杯坐标，
按轴向profile分成截锥，进行凸体相交窄相位计算。包围盒重叠只作粗筛，不足以触发反应。
假水不产生碰撞事件，但几何计算仍能判定接触；浅浸、偏心和倾斜接触均可。
只有上段碰水、只碰杯壁、仍在水面以上或杯外，都不累计。
显示水面用96边形近似圆形，接触使用同一剖面的解析圆截面；边缘差异为很小的离散误差。

烧杯移动时，假水和接触区域同步跟随。假水没有自由液面或洒出模拟。管内样液和沉淀也刚性跟随试管，倾斜时不模拟保持水平或流出。
接触量不影响计时速率：接触1秒累计1秒；不模拟残热、浓度稀释或非规范操作的化学后果。
取出后的观察仍要求近竖直及稳定3秒；该观察要求与加热接触条件分开。
