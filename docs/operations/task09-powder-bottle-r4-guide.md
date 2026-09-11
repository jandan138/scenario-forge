# Task09 近满瓶粉末 r4（Isaac Sim 4.5）

## 看起来接近装满的真实粉床

直接打开 `scene.usda`，粉末已处于预沉降后的高位初态。瓶仍为 60×60×100 mm 温白圆角方瓶，
最小通口 48 mm、薄圆口沿；原勺初始放在烧杯中。

| 项目 | r4 |
|---|---|
| 内托 | 位于 82–84 mm，厚 2 mm，贴合收肩内壁；下部空腔 |
| 瓶＋内托质量 | 约 46.805 g，共用单动态根刚体 |
| 碰撞 | 289 个凸片：256 壁块、底板、32 个薄内托扇区 |
| 粉末 | 10,240 个独立 `obj_powder_grain_*` Xform 根刚体 |
| 粒径／总质量 | 等体积直径 1.4 mm、ico 外包半径约 0.8274 mm；约 22.0686 g |
| 冷启动后粉床 | 再沉降 8 s，代表性深度约 **10.28 mm** |
| 粉面距瓶口 | 中位约 **5.72 mm**，最高颗粒的外包顶面仍在瓶口下约 **4.72 mm** |
| 运行配置 | Isaac 4.5.0、GPU dynamics/broadphase、PGS、240 Hz、32 次位置迭代 |

满瓶感来自抬高薄内托及其上方真实颗粒。厚度按瓶局部 4 mm 网格列最高粒心加外包半径统计，
不是每个位置都严格等厚。验收同时要求代表性床深 10–12 mm、距瓶口 3–7 mm，且最高颗粒保留至少 1 mm 口部余量。
密度 1500 kg/m³ 是工程假设，未标定实物粉末黏聚性质。

## 预沉降初态

生产者先在瓶口通道上方建立有间隙的颗粒列，运行 8 s 重力沉降；这是制作过程，不能作为交付初态。
通过保持/防漏检查后，将实际粉粒位姿转换回初始瓶坐标，保存到新 USD，初始速度取零。
交付前再次冷启动验证，避免依赖预热求解器或接触缓存。

`scene_config.json` 的 `initial_state` 为 `presettled`，`preparation_only=false`；
`preparation_evidence/` 保留制作沉降报告，配置记录来源场景、报告及状态数组哈希。
初始场景仍保存每颗独立刚体，不是固定粉末网格。

## 操作与验证

在解压后的目录执行，每轮选择新的输出目录：

```bash
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/settle --mode settle --seconds 8
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/scoop --mode scoop --seconds 50
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/calibration --mode calibration --seconds 43
```

GUI 播放运行颗粒及天平物理。规定舀取由 `scoop` 执行：空舟上秤并去皮，原勺从烧杯提出，
70° 入粉、暂停、慢速推进转到 30°，抬离后转平、搬运、倾倒、移开并读取稳定值。
勺头轨迹根据新粉面、原勺底面包络和口沿净空计算；工具在夹具内临时运动学驱动，粉末始终由物理接触驱动。

最终规定动作：舟内 253 粒，约 **0.545249 g**；净读数 **0.545243 g**，LCD **0.55 g**。
瓶中剩余 9,986 粒，另有 1 粒落在瓶旁台面（`obj_powder_grain_07556`），这次转移并非零损耗。

测量来自秤盘世界竖直接触力，按实际 dt 换算冲量，经过 1 s 积分窗、0.25 s 低通与去皮。
粒数仅用于独立质量核验，显示分度 0.01 g 不代表实物计量精度。
`calibration` 独立放置 0/46/186/371/0 粒，再移走去皮舟并重置仪器；这属于已知载荷诊断。

`balance:reset_requested=true` 只重置仪器。完整场景恢复需要重新打开初始 USD 并重建物理 view。
使用 `report.json` 的状态、完整 checks 和空引擎错误列表验收，不能只看退出码。

## 视频、源文件与证据

- `video/overview.mp4`、`video/close.mp4`：50 s 的实际物理状态回放。
- `video/bottle_*.png`：高视角粉面、口部与舀取观察。
- `source_bottle/bottle.blend`、`geometry.json`、`preview_section.png`：新内托模型及空瓶半剖。
- `source_boat/`、`SubUSDs/`、`deps/`：称量舟和原台面依赖。
- `scripts/`、`source_scripts/`：验证/回放与生产者源码。
- `evidence/`、`recording/`、`package_manifest.json`：最终资格报告、状态和文件哈希。

```bash
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root . --states runs/scoop/states.npz --out runs/video --view close --video
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root . --states runs/scoop/states.npz --out runs/video --view overview --video
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root . --states runs/scoop/states.npz --out runs/bottle --view bottle --frames 0,210,750,900
```

回放一次载入压缩状态，临时使用视觉 instancer 呈现所有实际粒子和物体位姿。视频按仿真时间播放；
不表示求解已达到实时。资格限于当前 Isaac 4.5 场景和规定动作，不包含机器人抓取或连续多勺操作的普适能力。
最终转移量、测量结果和视觉限制以包内报告为准。

独立新上下文目视审核为 **WARN、无阻塞问题**；盲比确认本版粉面明显更接近瓶口，视角具有可比性。
仍有可见的颗粒排列纹理、初始烧杯底部较暗和 44 s 秤台过渡镜头；入粉、带料搬运、落粒和最终数字均可辨。
审核检查 22 张配对/阶段/模型图，没有逐帧人工观看全部视频。两路视频另经 1500 帧、30 fps、50 s 检查和完整解码。
