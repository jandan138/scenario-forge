# Task18 回到菲林正式包的最小迁移对照

状态：实施与诊断中，未交付。用户批准以菲林正式包为物理基准，允许在有故障证据时重做等效银镜显示；120Hz、7000步、原银镜反应时间、评分与原动作不变，本轮不更新LeRobot。

## 基准与失败证据

基准为 `/mnt/data/chenjiantong/scientific_experiments_data/releases/task12_real_liquid_r1`，校验 READY 对应的 MANIFEST、ACCEPTANCE 和 ZIP，提取并逐项核验705个离线文件。GenManip代码基线为 `9490df9a3710bbcea97cd2470adc364a13883914`。正式包和建通安装目录不改动。

新制作根为 `/cpfs/user/zhuzihou/dev/task18-fehling-baseline-20261021`。`evidence/A_identity.json` 绑定冻结副本与文件哈希。原制作根 `task18-silver-delivery-20261020` 保留，不覆盖旧失败。

v8候选11次回放已结束，但接收端mixed20在最后记录约1580步后出现SparseGrid/isosurface CUDA700，仍未获运行资格。接收初始化mixed10已完成；GPU1随后响应全局停止，并非独立初始化失败。旧监督器会覆盖首错标记，新独立工具用不可覆盖的首错文件及逐事件记录区分直接失败与连带停止。两项测试验证首错保留和无故障时无停止标记；工具不进入交付包。

## 对照设计

- A原包：归档字节不变，先复跑已验证来源11（unseen_background_9、chunk30），只检查当前环境与历史协议，不把能启动等同恢复满分。
- A匹配诊断：保留菲林场景物理与反应，显式采用银镜对应案例的布局和粒子初态，保持同一动作输入；记录场景映射，跨任务分数不比较。
- B最小银镜：从A场景复制物理，接入银镜内壁外观、透明样液及任务语义；不带入v6/v7/v8烧杯、地板或液面改动。
- C显示冻结：只停止银镜外观写入，保留状态计算与物理；仅用于隔离，不交付。

同一GPU0、相同软件与执行协议，mixed20和mixed17分别A-B-B-A；B单独故障时转C-B-C诊断，A也故障时先查共同配置或环境。最终仍需独立接收验证、全量场景检查和正式发布，不能以对照中一次不复现抵消既有失败。

## 首轮落地结果

20个B场景与A的物理属性、原始API标记、碰撞体和物理材质绑定一致，依赖闭包通过；两个配对案例的布局与粒子初态逐项相等。原银镜时序保持不变，9项规则测试和12项实际metric方法测试通过。证据为 `evidence/minimal_static_audit.json` 和 `evidence/minimal_actual_metric_tests.json`。继承的浴水surface/grid范围问题仍作为明确诊断变量保留，不以静态物理一致宣称新包合格。

原包校准 `silver_baseline_A_calibration_h11_20261021T024815_100750Z` 正常完成2902步、1分，完整日志复扫无匹配错误、四路视频完整解码。四机位各9帧由实施者查看：水中样液蓝→绿→黄橙，终帧试管在架孔内、夹爪撤离，选帧未见整体弹飞或灰屏。手腕机位有遮挡，不作逐帧保液/碰撞保证。新旧同来源的机器人观测并非逐位一致：关节最大差约0.000205rad、底座约8.94微米、夹爪约0.000571；不推广为物体轨迹确定性。见 `reviews/silver_baseline_A_calibration_h11` 和 `evidence/A_calibration_state_comparison.json`。

离线证据收集初版只读server.log而漏掉worker内物理时钟，产生“无时钟证据”的分析错误；原记录保留，v2合并server/worker读取并复用现有视频，不重跑仿真。当前A匹配诊断已自动启动mixed20。分支监督器已准备在B直接失败时接续C-B-C，不把连带停止当第二个资产故障。

A匹配诊断首次在初始化失败：其task data仍带有25个银镜内壁显示重置键，菲林USD没有这些对象；尚未开始物理动作，因此不是共享PBD崩溃证据。保留该尝试，另建 `A_matched_diagnostic_r2`，只将这25项替换为菲林自己的视觉重置项，布局/粒子/物理资产不变。全部A/B/C配置均追加“每个重置属性确实存在”检查后通过。当前权威队列为 `evidence/diagnostic_queue_r2.json`，配对清单为 `evidence/paired_jobs_r2.json`；分支为 `branch_coordinator_r2.json`，离线收集为 `review_preparation_queue_v3.json`。不重跑已成功的原包来源11校准。

仓库 `make check` 已完成：1255 passed、1 skipped，Ruff及包/suite smoke通过。该检查不代替外部Isaac运行资格。

## 边界与同步

适用MAT-001/004/006、STATE-001..004、VAL-001..008；诊断与制作工具留在仓库外，Scenario Forge无新增运行器、SDK依赖或公共接口。当前只是任务特定诊断，尚无依据更改通用规范。操作入口同步至Task18交付指南。后续实测结论追加到本记录，不能把静态比较写成运行通过。
