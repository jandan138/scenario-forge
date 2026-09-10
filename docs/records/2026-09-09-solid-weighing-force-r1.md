# 2026-09-09：固体称量的受力天平修复与双版本准入

## 来源与责任

来源为 `external_artifacts/incoming/from_xinyu/task_09_solid_weighing.zip`。
ZIP SHA256：`adf898a57146a858d37ca4f4eddfc039cfe41bf78271818cfeee667914a95d5d`。
原场景 SHA256：`f0cb8161d0d8476c2ffa4b27439bfa90c59bc8a866c0d51da69b1f17405be355`。
来件编号 task09 与旧任务目录中的固体称量任务序号不是同一套编号，未改写历史任务包。

原文件包含静态 `balance:lcd_readout = "0.0000 g"`、数字几何和一个按钮滑动关节，
未找到称重／去皮的内嵌实现。原机身 `physics:mass = 1000000 kg`，与标注的 6.8 kg 不符。
原加载器代码未提供；在本机独立进程中，用现有高层 Articulation API 显式写零并重复 reset，
两个版本都没有复现原反馈中的崩溃。不能据此否定同事报告或宣布已定位原始根因。

生产者修复在 ConvertAsset；Scenario Forge 只消费新资产及来源绑定的载荷物理配置，
组装任务与交付。没有修改 core/schema/API，没有添加 episode runner。

## 最终行为与实测选择

- 机身恢复 6.8 kg；独立 0.05 kg 秤盘通过固定承重关节连接机身，按钮为 0–1.5 mm 滑动关节。
- 保留可搬动机身；没有 `BaseFixed`。记录来源元数据，并将当前版本和按钮角色更新为受力称重版本。
- 对 link-local 反作用力作世界竖直投影，除以重力，扣秤盘自重，滤波后扣皮重。
- 默认分度 0.1 g、量程 200 g、目标净重 30 g、容差 ±0.2 g；后台保留未舍入的连续值。
- 0.01 g 在规则砝码上可以得到较小误差，但真实颗粒接触下在两个版本间不能稳定满足同样条件，未按该精度交付。
- 去皮等稳定，超时 5 秒不覆盖旧皮重；成功保持 2 秒并锁定快照，实时读数继续变化。
- 机身移动／拿起时读数无效，放稳后恢复，皮重保留；整轮重置清除逻辑状态但不替加载器移动物体。
- 原任务样品初始放在称量舟附近，现将五颗样品放入已有样品瓶，保留其余布局和称量舟，新增可达到性检查。

## 关键实验教训

独立真实几何实验曾出现 30 g 载荷只读到约 3.75 g 的情况。
保持 articulation 与载荷清醒并关闭相关稳定化后，已知载荷读数恢复；没有乘以经验倍率补偿，
没有用粒子数量代替受力。结论绑定本次 PhysX/Isaac 组合条件，不声称所有 force sensor 都有相同问题。

4.1 的 CPU 物理不能接收来件中部分 SDF 容器，导致部分物体没有加入物理场景。
因此最终任务采用 GPU Dynamics / GPU Broadphase / TGS，并在两个版本中验证。
天平本身的 CPU 测力实验不能替代完整任务 GPU 验证。

交付闭包检查发现原文件依赖隐式 SDK `OmniPBR.mdl`、`OmniGlass.mdl`、`OmniSurface.mdl`。
生产者通过 AAN 的 `build_material_runtime_closure` 分别收集两个 runtime 的模块及辅助依赖，
保留版权头；使用对应版本的本地文件，不把这些非原生模块简单列为“可忽略缺失”。
本地化后两个 USD 入口的 `ComputeAllDependencies` 均无缺失，重新执行 `bundle*` 验证矩阵。

4.5 的 World 管理器在部分预打开场景路径下使用 60 Hz fallback。
最终验证直接以 1/120 秒调用物理推进，分别记录实际步长和 World 管理器返回值；
任务控制器从 OnPhysicsStep 的实际 delta 计时，没有用外层循环次数冒充仿真时间。

