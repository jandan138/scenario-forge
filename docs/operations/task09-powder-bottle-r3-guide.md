# Task09 紧凑粉末瓶 r3（Isaac Sim 4.5）

## 场景与入口

直接打开 `scene.usda`。本版沿用原 task09 台面资产、五颗大固体、原药勺、修复天平及 r2 重建称量舟；
初始药勺仍插在烧杯内。新瓶是 Blender 制作的温白圆角方身薄壁瓶。

| 项目 | r3 配置 |
|---|---|
| 瓶身外尺寸 | 60×60×100 mm |
| 瓶口 | 最小通孔 ID 48 mm；口沿最大 OD 54 mm；顶冠径向宽约 0.8 mm |
| 固定内托 | 距瓶底 57–59 mm，厚 2 mm；下方保留空腔 |
| 瓶体＋内托 | 同一个动态根刚体，约 48.518 g，258 个独立凸碰撞片 |
| 粉粒 | 16,384 个独立 `obj_powder_grain_*` Xform 根刚体 |
| 粒径／质量 | 等体积球直径 1.4 mm，ico 最大外包半径约 0.8274 mm；每粒约 0.002155 g |
| 总粉末 | 约 35.3097 g；1500 kg/m³ 为工程假设密度 |
| 沉降后粉床 | 8 s 独立沉降：有效列顶面深度中位数约 10.56 mm，p10/p90 约 10.24/10.86 mm |
| 物理配置 | Isaac 4.5.0，GPU dynamics/broadphase，PGS，240 Hz，32 次位置迭代 |

厚度来自实际沉降后的粒子坐标：瓶局部 XY 的 4 mm 网格列、至少 5 粒的有效列，取最高粒心加外包半径，
相对内托顶面统计。它是颗粒表面估计，不是初始装填层高或每个位置都等厚的声明。
白色瓶壁不透明，正常镜头主要展示口沿、内壁和粉面；`source_bottle/preview_section.png` 是空瓶模型的静态剖面。

## 包内文件

- `scene.usda`、`scene_config.json`：初始场景、配置、来源及保留对象变换。
- `objects.json`：顶层对象、根刚体及质量清单。
- `source_bottle/bottle.blend`、`geometry.json`：可编辑新瓶、轮廓、碰撞及质量数据；附整体/瓶口/空瓶剖面预览。
- `source_boat/`：沿用的重建称量舟模型。
- `SubUSDs/`、`deps/`：原场景和修复设备的包内依赖。
- `scripts/`：验证器、深瓶动作、仪器逻辑、实际状态回放。
- `source_scripts/`：ConvertAsset 的场景与 Blender 模型生产脚本。
- `evidence/`、`recording/states.npz`：最终报告、日志和 30 fps 实际物理状态。
- `video/overview.mp4`、`video/close.mp4`：50 s 全景及操作近景；附瓶口观察图和目视记录。
- `package_manifest.json`：资格范围、依赖闭包与所有交付文件 SHA-256。

## 运行与复现

在解压后的包目录执行；Isaac Python 路径按安装位置调整，每次选择新的输出目录：

```bash
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/settle --mode settle --seconds 8

/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/scoop --mode scoop --seconds 50

/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root . --out runs/calibration --mode calibration --seconds 43
```

直接 GUI 播放运行颗粒物理及内嵌天平控制器；上述 `scoop` 命令才会执行规定舀取动作。
验收依据是 `report.json` 的 `status`、完整 checks、引擎错误列表及场景哈希，不能只看进程退出码。

`scoop` 初始化空舟到秤盘并触发去皮，把原勺临时设为运动学工具：8–11 s 从烧杯提出，
11–14 s 移到瓶口，14–20 s 以 70° 入粉，20–21 s 暂停，21–28 s 慢速推进并转到 30°，
28–32 s 抬出，32–36 s 搬运，36–40 s 倾倒，40–44 s 移开，44–50 s 稳定读数。
控制基于原勺实际几何的勺头 anchor、外底高度包络和瓶口净空。
颗粒始终由接触求解驱动，录制保存的是实际物理位姿。交付初始勺仍是普通动态刚体。

最终一次规定动作转移 54 粒，质量约 0.116377 g；受力净读数约 0.116398 g，LCD 为 **0.12 g**。
这是规定工具轨迹的场景夹具验证；没有机器人抓持、策略成功或任意姿态资格。

## 校准、测量与重置

`calibration` 是独立诊断：0、46、186、371、0 粒，分别约 0、0.099136、0.400855、0.799554、0 g；
随后移走已去皮的 10 g 舟，再重置仪器。诊断放置使用显式位置变更，不能当作舀取证据。

测量来自秤盘世界竖直接触力，按实际 1/240 s 步长换算冲量，经过 1 s 积分窗、0.25 s 低通和去皮。
区域计数只做独立质量核验，不生成仪器读数。显示分度 0.01 g 不代表已建立同等实物测量精度。
读取 `balance:net_g` 时同时检查 `balance:valid`、`balance:stable`、`balance:tared`。

`balance:reset_requested=true` 清除仪器状态。完整场景重置需重新打开初始 USD 并重建物理 view，
恢复粉末、瓶、舟、勺及其他对象；TARE 不会补回已舀走颗粒。

## 回放与性能范围

```bash
/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root . --states runs/scoop/states.npz --out runs/video --view overview --video

/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root . --states runs/scoop/states.npz --out runs/video --view close --video

/isaac-sim/python.sh scripts/render_task09_powder.py \
  --root . --states runs/scoop/states.npz --out runs/bottle --view bottle --frames 210,600,750,840
```

需要 Replicator、Pillow 和 ffmpeg。回放恢复颗粒、工具、普通对象、天平 links、LCD 与状态灯；
临时视觉 instancer 只用于呈现，磁盘颗粒仍为独立根刚体。视频以仿真时间播放，不是实时求解录像。
回放将压缩状态数组一次载入内存，避免逐帧重复解压；本录制的主要状态数组约需 0.7 GB 内存。
参考 RTX 4090 上 50 s 仿真的记录循环约 678 s，物理步耗时 p50/p95 约 44.4/61.0 ms；
该结果不含全部启动/保存成本，也不保证其他机器性能。

独立审核查看了 21 张阶段/模型图，结论为 **WARN、无阻塞视觉问题**：
部分入粉近景的勺尖被前口沿遮挡，使用 `video/bottle_0750.png` 补充观察；
初始烧杯内勺面较暗，抬出图可辨；粉床有可见的排列纹理，44 s 的过渡画面主要是秤台。
抬离留料、搬运、落粒、舟中颗粒和最终显示均有可辨识画面。
独立审核限于选定帧；两路视频均另经 1500 帧/30 fps/50 s 元数据检查及完整解码，未把解码通过等同于逐帧人工审核。

本版只声明 Isaac Sim 4.5 的这套几何、粒径、时间步和操作范围；不宣称黏聚粉末物性、
反复多勺任务完成、机器人抓取、VR、Isaac 4.1 或实时运行资格。最终资格及目视限制以包内 evidence 为准。
