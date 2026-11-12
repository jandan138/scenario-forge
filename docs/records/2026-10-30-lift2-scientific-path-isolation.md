# 科学实验 Lift2 路径隔离候选

日期：2026-10-30。状态：已验证候选；未安装、未共同合并、未 push。

## 变更与来源

GenManip 提交 `73066ae3d066a100269f7957663173ab6e9843de` 在 `RobotConfig` 增加可选 `usd_path`，Lift2 使用显式非空路径，否则保留 `robot_usds/lift2/robot.usd`。仅科学实验配置迁移：957 份 YAML、977 行文本新增、1914 条解析后机器人路径；937 份 anchor/alias 文件各加一次，20 份 z4 双 mapping 文件各加两次。非目标 541 份配置哈希不变。

当前 Lift2 实际字节独立复制为 `robot_usds/lift2_scientific_experiments`，原 `lift2` 保留。12 个文件哈希一致且 inode 独立；两个运行 USD 的相对依赖在新目录闭合。既有 `OmniPBR.mdl` 是 Isaac/MDL 外部前提，cuRobo R5a 资产未改。HF 元数据与当前 `robot.usd` 实际哈希不一致，候选以来源实际 SHA 为身份，不宣称上游未改版（ASSET-002）。

候选包：`/mnt/data/zhuzihou/GenManip-Sim-deliveries/releases/lift2-path-isolation-r1-20261030.tar.gz`，SHA-256 `b94399f460233ccf23abe699b68e26a1990367a66d81fe92b612cb742ac3a68b`。完整证据在任务目录 `/cpfs/user/zhuzihou/dev/scientific-lift2-path-20261030/`。

## 验证

- 5 项目标测试及完整 37 项 unit 通过，Black、`git diff --check` 和最终变更 allowlist 通过。
- YAML 删除新增行可逐字节还原全部基线；类型感知语义差分仅允许机器人 `usd_path`。
- 科学 test、科学 validation 和默认对照分别独立冷启动；实际 stage layer 证明前两者加载新目录，默认对照加载旧 `lift2`，DOF/joint paths 一致（VAL-001、VAL-002、VAL-003）。
- task11 `validation_unseen_prospect_2` 使用 R2 原 LMDB、原 metric、杯体16/1和独立缓存完成 3604 步，score 1.0、SR1，无 guarded invalid state。输入前缀逐值一致，四路各3605帧完整解码；20类归一化 PhysX 错误签名与 R2 相同，不宣称无引擎错误（VAL-008）。
- 独立匿名 A/B 目视复核无可辨回归；初次为 WARN，因左右相机遮挡和采样稀疏。补看2298–2309连续12帧后，两组均无甩臂、容器弹出或渲染异常。精细接触仍受遮挡限制（VAL-004）。

两次队列重试分别是 Ray socket 路径过长和默认链接路径断言过严，均不是候选物理失败；证据保留。

## 交付边界

候选未写入共享接收目录，R2 `ACTIVE_DELIVERY.json` 未改，水浴环境未改。等水浴版本完成后重新扫描最新科学实验 YAML，再执行纯新增安装和共同合并；不得把当前候选当成已部署版本。大资产、日志和视频留在 Git 外（VAL-005）。

本次仅实现任务特定路径路由和资产隔离，现有 ASSET/VAL 规则已覆盖，无需新增或修改通用 standards。
