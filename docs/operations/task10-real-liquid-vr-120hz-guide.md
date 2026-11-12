# Task10 真液体 VR 数采入口（Isaac Sim 4.5，120 Hz r2）

本包在 chenjiantong task10 真液体修复版上增加旧滴定 r1.7 的房间、房间朝向和照明布置。
桌面器材、透明液体、连续显色、ON 显示和真实旋塞沿用本次 task10；不导入旧版假液体。
资格以包内 `evidence/delivery.json` 为准。真实头显和采集插件未在本 repo 中运行。

## 文件与入口

repo 输出：`outputs/task10_real_liquid_120hz_r2_20261010/vr/handoff/scientific_workbench_titration_task10_real_liquid_vr_120hz_r2/`。
整个目录一同部署，不能只拷贝 USD。

- `scene.usd`：4.5 直接打开入口，包含房间、灯光和物理场景。独立查看时启用脚本节点后可直接 Play；采集端使用 World 或随机摆放时仍须按下文调用 prepare_episode。
- `task_config.py`：将唯一的 `TASKS` 条目合并到采集端配置，场景路径相对本配置文件定位。
- `task10_vr_episode.py`：采集端初始化和重置接口。不是自动识别的插件回调配置。
- `deps/task`：原样式干净 task10，资源使用包内相对路径。
- `deps/environment`：旧滴定房间依赖。

共享 `scene_usd/zzh_fixed/task_10_titration_experiment` 继续只有干净 USD 与 `SubUSDs`。
这里的 VR 场景和共享干净版是两个明确入口；发布新版前保留共享旧版备份，旧 ZIP 保持原字节。

## 采集生命周期：必须接入这两个调用

源场景根是 `/World`，采集端挂载到 `/World/_scene`，挂载根须为单位变换。
不预建双重 `_scene`。任务对象和关节 links 按 `task_config.py` 注册，USD 不含机器人。
机器人由采集端按旧滴定的基座位姿创建。

滴定站、搅拌器、接收瓶共组随机平移 X/Y 各 ±0.01 m、yaw=0；两个旁侧容器独立分组。
PBD helper 不作为随机化对象或可抓取对象。随机化后由初始化接口依据容器实际变换同步粒子。

```python
# 从部署包目录导入；模块路径由采集端的现有加载代码配置。
from task10_vr_episode import prepare_episode, reset_episode

# 加载场景 -> 停止物理 -> 按 task_config 随机化 -> 初始化 -> 启动物理。
# timeline.stop() 后先让 Kit 处理停止事件，再进行以下 USD 修改。
stage.SetEditTarget(stage.GetSessionLayer())
prepare_episode(stage, "/World/_scene", collector_physics_scene_path)
# 此后由采集端初始化物理对象并 Play。

# 同一摆放重开一轮：停止物理并处理停止事件，然后调用：
reset_episode(stage, "/World/_scene")
# 此后重新初始化物理对象并 Play。
```

`collector_physics_scene_path` 是采集端实际创建的 PhysicsScene 路径。传入外部场景时，
接口停用包内 PhysicsScene 并把全部粒子系统绑定到外部场景；不创建第二个并行求解场景。
没有外部物理场景时可省略第三个参数，使用包内唯一 PhysicsScene。

若要重新随机摆放，先停止并 `reset_episode`，再从既定基准生成本轮摆放，最后 `prepare_episode`。
随机偏移应相对原始任务布局，不应逐轮累加。接口拒绝不一致的任务组移动、超出 ±1 cm、
非零 yaw 或非单位挂载变换，不在错误坐标上继续执行。

停止时恢复每轮保存的 USD 变换操作、粒子初态及初始速度；重新运行时清空剂量账目、空中液滴、
颜色、计时和成功标记。仿真过程中不通过父节点动画或逐步重写坐标把液体粘在容器上。
当前集成验收使用 Stop 后重置；仅 Pause 下保留 live PhysX actors 的重置不在本接口支持范围。

## 物理条件与任务状态

GPU dynamics、GPU broadphase、TGS、120 Hz、位置迭代 min=max=64、重力 9.81 m/s²。
配置和初始化接口保持一致；粒子 USD 位置/速度回写由内嵌控制器打开。
这些条件来自 task10 资格，不是沿用旧假液体的默认物理设置。

只有实际向下穿口并接触瓶内主体液体的试剂才计量/显色。15 至约 16.925 mL 为浅粉红窗口，
关阀保持 3 仿真秒后锁定成功；过量仍继续显色。源液体到滴嘴采用受控守恒转移，
不是解析毛细阀道。ON 为静态显示修复，没有新增物理搅拌。

运行中可读取滴定站的 `titration:dispensed_volume_ml`、`indicator_phase`、`task_success`、
`released_volume_ml`、`spilled_volume_ml`、`pbd_valid` 与 `pbd_error`。
直接设置 `titration:reset_requested` 只重置任务液体和状态；完整采集轮次应使用上面的停止/重置接口。

## 验证与性能解释

专项验收要求复现直接打开、VR 引用挂载、外部 PhysicsScene、四个随机边界和固定种子样本，
并检查每个物理步的真实内腔、粒子质量、连续接收、终点、重置、过量和漏接。
采集端完整握持/头显加载与操作效果需要在真实插件中进一步验收。

报告的 `physics_time_ratio` 是仿真时长除以整个验收进程墙钟时长，包含冷启动、逐粒检查、
日志和可选渲染开销；它不是头显帧率，也不构成实时交互性能保证。


### 已验证的运动范围

以下时长均为仿真时间。本次规定晃瓶轨迹为：先平移80 mm避开滴嘴（2秒），倾摆8°并升降25 mm（2秒），
**静置2秒，再用2秒回移**，回位后静置3秒。这里只驱动容器，液体始终动态。
资格以新版报告为准；不将规定轨迹解释为任意快速连续手部运动均已防漏。

`prepare_episode` / `reset_episode` 从内嵌 runtime_contract 读取 120 Hz 与 64 迭代，
并在完全停止时同步 Isaac 4.5 的已加载 PhysicsScene 注册。包内 `task10_clock.py`
必须一起部署。初始化不能在 Play/Pause 中调用；已存在的 World 也必须重新核对实际 dt。
具体时钟问题和原生步进证据见 [本次记录](../records/2026-10-10-task10-real-liquid-120hz.md)。

## 重建输入必须配套

新版本构建时显式传入对应主任务包和由它导出的干净目录：

```bash
python scripts/build_task10_vr.py --source <120hz-main-package> --shared <matching-clean-export> --out <new-vr-package> --task-id scientific_workbench_titration_task10_real_liquid_vr_120hz_r2
```

构建器会核对两者的任务配置，拒绝把旧 240 Hz 主包的来源记录与新 120 Hz 共享场景混用。
历史默认参数保留用于旧版本重建，不自动猜测共享目录当前属于哪一版。
