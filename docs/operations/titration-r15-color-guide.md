# r1.5 滴定液体颜色教学：存在哪里、怎么读、怎么变

适用任务包：`scientific_workbench_traditional_acid_base_titration_vr_r1_5`。
适用场景：包内 `scene.usd`，Isaac Sim 4.5。本文重点讲**锥形瓶里的液体**。

## 1. 先记住这三个结论

1. **颜色数值写在液体材质的 Shader 节点上，属性叫 `inputs:glass_color`。**
2. **颜色随锥形瓶累计接收的液量变化。**旋塞角度决定流速，进而决定变色速度。
3. **从无色到淡粉、从淡粉到深色都是渐变。**进入淡粉窗口后，RGB 会先保持不变；超过窗口才继续加深。

```text
旋塞角度 → 流量（mL/s）→ 本步增加的液量 → 累计接收液量 V
                                               ↓
                                      判断阶段、计算 RGB
                                               ↓
                                 写入 Shader.inputs:glass_color
                                               ↓
                                     显示对应的液体 Mesh
```

这里的“无色”“淡粉”都是视觉任务规则，不是化学反应求解结果。

## 2. 颜色究竟在哪个 Prim、哪个属性里？

### 2.1 Prim、Mesh、Material、Shader 分别是什么？

可以把 **Prim 理解为 USD 场景树中的一个节点**。不同节点负责不同事情：

| 节点种类 | 在这里负责什么 |
|---|---|
| Mesh | 液体的几何形状，也就是那一块“假液体” |
| Material | 材质容器，绑定到液体几何上 |
| Shader | 材质的具体参数，包括液体颜色和折射率 |

直接打开 `scene.usd` 时，锥形瓶液体的结构如下：

```text
/World/obj_receiver_flask/VisualLiquid
├── SolutionColorless                  无色阶段的液体 Mesh
├── SolutionTransition                 渐变阶段的液体 Mesh
├── SolutionEndpointPalePink            淡粉阶段的液体 Mesh
├── SolutionOvershoot                   过量阶段的液体 Mesh
└── Looks
    ├── WaterColorless/Shader
    ├── WaterTransition/Shader
    ├── WaterEndpointPalePink/Shader
    └── WaterOvershoot/Shader
```

例如，无色材质的 **完整 Shader 路径**为：

```text
/World/obj_receiver_flask/VisualLiquid/Looks/WaterColorless/Shader
```

其颜色属性为：

```text
inputs:glass_color
```

完整的 USD 属性路径可以写成：

```text
/World/obj_receiver_flask/VisualLiquid/Looks/WaterColorless/Shader.inputs:glass_color
```

注意最后的点号：前面是 Prim 路径，后面是该 Prim 上的属性名称。

四个 Shader 的完整路径分别是：

```text
/World/obj_receiver_flask/VisualLiquid/Looks/WaterColorless/Shader
/World/obj_receiver_flask/VisualLiquid/Looks/WaterTransition/Shader
/World/obj_receiver_flask/VisualLiquid/Looks/WaterEndpointPalePink/Shader
/World/obj_receiver_flask/VisualLiquid/Looks/WaterOvershoot/Shader
```

### 2.2 这个属性里的三个数是什么意思？

`inputs:glass_color` 的 USD 类型是 **`color3f`**：三个浮点数，依次是红、绿、蓝，即 `(R, G, B)`。本任务使用 0–1 范围的数值。

| 颜色角色 | 本任务的 RGB |
|---|---|
| 无色清水外观，带非常轻的冷色调 | `(0.97, 0.99, 1.0)` |
| 稳定淡粉色 | `(1.0, 0.80, 0.88)` |
| 过量后的深粉／红色终值 | `(0.85, 0.12, 0.28)` |

这些是**材质输入值**。截图中的像素还会受到玻璃、光照、背景、反射和显示处理影响，不应直接与这三个数逐项比较。

### 2.3 怎样知道当前显示的是哪一块液体？

每个 `Solution...` Mesh 有两个相关属性：

- `titration:phase`：这个 Mesh 对应的阶段名称。
- `visibility`：控制是否显示；控制器把当前阶段设为 `inherited`，其他阶段设为 `invisible`。

`inherited` 的意思是继承上层可见性，并不保证无论父节点怎样设置都可见。读取最终可见性可用 `UsdGeom.Imageable(prim).ComputeVisibility()`。

滴定站 `/World/obj_titration_station` 上还有这些便于观察的属性：

| 属性 | 含义 |
|---|---|
| `titration:dispensed_volume_ml` | 锥形瓶累计接收液量，单位 mL |
| `titration:indicator_phase` | 当前颜色阶段：`colorless`、`transition`、`endpoint_pale_pink` 或 `overshoot` |
| `titration:flow_rate_ml_s` | 当前流速 |
| `titration:stopcock_angle_deg` | 当前旋塞角度 |
| `titration:task_success` | 本次是否已经成功；成功后锁定至重置 |

## 3. 怎么读？先看运行中的值

### 3.1 在 Isaac Sim 界面里查看