曾尝试减小颗粒／称量舟的接触偏移，实际稳定性变差，未采用该调整。
最终保留来件这部分碰撞参数，仅由生产者提供已验证的清醒／稳定化配置。

数字显示最初的小数点被屏幕表面遮挡，后改为间隙内可见的小圆点，并重拍。
渲染结束后的 Replicator 等待曾导致实验进程不退出；验证脚本改为不等待已完成的 Replicator，
正式运行还检查进程退出码。旧诊断没有改成新的通过证据。

## 证据位置与边界

最终任务目录：

```text
/cpfs/user/zhuzihou/dev/scenario-forge/outputs/scientific_workbench_solid_sample_weighing_vr_r1_20260909/handoff/scientific_workbench_solid_sample_weighing_vr_r1
```

任务证据在同一生成根的 `evidence/bundle{41,45}_{zero,omitted,pressed}.json`。
报告绑定场景 SHA、设备 SHA、包含 USD/MDL/纹理/入口配置的内容指纹、PID、runtime 和实际物理步长。
原始诊断 `gpu*`、`candidate*`、早期 `final*`、材质本地化前的 `release*` 不代替 bundle 报告。
生产者证据位于 ConvertAsset 的 `outputs/balance_force_r1_20260909/`。
最终是否准入以交付 `manifest.json`、生产者 promotion 和 ZIP receipt 为准。

验证使用真实物理中的受控放置、关节位置按压与外力施加；不证明机器人完成了抓取、舀取或完整策略。
搬动验证包含 12 cm 抬起、12 cm 平移、30° 水平转向及重新加样。
运行时有效性使用姿态、速度和台面高度条件，不能称为完整接触检测或校准系统。

## 规范同步

依据当前工作树制作规范，适用 ASSET-001/002/003、ART-002/005/006、STATE-001 至 STATE-006、VAL-001 至 VAL-007。
自由基座不进入 ART-001 至 ART-004 的固定基座资格范围。
新增 STATE-007，明确测量条件、显示分度和实际误差的区分。
同步设计 `docs/design/force-weighing-device.md`、教学 `docs/operations/solid-weighing-r1-guide.md`，
保留旧任务与旧规范记录，不做历史追认。

## 最终检查

- `make check`：973 passed、1 skipped；Ruff、package-smoke、phase10x 与 `git diff --check` 通过。
- 最终元数据更新后，相关测试再跑 22 项通过。ConvertAsset 定向测试 3 项通过；结合现有 MDL 闭包测试共 24 项通过，相关脚本 Ruff 通过。
- 任务与独立资产各 6 次独立进程，覆盖两个 runtime 的省略／零／非零初值，全部通过相应门槛并正常退出。
- 10 张最终图做本地目视检查，未独立委派视觉复核。读数、小数点、负号可读；特写裁切称量舟上沿、两版背景塑料件色调不同，保留 WARN，不声称像素一致。
- 交付类别为 `scene_fixture_verified`；已加入当前任务头 `solid_sample_weighing / vr_force_balance_dual_runtime`。

场景 SHA256：`ca7410b8810de82a92a9fda06ffbc4a4cbd1d627b21086d8aa3894bc198f8335`。

内容指纹：`46c7239bcd1352d4ecc3b4a4711e3c283c9f684a748d0dade051eded5cd5cde1`。

任务 ZIP SHA256：`e6e520aa376aba95a3bf387c14cba8a15ba13154f3dc3d656a30ff7add7ebc8c`。

独立资产 SHA256：`56ef7fbe5d9313c3f33a9bf9777aab13ba42e3d47589f2c7e90ca486d8f93a0b`。

独立资产 ZIP SHA256：`91927b1d2cfa1db9e8d2488b2a46e3ec0f6a822498047bca4f74d4c5f1f4fac0`。

原始 CPU SDF 失败日志已保留在 ConvertAsset `outputs/balance_force_r1_20260909/diagnostics/weighing-live41.log`。最终源依赖、材质编译日志和视觉指纹随生产者包保留。

生产者代码与记录提交：ConvertAsset `8d7e2da`。Scenario Forge 本次实现与规范更新保留在当前工作区，未混入此前未提交的其他任务变更。
