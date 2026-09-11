# 斐林水浴 r4：CPU 可接触碰撞（摆放不变）

规范依据：2026-09-08 场景制作规范首版；本次同步 [USD-008](../standards/usd-layout.md#usd-008)、[ASSET-007](../standards/asset-intake.md#asset-007)。
涉及规则：USD-008、ASSET-001、ASSET-007、MAT-001、VAL-001。
变化：新包 r4 从 r3 派生。所有 `obj_*` / table / background 世界坐标不变。试管架视觉网格去掉碰撞、保留孔底圆柱；试管空心 SDF 碰撞 API 全部移除，增加与外形包络一致的不可见圆柱。烧杯改为 kinematic，杯壁 SDF 改为三角网格。反应策略仍为 `visual_water_contact_v3`。假水无碰撞。
验证：`tests/test_fehlings_r4.py` 对照 r3 源包检查摆放哈希级相等与碰撞改写。Isaac 4.1 DemoGen 抓取视频不作为包 fixture 资格。
限制或例外：用户授权在新包中改 USD 物理近似，作为 ASSET-001「消费者不修生产者碰撞」的任务例外。不宣称 4.1 变色、不宣称策略成功。
同步内容：生成器、测试、current_task_heads、本记录、USD-008/ASSET-007。

## Why

Isaac 4.1 `EnableGPUDynamics=false` 时 PhysX 拒绝 SDF 刚体：`Rigid actors with SDFs are currently only supported with GPU-accelerated scenes`。r3 试管架与试管的 SDF 因此未进入场景，Lift2 抓夹穿试管架、合拢穿过试管。这不是 Fehling metric（触水 60 s / 观察）的设计结果。打开 GPU dynamics 后 SDF 会进 PhysX（4.1 支持 GPU+SDF），但本机 Lift2 夹空心 SDF 试管时出现大量 `Invalid PhysX transform`，物体位姿飞到几十米；不是 GPU 驱动崩溃。r4 因此走 CPU 近似碰撞，而不是打开 GPU dynamics。

## Package

Generator: `python -m scripts.generate_fehlings_water_bath_r4`

Output: `outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r4_20260911/`

Tube cylinder: radius 8.61 mm, height 101 mm, origin at tube bottom, contactOffset 0.5 mm. Rack hole slot cylinders from r3 are unchanged. The rack visual mesh has collision stripped so the 15 mL slots stay open for extraction; disabled SDF on the tube mesh is stripped because a leftover SDF shape rejects the whole rigid actor on CPU. The beaker is kinematic with triangle-mesh walls so immersion can contact without GPU dynamics.

## DemoGen evidence (Isaac 4.1, not a package fixture)

Lift2 25° side rim pinch. Object world placements unchanged vs r3.

- Oracle (kinematic attach, finger opening 0.005): episode `GenManip-Sim/saved/demonstrations/scenario_forge/fehlings_r4_oracle_rim/trajectory/2026-09-11_14_31_05_273583`. Hold 1977 frames within 4 cm of beaker XY, tube bottom mean z 0.886 (about 32 mm below fake-water surface 0.919). Videos: `.../fehlings_r4_oracle_rim/videos/fehlings_r4_oracle_rim_overlook.mp4` and `..._left_wrist.mp4`.
- Contact (no attach, commanded opening 0.0, qpos stalls ~0.0037): episode `.../fehlings_r4_contact_rim/trajectory/2026-09-11_14_34_53_805829`. Hold 1866 frames within 4 cm, tube bottom mean z 0.877 (about 42 mm below water). Tube dropped on withdraw. Videos: `.../fehlings_r4_contact_rim/videos/fehlings_r4_contact_rim_overlook.mp4` and `..._left_wrist.mp4`.

Does not claim `robot_policy_success`, Fehling color change, or `scene_fixture_verified`.

## Git 收尾：无 PhysX 插件时的 schema 移除修正

收尾检查在普通 usd-core 26.5 中发现：原候选试管网格的 `GetAppliedSchemas()` 只显示
MaterialBindingAPI，但原始 `apiSchemas` 仍含 `PhysxSDFMeshCollisionAPI` 和 `PhysxCollisionAPI`。
原实现只在能导入 PhysxSchema 时删除这些 API，纯 USD 环境生成的文件会把标记留给之后的 PhysX loader。

新增回归测试先模拟没有 PhysxSchema 的环境，直接检查 metadata，复现失败；
修复为按已知 schema token 调用 `RemoveAppliedSchema`。两项 r4 测试及定向 Ruff 通过。
同步 USD-008 对未知 schema 的检查说明；没有扩大 CPU 场景或机器人资格。

修正候选单独生成至：
`outputs/scientific_workbench_fehlings_reducing_sugar_water_bath_vr_r4_cpu_schema_fixed_20260911/`。
原 `...vr_r4_20260911/` 及上述历史 DemoGen 证据保留，不替换为新场景运行证据。

- 修正场景 SHA256：`54fad903fe1e3e0413ce9e9d359e2de366a6b7c165ee4b611ae81b2c4620a992`。
- 试管／架子原网格的 authored API 只保留 MaterialBindingAPI，物体世界平移与 r3 相同。
- 静态闭包与异目录解压检查通过，70项包内依赖；ZIP CRC 通过。
- ZIP：94,391,459 bytes，SHA256 `10e1ff2fb5819ee400fd2d418dae63ee78ffc5a69ed5b0ee2f9495ae8bd8fe11`。
- 当前 CPU variant 头指向修正候选，状态仍为 `current_candidate`；manifest 为 `runtime_pending`。
- 本次没有对修正候选进行 Isaac 4.1／机器人运行验证，不用静态通过替代该证据。

生成器默认输出改为修正候选目录，避免后续生成误写原候选。复现时使用 `--out` 选择新目录。
