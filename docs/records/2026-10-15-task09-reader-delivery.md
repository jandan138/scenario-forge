# 称量600条：远端标准reader验收与交付

状态：完整五类本地交付已就绪。生产目录及最终独立交付目录的远端标准reader验收、归档检查和仓库检查通过，READY已生成并绑定最终MANIFEST。

工作根W：`/mnt/data/zhuzihou/GenManip-Sim/saved/repair_20261010/task09_recapture_600_20261012`。
交付入口：`W/handoff_readout_range_v1/`。本次仅收尾称量数据，不重启渲染、不操作水浴GPU、不安装到同事目录、不上传OSS。

## 来源与格式

本次直接读取OSS基准`oss://pjlab-bjpai-sim/chenjiantong/scientific_experiments_data/lerobot_dataset/task_09_solid_weighing_500/`的info、tasks和首条Parquet。
字段、Arrow类型、维度、任务映射及四路640×480 RGB AV1/15FPS与新600条一致；info仅条数、帧数、视频数、train范围变化。
HF元数据的唯一结构差异是List→Sequence；不宣称与旧文件逐字节相同或在任意datasets版本兼容。

`evidence/delivery600_integrity_20261015.json`绑定实时OSS基准哈希、全部600个Parquet和2400个视频哈希。
全1248020帧的数值与numeric源逐值相同，逐episode索引、全局索引、任务映射、15FPS时间戳、数值有限性和统计量检查通过。
视频哈希与原生产验收收据一致，复用原全量解码证据；本次不重复宣称为新完成的全量解码。
新增制作侧检查先验证索引串episode、索引缺口及错误时间轴会失败，再实现检查，4项测试通过。

## 远端环境与范围

用户指定使用SSH评测机；当前已核实入口`root@10.150.163.175:22`，主机`dsw-529861-6cb4cb97bf-vdwmr`。
Python为`/root/miniconda3/envs/lerobot/bin/python`。
该环境默认datasets是4.5.0；使用已有隔离路径`W/../lerobot_reader_deps`后实际导入3.6.0。
验证组合为LeRobot0.1.0、datasets3.6.0、PyAV16.1.0、torch2.10.0；没有修改原环境。
设置CUDA_VISIBLE_DEVICES为空并限制CPU线程，不占用水浴GPU。

生产目录标准reader检查全部600条首/中/末帧共1800个位置，与numeric源逐列相同；四路图像形状/有限性/范围和batch_size=2通过。
证据为`dataset/task_09_solid_weighing_recapture_600/reader_validation.json`和`evidence/full600_remote_reader_20261015.log`。
最终目录检查仅依赖交付数据与安装库，全600条首/中/末共1800位置、7200路图像通过，额外检查3个随机batch、跨episode batch及十背景首尾episode的40个时序边界填充，全部通过。
报告位于交付目录`evidence/portable_reader600_20261015.json`；实际pyarrow为23.0.0，标准读取示例亦在同机退出0，输出batch形状[2,12]及[2,3,480,640]。
num_workers=0；没有扩展到多进程解码、模型训练或机器人成功率。
torchvision视频接口弃用提示保留为环境WARN，不通过升级库掩盖。

## 交付及证据边界

数据独立复制到交付目录，避免视频硬链接与生产目录共享可修改字节；读取示例无需生产工具、numeric或原场景文件。
前四类运行包复核原manifest和补丁身份；其原生成功/失败资格沿用原范围，本次不新增物理资格。
数据归档为`W/delivery_archives/task09_readout_range_v1_lerobot600_20261015.zip`，5745841324字节，3016项；3008个数据文件清单见`LEROBOT_FILES.json`。
ZIP SHA-256为`d51b33ae60e7654101e6cc7f31c5ed181c9e02b7e5db76c4b9cea716df16f35b`；逐成员完整读取通过CRC并与源内容SHA一致。
前四类运行内容1143项及metric补丁身份复核通过。原任务运行ZIP保持不变，数据ZIP独立交付。
READY绑定最终MANIFEST哈希，只有迁移读取、归档完整性及仓库检查通过后才写入。
本次最终MANIFEST SHA-256为`a403ccca46f39c53a22e23ecc84606dcf9d7eb32a6099027d9c1b03e39f1222c`。
数据ZIP旁已提供.MANIFEST.json、.READY.json和.zip.sha256；清单描述五类完整交付，数据ZIP自身仅含LeRobot部分。
原队列SSH超时状态、旧CURRENT_STATUS、旧manifest和旧收尾失败状态均先保存到`evidence/pre_reader_closeout_*`，再更新当前入口；没有删除失败记录。

`make check`退出0：1255 passed、1 skipped，522.42秒；ruff、package smoke、Phase10.x和diff检查通过。
本轮文档相对链接16项通过，远端标准示例退出0；证据及制作工具身份见配套evidence.json。

这批是60条记录×10背景的状态渲染，不是600次物理成功。源采样频率未知，15FPS是导出时间轴；保留连杆反算状态、原始动作及静止底座增量假设的声明。

规范依据VAL-001/002/003/004/005/006/008及维护流程。通用规范无需变更：本次执行既有数据、迁移与证据绑定规则，没有新增核心package/schema/API或模拟器依赖。
同步本记录、称量操作说明及科学实验交接入口；历史生产失败和已封包字节保留。
