# task_09 五颗固体称量

本任务从 `/mnt/data/chenjiantong/scene_usd/task_09_solid_weighing` 建立独立新包，
天平来自同批 `task_14_fixed_weight_weighing`。源文件及历史交付保持不变。

采用质量依次为 0.923113、0.591217、0.736416、0.928100、1.379894 g，总计 4.558740 g；
LCD 显示 4.56 g。参考材质为 NaCl，真实化学成分没有在本任务中鉴定。
接触间距和休眠阈值采用生产者的任务专用配置，详见包内质量审计与日期记录。

## 入口与读数含义

- `scene/main.usda` 是干净的主场景，包含源桌子，不包含 PhysicsScene、背景、灯光或机器人。
- `scene/runtime41.usda`、`scene/runtime45.usda` 是不同运行时的控制节点／材质覆盖入口。
- `scene/demo41.usda`、`scene/demo45.usda` 增加 GPU Dynamics、GPU broadphase、TGS、120 Hz、
  向下 9.81 m/s² 重力和演示灯光。实际验证按 1/120 秒推进，不依赖 World 管理器的 fallback。

读数来源是 `balance:measurement_source = supported_mass_inventory`：
用实际接触及位姿确认承托，再累加刚体的 `physics:mass`。这保留 task_14 的质量累加语义，
不把 LCD 显示或配置质量总和称为独立受力传感器测量。
新控制器包含称量舟及堆叠固体的间接承托，排除外部支撑与悬空物体。
普通物体可以正常休眠；仅在位置没有变化时保留已观测到的静止接触，避免休眠造成假卸载。

## 操作与完成条件

放置空舟，等待读数稳定，实际按压右侧去皮按钮并释放。逐颗加入五颗固体。
完成要求五颗均由舟承托、已去皮、净重距配置总重不超过 0.01 g，并稳定保持 2 秒。
完成状态锁定，LCD 持续更新；移走全部固体回零，移走空舟显示负皮重。
`balance:reset_requested` 清除皮重、完成状态和承托缓存；场景物理初态由加载器重置。

天平根 `/World/obj_analytical_balance` 暴露 `gross_g`、`net_g`、`tare_g`、`stable`、
`valid`、`lcd_readout`、`supported_sample_count`、`supported_paths` 和 `success`。
动态控制和 USD SDK 只在目标运行时脚本中使用，没有新增核心包 API。

## 复现与证据

使用 `scripts/build_task09_inventory_package.py`，传入来源目录、新输出目录、ConvertAsset
质量 profile 和材料闭包。可用重复的 `--physics-profile` 消费经过对照的生产者物理覆盖层。
构建不会覆盖已有包。具体最终参数和命令见对应日期记录。

```bash
/isaac-sim/python.sh scripts/validate_task09_inventory.py \
  --package <package> --out <evidence-directory> --runtime 45 --record
/isaac-sim/python.sh scripts/render_task09_inventory.py \
  --package <package> --recording <evidence-directory>/recording.npz --out <video-directory>
```

验证包含初始静置、逐颗上秤、卸载、重置、两种高度释放和舟内静置。
渲染默认 `PathTracing`、16 samples/frame、1080p/30 fps，保留原材质。
默认 `--frame-step 2` 为明确标注的 2 倍速回放；`--frame-step 1` 可重现实时速度。
`RayTracedLighting` 在当前环境会把盐粒上表面显示为黑色，不属于本次通过的视觉路径。
视频主视角与俯视特写来自相同时间点。
固体刚体原点可能在网格外；穿透检查使用实际变换后的几何顶点，不能用根节点高度。
稳定性使用每个物理步所有网格顶点的实际位移速度（含转动），门槛为末 2 秒不超过
1 mm/s、稳定观察期位移不超过 1 mm。引擎报告的瞬时线速度独立保留：在本任务
articulation 承托下，该值可有数 mm/s 的求解残差而网格运动只有微米量级；不把两者混称。
报告保留位移、两种速度、显示、质量及场景 SHA；视频按实际物理状态和 LCD 回放渲染，
没有用预设目标文字替换仪器读数。受控搬运轨迹只证明本次无机器人夹具，不证明勺取或机器人抓取。

规范范围：ASSET-001/002/003、USD-002、ART-002/005、STATE-001 至 STATE-007、VAL-001 至 VAL-007。
本天平为自由基座，不能引用固定基座 v2 资格。参考质量和碰撞候选为任务专用参数，不升级为通用默认。

## 同事目录样式的共享副本

`/mnt/data/chenjiantong/scene_usd/zzh_fixed/task_09_solid_weighing/`
对应用户侧 `/shared/smartbot_new/chenjiantong/scene_usd/zzh_fixed/task_09_solid_weighing/`。
其中 `scene.usd` 默认用于 4.1，`scene_isaac45.usda` 用于 4.5，依赖全部在旁边的 `SubUSDs`。
两个入口均显式米制、Z 轴向上，不含 PhysicsScene、背景、灯光或机器人；加载器提供运行环境。
此处只发布场景／资源，视频仍在仓库交付包内。生成、复跑与哈希证据见
[共享副本记录](../records/2026-10-08-task09-colleague-layout.md)。

## VR 数采入口

`vr/scene.usd` 与 `vr/task_config.py` 是额外的直接打开入口，不替换上面的干净主场景。
房间来自已登记的现代湿化学环境 `scientific_environment_code_room_wet_chemistry_v2`，
摆放沿用该环境锁定的 `(0.002882434, -0.0069055, 0)` 平移。
直接打开灯是无纹理白色 DomeLight，intensity 750、exposure 0。
采集配置注册全部 `obj_*`，并在天平根之后登记 `RightTare`、`Body`、`WeighingPan`；
只有对象根进入 ±0.01 m 的局部平移，yaw 固定为 0。天平仍是自由基座，不套用固定基座 v2 注册器。

```bash
python scripts/build_task09_solid_weighing_vr.py
```

该命令把入口写进当前 handoff 的 `vr/`。头显加载和一次真实数采不在本仓库的验收范围内。
