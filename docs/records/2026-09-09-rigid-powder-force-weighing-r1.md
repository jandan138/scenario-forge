# 刚体粉末与真实受力称重 r1

## 目标与范围

用户提供 `external_artifacts/incoming/from_zzh/labmius` 来件，要求复现官方视频中的粉末，
并接入最新天平。已确认首版先交付规定工具轨迹下的完整物理演示，精度以实测为准；允许本机 Blender 建模。

实现分工：ConvertAsset 生产、修正并资格验证粉末/工具/承托夹具；Scenario Forge 提供测量策略、
有限时长验证、实际物理状态记录、渲染和可移植打包。没有修改 core/schema 或引入机器人 episode runner。

## 调研与输入

- 论文：[Labimus §3.1](https://arxiv.org/html/2606.31037v1#S3.SS1)。作者使用小刚体/PhysX 接触，
  未公布可恢复全部配置的参数表；正文的累计质量描述也不足以证明作者使用承重关节反力。
- [官方视频](https://labimus.github.io/videos/task06_scoopweigh.mp4)：960×540、30 fps、7 s；
  来件参考帧已目视，原视频已下载保留。可见浅黄色颗粒材料的取料与转移，不能由视频恢复精确粒径。
- 来件含球体与 ico 两个 8192 粒工程初值，原包只有静态检查，没有动力学证据。
- 最新天平来源：`ConvertAsset/outputs/balance_force_r1_20260909/packages/analytical_balance_force_r1`，
  `asset.usda` SHA256 为 `56ef7fbe5d9313c3f33a9bf9777aab13ba42e3d47589f2c7e90ca486d8f93a0b`。
  原 4.1/4.5 资格覆盖既定规则载荷，未覆盖毫米级粉末接触机身。

## 实施与诊断

1. 来件的 `TokenListOp.GetAppliedItems` 和 `PrimDefinition.GetAttributeDefinition` 与当前 Isaac 4.5
   USD Python 接口不兼容；独立验证器使用 `GetAppliedSchemas` 和 `GetSchemaAttributeSpec`。
   原 `finally: app.close()` 可使异常在未输出报告的情况下结束；新脚本在试验主体异常时保存 traceback 与显式状态，
   不包含 `SimulationApp` 构造本身失败的完整恢复保证。
2. 数千刚体逐步 USD 写回有明显开销。关闭 pose/velocity 写回后通过 tensor 读取实际状态，
   以 `set_kinematic_targets` 驱动工具；GPU dynamics 与 GPU broadphase 在 World 初始化后显式恢复。
3. 采用单位尺寸 ico 网格再施加 collider 缩放，与直接在小坐标上 cooking 的初值做对照。
   同时检查实际质量和惯量；最终等体积 1 mm ico 单粒惯量对角约 `7.94087e-14 kg·m²`。
   不把改善结果写成已确定某一个底层 cooking 阈值的根因。
4. 微粒尺度的 `frictionOffsetThreshold=30 μm` 会抑制宏观支脚在较大接触间距处的摩擦。
   联合夹具改为 5 mm 摩擦激活范围，颗粒/工具仍使用各自的小接触偏移；地面使用 5 mm contactOffset、
   40 mm 厚度，并对粉粒启用 CCD，以处理从抬高源料盘掉落的高速粒子。
5. 24 次位置迭代仍有明显称量偏差；最终联合夹具的粉粒、舟和 articulation 使用 64 次位置迭代，
   4 次速度迭代、480 Hz、无稳定化，质量和惯量未以称量结果反向修改。
6. 本机 Blender 4.4.3 生成 `powder_tools.blend`，保留与诊断 USD 对应的开口源料盘、抬高柄勺和舟几何。
   Blender 文件是可编辑几何源；动力学仍在 Isaac 中完成。

### 单颗机身落粉导致反力通道漏项

初始完整转移中，舟一直位于秤盘上，去皮后净读数却降至约 −10 g。
独立离线几何检查把开始持续失重与 `g_02469` 落到 `Body/Chamber/Deck` 联系起来。
随后固定远置药勺，只将一粒放到机身、移走并重复，实跑得到：

- 原 joint-force 毛重：约 `10 → 0 → 10 g`；post-fetch 独立读取相同，排除仅 callback 相位问题。
- 同时测得的秤盘接触力毛重：持续约 10 g。
- 额外唤醒 articulation 和舟没有修复原通道。

这说明问题是当前运行组合中的测量链漏项，不是舟真的卸载。底层 PhysX 内部根因未确定。
新粉末变体固定使用秤盘接触力：世界竖直方向接触冲量 / 实际 dt / g，1 s 时间积分窗，
再复用既有 0.25 s 低通、0.6 s 稳定判断、按钮去皮和 0.1 g 显示。
原关节通道保留诊断；没有加常数补舟重、没有用区域计数代替传感器。

## 最终参数与已完成数值证据

最终场景：`outputs/powder_weighing_r1_20260909/handoff/powder_weighing_r1/scene.usda`。
SHA256：`fcb2db7e269f9aa946a880c50352e65f8baa968a736841a8d98ab76d93778d13`。

4096 粒；1 mm 等体积直径；1500 kg/m³；总质量约 3.216991 g；10 g 动态舟；自由基座天平。
这些是干颗粒代理参数，未声称实物粉末标定或 Labimus 作者原始参数。

原始报告位于 `outputs/powder_weighing_r1_20260909/`：

| 试验 | 证据 | 结果 |
|---|---|---|
| 28 s 完整舀取/倾倒，seed 42 | `weighing_contact_r3/report.json` | passed；406 粒进入舟区域，约 0.318872 g；末段测力约 0.33 g |
| 已知颗粒载荷、撤载、移舟、reset | `calibration_final/report.json` | passed；在已打包场景上运行 |
| 单颗机身接触/移走/重复 | `body_contact_qualified/report.json` | passed；新通道维持舟载荷，旧反力漏项仍可在诊断列看到 |

已知载荷每个 case 的最后 1 s、30 个采样点：

| 标称粉末质量 | 滤波净重最大绝对误差 |
|---:|---:|
| 0 g | 0.000058 g |
| 0.100531 g（128 粒） | 0.000186 g |
| 0.402124 g（512 粒） | 0.015176 g |
| 0.804248 g（1024 粒） | 0.047735 g |
| 撤去粉末回零 | 0.000117 g |
| 移走去皮舟，期望 −10 g | 0.000869 g |
| 重置后空盘，期望 0 g | 0 g（该窗口） |

接受阈值为 0.1 g，并要求窗口内 valid/stable；不是由最优单个 case 推断毫克级准确度。
舟外但仍在秤盘上的洒粉也会被传感器称到，所以 ROI 质量只作独立交叉检查。

seed 42 的记录阶段用时约 247.1 s / 28 s 仿真时间，物理步 p50 17.18 ms、p95 27.19 ms。
这包含当前机器负载和采样条件，尚未达到实时运行。视频是按仿真时间恢复的实际状态回放，不代表 RTF≥1。

## 验证命令与代码

- `python -m pytest -q tests/test_powder_weighing.py tests/test_balance_force.py`：11 passed。
- ConvertAsset：`python -m pytest -q tests/test_powder_fixture.py`：2 passed。
- `make check SMOKE_OUT=/tmp/opencode/powder-smoke-package SMOKE_SUITE_OUT=/tmp/opencode/powder-smoke-suite PHASE10X_SUITE_OUT=/tmp/opencode/powder-phase10x-suite`：
  976 passed、1 skipped；Ruff、package/suite smoke、Phase 10.x 和 diff-check 通过。
  首次 240 s 工具超时后重跑，完整日志为 `make_check_full.log`。
- `UsdUtils.ComputeAllDependencies` 对已打包 `scene.usda`：2 个 USD layer、2 个直接 asset，
  无 unresolved 或包外依赖；MDL 传递闭包沿用原设备的同字节 AAN 本地闭包。
- 运行和录制命令见[操作指南](../operations/powder-weighing-r1-guide.md)。

新增 SF 脚本：`powder_weighing_protocol.py`、`powder_balance_runtime.py`、`validate_powder_weighing.py`、
`render_powder_recording.py`、`package_powder_weighing.py`。原 `balance_force_runtime.py` 只增加默认行为不变的测量扩展点。
生产者新增 `build_powder_fixture.py`、`build_powder_balance_fixture.py`、`run_powder_probe.py`、`powder_tools_blender.py`。

## 规范同步与边界

依据当前工作树中的场景制作规范，涉及 ASSET-001/003/006、STATE-002/003/005/007、VAL-001/002/003/005。
本次同步 ASSET-003 的颗粒尺度资格、STATE-007 的多 link 接触验证、VAL-003 的实际运动学工具位姿记录，
以及设计和操作指南。参数是本夹具配置，不提升为跨运行时通用默认值。历史输入和原 force r1 交付保持原字节。

尚未覆盖：真实机器人抓持、VR loader、Isaac 4.1 粉末组合、黏聚/湿度/静电、实物粉末标定、毫克级测量及实时性能。
当前没有把工具规定运动轨迹解释为机器人策略成功。

## 多 seed、视觉和交付收尾

保持相同粒径、密度、粒数、求解器和规定轨迹，另生成 seed 43/44 的初始位置抖动及朝向：

| seed | 舟内区域粒数 | 区域质量 | 末段连续受力净重（约） | 结果 |
|---:|---:|---:|---:|---|
| 42 | 406 | 0.318872 g | 0.33 g | passed |
| 43 | 433 | 0.340077 g | 0.35 g | passed |
| 44 | 415 | 0.325940 g | 0.34 g | passed |

后两份证据位于 `seed43/report.json`、`seed44/report.json`，各自绑定其变化后的场景哈希。
没有要求混沌接触系统逐粒轨迹相同。三个运行均无被采样到的穿地粒子；正常洒落仍存在。

最终两路 MP4 均为 **1280×800、30 fps、840 帧、28 s**：
`final_video/overview.mp4` 与 `final_video/close.mp4`，ffprobe 核对编码/时长，ffmpeg 完整解码无报错。
画面恢复记录的实际粒子、药勺、舟及天平 link 位姿，顶部明确标为 recorded PhysX simulation。
补充高俯视角静帧展示料床与勺腔、倾倒中段；`close_flow.png` 直接抽自近景视频 16.1 s。

图像专用新上下文审查：全景 WARN（细节尺度较小），初次近景 WARN（关键帧未选中落料中段），
补充细节与视频抽帧后整组动作叙事 **PASS，保留局部 WARN**。审查者未读取代码或测量报告。
记录为 `final_video/visual_review.json`，task IDs 为
`ses_f78f2aeb2ffe7plg4pEzKiOpWD`、`ses_f78ea9147ffe6Dmv9GronLzP3m`。
可见洒落与局部遮挡不被隐瞒；视觉审查不替代数值测量和物理验证。

交付目录：`outputs/powder_weighing_r1_20260909/handoff/powder_weighing_r1/`。
ZIP、CRC 与最终 SHA256 由 `scripts/package_powder_weighing.py` 在证据及视频齐全后生成；
包内 `package_manifest.json` 绑定所有保留文件，完整日志和可编辑 Blender 源一同保留。

最终 ZIP：`outputs/powder_weighing_r1_20260909/handoff/powder_weighing_r1.zip`。
SHA256：`acdd7cecf51afe72b758b06682cb2368a0e5caaf57e7bdb423ea0ee19c0d412a`。
132 个非自引用 manifest 文件条目，ZIP CRC 通过；当前头登记为
`solid_sample_weighing / isaac45_rigid_powder_force_demo / r1`，与原双 runtime solid r1 并存。
解压到 `/tmp/opencode/powder-delivery-check/powder_weighing_r1` 后，132 个文件哈希、
全部 Python 语法和嵌入控制器编译、USD 依赖闭包再次通过；证据为 `delivery_check.json`。
收尾定向测试（粉末、原测量策略、当前头）15 passed，全仓 Ruff 与 diff-check 通过。
