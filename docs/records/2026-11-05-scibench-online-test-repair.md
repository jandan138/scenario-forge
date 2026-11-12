# SciBench 在线 test 交付修复（进行中）

旧版交付遗漏运行时强制使用的340个scene.usda入口及递归共享依赖。旧文件数/哈希核对仅证明已选文件传输完整，不能证明运行入口完整；此前可运行结论撤回。原OSS完成标记已改为REPAIR_IN_PROGRESS_PREVIOUS_DELIVERY_INCOMPLETE。

用户要求在10.150.168.71（Isaac4.1.0）新建独立GenManip仓库，拉取feature/pioneer最新代码，saved只使用实际交付内容，原生验证通过后才补传同一OSS地址。已成功从远端fetch并固定7939a4c88b5348b45b827e1d684fc560b134fce2，客户端子模块61202ccc1419d1e1427ea750bfdeb44309862386。源仓库、源saved与其他validation工作保持不变。

工作目录：/cpfs/user/zhuzihou/dev/scibench-test-repair-20261105/。
候选递归收集scene.usda、_dependencies、materials及项目MDL，尚未声明闭包通过；旧包入口回归审计返回失败符合预期。全量680例reset/10步原生测试和视觉复核尚待运行。

适用ASSET-002、VAL-001/002/003/004/005/007。规范无需变更：修复交付实现违反既有入口/依赖验收要求的问题，不改变物理规则、任务参数或评分。操作说明将在验证后同步最终清单与验收范围。

## 原生检查进展

三个task_z1 mixed_1/2/3已在新仓库和完整saved副本中通过reset及10步保持动作测试；mixed_3启动器收尾错误后另做干净重跑，证据为scibench_canary3_clean_20261105。首次原生运行发现规划器读取miscs/curobo/R5a，已补20个文件。候选8734文件，运行副本全量SHA256检查零差异。旧包入口回归失败、新包340入口/680metadata静态检查通过。make check通过：1259 passed、1 skipped。

全量诊断使用原配置的副本，仅将num_steps设为10，以便返回正式episode_result；原始配置不修改，诊断配置不交付。当前run为scibench_fullsuite_r2_20261105，使用离线模式，结果在evidence同名.client/progress.json，尚未全量完成，禁止标记最终交付通过。首轮JSON路径提交因接口只接受配置目录而失败，未下载额外数据；已改用本地目录组。

## 用户缩减运行范围

用户明确要求停止680例全量运行。全量r2在完成5例后中止，已通过结果保留，不声称全量通过。改为20类任务各一例代表样例（mixed_1优先）加已完成的task_z1三例回归；静态入口和metadata检查仍覆盖全部680例。当前run：scibench_representative_r1_20261105。用户询问_dependencies是否必要；源task12 seen_scene_1/scene.usda显式引用../../../../_dependencies/usd/c4dd50a6c0f8d8a34a6e/scene.usda，因此当前引用关系下必须保留实际依赖子集，不能视为缓存省略。

## _dependencies来源复核

用户询问c4dd50a6c0f8d8a34a6e/scene.usda的来源。该2951字节文件是2026-10-30 task12-task18-fixed-bath-normal-operation-v1 payload的一部分，由scientific-round2-final-integration-20261030/apply_payload.py安装；baseline_saved_manifest中不存在，integrated_saved_manifest中新增。当前SHA256为77e26fc3ca59d2786c259fb93e0d37a36caf9d801877ff89ae415255f1b5dd60，与当时清单一致。其subLayer为../8e649de41fdd34f45302/scene.usda，并对试管Visual/GlassShell设置sdfNarrowBandThickness=0.05；外层task12入口再叠加固定烧杯和视觉水浴。此次修复只是补交已有依赖，未引入这项物理设置。

## 本地验收完成

代表样例20/20通过，每例实际执行10步并返回有限数值评分；原task_z1三例回归也通过。全量680例仅作静态入口/metadata检查，不声称原生全量通过。20组overlook/top起止画面由实现者复核，暗玻璃与遮挡限制记录在visual/review.json。运行前后8734数据文件哈希一致；新增834文件178226224字节，旧重叠文件哈希未改。

完整Ray IsaacWorker out/err扫描指定阻断标记零命中，但有227条引擎Error记录（37种完整文本），包括接触/静止偏移、非根关节速度恢复、ScriptNode.release以及删除不存在Camera。Camera/ScriptNode释放问题在10月30日交付KNOWN_ISSUES中已有记录。本次不作零错误或完整热切换稳定性声明，不为消日志修改物理参数。

候选已上传原OSS，下载回读校验进行中；最终完成标记在校验后发布。VALIDATION_REPORT.json、VISUAL_REVIEW.json、manifest.json及RETAINED_LEGACY_FILES.json同步限定证据范围。

## 最终交付

修复r2已上传原OSS。rclone下载回读：8740文件匹配、0差异；最终两份计数澄清文档另做下载回读2文件匹配、0差异。远端实际数据逐路径列举8734文件，缺失0、额外0；首版427附加材质路径在当前远端未列出，已有接收目录可能仍保留。本次未执行远端delete/sync，最终说明按实际远端清单更正。

DELIVERY_COMPLETE.json最后发布并回读逐字节一致，状态TRANSFER_VERIFIED_SMOKE20_PASSED_WITH_RUNTIME_LIMITS。必需数据总量14113368863字节；远端scene_usds/scientific_experiments7559文件、tasks680、专用robot2。旧接收目录若保留427附加文件，场景计数会为7986，需以manifest/SHA而非单独总数判缺失。

最终证据入口：工作目录FINAL_DELIVERY.json、post-runtime-hash-audit.json、remote-inventory-audit.json、download-check.log、final-doc-check.log、remote-completion.json、native-log-audit.json、visual/review.json。操作指南已同步。本次没有修改科学任务物理/评分或核心接口；规范无需变更的理由同上。
