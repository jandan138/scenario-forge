# 固体称量 r1：天平操作与读数教学

这版天平通过秤盘承重关节的实际受力计算重量。容器、样品和手的压力都会影响读数；
屏幕不是预先做好的几张数字图片，也不是按放入颗粒的数量显示克数。

## 1. 打开哪个文件

| 使用环境 | 场景入口 | VR 配置 |
|---|---|---|
| Isaac Sim 4.5 | `scene.usd` | `task_config.py` |
| Isaac Sim 4.1 | `scene_isaac41.usda` | `task_config_isaac41.py` |

两个入口使用相同的几何、物理配置和称量逻辑，分别选择物理步节点名称及对应版本的本地 MDL 模块。
场景需要 **GPU Dynamics、GPU Broadphase、TGS、120 Hz、Z 轴向上、米制、重力 9.81 m/s²**。
4.1 不能用 CPU 物理运行来件中的 SDF 容器；不要仅因天平读数出现就认为其他物体也已正确加载。

需要启用场景内 Script Node。首次使用时按 Isaac Sim 的场景脚本信任提示处理。
运行代码已经嵌入 USD，不依赖制作机器的 Python 文件路径。

独立天平资产是设备资产，不包含桌子与完整实验场景。引用它时配置
`balance:tabletop_z` 为承托台面高度；两个版本的资产入口分别为
`asset.usda` 和 `asset_isaac41.usda`，设备 Prim 为 `/World/obj_analytical_balance`。

## 2. 默认任务怎么做

1. 把空称量舟放到秤盘中央，等待读数稳定。
2. 按下黄色 **TARE** 按钮后松开。若仍有波动，天平会等待稳定后归零。
3. 用药匙从样品瓶向称量舟加样，目标净重为 **30 g**。
4. 归还药匙。净重稳定保持在 **29.8–30.2 g** 内满 **2 秒**，并满足容器和样品位置条件后，记录任务成功。

默认五颗样品各为 10 g。场景初始将样品放在样品瓶中，称量舟留空。
这是有限颗粒的操作任务，不是连续粉末模拟。CAL、OFF 等其他按键保留外观，本版只接通 TARE。

## 3. 读数会怎样变化

| 操作 | 应看到的表现 |
|---|---|
| 空盘 | 稳定后接近 `0.0 g` |
| 放入 10 g 称量舟 | 先波动，随后接近 `10.0 g` |
| 去皮 | 稳定后接近 `0.0 g`，记住容器皮重 |
| 加入三颗样品 | 净重接近 `30.0 g` |
| 用手压秤盘 | 读数增加；松开后恢复 |
| 去皮后移走容器和样品 | 接近 `-10.0 g`，负号是正常结果 |
| 拿起、明显倾斜或移动机身 | 显示横线，暂时不能完成去皮或称量判定 |
| 放回台面并放稳 | 恢复读数，已有皮重保留 |
| 超量程 | 显示 `OL`；移除额外载荷后恢复 |

显示分度为 **0.1 g**，量程为 **200 g 毛重**。量程包含容器，不因去皮而扩大。
选择 0.1 g 是因为真实颗粒接触下，0.01 g 档位在两个版本间不能稳定满足相同条件。
不能把原先印在屏幕上的 `0.0000 g` 当作已经实现了 0.0001 g 测量精度。

系统先对连续受力进行时间常数 0.25 秒的低通滤波，再观察最近 0.6 秒的波动。
窗口内变化不超过两个显示分度才标为稳定。没有人为添加随机跳数。
物体还在滚动或碰撞时会继续显示未稳定，不能保证所有放置方式都在固定秒数内稳定。

TARE 长按只触发一次。等待超过 5 秒仍不能稳定去皮，会记录 `tare_timeout`，保留旧皮重；
松开后重新按下可重试。左侧三个状态灯依次表示稳定、等待去皮、无效或错误。

## 4. USD 中在哪里读取

设备根路径：

```text
/World/obj_analytical_balance
```

VR 挂载后通常增加 `_scene` 前缀，成为 `/World/_scene/obj_analytical_balance`。

| 根 Prim 的属性 | 含义 |
|---|---|
| `balance:gross_g` | 扣除秤盘自重后的瞬时受力换算毛重，尚未滤波 |
| `balance:net_g` | 滤波后减去皮重的净重，未按显示分度舍入 |
| `balance:tare_g` | 已记录的皮重 |
| `balance:lcd_readout` | 屏幕显示文本，如 `30.0 g`、`-10.0 g`、`OL` |
| `balance:valid`、`balance:stable` | 当前读数是否有效、是否稳定 |
| `balance:status` | `initializing`、`settling`、`stable`、`tare_wait`、`invalid`、`overload` |
| `balance:tare_pending`、`balance:tared` | 是否正在等待去皮、是否已去皮 |
| `balance:error` | 错误说明；无错误时为空字符串 |
| `balance:success` | 本轮是否已记录成功 |
| `balance:completed_net_g` | 记录成功时的净重快照 |
| `balance:reset_requested` | 设置为 `True` 后，下一个物理步清除本轮逻辑状态 |

