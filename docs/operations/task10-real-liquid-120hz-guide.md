# Task10 真液体滴定 120 Hz r2 任务包

基于 chenjiantong 的 `task_10_titration_experiment/scene.usd`。锥形瓶、滴定管上腔和细管均使用真实 GPU PBD 液体；保留原透明材质和连续显色规则，显示屏静态文字改为 ON。

目标运行条件是 Isaac 4.1 / 4.5、真实 120 Hz、位置迭代 min=max=64。
交付资格以包内 evidence 和 [本次记录](../records/2026-10-10-task10-real-liquid-120hz.md) 为准。
新版的运行证据独立于旧 240 Hz 报告。

## 入口与运行条件

- `scene/main.usda`：干净的 4.1 主场景。
- `scene/isaac45.usda`：干净的 4.5 主场景。
- `scene/demo41.usda` / `scene/demo45.usda`：附带 GPU PhysicsScene 和照明的无机器人入口。
- 共享目录使用 `scene.usd`、`scene_isaac45.usda` 和 `SubUSDs/{materials,textures}`。

干净入口保持无 PhysicsScene、环境背景和灯光；宿主须启用脚本节点，并提供 **GPU dynamics、GPU broadphase、TGS、120 Hz、位置迭代 min=max=64**，将各 ParticleSystem 的 `simulationOwner` 绑定到宿主物理场景。改变这些条件需要重新验证。

粒子位置、速度须回写 USD，`suppressReadback=False`。控制器 setup 会开启这些读回设置；粒子平滑关闭，等值面平滑独立保留。控制器在 OnPhysicsStep 读取前显式同步物理状态。空 Falling 集只关闭等值面，保留粒子系统，兼容 4.1。

## 操作与计量

使用 `/World/obj_titration_station` 的真实 `stopcock_joint` 调节阀门。开度不超过 5°时关断；最大流量为 30/11 mL/s，其余角度沿用原线性规则。

只有实际向下穿过瓶口、随后接触瓶内主体液体的试剂粒子才计入 `titration:dispensed_volume_ml` 并驱动颜色。空中液滴、瓶颈内孤立液滴和漏接液滴不提前显色。单个主体系粒子的名义体积为 0.003375 mL，可用试剂总量为 25 mL。

15 至约 16.925 mL 为浅粉红终点区间；关阀保持 3 个仿真秒后，`titration:task_success=True` 并锁定。成功前过量不能获得成功。继续加液仍会变深粉红。`titration:reset_requested=True` 恢复全部初始粒子位置、真实初始速度、剂量、颜色和标记；需要同时由操作者或夹具关闭阀门、恢复容器位置。

`released_volume_ml`、`inflight_volume_ml`、`spilled_volume_ml`、`source_total_volume_ml` 和 `conservation_error_ml` 提供剂量账目。`pbd_valid` / `pbd_error` 表示控制器数据是否有效。

## 物理边界与证据范围

源液体到滴嘴采用守恒的受控转移，随后由真实粒子运动和碰撞计算下落；不声称解析亚毫米阀道或毛细流。数值阀座、出口封口和向外扩展的碰撞壁由生产者声明，外观以原 USD 为准。接收体系合并保留实际粒子坐标和速度。

晃瓶验收只驱动容器的 kinematic targets，液体始终动态：先平移避开滴嘴，再小幅升降倾摆、回正静置 2 仿真秒，然后移回。没有机器人抓取、任意自由抛掷或 VR 控制资格。ON 只是静态显示修复，没有新增物理搅拌。

视频使用实测粒子记录，由 SDK 重新生成等值面；渲染前后逐值检查粒子坐标一致，并核对等值面位于对应粒子范围内。空中小液滴的回放表面关闭网格过滤与网格平滑，避免过滤抹掉孤立液滴；容器内液体保持原表面参数。正式画面使用 PathTracing，原始几何和 MDL 材质均保留。

## 重建与审计

```bash
python scripts/build_task10_pbd_candidate.py --producer <frozen-producer> --out <new-candidate>
<isaac-python> scripts/validate_task10_native120.py --package <new-candidate> --runtime 45 --out <new-evidence> --seconds 3 --full --record
python scripts/build_task10_pbd_package.py --candidate <new-candidate> --out <new-package>
```

4.1 需用对应 SDK 独立冷启动。验收逐物理步检查真实内腔及数值封口内表面，订阅 PhysX error stream；静态导出或接口 smoke 不能替代完整资格。

`scripts/finalize_task10_native120.py` 核对双版本报告、视频解码、视觉复核和所有帧哈希后归档。大规模原始粒子帧留在任务输出目录，包内 `evidence/recording_files.json` 给出位置和校验值；这些帧用于审计与重渲染，不是 USD 运行依赖。

## 原生时钟与接入

120 Hz 表示每个真实 PhysX 回调约 1/120 秒。渲染 60 Hz 时可每帧运行两个 120 Hz
物理步；不能把内部两个 240 Hz 子步当作本次 120 Hz 资格。位置迭代 64 是同一步内
求解接触的迭代次数，与物理步频不同。

Isaac 4.5 加载已有 USD 后，SDK 的场景注册可能为空，World getter 会回退到 1/60 秒。
在完全 Stop、尚未初始化 World/物理对象时，调用包内 `task10_clock.synchronize_loaded_scene`
同步已加载的 PhysicsScene。该函数经公开 USD 类型变更通知重新注册真实场景，保留其属性；
不会替换 SDK getter 或伪造回调。采集端须同时核对 World dt、当前 PhysicsScene 的 120 Hz
和实际物理回调 dt。控制器遇到不匹配的正 dt 会报错，防止错误步长继续计量。

新验收只通过原生 `World.step` 推进，包含 SDK 暖启动的每步内腔检查，并将 post-step
读回与 after-fetch 数据逐值抽查。World 逐步完整流程和渲染 60 Hz 的 Play 时钟/落液检查
分别记录。报告中的请求参数本身不构成真实频率证据。
