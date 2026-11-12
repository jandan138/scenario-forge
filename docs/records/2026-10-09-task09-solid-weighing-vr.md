# 2026-10-09：task_09 固体称量的 VR 数采入口

## 来源与决定

在已交付的 `scientific_workbench_solid_weighing_task09_r1` 上增加直接打开的 VR 入口。
用户指定房间为现代湿化学。干净主场景、两份 runtime、两份 demo 保持原样：主场景仍然没有
PhysicsScene、背景、灯光或机器人。称量质量、承托读数和 2026-10-08 的 Isaac 4.1/4.5 证据不改写。

## 规范

规范依据：同组 `docs/standards`。涉及 USD-002、USD-003、ART-003、VAL-001、VAL-002、VAL-003。
变化：**规范无需变更**。这是既有 VR 直接打开契约在本任务上的入口，不把 750 intensity、
120 Hz 或现代湿化学房间写成其他任务的默认。天平仍是自由基座，不能引用固定基座 v2；
因此没有调用固定基座注册器，只按遍历顺序登记对象根和天平下已有的刚体 link。

## 入口

- 场景：`outputs/task09_solid_weighing_r1_20261008/handoff/scientific_workbench_solid_weighing_task09_r1/vr/scene.usd`
- 配置：同目录 `task_config.py`
- 房间：`scientific_environment_code_room_wet_chemistry_v2`，复制到 `vr/deps/environment/`，
  引用为包内相对路径。平移沿用锁定环境的 `(0.002882434, -0.0069055, 0)`。
- 灯：`/World/vr_direct_open_light`，无纹理白色 DomeLight，intensity 750，exposure 0。
- 源文件不预建 `/World/_scene`。房间、桌子和灯不进随机化。每个 `obj_*` 根单独一组，
  局部 XY ±0.01 m，yaw 为 0。天平 link 只注册，不单独随机化。
- 配置中的机器人位姿和接触参数留给采集端生成机器人。场景 USD 里没有机器人。
- `physx_scene_cfg.TimeStepsPerSecond` 为 120，与本任务已验证称量步频一致。物理场景仍由采集端按配置插入，不写进这份 USD。

组合后的桌子包围盒为 x `-1.0…1.0` m、y `-0.4…0.4` m、顶面 z `0.755` m，落在房间包围盒内部。
这只说明初始几何包含关系，不是头显画面或数采成功。

## 验证与限制

静态检查：`tests/test_task09_inventory_package.py` 的 VR 条目检查通过，连同原有三份包检查共 4 项。
打开 `vr/scene.usd` 后默认根是 `/World`，依赖闭包没有未解析路径，主场景字节未改。
没有在 Isaac、头显或采集插件里加载这份入口，因此不声明数采、去皮或称量在 VR 运行时通过。
已有六次称量冷启动仍只覆盖 2026-10-08 的主场景和 demo 入口。

同一 handoff ZIP 已重新打包，纳入 `vr/`。新 ZIP SHA256 为
`2d0e5daf9e4be8e58837b20917a6d14f42cee8fb2ffb8fd5cfc6c1a5c6e72815`。
收据里的称量场景指纹和运行内容指纹未改，因为主场景和已验证称量内容没有重写。
