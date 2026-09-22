# Scientific experiments colleague final packages

Date: 2026-09-20.

规范依据：当前 `docs/standards` 资产接入与验证正文；包形状仍以 `docs/design/package-v0.2.md` 为准。
涉及规则：ASSET-001、ASSET-002、ASSET-004、USD-003、USD-004、VAL-001、VAL-003。
变化：**规范无需变更**。本批是一次外部精校拍扁场景的静态打包，不新增通用准入、
物化或 runtime 规则。ASSET-001/002 与 VAL-001/003 已覆盖「文件名含 final 不能冒充
ConvertAsset 生产者准入」。
验证：`scripts/build_scientific_experiments_colleague_final.py` 对 14 个包跑
`scenario-forge package check`（`validate_package` + `check_asset_lock`）。
限制：不宣称 ConvertAsset visual/runtime admission、`scene_fixture_verified`、
机器人抓取、液体转移或 benchmark。未更新 `configs/artifact_retention/current_task_heads.v1.json`。
同步内容：一次性构建脚本、本记录、`outputs/scientific_experiments_colleague_final_20260920/`。
未改 `docs/standards` 规则正文。

## Source

`/cpfs/shared/simulation/chenjiantong/scene_usds/scientific_experiments`

14 任务 × 10 seen + 10 unseen。几何已拍扁进各 `scene.usd`；MDL/纹理走旁边的 `SubUSDs`。
同事目录号 `task_01`–`task_14` 与飞书 18 行目录 / `current_task_heads` 编号不是同一套，
不回写。

输出：`outputs/scientific_experiments_colleague_final_20260920/`。
盘点：280 场景、3640 条 prim 观察、**48 个 unique 几何指纹**（无重复）。
`table` 全批次同一指纹。Room 有 5 个指纹（425 / 440 / 456 / 622 / 704 mesh），
不是简单的 seen vs unseen 二分。同指纹异名记入 `aliases`
（例如 `obj_plate` = `obj_steel_plate` / `obj_paper`；`obj_primary_tube` = `obj_balance_tube`）。

## Unique-asset rule

- 指纹：对象根下 mesh 相对路径 + 点数/面数 + 三点采样，**不含**世界平移。
- 同一几何指纹只准入一次；`asset_id` 用首次出现的 prim 名 + 12 位指纹，例如
  `colleague_obj_r9_amber_bottle_<12hex>`。后续同指纹别名写入 `aliases`。
- 计入：`obj_*`、`table`、`Room`；`background_object` 内部递归 `obj_*`。
- 跳过：`ParticleSystem` / `ParticleSet` / `fluid_runtime` / `Looks` /
  `BlueBottleGraph` / 单粒 `obj_grain_*`。task_09 每个 variant 有 5 粒 World 级
  `obj_grain_*`（20×5=100），只在 provenance 记配方，不各算一个准入资产。
- License：`internal-colleague-reviewed-20260920`。
- SubUSDs 按内容哈希 hardlink 去重；lock scanner 只扫 `.usd`/`.usda`。
- 这不是 ConvertAsset `evidence/manifest.json` 准入。claim 停在 `asset_locked`。

Identity USD 在 `admitted_assets/`：mesh ≤ 200 用 `Sdf.CopySpec` 抽几何（清世界平移）；
更大的 Room 只写指纹记录 USDA。`scene/main.usda` **不**改引用这些 identity USD。

## Package shape

每个任务族一个 `scenario-package/v0.2` fat 包：

- `assets/composed/{seen,unseen}_scene_NN/scene.usd`：精校 crate 原字节
- 同目录 `SubUSDs/`：保留 crate 内 `./SubUSDs/...` 相对引用
- `scene/main.usda`：薄包装，`payload = @../assets/composed/seen_scene_01/scene.usd@`
- 20 个 variant 写入 `metrics/splits.yaml`；默认入口 `seen_scene_01`
- `scene/instances.yaml`：默认场景 `/World` 子节点绑定 unique `asset_id` 与世界位姿
- `locks/asset_lock.yaml`：`generate_asset_lock`

未把拍扁解析放进 `src/`，避免扩大包契约。未做 VR 物化重导出。

## Semantics

| 同事目录 | 模式 | 来源头 |
|---|---|---|
| task_01 | port | `task01_flask_to_cylinder` |
| task_02 | port | `task02_cylinder_to_beaker`（场景含搅拌棒，不宣称搅拌已验证） |
| task_03 | stub | 磁力搅拌 |
| task_04 | stub | 漏斗倒液 |
| task_05 | port | `task05_remove_ground_glass_stopper` r11 |
| task_06 | port | `task11_centrifuge_unload_shutdown` |
| task_07 | port | `task12_centrifuge_rack_to_rotor` |
| task_08 | port | `task09_oven_load_start` r16 |
| task_09 | port | `solid_sample_weighing` |
| task_10 | port | `traditional_acid_base_titration` r1.7 |
| task_11 | port | `task12_oven_unload_dual_glassware` r2 |
| task_12 | port | `fehlings_reducing_sugar_water_bath` r10 |
| task_13 | stub | 蓝瓶子 |
| task_14 | stub | 定质量称量 |

谓词/metrics 标 `not_run`。`robot.yaml` 统一 Lift2 占位，`robot_grasp_verified: false`。

## Claim boundary

通过：包 schema、`asset_lock`、`main.usda` 引用的 composed crate 在 `assets/` 下且已锁、
crate 旁 SubUSDs 闭包存在、inventory 无重复指纹。

不宣称：ConvertAsset visual/runtime admission、`scene_fixture_verified`、抓取、
液体转移、显色/粉末/水浴 runtime、benchmark。
