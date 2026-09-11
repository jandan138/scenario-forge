# 2026-09-11 EBench dish 几何 × 初始进度任务编译

状态：四个实验条件已编译并注册到独立 GenManip 任务目录；尚未完成条件内运行验证。
本次承接 EEOS 自主进化研究中 Astra 提出的 dish 竞争假设。

## 设计与范围

几何因素为 ConvertAsset 生产的原尺寸和 2×横截面勺柄。初始进度因素为原完整布局，
以及四件餐具已放入大篮而勺子仍在原位置的布局。指令和五项最终 goal 保持不变。

预放置姿态取自源演示 LMDB 的真实末帧。编译器要求源演示的篮子从初帧到末帧保持相同位置、
方向和缩放，并与 initial_layout 一致；否则拒绝将末帧坐标直接用作初始位姿。
只改变 dish1、dish2、dish3、glass，勺子、篮子、机器人及其他对象保持原初态。
预放置仍需在 reset 后验证稳定性和实际分项目标。

源演示数据由 EEOS 输出 JSON，带元数据与 LMDB 文件哈希。Scenario Forge 不读取外部 pickle；
仅将生成 JSON 编码成 GenManip 所需的 `meta_info.pkl`。
几何、材质和物理属性由 ConvertAsset 预制 overlay 提供，本仓库只组合，不修资产。

新增文件：

- `src/scenario_forge/adapters/ebench/intervention_suite.py`
- `scripts/compile_ebench_intervention_suite.py`
- `configs/research/ebench_dish_interventions.json`
- `tests/test_ebench_intervention_suite.py`

该早期适配器输出明确命名的 `ebench-native-intervention-suite/v1`，不是伪装成已通过
通用 `scenario-package/v0.2` 验证的发布包。当前保留外部源依赖，状态为
`compiled_not_runtime_verified`。通用场景包表达与完整可分发闭包属于后续工作，不能以此替代。

## 产物与安装

当前产物：`outputs/ebench_dish_interventions_20260911_r3/`。

后续运行发现 r2 缺少 GenManip 必需的 `.usda` 入口，因此 r2 不可作为已就绪运行包。
当前改为 `outputs/ebench_dish_interventions_20260911_r3/`，任务前缀为 `dish_r3`。
r3 保留原 `.usda` 入口的全部内容，只将其 content payload 指向新 `main.usd`。
安装核对入口哈希、基础场景及 overlay 哈希，并从原配置重建预期值以拒绝配置篡改。
真实 USD 检查确认四个入口均可加载且包含 `/World/_scene/obj_spoon`。
r2 原注册目录保留，未覆盖；r3 注册到新的 `dish_r3_*` 名字。

| cell | 几何 | 初始进度 |
| --- | --- | --- |
| dish_r3_control_full | 原尺寸 | 完整任务 |
| dish_r3_control_preplaced | 原尺寸 | 四件餐具预放置 |
| dish_r3_wide_full | 加宽勺柄 | 完整任务 |
| dish_r3_wide_preplaced | 加宽勺柄 | 四件餐具预放置 |

各条件输出 `scene/main.usd`、`task_config.yml`、权威 `episode_metadata.json` 和
兼容 `meta_info.pkl`。`suite.json` 记录源指纹、场景与元数据哈希、变量标签和待验证状态。

实际安装到 `/cpfs/shared/simulation/zhuzihou/dev/GenManip`：

- `configs/tasks/eeos_evolution/dish_*.yml`
- `saved/tasks/eeos_evolution/dish_*/000/`

安装不覆盖已有目录，先核对场景、JSON 与 pickle 哈希。`installation.json` 保留目标路径与配置哈希。
本次编译／安装没有运行机器人或模型，也没有修改官方任务。

## 检查

实际 USD 组合检查显示勺子 source pose 一致，原尺寸版点数组与原源一致，加宽版点数组不同；
两版材质绑定有效，质量均保留约 0.1 kg。其余 2,877 个源场景节点仍存在，Xform 与源场景一致。
这不替代最终 reset 后的模型观测检查。

两项针对性测试通过：只修改四件餐具、篮子坐标系变化时拒绝预放置；四条件 goal 相同，
同进度的两种几何初态相同；不能覆盖已有任务；修改兼容元数据后拒绝安装。
新增模块、CLI 与测试 ruff 通过。未运行完整 `make check`，未合并。

```bash
EEOS_PYTHON=/cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python
"$EEOS_PYTHON" scripts/compile_ebench_intervention_suite.py \
  --config configs/research/ebench_dish_interventions.json \
  --output outputs/NEW-dish-interventions
"$EEOS_PYTHON" scripts/compile_ebench_intervention_suite.py \
  --output outputs/NEW-dish-interventions \
  --install-genmanip-root /path/to/unused-runtime-root
```

实际注册的四个名字已占用，不应重复执行安装去覆盖它们。

EEOS 已用新 run ID 启动 r3 原尺寸完整初态对照，并实际完成 reset；终止模型结果仍待回收。

## 规范与下一步

遵循 ASSET-001 的生产者职责、ASSET-002 的来源绑定，以及 VAL-002/003 的验证范围与最终内容。
没有改变通用制作准则，因此不改写规范库。下一步由 EEOS 执行 reset、固定相机与分项目标检查，
再开展配对 VLA 实验；没有提前声明任务可解或新弱点成立。

## 2026-09-11 Git 收尾复核

同期的惯性匹配、剩余目标指令配置与本编译器一并整理，接口定义补至
[native intervention contract](../design/ebench-native-intervention-suite.md)。
补齐公开函数的类型标注，严格定向类型检查通过。

收尾回归先复现两个异常路径缺口，再作最小修复：
非法 USD 路径此前会创建半成品目录，现于建目录前拒绝；安装此前未复核源 wrapper，
现检查 `base_entrypoint_sha256`，在写任务前拒绝源入口变化。
四项 adapter 测试通过；包含原有四条件、坐标系、指令一致性、禁止覆盖和篡改拒绝检查。

三份实际研究配置在独立临时目录重新编译，共12个原生入口均能用 USD 加载并找到
`/World/_scene/obj_spoon`，各入口2886个 prim；临时运行目录的安装检查也通过。
验证没有改写原 GenManip 注册、没有运行模型或仿真，状态继续为
`compiled_not_runtime_verified`。原研究输出和已记录的下游证据保留。

类型检查命令（临时工具环境使用 mypy 2.3.1）：
`mypy --follow-imports=skip src/scenario_forge/adapters/ebench/intervention_suite.py`。
跟随项目全部导入的尝试另暴露了已提交模块中的历史类型问题，未将定向通过解释为全库 mypy 通过。
