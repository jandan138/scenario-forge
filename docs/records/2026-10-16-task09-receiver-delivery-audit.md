# Task09 建通仓库交付前兼容核验

状态：`BLOCKED_STANDARD_RENDER_INPUT_INCOMPLETE`。本记录补充同日训练划分记录，不撤销既有标准 reader 与独立单例动作回放证据，也不将旧 READY 扩展为已部署或标准制作流程兼容。

## 已确认的交付约定

- 三类离线文件覆盖建通 GenManip 的 Task09 相对目录；metric 独立分支向 `feature/scientific_experiments` 提 PR，同时在建通本地同步相同改动，保留已有 Task10 提交。
- 两档数据目的地为 `/mnt/data/chenjiantong/scientific_experiments_data/releases/task09_v2/lerobot_dataset/`；保留旧数据，不上传 OSS。
- 300/500训练划分、40例评测入口与逐例独立进程验收范围不变；旧600包继续保留为历史归档。
- 用户选择：先做兼容核验，通过则复用现有数据；发现实质问题先提交证据及修复方案，暂停安装，不自动整批重做。

飞书依据为 Wiki `Og5Hw2fGGi8pIyk0SpBcrkGCnjf`，通过用户身份 CLI 读取，document `Ad41dB1IxobdSfxIk1ucUTgSnCd` revision 6609。其交付段列明 teleop 转 LMDB、按需液体缓存、`render.py`、`genmanip2lerobot.py`。两份本地 checkout 中未找到 `create_lmdb_from_json.py`，不声称已复现该步骤。

## 本次实际执行

在 SSH 主机 `10.150.163.175`、hostname `dsw-529861-6cb4cb97bf-vdwmr` 执行 CPU 核验。LeRobot 安装元数据确认 commit 为 `2b71789e15c35418b1ccecbceb81f4a598bfd883`。GPU 当时运行其他评测，未启动或停止任何 GPU 工作。

核验提取接收仓库 `genmanip/demogen/recoder/utils.py` 中三个原始函数的 AST，原样执行 `parse_planning_result`；仅绕过 SDK import，并利用绝对路径定位既有 LMDB，不改函数体或源数据。没有运行整个 `render.py`、标准转换器或视觉对照。

| 源示范 / 背景 | 帧数 | 500档 episode | 原16维动作 | 与制作 numeric 的11字段最大误差 |
|---|---:|---:|---|---:|
| 3 / 1 | 2494 | 0 | 逐值相同 | 0 |
| 64 / 5 | 2318 | 229 | 逐值相同 | 0 |
| 112 / 10 | 2082 | 499 | 逐值相同 | 0 |

上述数值对比证明现有数据保存了既定制作结果，不等于独立证明标准导出器数值等价，也不等于两个背景画面已比较。

三个动作回放 LMDB 都只有 arm/gripper/base action、qpos、qvel、name、gripper_close 七类 scalar。原始解析器返回的所有帧均没有 `joint_world_pose`，且 `obj_info`、`articulation_info`、`prim_attributes` 为空。相应原始记录每条仍包含49条位姿轨迹和70条属性轨迹。

标准 renderer 的 `_render_single_frame` 在缺少 `joint_world_pose` 时执行 `scene.world.step()`；有该字段时执行 `scene.world.render()`。所以不能把这些动作回放输入直接当作当前暂停物理、逐帧恢复场景状态的制作输入。此处阻断的是标准流程对照所需输入完整性，不是判定现有 LeRobot 损坏或评测 LMDB 无效。

另外，旧 metric 补丁对建通当前目录的 `git apply --check` 失败，因为 Task10 已新增 `repair_checks.py`；逐字节比较与 Task09 版本相同。后续本地安装应复用，PR 则根据远端目标分支是否已有该文件处理，不能覆盖或夹带 Task10 提交。

## 修复方案与后续门槛

1. 在独立制作目录生成三个样本的标准渲染 LMDB。保留已批准的修正 qpos 和原动作，将源记录的物体、连杆、articulation、逐帧属性映射到接收 parser 实际读取的键；不得覆盖原始记录或现有评测 LMDB。
2. 为输入映射写失败测试，校验每条轨迹长度、实际帧索引、对象映射及属性值；再次调用原始 parser，确认已恢复的逐帧记录与来源一致，明确 qvel 与其他推断字段的使用边界。
3. 在评测 GPU 可用时执行标准 `render.py` 和指定版本转换器，完整比较三条样本的数值、时序、四路画面、视频及统计量。核实动态液体记录是否存在，若有则生成相应 mesh 缓存；不能由任务名称推断无需缓存。
4. 对照通过后才继续接收目录备份/安装、独立 PR、本地 metric 同步、远端40初始化与四组代表动作回放。若存在内容偏差，报告受影响字段/帧与是否需要重新导出或重渲染；当前不自动重做300/500。

本轮没有修改建通目录、创建代码提交/PR、上传 OSS、修改飞书或通知同事。发布门槛尚未通过，不能报告“交付完成”。

## 证据与规范

外部核验目录：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task09_recapture_600_20261012/delivery_audit_20261016/`，包含 `tools/check_pipeline_inputs.py`、`pipeline_inputs.json` 和 `STATUS.json`。对应小型证据索引见同名 `.evidence.json`。

适用 VAL-001/002/003/004/005/006/008。规范无需变更：这是既有动作回放与状态渲染资格区分的具体应用，没有新增通用数据协议或修改核心包/API。同步本记录与 Task09 操作说明，历史包及既有 READY 保持原字节。

本轮仓库检查：`make check` 退出0；1255 passed, 1 skipped in 519.44s (0:08:39)。lint、包 smoke、Phase 10.x 及 `git diff --check` 通过；核验脚本语法、证据哈希和受影响文档链接另行核对通过。这些检查不替代尚未执行的标准渲染对照。
