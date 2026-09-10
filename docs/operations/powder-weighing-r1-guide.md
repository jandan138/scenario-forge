# 粉末舀取与受力称重 r1

## 范围

目标运行时：**Isaac Sim 4.5.0，GPU PhysX / TGS，480 Hz**。
4096 个独立凸多面体刚体，等体积球直径 1 mm，密度 1500 kg/m³，
单粒约 0.785398 mg，总量约 3.216991 g。密度和粒径是工程代理参数，非 Labimus 作者参数或实物标定。

源料盘、抬高柄药勺和称量舟是明确尺寸的诊断工具。药勺按规定的运动学轨迹驱动，
粉末和称量舟是动态刚体，靠接触完成转移。天平沿用 force r1 的自由基座、秤盘和去皮按钮。
本版验证完整物理演示；VR/Lift2 动态抓持、真实粉末黏聚及毫克级精度不在已验证范围内。

## 包内入口

- `scene.usda`、`scene.json`：初始场景及实际参数。
- `balance/`：原始设备与本地材质闭包；粉末场景的控制器和求解器覆盖在顶层场景中。
- `scripts/validate_powder_weighing.py`：有限时长的物理试验与记录。
- `scripts/render_powder_recording.py`：恢复逐帧实际物理状态后渲染，不重新求解轨迹。
- `video/overview.mp4`：全景，观察粉末转移和天平。
- `video/close.mp4`：跟随操作阶段的粉末近景。
- `recording/states.npz`：粒子、实际药勺、舟及天平 link 的物理位姿和称量读数。
- `evidence/`：加载、转移及机身落粉回归报告。
- `source/powder_tools.blend`：可编辑的诊断工具几何。动力学配置以 USD 为准。
- `package_manifest.json`：验证范围及文件 SHA256。

## 运行

以下命令在**解压后的包目录**执行，Python 路径替换成实际 Isaac 安装路径。
每次输出路径必须是新的目录，以保留既有证据。

```bash
/isaac-sim/python.sh scripts/validate_powder_weighing.py \
  --scene scene.usda --out runs/my_scoop --mode scoop --seconds 28

/isaac-sim/python.sh scripts/render_powder_recording.py \
  --scene scene.usda --states runs/my_scoop/states.npz \
  --out runs/my_video --view overview --video

/isaac-sim/python.sh scripts/render_powder_recording.py \
  --scene scene.usda --states runs/my_scoop/states.npz \
  --out runs/my_video --view close --video
```

直接在 GUI 打开 USD 并播放，只会运行物理和仪器控制器，自动舀取轨迹由上述试验脚本执行。
场景携带本地嵌入控制器，运行器启用该 Script Node。渲染需要 Isaac Replicator、Pillow 和 ffmpeg。
视频按仿真时间 30 fps 回放；视频播放速度不代表求解实时速度。物理耗时见报告。

独立校验：

```bash
/isaac-sim/python.sh scripts/validate_powder_weighing.py \
  --scene scene.usda --out runs/known_loads --mode calibration --seconds 32

/isaac-sim/python.sh scripts/validate_powder_weighing.py \
  --scene scene.usda --out runs/body_contact --mode body_contact --seconds 25
```

`calibration` 是明确标记的已知载荷放置夹具，不是舀取视频：0、128、512、1024、0 粒，
随后移走空舟并重置。`body_contact` 把单颗粉粒放到机身上、移走并重复，检查秤盘读数保持。
必须查看 `report.json` 的 `status`、`checks` 与异常，不能只看进程退出码。

## 称重读数如何产生

本版固定使用**作用在独立秤盘上的真实接触力**，不是颗粒计数：

`gross_contact_g = -F_contact_world_z / 9.81 * 1000`

实际物理 dt 用于把接触冲量换算成力。接触力积分窗为 1 s，随后复用设备原有的
0.25 s 低通、0.6 s 稳定窗、按钮去皮与 0.1 g 显示分度。延迟是测量链路的一部分。
移动/倾斜时须结合 `valid`，受工具接触、冲击和加速度影响时不能把瞬时值作为质量。

| Live Stage 根属性 | 含义 |
|---|---|
| `balance:measurement_source` | `pan_contact_force` |
| `balance:contact_raw_gross_g` | 当前物理步接触力换算值，可能有明显冲击尖峰 |
| `balance:gross_g` | 1 s 接触力时间窗平均值 |
| `balance:net_g` | 低通后减去皮重的连续净重 |
| `balance:joint_gross_g` | 原关节反力通道，保留作诊断 |
| `balance:channel_disagreement_g` | 关节通道与瞬时接触通道的差 |
| `balance:valid` / `stable` / `tared` | 测量条件、稳定与去皮状态 |

在原始配置中，单颗粉粒接触自由基座机身曾使 incoming joint force 漏掉整个舟的载荷，
而秤盘接触力仍存在。新通道及更高求解迭代因此单独验证；不能把旧设备资格自动外推给粉末。
本通道测量秤盘接触荷载；直接通过代码施加到秤盘上的外力不是接触传感器输入。

报告的 `region_mass_g` 只用于隔离夹具的空间交叉检查，不写入仪器读数。
舟外但仍在秤盘上的粉末也会被真实称到，所以这两者不必严格相等。
已知载荷试验的实际误差和稳定窗统计见 `evidence/calibration.json`；显示一位小数不意味着毫克级精度。

## 重置与移植

`balance:reset_requested=true` 清除仪器滤波、去皮与状态，不搬回粉末、舟或药勺。
完整复现实验应重新打开初始场景并重建物理 view；不要只把视觉模型移回原处。
录制脚本关闭逐步 USD 位姿写回并使用 tensor 实时状态，因此直接读取 USD xform 不是实时物理观察。

细粉碰撞偏移不可直接用于宏观支脚的摩擦阈值。本版保留宏观接触摩擦所需范围，并对
颗粒、容器、地面分别配置接触偏移。更改粒径、密度、形状、求解器或 runtime 后须重新验证。
Blender 文件用于编辑几何；重新设计药勺后，碰撞资格与轨迹也要重做。

## 重建几何与参数

包内 `source/reference_generator/` 保留来件生成器及来源说明，
`source/producer_scripts/` 保留本版适配与 Blender 建模脚本。带 `pxr` 的 Python 可执行：

```bash
python source/producer_scripts/build_powder_fixture.py \
  --source source/reference_generator --out rebuild/powder.usda \
  --hz 480 --count 4096 --shape ico --radius 0.0005 --seed 42

python source/producer_scripts/build_powder_balance_fixture.py \
  --powder rebuild/powder.usda --balance balance --controller-source scripts \
  --iterations 64 --out rebuild/fixture
```

重建后的参数变化会改变物理结果；按上面的三类运行试验重新保留证据。
`source/reference_generator/README_复现说明.md` 是原始工程起点的历史说明，
其中 8192 粒与“未运行”的状态不代表本包当前配置；本包以 `scene.json` 和验证报告为准。

## 来源

[Labimus 论文 §3.1](https://arxiv.org/html/2606.31037v1#S3.SS1)、
[项目页](https://labimus.github.io/)、
[官方舀取视频](https://labimus.github.io/videos/task06_scoopweigh.mp4)。
来件 `Labimus_Rigid_Powder_Reproduction.zip` 提供工程起点，未提供作者原始数值参数。
原输入未声明统一可再分发许可，保留原设备/NVIDIA 材质声明；此包面向当前本地协作交付。