在 **正在运行的 Isaac Sim Stage** 中读取：

```python
import omni.usd

stage = omni.usd.get_context().get_stage()
balance = stage.GetPrimAtPath("/World/obj_analytical_balance")
valid = balance.GetAttribute("balance:valid").Get()
stable = balance.GetAttribute("balance:stable").Get()
if valid and stable:
    print(balance.GetAttribute("balance:net_g").Get(), "g")
print(balance.GetAttribute("balance:lcd_readout").Get())
```

用 `Usd.Stage.Open()` 在另一进程打开磁盘文件，只会读到保存的初始状态，读不到当前仿真的实时结果。
暂停不会推进去皮等待或目标保持计时。

重置逻辑不会凭空移走容器或样品，也不等同于重置物理位姿；整轮重置应由加载程序同时恢复对象初始位姿。
重置后如果仍有载荷，天平应显示它的毛重，而不是强行把有载荷的秤盘显示为零。
已成功后可以继续加样或移走容器，实时读数继续变化，成功快照保留到重置。

## 5. 受力和屏幕分别在哪里

```text
obj_analytical_balance
├── Instance
│   ├── Body                     机身，质量 6.8 kg
│   │   └── ControlPanel/LiveDigits
│   ├── WeighingPan             独立秤盘，质量 0.05 kg
│   ├── RightTare               可按下的按钮
│   └── Joints
│       ├── LoadCell            秤盘承重固定关节
│       └── RightTarePress      0–1.5 mm 的按钮滑动关节
└── BalanceRuntime/Graph
    └── FlowController          inputs:script 中保存运行代码
```

承重关节是“机身与秤盘之间固定”，不是“把整台天平固定到世界”。本版机身可以搬动。
程序按实际 link 名称找到测力数组中的秤盘，不能把按钮 DOF 序号直接当作测力序号。

换算过程为：**关节受力转到世界竖直方向 → 除以重力 → 减去秤盘自重 → 滤波 → 减去皮重**。
已知物体质量只用于校验与资产配置，不替代传感器输入。

`LiveDigits/D0_a` 等 Prim 是七段数字，`P0` 等 Prim 是小数点。
控制器更新它们的 `visibility` 来组成数字，另同步 `balance:lcd_readout` 文本。
这部分是数字显示，不是液体的连续变色材质逻辑。

## 6. 改目标、容差和颗粒质量

生成任务时，`scripts/generate_solid_weighing_r1.py` 提供 `--target-g`、`--tolerance-g`。
颗粒物理质量由 ConvertAsset 的 `scripts/build_balance_force_asset.py --grain-mass-g` 生成。
生成器会拒绝五颗样品无法达到的目标，以及大到无法区分相邻颗粒数量的容差。

修改这些参数应生成新候选版本并重新验证，不直接改写已准入历史包。
制作顺序为生产者 `build_balance_force_asset`、`attach_balance_runtime`、
`localize_balance_materials`，随后完成生产者资格和任务生成／验证／打包。
材质本地化使用 ConvertAsset 的现有 AAN 工具，不能跳过该步骤而继续依赖制作机器安装目录。
不要只改 `task_config.py` 中的展示配置，留下 USD 中的目标和控制器参数不变。
若仅在仿真中探索目标，可在播放前修改设备根上的 `balance:target_g` 和 `balance:tolerance_g`，
重新开始播放使控制器读取新值；这不自动获得新参数的准入资格。

## 7. 使用边界

- 载荷休眠可能使这两个版本的关节反作用力读数异常；生产者为本任务载荷关闭休眠／稳定化，设备桥接也会唤醒可见的动态物体。
- 搬动资格覆盖已验证的台面与摆放范围；运行时用姿态、速度和足部相对台面高度判断读数有效性，不是完整接触传感器或水平校准系统。
- 这是场景与受控物理交互验证。它不证明机器人已经能完成抓取、舀取或整段策略；原同事加载器的崩溃也未在现有复现路径中复现。

准入依据与最终哈希见交付包 `manifest.json` 和 `evidence/`；制作责任见
[资产准入](../standards/asset-intake.md)、[交互状态](../standards/task-state.md)及
[验证与交付](../standards/validation-and-delivery.md)。
