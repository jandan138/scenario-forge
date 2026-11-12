# Scientific experiments zero-shot packages

Date: 2026-09-24.

规范依据：当前 `docs/standards` 资产接入与验证正文；包形状仍以 `docs/design/package-v0.2.md` 为准。
涉及规则：ASSET-001、ASSET-002、ASSET-004、USD-002、VAL-001、VAL-003、VAL-005。
变化：**规范无需变更**。本批沿用 2026-09-20 同事精校拍扁场景的静态打包，只增加
`task_z*` zero-shot 目录。不新增通用准入、物化或 runtime 规则。
验证：`tests/test_scientific_experiments_zero_shot_packages.py`；
`scripts/build_scientific_experiments_colleague_final.py --batch zero-shot`
对 6 个包跑 `validate_package`（v0.2 含 `check_asset_lock`），全部 PASS。
120 个 `scene.usd` 与源文件为同一 inode。源目录 mtime 未变。
限制：不宣称 ConvertAsset visual/runtime admission、`scene_fixture_verified`、
机器人抓取、液体转移或 benchmark。未更新 `configs/artifact_retention/current_task_heads.v1.json`。
未改写 `outputs/scientific_experiments_colleague_final_20260920/`。
同步内容：构建脚本的 `--batch zero-shot`、本记录、
`outputs/scientific_experiments_colleague_zero_shot_20260924/`。
未改 `docs/standards` 规则正文。

## Source

`/cpfs/shared/simulation/chenjiantong/scene_usds/scientific_experiments`

6 个目录，各 10 seen + 10 unseen。源只读：不改 `scene.usda`，也不改 crate 内
OmniGraph、设置 Scope 或 `userDocBrief`。

| 目录 | 模式 | 包 |
|---|---|---|
| `task_z1_remove_beaker_pour_shake` | stub | 取出烧杯、倾倒并振荡 |
| `task_z2_key_steps_in_mof` | stub | MOF 关键步骤 |
| `task_z3_boat_pour_stir` | stub | 称量舟倾倒与搅拌；不移植 `boat_pour_stir` |
| `task_z4_silver_mirror_reaction` | stub | 银镜反应 |
| `task_z5_fixed_weight_weighing` | stub | 定质量称量；不移植 `task_14` |
| `task_z6_evaporative_crystallization_prep` | stub | 蒸发结晶准备 |

输出：`outputs/scientific_experiments_colleague_zero_shot_20260924/`。
盘点：120 场景、1740 条 prim 观察、**42 个 unique 几何指纹**。
谓词/metrics 为 `catalog_pending` / `not_run`。`robot.yaml` 仍是 Lift2 占位，
`robot_grasp_verified: false`。

## What stays in the crate

身份抽取仍只收 `obj_*`、`table`、`Room`。下列 prim 留在原 `scene.usd` 字节里，
不拆成 identity USD：

- 元数据：`MixingGraph`、`MixingSettings`、`Task15Glass`、`Task15GlassFoot`、
  `CopperCrystalLooks`、`CopperSulfateExperiment`、`PhysicsMaterials`、`Graphs`、
  `LiquidSource`、`HeatingStatus`
- `asset_01` / `asset_03`（z6，带 mesh 与 `userDocBrief`）

`scene/main.usda` 仍 payload 默认 `seen_scene_01` 的 `scene.usd`，不改写同事的 `scene.usda`。

## Claim boundary

通过：包 schema、`asset_lock`、composed crate 与源字节一致、inventory 无重复指纹、
元数据 prim 未进入身份表。

不宣称：ConvertAsset visual/runtime admission、`scene_fixture_verified`、抓取、
液体转移、显色/粉末 runtime、benchmark。
