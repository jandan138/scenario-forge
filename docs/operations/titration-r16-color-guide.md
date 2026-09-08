# r1.6 滴定液体颜色教学：一块液体、一套材质、连续变色

适用任务包：`scientific_workbench_traditional_acid_base_titration_vr_r1_6`，Isaac Sim 4.5。
本文讲锥形瓶内的假液体；滴定管内部液体沿用原设置。

## 1. 现在只有一套液体几何与材质

r1.6 用一个 Mesh、一套 Material 和一个 Shader 表示锥形瓶内的液体。
整个滴定过程始终显示同一块液体，仅更新 Shader 的 `inputs:glass_color`。
无色、渐变、淡粉、过量是逻辑阶段，不再对应四套几何或材质。

```text
旋塞角度 → 流速 → 累计接收液量 → 计算 RGB
                                    ↓
                   同一个 Shader 的 inputs:glass_color
                                    ↓
                          同一个液体 Mesh 显示
```

## 2. Prim 路径和属性

Prim 是 USD 场景树中的节点；Mesh 定义几何，Material 绑定到几何，Shader 保存颜色等材质参数。

```text
/World/obj_receiver_flask/VisualLiquid
├── Solution                  唯一液体 Mesh
├── Looks
│   └── Water                 唯一液体 Material
│       └── Shader            唯一液体 Shader
└── StirBar                   磁子，独立保留
```

颜色所在的完整 Shader 路径：

```text
/World/obj_receiver_flask/VisualLiquid/Looks/Water/Shader
```

属性名是 **`inputs:glass_color`**，类型是 **`color3f`**。完整属性路径为：

```text
/World/obj_receiver_flask/VisualLiquid/Looks/Water/Shader.inputs:glass_color
```

三个浮点数分别为红、绿、蓝 `(R, G, B)`；本任务使用 0–1 范围。
无色外观为 `(0.97, 0.99, 1.0)`，淡粉为 `(1.0, 0.80, 0.88)`，深色终值为 `(0.85, 0.12, 0.28)`。
材质输入值不等于截图像素值，实际画面还受折射、反射、光照和背景影响。

滴定站 `/World/obj_titration_station` 上保留这些状态和关系：

| 属性或关系 | 用途 |
|---|---|
| `titration:dispensed_volume_ml` | 累计接收液量，mL |
| `titration:indicator_phase` | `colorless`、`transition`、`endpoint_pale_pink`、`overshoot` |
| `titration:flow_rate_ml_s` | 当前流速 |
| `titration:stopcock_angle_deg` | 当前旋塞角度 |
| `titration:task_success` | 本次已成功的锁定结果 |
| `titration:receiverLiquidVisuals` | 只指向 `VisualLiquid/Solution` |
| `titration:receiverLiquidShader` | 只指向 `VisualLiquid/Looks/Water/Shader` |

`Solution` 的 `visibility` 保持 `inherited`，控制器不再切换可见性；如果人为隐藏父节点，它仍会随父节点隐藏。
该 Mesh 不再有 `titration:phase` 属性，当前阶段统一读取滴定站的 `titration:indicator_phase`。

## 3. 怎么读取当前颜色？

### 3.1 在 Isaac Sim 界面查看

打开 `scene.usd` 并允许脚本执行。在 Stage 树选中 `VisualLiquid → Looks → Water → Shader`，
在属性面板找 `glass_color`。启动仿真、转动旋塞，即可观察其数值更新。

通过 VR 导入时，根路径可能变成 `/World/_scene/...`。下面的示例通过关系找到液体，不依赖固定根路径。

### 3.2 Script Editor 实时读取

每运行一次代码，打印当前打开场景的一次快照。代码只读，不修改 USD。

```python
import omni.usd
from pxr import UsdGeom


def print_liquid_colors(stage):
    if stage is None:
        raise RuntimeError("请先打开滴定场景。")

    # 直接打开和 VR 导入都使用关系查找，不依赖固定的 /World 根路径。
    stations = [
        prim for prim in stage.Traverse()
        if prim.GetRelationship("titration:receiverLiquidShader")
    ]
    if not stations:
        raise RuntimeError("没有找到滴定站的液体材质关系。")

    for station in stations:
        print("\n滴定站:", station.GetPath())
        for name in (
            "titration:dispensed_volume_ml",
            "titration:indicator_phase",
            "titration:flow_rate_ml_s",
            "titration:task_success",
        ):
            attr = station.GetAttribute(name)
            print(name, "=", attr.Get() if attr else "属性不存在")

        print("液体几何和可见性:")
        for path in station.GetRelationship("titration:receiverLiquidVisuals").GetTargets():
            prim = stage.GetPrimAtPath(path)
            if not prim:
                print("找不到节点:", path)
                continue
            visible = UsdGeom.Imageable(prim).ComputeVisibility() != "invisible"
            print(path, "最终可见 =", visible)

        print("材质颜色:")
        for path in station.GetRelationship("titration:receiverLiquidShader").GetTargets():
            shader = stage.GetPrimAtPath(path)
            if not shader:
                print("找不到 Shader:", path)
                continue
            attr = shader.GetAttribute("inputs:glass_color")
            if not attr:
                print("没有 glass_color:", path)
                continue
            rgb = attr.Get()
            print(path, attr.GetName(), "=", tuple(float(v) for v in rgb))


print_liquid_colors(omni.usd.get_context().get_stage())
```

