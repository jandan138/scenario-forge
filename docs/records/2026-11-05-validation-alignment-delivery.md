# Validation 对齐：实际安装与远端交付完成

状态：INSTALLED_SMOKE_PASSED_PUSH_VERIFIED。

建通 `/mnt/data/chenjiantong/GenManip-Sim` 的 `feature/scientific_experiments` 已合入并正常push，远端回读确认为 `8bb1df4355a0bf1afeba506304e1c7a23425eacb`。28份初始化数据已逐文件备份并安装，配置/测试/数据及新增日志修复共52个文件有交付清单。既有task07未提交修改的哈希保持，未混入提交。

认证后发现远端已从40ebb020推进至28216d22（请求日志追踪）。将原478874d1候选重新应用为9dcc6b3f。实际原生reset暴露ContextVar无法序列化及Ray展开装饰器后丢失_request_trace参数两个问题；初次安装已回滚保留现场，随后分别添加失败回归测试，以25dcc059和8bb1df43修复。未移除远端追踪功能，也未强推。

## 验证边界

- 资产/配置候选：28例最终选择回放、112路视频完整解码、命令与原动作/末目标保持一致，关键帧由实现者复核。
- 整合后的实际安装：38项unit、8项server测试通过；称量、滴定、水浴、银镜的四项原生reset均通过。此层不冒称重新执行了全28例。
- 银镜短片段90/62/62/64条不能证明完整任务成功；水浴低分及布局/操作限制、原CUDA700失败均保留。冷重跑成功不构成故障根因证明。

## 交付入口

根目录：`/cpfs/user/zhuzihou/dev/validation-alignment-20261104/`。

- `FINAL_DELIVERY.json`：当前提交、归档和SHA256。
- `FINAL_REPORT.json`：最终已安装状态、两层验证及已知限制。
- `INSTALLATION.json`：28份saved备份位置及task07保护哈希。
- `validation-alignment-final-r3.tar.gz`、`release-final-r3/manifest.json`和`SHA256SUMS`：依赖建通已有USD资产基线的增量包。

既有ACTIVE_DELIVERY入口已同步到本次交付。所有GPU作业已结束，临时Git认证文件已删除，凭据未加入仓库、URL或交付归档。

适用VAL-001/002/003/004/005/008及STATE-001/003。规范无需变更：未形成新的通用物理规则或Scenario Forge核心包/schema/API；新增测试只覆盖本次外部运行时追踪整合故障。相关操作说明与历史记录已同步。
