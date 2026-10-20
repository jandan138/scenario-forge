# Task12正式交付准备与接受范围变更

状态：STAGED_NOT_READY。隔离候选和离线包已完成，专项坏例/演示正在接收基线副本回放；尚未修改建通正式目录，未更新飞书交付状态，未生成READY。

## 用户确认的范围

用户与同事接受更换USD导致旧动作成功率下降，接受原参考版11/38，不再要求新版最多比旧版少成功7次。此前相对验收阈值及更早19组全成功要求保留为历史，不再阻塞本次交付。该接受不等于穿模、引擎错误、异常加热等专项问题已修复。

最终交付采用含显色提前0.75秒的版本；保留真实液体交互，不带浴液关闭、额外接触过滤、扩孔、居中或诊断观察器。原参考版38次中的11次满分和该候选5条0.85/0.85/1/1/0.15分别报告，不将前者写为最终版实测成功率。成功演示接受已有历史评测记录动作，本轮不宣称原始teleop示范通过。LeRobot、训练及OSS数据集不更新。

用户选择补文档坏例专项复核再交、包含建通正式目录安装验收，并在完成后同步飞书第4节Task12状态和入口；不发送群聊/私信。未解决专项异常须报告并暂停正式安装，不盲目提高旧动作成功率。

依据飞书CLI本轮读取revision6827，文档要求三个离线目录覆盖与metric代码提交。成功演示来源与本轮不做LeRobot均为明确的任务约定，需在交付说明中披露。

## 隔离候选与包

制作根`/cpfs/user/zhuzihou/dev/task12-final-delivery-20261020`，候选在candidate，暂存包在release。接收仓库当前分支delivery/task09-standard-v3-final，基线82cabca55427cb199565584f20746e6862f2394d，已有40个Task09 YAML工作区覆盖；原样保留。

候选从接收基线独立clone，分支delivery/task12-real-liquid-r1，metric提交9490df9a3710bbcea97cd2470adc364a13883914，仅修改task_12_fehling_test.py的31行新增。共享repair_checks.py与候选源相同，未覆盖。接收仓库已有的set_robot_joint_max_force loader接口保留，本任务未添加调用或修改其实现。

候选初次commit因新clone没有作者配置失败，随后仅在候选仓库沿用Scenario Forge配置并完成提交，无全局或接收仓库配置改动。

从completion_advance075复制四类内容后，发现早期repair_training_001及_derived_actions混在候选中；它们不在正式40-case JSON入口里，已移出候选并保留到excluded_private，来源和哈希在evidence/excluded_private.json。未改制作源，也未动接收任务文件。最终705个离线文件。

静态检查20场景、40正式case通过，所有任务专用依赖在任务目录内，无未解析/越界引用；两套粒子系统启用，timing_version3和0.75字段正确，过滤关系逐场景与冻结生产源一致。不能把mixed5的25个过滤目标当所有场景的固定数量，初版该假设被静态检查拒绝后改为逐场景源对照。

直接提取候选USD函数与metric运行7项规则测试：有效加热；无效入水/液体/倾斜/失去承托/越界拒绝；碰壁不单独停热；暂停/重置；0.75映射；连续单调显色；正确落座及横倒/浅插/偏孔反例。测试通过，但不代替全部运行时守卫或保液资格。

release/task12_offline.zip大小764342225字节，705文件逐文件SHA与ZIP CRC检查通过；code下增量bundle/mbox绑定82cabca5到9490df9a，bundle verify通过。MANIFEST标记STAGED_NOT_READY；README说明两批成绩、原生回放协议、公共资产前提及所有未完成项。

## 安装前运行与恢复

文档5条坏例：pi05_all14_100000_20260924的unseen_background_3/4/8、unseen_instruction_5；gpt6_all14_mixed_20260926的mixed_5。四条pi05记录均有7000个有限16维动作，底座严格零；原对应episode日志有chunk结束executed10/step_count7000及subframe记录，与已校准chunk30协议一致。原日志和输入SHA绑定在badcase_protocol_admission.json；不宣称逐位恢复历史物理状态。

在10.150.164.127四卡机运行接收基线隔离候选，安排7条完整回放：上述5坏例及来源11、15成功演示。低分与执行/物理异常分开记录。使用原生120Hz、7000上限，按来源保持原动作、分块及底座模式。

四条同时启动时，GPU0/3的Ray runtime_env_agent在30000ms内未就绪，driver在服务ready前退出，未执行动作。保留原队列及日志，不计任务零分。改为错峰、相同输入和新ID重试一次；GPU0 retry ready后才启动GPU3 retry，现四条均已看到持续step_chunk请求。

权威队列在远端`/tmp/task12_four4090_20261019/receiver_task12_gpu{0_retry1,1,2,3_retry1}/queue.json`。共享镜像在个人repair的对应four4090目录。初始retry监督PID为GPU0:3463571、GPU3:3468914；原GPU1/2为3451041/3451042。具体运行以进程和实时队列为准。启动恢复安排在evidence/startup_retry_plan.json。

## 尚未完成

7条完整回放收尾、文档专项异常画面复核、代表保液检查；之后才备份/安装正式Task12目录。正式接收端仍需40独立初始化、来源11/15及mixed5回放、未涉及文件哈希与进程清理、正式README/MANIFEST/READY，再更新飞书。已准备原生CLI num_steps=1的初始化辅助入口，尚未执行正式接收验收。

规范依据STATE-001..004、MAT-003、VAL-001..006/008及维护流程。仅更新任务交付记录/操作入口，制作工具位于仓库外；无Scenario Forge核心API/schema变化。用户接受标准为任务特定，通用规范无需修改。没有为通过而改原动作或原始分数，也没有将准备完成写成安装完成。
