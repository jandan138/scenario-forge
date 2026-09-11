# Task09 原场景＋粉末瓶 r2（Isaac Sim 4.5）

## 场景内容

以新宇提供的 `task_09_solid_weighing.zip` 为底稿，保留原台面资产和五颗大固体。
初始场景中原药勺仍在烧杯内；天平换为修复后的自由基座设备。
新增 `obj_powder_bottle`，来源为空心版 `bottle_empty`：下部是固定填充，上方是约 36 mm 的浅粉槽。
4096 颗 1 mm 等体积 ico 粉末共约 3.217 g，密度 1500 kg/m³ 是工程假设，未作实物标定。

每颗粉末为 `/World/obj_powder_grain_00000` 形式的独立 Xform 根刚体，Mesh 子节点只承担几何与碰撞。
这些不是跟随瓶子的视觉粒子。瓶内固定填充随瓶体移动，瓶体及固定填充共用 150 g 的工程质量。

原称量舟经诊断后按用户授权用 Blender 重建：白色外扩浅舟，外尺寸约 64.8×82×28 mm、质量 10 g，
保留 `obj_weighing_boat` 名称及初始位置/旋转。原 0.6 X 缩放已烘入新几何，根尺度为 1，质心与惯量由闭合模型积分计算。
原视觉与旧碰撞在源层中保留为 inactive 参考；新舟采用封闭凸块碰撞，不依赖原反向绕序的 SDF。

本版验收与运行入口为 **Isaac Sim 4.5**；4.1 与 VR 入口不属于本次交付资格。

## 文件

- `scene.usda`：可直接打开的初始场景；原大固体与原药勺的初始摆放保留。
- `scene_config.json`：粒数、质量、来源、修复项及初始变换记录。
- `objects.json`：顶层 `obj_*` 对象及刚体身份清单。
- `source_boat/weighing_boat.blend`、`geometry.json`：重建舟的可编辑模型和几何/惯量参数。
- `deps/bottle/bottle.blend`：空心瓶来源；假底/粉槽由生产者脚本在 USD 中添加。
- `scripts/`：场景验证、规定动作与实际状态回放工具。
- `video/overview.mp4`、`video/close.mp4`：全景和操作近景。
- `evidence/`、`recording/`：测量报告、日志与实际物理位姿。
- `package_manifest.json`：交付资格及文件哈希。

## 运行

以下在解压后的包目录执行，Python 路径按本机 Isaac 安装调整。每次使用全新输出目录：

```bash
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/settle --mode settle --seconds 5

/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/scoop --mode scoop --seconds 50

/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/calibration --mode calibration --seconds 43
```

需要 GPU dynamics、GPU broadphase、PGS、480 Hz、32 次位置迭代。场景内有已嵌入的本地仪器控制脚本。
直接在 GUI 播放只运行场景物理及天平，规定舀取动作由上述验证脚本执行。

`settle` 保留普通动态药勺，观察初始场景的自然沉降。
`scoop` 是规定轨迹夹具：初始化时将空舟放到秤盘、以关节位移触发去皮，再把原勺临时改为运动学驱动，
从烧杯上提、进入粉槽、慢速前推并转平、搬运、倾倒、移开。粉末始终由物理接触驱动。
这不是机器人抓持或策略成功证明，交付场景中的药勺本身仍是普通动态刚体。

`calibration` 是独立已知载荷试验，不是舀取动作：0、128、512、1024、0 粒，随后移走去皮舟并重置仪器。
规定位置变更属于诊断夹具；记录中区分放置、沉降、读数窗口与重置。
`report.json` 的 `status`、完整 checks、engine_errors 和内容哈希是验收依据，不能只看进程退出码或位置仍有限。

## 视频回放

```bash
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root . --states runs/scoop/states.npz --out runs/video --view overview --video

/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root . --states runs/scoop/states.npz --out runs/video --view close --video
```

回放恢复实际粒子、药勺、普通对象、天平 links、LCD 和状态灯，不再次求解或人工绘制粉末运动。
为了高效呈现，回放临时使用视觉 instancer；磁盘初始场景的每颗粉末仍是独立 `obj_*` 刚体。
需要 Replicator、Pillow、ffmpeg。视频按仿真时间显示，不表示求解已达到实时。

## 称重与重置

读数来自独立秤盘的实际接触力，使用真实 dt 换算冲量，经过 1 s 时间窗与 0.25 s 低通后减去皮重。
显示分度为 0.01 g。粒子区域计数用于独立检查，不用于生成仪器读数；在粉床中的勺区域计数不等于已装入勺腔。
须结合 `balance:valid`、`balance:stable`、`balance:tared` 读取 `balance:net_g`。

`balance:reset_requested=true` 只清除仪器测量状态。完整场景重置使用重新打开初始 `scene.usda` 并重建物理 view，
从而恢复粉末、瓶、舟、勺及既有对象；单独按 TARE 不会补回粉末。

已知载荷误差、完整舀取结果与视觉限制以包内最终 evidence 和 manifest 为准。
本版不宣称任意粉末的黏聚真实性、毫克级精度、VR/Lift2 抓取、无损耗转移或实时性能。
