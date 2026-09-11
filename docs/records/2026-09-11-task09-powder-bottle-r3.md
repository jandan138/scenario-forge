# Task09 r3：紧凑薄口瓶与约 11 mm 真实粉床

日期：2026-09-11；模型和运行产物沿用任务开始日的 `20260910` 目录。
本记录对应用户确认的“紧凑瓶＋更深真实粉床”，目标运行时为 Isaac Sim 4.5。

## 规范、分工及范围

Scenario Forge 基线 `90bfc13`，ConvertAsset 基线 `3240ca3`；规范库初始整理基线 `2a61514`。
适用 ASSET-001/003、USD-001/002、MAT-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006/007。
按维护流程，由实现者同步本记录、设计引用和 r3 操作说明。
**规范无需变更**：本次尺寸、深度统计及 PGS/240 Hz 配置是任务级验证，现有职责、尺度资格与证据规则已覆盖，
不能提炼成任意容器、任意粉末或其他运行时的通用参数。

ConvertAsset 负责 Blender 瓶几何、分片碰撞、质量/惯量、USD 场景生产及独立颗粒配置；
Scenario Forge 负责原勺规定动作、实际受力读数、运行与视觉检查、状态回放及自包含交付。
没有引入 core/schema SDK 依赖或机器人 episode runner。

## 设计与候选证据

r2 的 140 mm 高瓶在 131 mm 处有高假底，内部 36 mm 浅槽造成缩口厚环；沉降后粉层仅几毫米。
用户确认用 Blender 制作紧凑温白圆角方瓶，并允许适度增大粒径和一万量级的粒数。

- 外尺寸 60×60×100 mm，直身壁厚 1.8 mm，颈壁约 2.2 mm。
- 最小通口 ID 48 mm，口沿最大 OD 54 mm；顶冠 ID/OD 为 49.8/51.4 mm。
- 内托 z=57–59 mm，厚 2 mm，下面保留空腔；瓶壳及内托共用约 48.518 g 的单刚体。
- Blender `model_r2` 提供 258 个独立闭合凸片，非整瓶凸包；原模型的 482 片 LOD 诊断另有生产者记录。
- 采用等体积球直径 1.4 mm 的 ico 粒子，外包半径约 0.8274 mm；每粒约 2.15513 mg。
- `candidate_r1` 的 14,336 粒在 8 s 后约 9.6 mm 深，未满足目标，保留 `settle_r1` 失败报告。
- `candidate_r2` 改为 16,384 粒，总粉末约 35.3097 g；其余目标几何与粒径不变。

初始 HCP 排列带小抖动及壁面余量。床深按实际物理状态的瓶局部 XY 4 mm 列统计：排除壁边，
每列至少 5 粒，以最高粒心加外包半径减去内托顶面得到表面估计，再取 p10/median/p90。
这不是单颗粒中心分位数，也不是把初始层高当作沉降厚度；不声称每处粉面严格平整。

架构审核：新瓶及深粉床由生产者自有脚本输出，协议读取其轮廓；包层保持 simulator-neutral。
完整性审核：覆盖根刚体结构、来源保留、沉降防漏、抬离留料、转移称重、粒径匹配的已知载荷、卸载/重置和回放。
风险审核：不继承 r2 480 Hz 的细粒资格；新 240 Hz、薄内托和深瓶动作重新验证。已观察到离线求解成本，未声明实时性能。

## 代码与测试

生产者新增 `scripts/build_compact_powder_scene.py`，从冻结 r2 克隆并替换瓶与粉粒；
先移除旧瓶层规范再打开输出 Stage，避免构建中暂时解析已移除的瓶引用。
最终脚本默认 16,384 粒；按默认参数独立重建得到与被验证候选**相同的 scene SHA-256**。

消费者新增 `scripts/compact_powder_protocol.py`，按原勺实际底面包络、70°→30° 慢速舀取和颈部净空生成勺头轨迹；
验证器使用新内腔轮廓、按粒径调整校准铺料、保存真实床深，证据选择器按候选 dt 验证并要求 10–12 mm 沉降证据。
回放镜头跟随新粉面高度，增加固定瓶口观察视角；打包器选择 r3 身份、教程和新生产/协议脚本。

- ConvertAsset：`python -m pytest -q tests/test_compact_powder_bottle.py tests/test_compact_powder_scene.py`：13 passed。
  对应四个文件 Ruff 通过。模型行为/LOD 测试的红阶段见生产者模型记录；场景行为测试先失败后通过。
