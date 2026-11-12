# 非水浴第二轮交付：validation兼容适配

状态：独立分支和静态适配完成，GPU初始化验收执行中，尚未READY或安装建通目录。

接收方本地 `feature/scientific_experiments` 为 `d64a80ae4f2fefe96b06df1f66916228659a1e78`，新增validation配置218文件，工作区保持干净。远端查询缺少可用用户名认证，未确认远端最新；共同集成和push须后续重新确认，并等待另一位同事分支就绪。

我方分支 `delivery/zhuzihou-scientific-round2-validation-20261029`，独立worktree `/mnt/data/zhuzihou/GenManip-Sim-deliveries/round2-validation-20261029`。代码提交 `a523e0a2ecbd73f421cb96732aee60bb387f8a50`，作者 `zhuzihou <zhuzihou@pjlab.org.cn>`；只改task11两个metric文件。Black钩子格式化后AST与已验证版本一致。CPU检查通过84组几何配置及坐标/BVH/缓存/适配/旧条件构造检查。

交付范围为task06/11/13/14/19，排除水浴、银镜、task07参考方案和LeRobot。saved私有副本共221处覆盖：101USD（五任务各20入口及蓝瓶共享层1份）、120份初始化（原100份及新增validation20份）。validation共36入口，YAML保持；task11新增8份评分和烧杯迭代恢复适配，蓝瓶新增8份真染液，task19新增4份舟迭代恢复适配。

validation数据包含新布局、指令及来源，不按同名test整份覆盖。蓝瓶从definition_source对应的原染液，经粒子坐标到世界、来源烧杯局部坐标，再转到validation烧杯和粒子坐标；原粒子0/1和布局保持。prepare.py按允许字段剥离后深比较，静态复核36配置、来源、指令及布局，20种被validation引用的场景组合可打开。

运行验收在 `10.150.168.71` GPU0，36项各推进20步。输入为按实际Lift2 DOF映射生成的初始化姿态保持，不是成功示范，也不改原动作。首个蓝瓶mixed_1入口通过：1476颗染液、粒子与原生烧杯位置对齐，四视角解码通过，俯视已人工查看。后续自动续接其余入口，再跑task11原正常和误判轨迹。最终仍须逐项核对运行和画面后才能封包。

测试工具首轮假定固定benchmark目录，导致已结束运行的结果未被找到；修正为按测试配置前缀解析，原回执和原生结果保留，通过派生映射复用，没有修改任务资产或重跑。粒子审计的原生位姿改从同次pose记录读取；geometry记录不含该字段。以上均为外部工具修正，不属于接收方运行依赖。

实时状态和全部证据：`/cpfs/user/zhuzihou/dev/scientific-round2-delivery-validation-20261029/HANDOFF_CURRENT.md`、`smoke_status.json`、`regression_status.json`。`nonbath_validation_candidate_20261029.tar.gz` 明确为运行待验候选，不可冒充最终交付。建通原saved未修改；源码共同集成采用每方一条squash提交，saved按双方合并后的清单串行安装并备份，最后统一push，不强推。

依据VAL-002/003/008。规范无需变更：本次将既有任务修复按新增split布局适配，未形成通用液体/offset默认，也未改变核心包、schema或API契约；初始化检查不替代完整任务成功资格。

## 后续进展：远端认证及正式兼容验收准备

用户再次提供认证后，通过临时getpass/askpass完成远端ls-remote及fetch，远端分支确认为d64a80ae，与本地准备基线一致。令牌未写入仓库或运行日志；REMOTE_VERIFICATION.json保留不含凭据的结果。前文认证缺失是初始状态，现已解除。

只读核对36份实际LMDB动作：28份长记录、8份短片段，动作维度分别为N×12手臂、N×4夹爪、N×3底座，有限且等长；全部底座末帧增量为零。原采样时钟字段缺失，不声明原时长复现或静默重采样。用户确认正式验收为资产兼容：长记录原配置上限回放；短记录按实际33/60–78帧验证，不补成完整示范，不改原validation配置及动作。

用户已授权私有验收后安装实际建通目录：创建evaluation/zhuzihou-round2-validation-20261029评测分支，逐文件备份和原子覆盖221份saved；保留feature/scientific_experiments引用，随后实际目录回放28长＋8短。install_receiver.py默认dry-run，已核对清单和当前基线；实际安装必须在私有36项、两条评分回归和画面复核完成后执行。正式评测配置、队列和配套回滚记录已准备，尚未启动安装。最终与同事分支共同集成及push仍待其就绪。

## 安装前验收结束及实际接收安装

36项20步初始化检查全部通过，初始俯视画面已逐项复核。task11原正常案例2704步1/SR1，原误判案例5000步0.8/SR0；末态烧杯在托盘、锥形瓶在盘外，托盘阶段[1.6,0.0]与画面一致。保留原有初始化报错：非根关节链接速度写入及offset顺序赋值；四类报错也存在于冻结原版回执，最终原生参数读回通过，不宣称引擎无错误日志。

重新认证确认远端仍为d64a80ae，并确认两台已知远端无占用实际建通目录的Isaac进程后，按既有授权执行安装。建通工作目录当前为evaluation/zhuzihou-round2-validation-20261029，HEAD a523e0a2；feature/scientific_experiments引用仍保持d64a80ae，没有push。221份saved逐文件备份后安装，连同2个代码文件共223份哈希核验一致。备份：`/cpfs/user/zhuzihou/dev/scientific-round2-delivery-validation-20261029/receiver_backups/20261029T074744Z`。

实际接收目录的正式兼容回放已启动：10.150.168.71 GPU0，端口8395，28长记录使用原validation配置和上限，8短片段只使用临时配置运行已有动作数。不会提交临时配置；原动作保持。实时formal_status.json、queue_formal.log和安装证明在上述证据目录。正式兼容结论尚待36项完整运行、画面和评分复核；不以全部满分作为通过条件。

## 2026-10-30最终R2收尾

新增validation确实暴露了task11的192/16物理回归。原版与保留新评分的16/1均1分，192两次2303步关节异常。已在实际接收目录恢复原物理并保留新评分，8项补验6满分、2项0.8，无关节异常；穿模残留保留。五任务约定范围的兼容验收和R2归档完成，详见[最终记录](2026-10-30-nonbath-validation-r2-closeout.md)。本记录前面的192候选/待验状态属于历史阶段，不再作为当前安装建议。未共同合入或push。