例如，在稳定淡粉阶段，会读到接近：

```text
titration:indicator_phase = endpoint_pale_pink
inputs:glass_color = (1.0, 0.8000000119, 0.8799999952)
```

它与 `(1.0, 0.80, 0.88)` 表示同一组预期颜色；末尾小数差异来自浮点数存储。

### 3.3 离线读取：读的是文件，不是另一个正在运行的仿真

下面的代码可在有 `pxr` 的 Python 环境运行，例如 Isaac Sim 的 Python 环境。把 `scene_path` 换成解压后的实际路径。

```python
from pxr import Usd

scene_path = "/替换为实际任务包路径/scene.usd"
stage = Usd.Stage.Open(scene_path)
if stage is None:
    raise RuntimeError("无法打开 scene.usd，请检查路径。")

shader = stage.GetPrimAtPath(
    "/World/obj_receiver_flask/VisualLiquid/Looks/Water/Shader"
)
if not shader:
    raise RuntimeError("没有找到液体 Shader，请确认是 r1.6 原始场景。")

attr = shader.GetAttribute("inputs:glass_color")
print("属性类型:", attr.GetTypeName())
print("磁盘中的颜色:", tuple(float(v) for v in attr.Get()))
```

离线 `Usd.Stage.Open()` **不会执行滴定控制器**，也不会读取另一个 Isaac 进程尚未保存的运行状态。要观察正在变色的数值，应使用上一节的实时读取方式。

## 4. 无色是如何变成淡粉的？

### 4.1 颜色由累计液量决定

令 `V` 表示锥形瓶累计接收液量，即 `titration:dispensed_volume_ml`。

| 液量范围 | 阶段 | RGB 的变化 |
|---|---|---|
| `V < 150/11`，约 13.63636 mL | 无色 | 固定为 `(0.97, 0.99, 1.0)` |
| `150/11 ≤ V < 15` | 渐变 | 从无色连续变化到淡粉 |
| `15 ≤ V ≤ 3165/187`，上限约 16.92513 mL | 稳定淡粉 | 固定为 `(1.0, 0.80, 0.88)` |
| `V > 3165/187` | 过量 | 继续加入的前 1 mL 内逐渐加深，随后保持深色 |

计算时使用公式值，表中的小数只是便于阅读的近似值。

### 4.2 渐变就是“按进度混合两种颜色”

从约 13.63636 mL 开始，定义渐变进度 `α`：

```text
α = (V − 150/11) / (15 − 150/11)

当前颜色 = 起始颜色 + α × (目标颜色 − 起始颜色)
```

对 R、G、B 三个通道分别计算。`α = 0` 是刚开始，`α = 0.5` 是走到一半，`α = 1` 是到达淡粉。

| 累计液量 | 渐变进度 | RGB |
|---|---:|---|
| 约 13.63636 mL | 0% | `(0.97, 0.99, 1.0)` |
| 约 14.31818 mL | 50% | `(0.985, 0.895, 0.94)` |
| 15 mL | 100% | `(1.0, 0.80, 0.88)` |

所以它**不是从无色直接跳成粉色**。阶段名称和显示的 Mesh 会切换，但阶段边界两侧的 RGB 是连续衔接的。仿真每步更新一次，画面仍以离散帧显示；很慢的帧率会让渐变看起来不够细腻。

## 5. 变成粉色后，颜色值怎样加深？

### 5.1 先保持淡粉，不立即加深

在 `15–约16.92513 mL` 之间，RGB 始终保持：

```text
(1.0, 0.80, 0.88)
```

这就是留给操作者关阀的淡粉窗口。

### 5.2 过量后，再用 1 mL 完成加深

设窗口上限 `V_end = 3165/187`，约 16.92513 mL。超过它后：

```text
β = min(1, (V − V_end) / 1 mL)
当前颜色 = 淡粉色 + β × (深色 − 淡粉色)
```

| 累计液量 | 过量进度 | RGB |
|---|---:|---|
| 约 16.92513 mL | 0% | `(1.0, 0.80, 0.88)` |
| 约 17.42513 mL | 50% | `(0.925, 0.46, 0.58)` |
| 约 17.92513 mL 及以上 | 100% | `(0.85, 0.12, 0.28)` |

