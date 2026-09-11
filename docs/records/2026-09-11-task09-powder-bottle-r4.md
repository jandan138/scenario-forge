# Task09 r4：距瓶口约 5 mm 的预沉降粉床

日期：2026-09-11。用户先授权 r3 收尾/Git 提交，再确认 r4“抬高薄内托＋10–12 mm 真颗粒粉床”的近满瓶方案。
r3 已提交：ConvertAsset `4090ec0`，Scenario Forge `bb36b24`；范围见 [Git 收尾记录](2026-09-11-task09-r3-git-closeout.md)。

## 规范与方案审核

沿用现有 ASSET-001/003、USD-002、STATE-001/002/003/007、VAL-001/002/003/004/005/006。
规范基线 `2a61514`，本轮来源基线 `bb36b24`；**规范无需变更**，近满瓶的尺寸、颗粒列和检查阈值属于此任务，
不升级为其他场景的通用要求。同步本记录、设计与操作指南。

- 架构：ConvertAsset 负责贴肩薄内托、几何质量/碰撞、制作颗粒列及位姿固化；SF 负责物理验证、满瓶程度检查、工具协议和回放/交付。
- 完整性：区分 preparation 与交付初态；固化相对瓶坐标的颗粒位置/朝向；冷启动重新求解并验证真实厚度和距口高度；保留原台面对象与依赖。
- 风险：高位内托不能将 r3 的大方板直接平移进收肩；粒子列制作时可高于瓶口，但该场景禁止交付。
  最终初态需无漏粒、保留口部余量；动作和称重在新高度重新验证，不能继承 r3 运行结果。

## 生产者与初态

新模型 `ConvertAsset/outputs/task09_powder_bottle_r4_20260911/model_r1/`：
2 mm 薄内托 z=82–84 mm，精确剪裁三角化内腔，略向壁内重叠；质量积分只计实际腔内部分。
瓶＋内托 0.04680521063405403 kg；保留原瓶壳和墙面凸片，内托为 32 个凸扇区，总碰撞 289 片。
新 `model_full_powder_bottle.py` 复用 r3 模型帮助函数，Blender 根属性正确记录 84 mm。
模型测试、CPU 预览及重新打开证据见生产者 `docs/records/2026-09-11-full-powder-bottle-model.md`。

`build_full_powder_scene.py prepare` 建立 10,240 颗 1.4 mm 等体积 ico 的窄 HCP 颗粒列，
横向保留瓶喉几何和颗粒半径余量。源 r3 `scene.usda` SHA 为
`ec3cffc76cf32dabc714dd3b893c9a82cb32aac0715d690433188a0c6c9b3141`。
制作沉降 8 s 通过：全部保留，床深 median 10.60459 mm，无内托下/桌下颗粒。

`bake` 读取实际记录，将粉粒变换转换回初始瓶坐标，只写颗粒初始位置及朝向，初始速度为零；
保留其他对象的 authored 初态。存储制作 scene/report/states SHA，候选设为 `initial_state=presettled`。
不保留 PhysX 预热缓存，因此须重新冷启动验证；不能把制作阶段的高度直接当作交付运行结果。

最终候选 `ConvertAsset/outputs/task09_powder_bottle_r4_20260911/candidate_r1/scene.usda`：
SHA `50073c0b67f44992e5c55baebca4fe427f48de22599fdbe3feee4133c3807994`。
模型 JSON SHA `121118a218ceb2581ad9584f0f5f756b1de4b062eec47d77f65b9cb7ca6ea09c`。

## 验证

SF 证据根 `outputs/task09_powder_bottle_r4_20260911/`。
代表性床深按 4 mm XY 列顶面相对内托统计；median headspace 为瓶口减代表性粉面，minimum headspace 还检查最高颗粒外包顶面。
新 r4 证据门禁要求预沉降初态、厚度 10–12 mm、代表性距口 3–7 mm、最高颗粒距口至少 1 mm。
制作场景及错误 initial-state 标记不能通过最终资格检查。