1. 打开任务包的 `scene.usd`，允许场景脚本节点执行。
2. 在 Stage 场景树中找到锥形瓶的 `VisualLiquid → Looks → WaterColorless → Shader`。
3. 在属性面板中查找 `glass_color`。Python/API 中对应的完整属性名是 `inputs:glass_color`。
4. 启动仿真、操作旋塞，观察数值变化；再选中滴定站，查看 `titration:dispensed_volume_ml` 和 `titration:indicator_phase`。

通过 VR 导入时，节点可能位于 `/World/_scene/...` 下。例如滴定站会变成 `/World/_scene/obj_titration_station`。以下脚本通过场景中的关系查找液体节点，避免把材质路径写死。

### 3.2 在 Script Editor 中读取当前实时颜色

在 Isaac Sim 的 Script Editor 中运行下面的完整代码。**它只读取，不修改场景。**每执行一次，就打印当前时刻的快照；需要更新时再次执行。

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
            phase = prim.GetAttribute("titration:phase").Get()
            visible = UsdGeom.Imageable(prim).ComputeVisibility() != "invisible"
            print(path, "阶段 =", phase, "最终可见 =", visible)

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
    "/World/obj_receiver_flask/VisualLiquid/Looks/WaterColorless/Shader"
)
if not shader:
    raise RuntimeError("没有找到无色液体 Shader，请确认是 r1.5 原始场景。")

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

| 属性 | r1.5 数值 | 在本文中怎样理解 |
|---|---:|---|
| `inputs:glass_color` | 随上述规则变化 | 玻璃／液体的着色输入 |
| `inputs:glass_ior` | 1.333 | 折射率输入 |
| `inputs:depth` | 0.05 | 材质深度参数；不是瓶内液面的实际高度 |
| `inputs:thin_walled` | `False` | 使用非薄壁材质设置 |
| `inputs:frosting_roughness` | 0.02 | 表面粗糙度输入 |
| `inputs:enable_opacity` | `False` | 当前未启用该透明度开关 |
| `inputs:cutout_opacity` | 1.0 | 不能把这个值理解为清水被改成了不透明物体 |

控制函数还返回一个叫 `opacity` 的兼容数值，无色时为 0.36，淡粉时为 0.68，深色终值时为 0.78。但写入代码会先检查 Shader 是否具有 `inputs:opacity`。

**当前这四个 OmniGlass Shader 都没有 `inputs:opacity`，所以这些兼容数值没有写入它们，也不是本包实际透明度随时间变化的依据。**本包实际更新的是 `inputs:glass_color`。

因此，即使 RGB 是接近白色的清水值，玻璃也可能反射较暗的背景。不要只凭反射区域发黑就认定液体颜色参数是黑色。

## 8. 谁在更新这些属性？为什么读到四个相同的颜色？

控制器的完整 Prim 路径为：

```text
/World/obj_titration_station/Instance/Runtime/TitrationFlowGraph/FlowController
```

代码储存在这个节点的 **`inputs:script`** 字符串属性中。VR 导入后根路径可能增加 `_scene`；示例读取方法使用当前 Stage，不依赖磁盘路径。

主要调用关系是：

```text
compute()
  ├── advance()：根据角度和仿真时间更新液量、成功状态
  └── _sync_receiver()
        ├── _color() → color()：根据液量得到阶段和 RGB
        ├── 遍历 receiverLiquidShader：把当前 RGB 写入四个 Shader
        └── 遍历 receiverLiquidVisuals：仅显示当前阶段对应的 Mesh
```

滴定站上的两个关系提供实际目标路径：

- `titration:receiverLiquidShader`：指向四个液体 Shader。
- `titration:receiverLiquidVisuals`：指向四个液体 Mesh。

**所以运行起来后，读取四个 Shader 通常会得到相同的当前 RGB。**这是控制器的正常行为。节点名 `WaterColorless` 并不意味着它的数值在运行时永远保持无色。

刚打开、控制器尚未执行时，文件内储存的初始值则不同：

| Shader 所属材质 | 磁盘初始 RGB | 初始对应 Mesh 是否显示 |
|---|---|---|
| `WaterColorless` | `(0.97, 0.99, 1.0)` | 是 |
| `WaterTransition` | `(1.0, 0.90, 0.94)` | 否 |
| `WaterEndpointPalePink` | `(1.0, 0.80, 0.88)` | 否 |
| `WaterOvershoot` | `(0.85, 0.12, 0.28)` | 否 |

`WaterTransition` 的磁盘初始值是预设值，**不能把它当作运行时的固定渐变颜色或精确中点**；运行时的中点由插值计算得到 `(0.985, 0.895, 0.94)`。

在仿真运行中手动改 `inputs:glass_color`，下一次控制更新通常会将它覆盖。要长期改变规则，需要修改任务的颜色逻辑并重新生成、验证场景。在 Scenario Forge 仓库中，该逻辑源文件为 `scripts/titration_linear_policy.py`；生成脚本将其嵌入 USD，交付包运行时不依赖仓库源码。