- Scenario Forge：`python -m pytest -q tests/test_compact_powder_protocol.py tests/test_task09_powder.py tests/test_task09_powder_evidence.py`：10 passed。
  新证据配置测试先因缺少第四个参数失败，随后实现；覆盖拒绝旧 dt、错误 revision、缺失或不足床深证据。
- 相关脚本与测试 Ruff 通过。
- 全仓 `make check` 首次因 240 s 工具时限在测试阶段被终止；没有断言失败。增加时间预算后重跑通过：
  **986 passed、1 skipped（392.98 s）**，全仓 Ruff、package/suite smoke、严格 phase10x 和 `git diff --check` 均通过。
  日志为 `make_check_retry.log`；三个 smoke 输出参数分别为
  `SMOKE_OUT=/tmp/opencode/task09-r3-20260911-smoke`、
  `SMOKE_SUITE_OUT=/tmp/opencode/task09-r3-20260911-suite`、
  `PHASE10X_SUITE_OUT=/tmp/opencode/task09-r3-20260911-phase10x`。
- 后续修复回放逐帧重复解压：先新增读次数回归测试，缺少 `load_recording` 时失败；
  实现一次载入后通过。回放禁用关节，避免静态呈现时尝试建立静态刚体间的关节。
  同参数再次 `make check` 完整通过：**987 passed、1 skipped（295.63 s）**；最终日志 `make_check_final.log`。
  随后只调整近景镜头以跟随实际勺头，其验证采用重新渲染及目视，未重跑无关物理证据。

## 实际运行与结构证据

生产者根：`/cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r3_20260910/candidate_r2/`。
运行根：`outputs/task09_powder_bottle_r3_20260910/`。

| 证据 | 结果 |
|---|---|
| `static_validation.json` | PASS：16,384 个 Xform 根刚体及子 Mesh 碰撞、正确粒质量/尺度、258 个瓶凸片；19 个既有对象根层子树和依赖文件与 r2 相同；5 USD layers、19 assets、无缺失或包外依赖 |
| `final_settle/report.json` | PASS：8 s，颗粒全部保留，内托下和桌下为 0；184 个有效列的深度 median=10.56048 mm、p10=10.23509 mm、p90=10.86238 mm |
| `scoop_r1/report.json` | PASS：50 s，最终舟内 54 粒、瓶内 16,330 粒；约 0.116377 g，净读数 0.116398 g，LCD 0.12 g；最终 1 s 最大质量核验误差约 0.000020824 g |
| `final_calibration/report.json` | PASS：43 s，0/46/186/371/0 粒，各读数窗口最大误差分别约 0.00000567/0.00001917/0.00001419/0.00005793/0.00000572 g；移走去皮舟后约 −10 g，最大误差约 0.00002020 g；仪器重置为 0、tared=false |

规定轨迹的 33–35 s 搬运窗口有持续留料证据；初始深粉床内的 `spoon_count` 仍仅是区域诊断。
三份最终报告的 PhysX/CUDA 错误列表均为空，cfg-aware 证据选择器共同通过，摘要见 `qualification_summary.json`。
舀取记录循环耗时约 677.98 s，物理步 p50/p95 为 44.40/61.02 ms；
50 s 仿真不等于 50 s 墙钟。没有实物粉末物性、连续多次舀取或机器人抓持资格。

舀取运行后，验证器仅将独立 `settle` 的床深上限从候选容差 12.5 mm 收紧为 12 mm；
该改动不进入 `scoop` 路径。各报告保留实际执行时的 validator SHA，不追写旧报告。

复现命令见 [r3 操作说明](../operations/task09-powder-bottle-r3-guide.md)。完整命令的候选参数为：

```bash
python /cpfs/user/zhuzihou/dev/ConvertAsset/scripts/build_compact_powder_scene.py \
  --base outputs/task09_powder_bottle_r2_20260910/handoff/task09_powder_bottle_r2 \
  --model /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r3_20260910/model_r2/geometry.json \
  --out /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r3_20260910/rebuild_check
```

## 视觉与交付

最终呈现输入为 `scoop_r1/states.npz`（实际物理状态，不是目标轨迹替身）。
`video_retake/close.mp4` 使用勺头跟随镜头覆盖提勺和搬运；`video_final/overview.mp4` 为全景，
同目录 `bottle_*.png` 提供高视角粉床/勺尖观察。选择后的文件在 `video_delivery/`，
绑定相同 scene/states SHA；两路均 1280×800、1500 帧、30 fps、50 s，并由 ffmpeg 完整解码通过，
详见 `video_delivery/video_validation.json`。早期 `render_probe`、`video` 和 `video_final` 的旧近景保留为诊断，
没有把曾经缺少搬运目标的画面作为最终近景。