| 验证 | 当前证据 |
|---|---|
| 静态 | `static_validation.json`：根刚体、质量、模型哈希、289 凸片、19 个原对象子树/依赖保留与闭包 |
| 冷启动沉降 | `final_settle/report.json` PASS：8 s，全 10,240 粒保留；厚度 median 10.27848 mm，p10/p90 10.04846/10.72127 mm；median headspace 5.72152 mm，minimum headspace 4.72370 mm；引擎错误为空 |
| 初始运行采样 | 首个记录时刻厚度 10.25414 mm，median headspace 5.74586 mm，初态近满瓶检查通过 |
| 舀取 | `final_scoop/report.json` PASS：50 s；舟内 253 粒，约 0.54524862 g，净读数 0.54524271 g，LCD 0.55 g；最终稳定窗口最大误差约 0.00001587 g |
| 校准 | `final_calibration/report.json` PASS：43 s，0/46/186/371/0 粒窗口、撤舟和仪器重置通过；已知载荷最大误差约 0.00008051 g，撤舟约 −10 g，重置净读数为 0 |

`qualification_summary.json` 使用 r4 配置共同校验三份最终报告，全部通过、引擎错误为空。
舀取结束库存为瓶中 9,986 粒、舟中 253 粒，另外 1 粒落在瓶旁台面：
`obj_powder_grain_07556`，最终世界坐标约 `(-0.035085,-0.068082,0.755658)` m，
距台面约 0.658 mm。证据 `transfer_inventory.json`。本次没有零损耗转移资格，不能把区域计数差一粒隐去。
舀取记录循环耗时 506.80 s（50 s 仿真），物理步 p50/p95 约 32.46/68.86 ms；只表示当前机器上的离线参考。

测试先行：生产者颗粒列/瓶坐标持久化测试先缺模块失败，再通过；SF 满瓶程度/证据门禁测试先缺接口失败，
并先复现 preparation_only 被误接收后修复。历史 r3 协议与证据测试继续通过。

## 视觉、检查与交付

最终 `video/` 两路视频均为 1280×800、1500 帧、30 fps、50 s，ffprobe 核对和 ffmpeg 全片解码通过；
输入实际状态 SHA `dce09fdfd379ebcd091acd27bfa970d6d57ed0e437df782afc4d5350453ad4d2`。
瓶口取景匹配 r3，避免用镜头改变伪装填充差异。

独立 clean-room reviewer `ses_f70f5580dffeJIkwxd8wlP8P2g` 查看 22 张指定配对/阶段/空瓶剖面图，
只获得图像和视觉目标，结论 **WARN、无阻塞问题**。盲比先使用匿名 A/B：
A 为 r3 `bottle_0210.png`，B 为 r4 同名图；标签映射在返回后记录。审核认为视角可比，B 粉面明显更接近瓶口，仍有小间隙。
本版入粉、带料抬离/搬运、落粒、舟内颗粒与实际 LCD 0.55 g 均可辨。
剩余 WARN 为粒子排列纹理、初始烧杯底部较暗、末段秤台过渡镜头；不存在所需阶段观察缺失。
这是选帧审核，没有逐帧人工观看全视频，不证明物理精度或机器人抓取。
逐图证据与说明见 `video/visual_review.json`，视频/图像哈希见 `video/video_validation.json`。

代码验证：

- ConvertAsset 相关五个测试文件共 **35 passed（108.57 s）**，使用 `OPENBLAS_NUM_THREADS=1`；相关文件 Ruff 通过。
  第一次 120 s 工具时限中断，随后扩大时限并完成，未将中断当作通过。日志 `producer_tests.log`。
- 整个共享工作区 `make check`：**994 passed、1 skipped**，随后因斐林 r4 文件的两项 F401 失败，
  不能声明完整工作区检查通过。日志 `make_check.log`，该文件由其他任务维护。
- 以已提交 `bb36b24` 加本次粉末任务源码导出隔离快照，使用独立临时 Git index、不改变共享暂存区；
  显式接入本地 `outputs`/`external_artifacts/incoming` 后执行相同 `make check`：
  **979 passed、1 skipped**，Ruff、package/suite smoke、严格 phase10x 和 diff 检查全部通过。
  日志 `isolated_check.log`，快照 `/tmp/opencode/task09-r4-sf-check/`。

