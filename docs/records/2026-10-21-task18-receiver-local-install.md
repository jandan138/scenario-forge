# Task18 银镜本地提交与离线安装

状态：已本地提交并安装，接收冷启动通过；已知问题未全部关闭，未push、未更新LeRobot、无全部验收完成READY。

## 代码与安装范围

建通目录 `/mnt/data/chenjiantong/GenManip-Sim` 保持 `feature/scientific_experiments`。新提交 `f6ec55aece2f95f71fd8cd4d7506f9fae7dec515` 的父提交为 `a7084a999cda7889a575eebf27a0553531ec85b5`，保留Task04修复；原集成分支仍指向a7084a99。Author与Committer均为 `zhuzihou <zhuzihou@pjlab.org.cn>`。

代码仅新增指定 `task_z4_silver_mirror_reaction.py` 的31行metric修改，内容与阶段包dd219a7a提交一致。原Task09/10/12代码不重复提交，不带制作端渲染或核心源码修改。共享仓库默认Git身份未改，由本次操作显式指定朱子厚身份。

从阶段包安装三棵银镜任务目录：configs下22个文件、saved/assets/scene_usds下529个文件、saved/tasks下80个文件。按完整任务目录替换，不覆盖整个saved、其他任务或公共机器人/miscs。632个运行文件（含metric）全部匹配阶段包MANIFEST。

## 备份与保护

操作根 `/cpfs/user/zhuzihou/dev/task18-receiver-install-20261021` 保存原内容、Git bundle、工作区patch、提交映射和逐目录安装日志。backup保留原目录结构与20个相对符号链接，previous_live_trees保留激活前目录。其他1578个已交付运行文件哈希及146条非Task18工作区状态记录保持不变。

首次备份将相对符号链接展开，新增文件导致数量比较失败，安装前停止；保留该副本后改为保留链接结构重新验证。期间外部操作已将Task04快进合入原分支并切回feature，故重新读取状态，以a7084a99为直接基线，仅快进加入银镜，不重复合并或覆盖同事变更。

回退仅针对银镜三棵目录及单个metric：先备份安装后新增内容，再恢复原任务目录，使用新revert提交撤销银镜metric，保留原分支、Task04和其他工作区修改。不能用reset --hard或切旧delivery分支代替定向回退。

## 接收验证

实际metric方法12个正反例检查通过。已安装目录执行 `silver_installed_f6ec55ae_init_m17_20261021T095922_893444Z`：原生1步初始化完成，客户端退出0、无未分类引擎错误，四路视频完整解码；实施者查看四张初态图，主要资产、透明容器与机器人显示正常。近景上端有裁切，不能以此宣称完整任务成功。

一次启动辅助脚本因引号问题在Python解析阶段失败，未进入仿真；保留失败日志后使用独立校验入口启动。本次没有重跑之前14条完整回放，也没有调物理参数。启动后再次核对632个安装文件及1578个受保护文件哈希通过。

安装与回退入口：`/mnt/data/zhuzihou/GenManip-Sim/saved/deliveries/scientific_experiments/task18_silver_mirror_install_20261021/README.md`。阶段评估包保持原字节，安装回执另存，不改旧SHA256SUMS。

飞书只更新Task18状态段为“已本地提交并安装，问题未全部关闭”，8项问题限制继续保留；同步结果见安装记录目录的FEISHU_SYNC.json，不发送IM或邮件。

适用MAT-001/004、STATE-001..004、VAL-001..008。规范无需变更：本次为既有任务文件的接收安装，不建立新通用物理结论或公共API。外部安装与冷启动检查、12项metric方法测试、文档diff检查完成，不重复当日已通过的1255项仓库核心检查。