独立 clean-room reviewer `ses_f73897401ffeU7bJwGL5yBlEOa` 仅收到 21 张指定图片和自然语言视觉目标，
未获代码或数值报告。结论 **WARN、blocking_visual_failures=[]**，逐图结果保存在
`video_delivery/visual_review.json`。完整观察覆盖：瓶口和粉床、烧杯提出、入粉、勺上留料、搬运、空中落粒、
舟内颗粒和实际 LCD 0.12 g；空瓶 Blender 半剖明确显示薄内托及下部空腔。

保留的限制：初始烧杯内勺面反射较暗；部分入粉近景前沿遮挡勺尖，以 `bottle_0750.png` 补充；
抬勺后粉床有可见排列纹理、瓶沿轮廓略不平滑；44 s 为信息较少的秤台过渡画面。
没有缺失任务所需观察。审核针对选定帧，不宣称逐帧人工看完视频或排除了所有中间闪烁。
这些视觉说明不替代独立床深和受力报告。

最终交付：

- 根目录：`outputs/task09_powder_bottle_r3_20260910/handoff/task09_powder_bottle_r3/`；入口 `scene.usda`。
- ZIP：`outputs/task09_powder_bottle_r3_20260910/handoff/task09_powder_bottle_r3.zip`，**703,547,355 bytes**。
- 资格：`scene_fixture_verified`，Isaac Sim 4.5.0，视觉 WARN，`robot_grasp_verified=false`。
- 清单包含 199 个文件哈希（manifest 自身另列于 ZIP）；对象清单包含独立颗粒与原场景对象。
- 已校验 ZIP CRC，解压到 `/tmp/opencode/task09-r3-delivery-check/task09_powder_bottle_r3/` 后重新检查
  全部 199 个文件、5 USD layers、19 assets、包内闭包、Python 语法及内嵌仪器控制器编译，均通过。
  证据：`relocated_static_check.json`。
- 在该异目录包中移除继承的 `PYTHONPATH`，使用包内验证器再次运行 **8 s settle**：全部 checks 为 true、
  引擎错误为空、16,384 粒保留，深度 median 同为 **10.56048 mm**。证据：`relocated_settle/report.json` 与日志。
- 原 r2 handoff 的 181 个清单文件哈希及闭包再次检查通过，见 `r2_preservation_check.json`。
- 当前任务头 `solid_sample_weighing / isaac45_original_scene_powder_bottle` 已指向 r3，保留 r2 原字节。
  配置更新后，当前头＋回放＋证据＋深瓶协议定向测试 **11 passed**，Ruff 与 `git diff --check` 通过。

最终打包参数如下；复跑请另选输出目录，避免混入已交付目录的后续文件：

```bash
python scripts/package_task09_powder.py \
  --candidate /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r3_20260910/candidate_r2 \
  --out outputs/task09_powder_bottle_r3_20260910/handoff/task09_powder_bottle_r3 \
  --settle outputs/task09_powder_bottle_r3_20260910/final_settle \
  --scoop outputs/task09_powder_bottle_r3_20260910/scoop_r1 \
  --calibration outputs/task09_powder_bottle_r3_20260910/final_calibration \
  --video outputs/task09_powder_bottle_r3_20260910/video_delivery \
  --producer-scripts /cpfs/user/zhuzihou/dev/ConvertAsset/scripts
```

## 文件身份

| 文件 | SHA-256 |
|---|---|
| r3 ZIP | `e1ac66ae061a1706951f70e3364e3d5c30c6e94f44ffcdae59f6a90d3dd0235b` |
| r3 `scene.usda` | `ec3cffc76cf32dabc714dd3b893c9a82cb32aac0715d690433188a0c6c9b3141` |
| 舀取 `states.npz` | `d9e17593704f9a7e24ca4de34632710701deb9bc6ad067ff1e0dba724727eb1d` |
| 新瓶 `model_r2/geometry.json` | `1faef532b41c1eddbe629ced7ca52109c5211b1d7996aaba507d3be9fb8a70a9` |
| 新瓶 `model_r2/bottle.blend` | `ef3f1bce668874d85ab9f4460f501ad28a5294fbaa139fbad5a8c702d6fbeeaf` |
| 来源 r2 `scene.usda` | `c27fe80c056e5316fc1f0e2266b4ac6e9d81861048f24d7f61a82f4919b82c1a` |

r2 冻结 handoff、模型 model_r1/model_r2 及失败候选均保留；新结果只在 r3 目录和记录中追加。
规范/文档同期工作树中另有滴定、斐林及论文修改，未将其纳入本任务结论。
