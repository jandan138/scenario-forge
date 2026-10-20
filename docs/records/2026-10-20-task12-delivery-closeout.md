# Task12真液体水浴r1交付收尾

状态：READY_WITH_STATED_LIMITATIONS，2026-10-20已发布并同步飞书。前序安装过程见[准备记录](2026-10-20-task12-final-delivery-preparation.md)。

正式入口：`/mnt/data/chenjiantong/scientific_experiments_data/releases/task12_real_liquid_r1/README.md`。同目录有705文件的task12_offline.zip、metric bundle/mbox、MANIFEST、ACCEPTANCE、SHA256SUMS、READY及7组四机位验证视频。生产已安装于`/mnt/data/chenjiantong/GenManip-Sim`，分支delivery/task12-real-liquid-r1，提交9490df9a3710bbcea97cd2470adc364a13883914。备份和原始结果保留。

仅交付YAML、USD、task data、scientific metric；LeRobot/训练/OSS数据集不更新。接收运行不依赖制作脚本。705项安装内容全量SHA一致，1476个其他受追踪文件保持原内容，含称量40个既有YAML覆盖。

## 接收验收

主机10.150.164.127，dsw-536365-78bdb944c8-q99ff，4×RTX4090。GPU0..3各10例原生冷启动，40/40完成；四机位视频解码与日志检查通过，160张初始化图通过14张汇总图目视，未见明显缺资产/黄色贴图。黑色桌面场景偏暗，不能由此推广为所有动态行为合格。

GPU0来源15完整回放0.85/7000步，GPU1来源11为1.0/2902步，GPU2 mixed5为0.15/7000步。所有原生结果保留。来源11画面确认蓝到黄橙、插回及撤手；来源15显色完成但回架失败。mixed5约3600步释放后落在架前桌面；周期状态有效加热约4.57秒、进度0.045，未达到显色门槛，故比预交付0.5少了显色分。两次结果均保留，不宣称完全确定性复现。三例周期pbd_valid均为真，runtime_error为空；未据此宣称逐步保液。

已查看三例color/release_left/release_global图；mixed5补看2900..4000每100帧、4500..7000每500帧top/left视角。完整自动队列09:37UTC结束，最终检查四卡0MiB、端口8187..8190空闲。没有新增仿真调参、改动作或为分数改metric。

## 明确保留的限制

用户与同事接受换USD后同动作成功率下降。11/38是最终显色提前0.75秒之前参考版成绩，不是本最终版的38次实测；没有用本轮3例估计策略成功率。成功演示为历史评测动作回放，不是原始teleop或在线策略验收。

文档5条坏例已有最终候选完整回放和关键帧复核，mixed5追加接收端回放。检查画面未见明显穿桌或烧杯大幅异常；没有定位原穿模瞬间、没有逐物理步几何间隙或保液证明，遮挡限制仍在。因此报告检查范围未复现，不宣称普遍无穿模或因果修复。回架失败等真实任务失败继续作为已知限制交付。

## 文档与证据

飞书第4节Task12当前交付状态及两项穿桌问题说明已精准更新，回读revision6888确认。未发送IM或群消息。工具回执保存在制作根evidence/feishu_update.json、feishu_issue_update0/1.json、feishu_after.json。

制作根`/cpfs/user/zhuzihou/dev/task12-final-delivery-20261020`，final_visual_review.json绑定画面检查范围，publication.json绑定正式READY。正式包ACCEPTANCE.json绑定每条录像来源及SHA，SHA256SUMS发布后逐项回读通过。备份在receiver-backup，回退工具不属于接收运行依赖。

适用STATE-001..004、MAT-003、VAL-001..008及维护流程。本轮只完成任务特定交付与证据同步；未改核心包/schema/API或通用物理规则，故不新增通用规范。此前make check通过；本轮文档diff检查通过，未重复仿真。其他既有未提交工作保留。
