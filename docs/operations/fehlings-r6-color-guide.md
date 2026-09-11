# 水浴显色 r6：五层等高，30秒蓝→绿→黄→橙→橙红

从 r5 派生，目标运行时 Isaac Sim 4.5。规范依据：仓库 `docs/standards/materials-and-liquids.md`
的 MAT-001～006 与 `docs/standards/task-state.md` 的 STATE-001～006。
五层是同一份视觉样液的高度分区，用于表现不同位置的显色进度，不表示五种独立液相。

## 几何与材质

每层占原液柱高度20%，不是等体积。总液面仍在原约3 mL样液的位置。
管腔底部局部 z=4 mm，顶部 z≈32.608 mm，每层高≈5.722 mm。
五个 Mesh 的相邻侧面精确相接，使用一致的边界法线，没有内部横向封口；
仅整段样液底部和最上方液面封口，减少初始同色时的横向分界。
运行时不改顶点、拓扑、法线、extent、变换或可见性。

五套 UsdPreviewSurface 材质仅更新 `inputs:diffuseColor`（color3f）、
`inputs:opacity`（float）与 `inputs:roughness`（float）。无额外颗粒、纹理或自发光。
颜色适度增强辨识度；以真实玻璃和水浴中的渲染作为外观验收，材质RGB不是截图像素。

## 显色曲线

按累计有效触水仿真时间计时；时间夹取到0～30秒。0～3秒保持蓝色。
每层依次连续经过蓝、绿、黄、橙、橙红，层与层的关键时刻错开；关键点间线性插值。

| 从下到上 | 蓝色保持至 | 绿色关键点 | 黄色关键点 | 橙色关键点 | 橙红终态 |
|---|---|---|---|---|---|
| Layer0 | 3 s | 7 s | 12 s | 18 s | 24 s |
| Layer1 | 3.5 s | 8.25 s | 13.5 s | 19.5 s | 25.5 s |
| Layer2 | 4 s | 9.5 s | 15 s | 21 s | 27 s |
| Layer3 | 4.5 s | 10.75 s | 16.5 s | 22.5 s | 28.5 s |
| Layer4 | 5 s | 12 s | 18 s | 24 s | 30 s |

颜色关键点 RGB 依次为 `(0.08,0.45,0.95)`、`(0.12,0.70,0.20)`、`(0.95,0.80,0.07)`、
`(1.00,0.40,0.04)`、`(1.00,0.22,0.035)`。
opacity 依次为 `0.70/0.82/0.90/0.95/0.98`，roughness 为 `0.10/0.18/0.28/0.40/0.50`。
30秒时所有层达到相同橙红浑浊终态；不再恢复 r5 的大片透明上清液。

参考视频位于 `external_artifacts/incoming/from_xinyu/菲林试剂.mp4`，实际实验画面结束于约54秒；
后面是片尾。水浴段标有×3，前面还有试剂配制与振荡，因此视频时长不是反应动力学时间。
参考的是蓝→绿→黄→橙红的色序、变化不同步和最后基本整段橙红的外观。
视频横穿试管的亮线是烧杯水面，不作为管内分层依据。

## 任务操作

沿用 r5 的样液区域与假水体积相交判定；浅浸、偏心和倾斜接触均可累计，离水暂停，重入继续。
仅上段碰水、杯外或只碰杯壁不累计。读取真实刚体位姿，位姿缺失时暂停。
累计30秒后允许取出，近竖直（20°内）、在2 cm半径内稳定观察3秒成功；成功锁定至重置。
重置当步优先恢复零计时、未成功、五层同蓝，不在同一步继续加热；材质重置不依赖物理位姿可读。
玻璃、碰撞、布局和假水基于 r5；不新增配试剂或振荡操作要求。

## 节点与读取

试管根 `/World/obj_sample_tube`；VR挂载可能增加 `/World/_scene/` 前缀。
优先用关系获取目标，底部索引0、顶部索引4：

- `fehlings:layerMeshes`：五个 `VisualLiquid/Layer0`～`Layer4` Mesh。
- `fehlings:layerShaders`：五个 `VisualLiquid/Looks/Layer0/Shader`～`Layer4/Shader`。
- `fehlings:layer_bounds_m`：各层固定的局部 z 下/上界。
- `fehlings:layer_count=5`、`fehlings:layer_height_fraction=0.2`。
- `fehlings:layer_progress`：五层各自的显色进度0～1，不代表体积/沉淀高度。
- `fehlings:color_progress`：3～30秒的整体时间进度，3秒前为0。
- `fehlings:reaction_stage`：warming、greening、yellowing、reddening、converging、developed。
- `fehlings:heated_seconds`、`stage`、`success`、`observation_seconds`、`reset_requested` 保留任务状态用途。
- `fehlings:policy_version=visual_five_layers_v6`。

r5 的 sample/sediment 两套关系与沉淀高度字段在新包中移除，不把其中一层冒充完整上清液或沉淀量。
旧版包及旧版语义保持在对应历史产物中。

在 Isaac Sim Script Editor 读取当前 Stage：

```python
import omni.usd

stage = omni.usd.get_context().get_stage()
if stage is None:
    raise RuntimeError("请先打开 r6 场景")
for tube in stage.Traverse():
    relation = tube.GetRelationship("fehlings:layerShaders")
    if not relation:
        continue
    print(tube.GetPath(), tube.GetAttribute("fehlings:heated_seconds").Get())
    for i, path in enumerate(relation.GetTargets()):
        shader = stage.GetPrimAtPath(path)
        print(i, {key: shader.GetAttribute("inputs:" + key).Get()
                  for key in ("diffuseColor", "opacity", "roughness")})
```

控制器仍位于 `ReactionRuntime/FehlingsGraph/FlowController`，自包含脚本嵌在 `inputs:script`。
手动改变运行中的材质可能被下一步控制器覆盖；长期改变应改策略、重新生成并验证。

## 验证与复现

生成：`python -m scripts.generate_fehlings_water_bath_r6`。
运行：`/isaac-sim/python.sh -m scripts.validate_fehlings_water_bath_r6 --root <包目录> --out <报告.json>`。
渲染：`/isaac-sim/python.sh -m scripts.render_fehlings_water_bath --root <包目录> --report <报告.json>`。
完成三次独立冷启动、目视检查后，用 `scripts.finalize_fehlings_water_bath_r6` 打包并校验。

截图回放保留的实际运行状态；带 `withdrawn` 的中间帧是指定轨迹暂时取出后的实际暂停快照，
用于避免水浴遮挡，不是加热状态的伪造姿态。外观比较应使用相同出水近景。
五层会有离散色差，不模拟视频中的云絮流动、混合或真实颗粒。假液体刚性跟随试管，
不保持水平、不洒出；不声明真实化学、温度求解、机器人操作成功或 Isaac Sim 4.1 资格。

已检查的渲染中，蓝、绿／青绿、黄绿、黄橙、橙红的时间变化可辨；中途上部和管尖有色差，
初始与完成态没有五个内部液面的叠层外观。玻璃与照明仍使下部偏暗，黄色可呈赭色、红色可呈红棕。
推荐先看包内 `evidence/initial_scene/color_progression.png`（0、9、15、21、27、30秒同尺度裁剪），
再看对应全幅 `*_withdrawn_closeup.png` 与 `observed_closeup.png`。
图像只是对实际运行快照的相同裁剪和缩放，无额外调色；本地目视检查记录不是独立审查。