最终交付：

- `outputs/task09_powder_bottle_r4_20260911/handoff/task09_powder_bottle_r4/scene.usda`。
- 同级 ZIP `task09_powder_bottle_r4.zip`，**480,811,518 bytes**，SHA-256
  `cd30b2fc1e07da1ac13ec70ffaf7a3b860cc7eb0ded8add430fc2977c18fba89`。
- manifest 状态 `scene_fixture_verified`，205 个文件哈希，视觉 WARN，机器人抓取未验证。
- ZIP CRC 通过，解压到 `/tmp/opencode/task09-r4-delivery-check/task09_powder_bottle_r4/` 后，
  205 个文件哈希、5 USD layers、19 assets、闭包、Python 语法和内嵌控制器编译检查通过。
  证据 `relocated_static_check.json`。
- 在异目录中移除继承的 `PYTHONPATH`，执行包内验证器重新运行 8 s settle，全部 checks 为 true、无引擎错误，
  10,240 粒全保留，厚度 10.27848 mm、距口 5.72152 mm。证据 `relocated_settle/report.json`。
- 当前交付索引的 `isaac45_original_scene_powder_bottle` 指向 r4。r3 ZIP 与其证据保留。
- 索引更新后粉末协议/证据/回放与当前头定向测试 **17 passed**；相关 Ruff、6 份文档的 27 个相对链接、
  代码围栏及 diff 检查通过。两个仓库暂存区为空；本轮 r4 源码尚未提交，r3 基线提交已在开始阶段完成。

可复现主命令（从 SF 根目录执行；复跑另选输出目录）：

```bash
python /cpfs/user/zhuzihou/dev/ConvertAsset/scripts/build_full_powder_scene.py prepare \
  --base outputs/task09_powder_bottle_r3_20260910/handoff/task09_powder_bottle_r3 \
  --model /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r4_20260911/model_r1/geometry.json \
  --out /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r4_20260911/preparation_r1
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r4_20260911/preparation_r1 \
  --out outputs/task09_powder_bottle_r4_20260911/preparation_settle --mode settle --seconds 8
python /cpfs/user/zhuzihou/dev/ConvertAsset/scripts/build_full_powder_scene.py bake \
  --source /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r4_20260911/preparation_r1 \
  --run outputs/task09_powder_bottle_r4_20260911/preparation_settle \
  --out /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r4_20260911/candidate_r1
```

最后按指南运行候选的独立 settle/scoop/calibration 和回放；打包命令：

```bash
python scripts/package_task09_powder.py \
  --candidate /cpfs/user/zhuzihou/dev/ConvertAsset/outputs/task09_powder_bottle_r4_20260911/candidate_r1 \
  --out outputs/task09_powder_bottle_r4_20260911/handoff/task09_powder_bottle_r4 \
  --settle outputs/task09_powder_bottle_r4_20260911/final_settle \
  --scoop outputs/task09_powder_bottle_r4_20260911/final_scoop \
  --calibration outputs/task09_powder_bottle_r4_20260911/final_calibration \
  --video outputs/task09_powder_bottle_r4_20260911/video \
  --producer-scripts /cpfs/user/zhuzihou/dev/ConvertAsset/scripts
```

操作见 [r4 指南](../operations/task09-powder-bottle-r4-guide.md)。

## 消费者 Git 收尾复核

本次分批提交纳入 SF 的近满瓶检查、证据门禁、包装／回放增量、测试和文档。
冻结 ZIP 与场景 SHA 均再次匹配上文记录；205个 manifest 文件哈希、ZIP CRC 和
新临时目录解压后的24项依赖（5层＋19资产）闭包通过，无包外或缺失路径。
为现有 ZIP 补齐相邻 `.zip.sha256` 文件，ZIP 自身字节保持不变。

收尾复用内容身份相同的已有运行和独立视觉证据，没有重新声明运行仿真或增加机器人资格。
生产者实现仍由 ConvertAsset 管理，交付包中的 `source_scripts` 保留来源源码快照。
当前 SF 提交将本记录及 r4 交付头一并纳入，规范仍无需新增通用规则。