这里不是把三个通道一起提高。红色从 1.0 降到 0.85，绿色从 0.80 大幅降到 0.12，蓝色从 0.88 降到 0.28。绿色和蓝色减少得更多，整体呈现更深、更偏红的颜色。

## 6. 旋塞角度与变色时间是什么关系？

以关闭位置为 0°，控制器取实际关节角度的绝对值并限制在 0–90°：

```text
角度 ≤ 5°：Q = 0
角度 > 5°：Q = (30/11) × (角度 − 5) / 85，单位 mL/s
本步增加的液量 = Q × 本步仿真时间
```

从重置状态开始、保持角度不变且液量计入锥形瓶时：

| 角度 | 开始渐变 | 进入稳定淡粉 | 稳定淡粉持续多久 |
|---|---:|---:|---:|
| 90° | 5 秒 | 5.5 秒 | 约 0.706 秒 |
| 45° | 10.625 秒 | 11.6875 秒 | 1.5 秒 |
| 25° | 21.25 秒 | 23.375 秒 | 3 秒 |
| 10° | 85 秒 | 93.5 秒 | 12 秒 |

以上是理论**仿真时间**，不是现实中用秒表等待的时间。仿真采样会产生约一个时间步的边界误差。

中途减小角度，已有液量不清零，只是后续增加得更慢，所以剩余淡粉窗口变长。关至 ≤5° 后，液量不再增加，颜色停留在当时的数值。

稳定淡粉时关阀保持 3 秒即成功。成功结果锁定，但颜色仍跟随实际累计液量：成功后重新开阀，仍可能变成深色。通过任务的重置请求 `titration:reset_requested` 重置后，累计液量回到 0，颜色回到无色，成功结果清除。

## 7. “透明”是不是 RGB 或 opacity 决定的？

**`(0.97, 0.99, 1.0)` 是清水外观的着色值，不是“透明度”。**本包使用 `OmniGlass` 材质；Shader 上同时存在这些参数：

| 属性 | r1.6 数值 | 在本文中怎样理解 |
|---|---:|---|
| `inputs:glass_color` | 随上述规则变化 | 玻璃／液体的着色输入 |
| `inputs:glass_ior` | 1.333 | 折射率输入 |
| `inputs:depth` | 0.05 | 材质深度参数；不是瓶内液面的实际高度 |
| `inputs:thin_walled` | `False` | 使用非薄壁材质设置 |
| `inputs:frosting_roughness` | 0.02 | 表面粗糙度输入 |
| `inputs:enable_opacity` | `False` | 当前未启用该透明度开关 |
| `inputs:cutout_opacity` | 1.0 | 不能把这个值理解为清水被改成了不透明物体 |

颜色函数为了兼容已有数学策略，仍返回 `opacity` 数值（0.36、0.68、0.78）。
r1.6 的接收瓶更新函数直接忽略这个返回值，只写 `inputs:glass_color`。
唯一的液体 Shader 也没有 `inputs:opacity` 属性，不能把这些数值当成实际透明度。

因此，即使 RGB 是接近白色的清水值，玻璃也可能反射较暗的背景。不要只凭反射区域发黑就认定液体颜色参数是黑色。

## 8. 哪段代码负责变化？

控制器节点为：

```text
/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph/FlowController
```

代码保存在其 `inputs:script` 字符串属性中。

```text
compute()
  ├── advance()：根据角度和仿真时间更新累计液量与成功状态
  └── _sync_receiver()
        ├── _color() → color()：根据累计液量计算阶段和 RGB
        ├── 向唯一 Shader 的 inputs:glass_color 写入 RGB
        └── 更新滴定站的 titration:indicator_phase
```

`_sync_receiver()` 不创建液体节点、不更换材质绑定，也不切换 Mesh 可见性。
同一个 Shader 从初始 `(0.97, 0.99, 1.0)` 连续更新，直到淡粉、深色，重置后恢复初始值。

与 r1.5 的区别仅在结构：r1.5 保留四套液体并切换可见性；r1.6 合并为一套。
角度、流量、颜色计算、淡粉窗口和成功规则一致。
旧的 `SolutionColorless`、`SolutionTransition`、`SolutionEndpointPalePink`、`SolutionOvershoot`
以及 `WaterColorless` 等阶段材质路径已删除；集成代码应通过上文的两个关系访问唯一目标。

仿真运行中手动修改颜色，下一次控制更新会覆盖它。持续修改规则需更新任务源码并重新生成验证。
颜色数学源文件仍是仓库内的 `scripts/titration_linear_policy.py`，
单套材质集成由 `scripts/generate_traditional_titration_vr_r16.py` 完成。
交付包已经嵌入所需控制代码，运行时不依赖仓库源码。
