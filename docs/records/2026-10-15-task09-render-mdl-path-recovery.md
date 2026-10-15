# 称量渲染第501条：MDL搜索路径恢复

状态：恢复后正在重渲，尚未将第501条计为验收完成。

称量600条队列已验收500条、1046964帧。episode_index=500/source43/scene9完整渲染退出码为0，
但启动日志有OmniPBR/OmniPBR_ClearCoat导入`::nvidia::core_definitions`失败，因此批处理日志门禁拒收并停止。
这与此前第474条Vulkan设备丢失不同，也与用户停止水浴远端无关；称量运行在本机独立GPU。

冻结render_states_frozen.py把MDL_SYSTEM_PATH设为`/isaac-sim/materials`及项目MDL目录，
本机Isaac4.5的前者不存在，实际NVIDIA标准模块位于`/isaac-sim/kit/mdl/core/mdl/nvidia/core_definitions.mdl`。
只在新启动进程设置`MDL_USER_PATH=/isaac-sim/kit/mdl/core/mdl`，补充现有SDK库的搜索路径。
没有创建SDK符号链接、修改SDK文件、修改资产或冻结渲染脚本。
冻结renderer SHA继续为`396e9ec2bda6ed14658a690d9fa96558169b195dbbdb6bb502c530f932e42d82`。

保留原失败目录和queue快照，使用`batch600.py --resume`从第501条新目录续跑；前500条哈希重新核验。
新启动已经进入帧渲染且没有原MDL错误；每条仍需完整日志、四视频解码、帧数、编码尺寸和LCD门禁。
不能将启动修复等同于第501条已通过，也不能将队列RENDERING视为训练集全部完成。

工作根：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task09_recapture_600_20261012`。
恢复身份见`evidence/batch600_mdl_resume_20261015T023709Z.json`，当前证据`evidence/mdl_path_recovery_20261015.json`。
后续若需重启该队列，应继承这项进程环境；不要修改冻结renderer来绕过其版本哈希。
最终reader的远端地址仍须在用户提供新地址后核实，不能沿用脚本中的历史SSH入口宣布数据集读取通过。

规范依据MAT-001、VAL-002/003及维护流程。通用规范无需变更：这是本机SDK路径恢复，
不推广为其他Isaac版本默认，不改变核心package/schema/API或数据格式。没有运行全仓库make check。
