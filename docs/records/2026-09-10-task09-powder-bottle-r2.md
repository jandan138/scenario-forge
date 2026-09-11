# 原 task09＋浅粉瓶＋重建称量舟 r2

## 范围与来源

保留新宇 `task_09_solid_weighing.zip` 中的台面资产、五颗大固体，以及原勺在烧杯中的初始放置。
替换修复天平，新增空心瓶、瓶内固定填充和独立 `obj_*` 粉末。用户最终取消 4.1/VR 验收，
要求先完成 4.5、较慢较稳地舀取，并允许用 Blender 重建外观大致相同的可用称量舟。

- 原场景 SHA256：`f0cb8161d0d8476c2ffa4b27439bfa90c59bc8a866c0d51da69b1f17405be355`。
- 原 ZIP SHA256：`adf898a57146a858d37ca4f4eddfc039cfe41bf78271818cfeee667914a95d5d`。
- 新瓶来源：`wide_opening_bottle_two_versions.zip` 的 `bottle_empty`。
- 最终 producer：`ConvertAsset/outputs/task09_powder_bottle_r2_20260910/candidate_r14`。
- 最终场景 SHA256：`c27fe80c056e5316fc1f0e2266b4ac6e9d81861048f24d7f61a82f4919b82c1a`。

## 实现

外瓶为 80×80×140 mm、56 mm 内口。假底高 131 mm，上部浅槽约 36 mm 直径、槽沿 139 mm；
瓶与填充共用 150 g 的工程质量。固定填充不计为可舀粉末。
4096 颗 1 mm 等体积 ico、密度 1500 kg/m³，单粒约 0.785398 mg，总量约 3.216991 g。
它们是 `/World/obj_powder_grain_00000` 形式的根 Xform 刚体，子 Mesh 仅承担几何与碰撞。
没有把粉床焊在瓶上，也没有逐粒布局随机化；初始采用有间隙的分层六角排列后由重力沉降。

原勺保留，先上提离开烧杯，再较陡入粉、停顿、慢速前推并转平。接触段前推约 6 mm / 7 s。
工具运动以实际勺头 anchor 插值并反算根位姿，避免直接插值根 pose 导致倾倒时勺头下探撞舟。

用户授权重建的白色浅舟约 64.8×82×28 mm、10 g、9 个封闭凸碰撞体。
继续使用 `obj_weighing_boat` 名称与原初始位置/旋转；原 X 尺度 0.6 烘入几何，根尺度为 1。
质心/惯量由 Blender 闭合模型体积积分得到。原视觉与旧碰撞作为 inactive 来源参考保留。
除替换天平和重建舟外，其余 17 个原对象根变换逐一比对一致，五颗大固体均保留。

最终配置：**Isaac Sim 4.5.0、GPU dynamics/broadphase、PGS、480 Hz、32 次位置迭代**。
秤盘实际接触力经过 1 s 积分窗与既有低通/去皮逻辑，显示分度为 0.01 g。
所有物理修复由 ConvertAsset 生产者完成；SF 仅提供测量、规定轨迹、验证、回放及打包入口。
MDL 闭包复用原合格 AAN 产物，没有在 core/schema 中导入 SDK 或增加 episode runner。

## 诊断与限制

1. 原舟六块 hull 有毫米级接缝；原显示网格虽闭合，但三角面整体向内，有向体积为负。
   直接启用 SDF 后，粒心进入了底壳实体。隐藏副本的绕序修正改善该问题，但没有使原舟完整称量稳定。
2. 支撑片、CCD、唤醒及 SDF 对照不能单独宣布解决问题。重建舟初版还暴露动态稳定性问题；
   最终组合采用单位尺度、明确惯量、凸碰撞和 PGS，按新场景重新验收，而不外推为通用求解器结论。
3. 勺的矩形区域计数曾把勺背下方颗粒算入，不能把床内计数当作装料。
   水平预装 64 粒的诊断能保持在真实勺腔；最终另检查离床后的持续持料和实际落料。
4. 4.1 试跑出现接触差异及 CUDA/TGS 内核错误，某些错误后仍能读到有限但停滞的旧位姿。
   这些早期“passed”、阻塞/超时或无完整报告的运行全部不作为资格。
   新验收器在主线程消费日志事件，捕获引擎错误后判失败；4.1 已按用户要求撤出验收。
5. 校验用瞬移不是实际搬运。颗粒瞬移前关闭 CCD，推进一个物理步后恢复，避免瞬移扫掠影响中间设备；
   实际舀取不瞬移粉末。该校验处理独立记录，不能宣称机器人完成了放置。

中间/失败证据就地保留在两个仓库的 `outputs/task09_powder_bottle_r2_20260910/`。
源输入和此前 r1 交付未改写。

## 最终证据

SF 证据根：`outputs/task09_powder_bottle_r2_20260910/`。

| 试验 | 报告 | 结果 |
|---|---|---|
| 自然沉降／重新打开初态 | `final_settle/report.json` | 5 s，通过；原勺动态，4096 粒留瓶，无采样到的假底/桌下泄漏 |
| 完整慢速操作 | `final_scoop/report.json` | 50 s，通过；持续携带 45 粒并全部进入舟区域 |
| 载荷、去皮、撤载、移舟、仪器 reset | `final_calibration/report.json` | 43 s，通过 |

三份报告同场景身份，无被验收器捕获的引擎错误。
实际转移约 **0.0353429 g**，稳定净重约 **0.03536 g**，LCD 显示 **0.04 g**。
末段 1 s 区域质量交叉检查最大差约 `1.64e-5 g`；ROI 从未作为测量输入。

已知载荷各 case 最后 1 s，接受阈值 0.01 g，须 valid/stable：

| 期望净重 | 最大绝对误差 |
|---:|---:|
| 0 g | `8.45e-6 g` |
| 0.100531 g（128 粒） | `3.11e-6 g` |
| 0.402124 g（512 粒） | `3.99e-5 g` |
| 0.804248 g（1024 粒） | `2.79e-5 g` |
| 撤粉回零 | `1.14e-5 g` |
| 移走去皮舟，−10 g | `2.51e-5 g` |
| 仪器 reset 后空盘 | 0（该窗口） |

这是特定离散刚体夹具的结果，不是实物仪器或任意粉末的精度认证。
完整物理重置采用重新加载初始场景并重建 view；TARE/reset_requested 不会自动补回物体。
50 s 记录约耗时 517.8 s，物理步 p50 18.72 ms、p95 38.40 ms；未达到实时，机器并发负载会影响墙钟结果。

## 视觉、测试与同步

`final_video/overview.mp4`、`close.mp4` 均为 1280×800、30 fps、1500 帧、50 s，完整解码通过。
回放恢复实际粒子、普通刚体、天平 links、LCD/灯状态和正确尺度；近景结尾可读实体屏幕。
`close_flow.png` 为 38.5 s 视频抽帧。
图像专用新上下文任务 `ses_f748b89a6ffeI0OgBWVOs1ee8i` 未读取代码或测量报告：
初审 WARN，补足杯内初态、持料搬运、下落帧后整组 **PASS，保留局部裁切/遮挡 WARN**。
详见 `final_video/visual_review.json`，不以图像判断力学准确度。

先写失败行为测试，覆盖根刚体/质量迁移、填充间隙、勺头旋转锚点、绕序修复和严格证据门禁。
`make check`：982 passed、1 skipped；Ruff、package/suite/Phase10.x smoke 与 diff-check 通过。
运行方式见[操作指南](../operations/task09-powder-bottle-r2-guide.md)，结构见[设计说明](../design/task09-powder-bottle.md)。

依据 ASSET-001/003/006、USD-002、STATE-002/003/007、VAL-001/002/003/005。
本次同步 SDF 内外/朝向验证及引擎错误后旧状态不能算通过的边界；数值参数仅用于该案例，
不成为所有舟、所有粉末或其他 runtime 的默认值。最终 ZIP、文件哈希与对象清单由交付 manifest 绑定。

## 交付收尾

- 目录：`outputs/task09_powder_bottle_r2_20260910/handoff/task09_powder_bottle_r2/`。
- ZIP：同目录层级的 `task09_powder_bottle_r2.zip`，241060555 bytes。
- ZIP SHA256：`193a3c566348c65d223097d2c66dd5ced94273860417298205f46231369eca0a`。
- 181 个 manifest 文件条目，ZIP CRC 通过；6 个 USD layer、19 个直接 asset，无 unresolved 或包外 USD 依赖。
- 解压到 `/tmp/opencode/task09-powder-delivery-check/task09_powder_bottle_r2` 后，全部文件哈希、Python 语法、
  嵌入控制器编译及 USD 闭包再次通过。
- 当前头登记为 `solid_sample_weighing / isaac45_original_scene_powder_bottle / r2`；此前独立粉末 r1 保留。
- 最终定向测试 10 passed，全仓 Ruff 和 diff-check 通过；生产者另有 3 项几何/根刚体测试通过。
