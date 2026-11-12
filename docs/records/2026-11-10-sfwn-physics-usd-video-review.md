# sfwn 视频审核：物理异常与 USD／资产错误

日期：2026-11-10。范围仅限已有评测记录的视觉审核及候选状态记录复核；普通操作失败、正常碰倒、洒出、停滞及策略得分均不作为问题。

## 首版交付（回放前）

[回放前自包含 HTML](/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/sfwn-20261110/history/before-replay-20261110/sfwn_physics_usd_review_selfcontained.html)

- 大小：10,731,187 bytes（约 10.7 MB）。
- SHA-256：`f209fdcecaf3d8167a17a288d65bd745e77c1385c4be5ee6741dfad56f98ce22`。
- 内嵌 19 段视频、24 张图片，无外部媒体或网络依赖。
- 唯一交付入口位于上述个人审核目录的 `download/`；未在 `/mnt/data` 根目录创建副本或快捷方式。

审核根目录为 `/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/sfwn-20261110/`。原始数据来自 `/mnt/data/chenjiantong/GenManip-Sim/saved/eval_results/scientific_experiments/sfwn1108*`，未改写源视频、USD、任务数据或成绩。

## 覆盖及审核方法

冻结 397 个 run、20 个任务：374 条完整四视角视频和结果 JSON，23 条缺少最终视频／结果但有中间图片的记录。完整主视频合计约 13.82 小时。主视频全程 1 fps 时间线加末帧，以及不完整记录现存主视角图片，形成 2,540 页，均已实际目视查看。候选补看原分辨率、密集帧及辅助机位。生成页面不算已审核。

| 审核记录 | 条数 | 实际查看页数 |
| --- | ---: | ---: |
| `reviewer/primary.json` | 26 | 192 |
| `reviewer/agent_a.json` | 144 | 718 |
| `reviewer/agent_a_z5.json` | 13 | 90 |
| `reviewer/agent_b.json` | 114 | 752 |
| `reviewer/agent_c.json` | 100 | 788 |
| 合计 | 397 | 2,540 |

独立视觉审核依据 `render-visual-reviewer` 技能；审核者不查看实现代码。主审核者另检查候选元数据，不以数值阈值自动生成视觉结论。T14 指定案例及 Z6 指部间隙另有独立复核记录。覆盖检查对比每个 run 的期望页面集合和实际查看集合，并拒绝重复及缺失记录。

这不是全部原生帧或全部辅助机位的逐帧审核。不完整图片记录仅说明留存范围，不能证明 episode 后续正常。视频秒数不是仿真秒数。

## 结论及边界

确认 **2 类异常，涉及 9 条记录**；没有建立任何一项 USD 资产根因结论。

1. **机器人仿真状态发散／突跳，8 条。** T10 `mixed_7`、`unseen_instruction_1`；T11 `unseen_background_3`；Z1 `mixed_5`、`mixed_16`；Z6 `mixed_1`、`mixed_5`、`mixed_6`。末段姿态／场景突变与记录中的极大关节值、突跳对应；T10 `mixed_7` 和 Z6 `mixed_1` 还出现 NaN。确认的是记录中的状态异常，不是控制、求解器、读取或 USD 中的具体因果责任。合并展示不代表同一根因。
2. **夹爪局部瞬时分离外观，1 条。** Z6 `mixed_17`，f3900（130.000 秒）指部与连接杆存在清晰背景间隙，f3904再次可见孤立部件，之后恢复邻接外观。密集帧及独立复核支持可见异常；未证明实际关节断裂，也未区分约束与渲染／变换同步原因。

待确认附录分三组，不计入上述确认数：

- 用户指定 T14 `mixed_10`：约 52.7–54 秒勺快速弹离和颗粒散出。多视角显示接触／松夹先发生，尚不足以排除正常释放冲量和颗粒碰洒。附主视角、右手近景、天平读数机位。
- T09 `unseen_instruction_2`：约 33.8–34.4 秒天平在接触后快速移出。固定近景排除了纯相机运动，但强烈响应是否不合理仍未确证。
- 6 条末段姿态／视野突变：T10 `mixed_4`，Z1 `mixed_14`、`mixed_20`，Z4 `mixed_13`，Z6 `mixed_8`、`mixed_14`。不将出画、倾倒、变暗或提前结束直接当成物理错误。

T02 托盘倾斜候选经多机位复核未能证明无支撑悬浮，已撤销。T14 其他颗粒／勺接触候选未建立异常证据，处置见 `CANDIDATE_DISPOSITIONS.json`。未继承上一轮已撤销的液体疑点，也未将普通操作失败混入。

## 验证与追溯

证据根目录包含 `inventory.json`、`issues.json`、`COVERAGE_VALIDATION.json`、`SOURCE_VERIFICATION.json`、`FINAL_SOURCE_STATUS.json`、`PAYLOAD_VALIDATION.json`、`DELIVERY.json`。`evidence/ALL_STATE_SCAN.json` 保存状态筛查及源哈希；其阈值仅供候选辅助，不代表缺陷自动判定。选定终端记录另保存处理后的动作范围，不能冒充原始模型输出。

验证通过：

- 27,814 个登记源文件哈希复核无变化，最终 size/mtime 复查无变化；374 条主视频读取帧数与声明帧数一致。
- 内嵌媒体逐字节匹配派生证据文件，397 条原始结果／空记录匹配冻结清单。
- 空审核记录故障注入使覆盖门禁正确失败。
- 单独复制 HTML 至隔离目录、禁用网络，19 段视频均完成解码、播放和跳转；24 张图片解码成功。搜索、空结果、恢复和记录展开通过。
- Chromium 在 1440×1000、768×1024、390×844 三种尺寸下无横向溢出、外部请求或脚本异常。15 张最终截图均实际查看，未见阻断缺陷。浏览器进程、隔离 HTML 和自有临时目录已清理。

从审核根目录重建／验证：

```sh
python tools/build_report.py
python tools/verify_payload.py
python tools/audit_html.py
```

重建会将交付状态恢复为待浏览器验收；验收与截图记录必须绑定最终 HTML hash，不沿用旧 hash 的通过结果。

## 规范与仓库范围

遵循 [验证与交付](../standards/validation-and-delivery.md) 的 VAL-001/002/003/004/005/007 和[维护流程](../standards/maintenance.md)。规范无需变更：本轮未修改场景、物理参数、任务状态或包/API 契约，也未形成新的通用物理准则。历史任务包保持不变。

仓库只新增本日期记录，大型证据和工具留在外部个人目录，未引入核心 episode runner、模型适配器或 benchmark reporting。文档做引用及空白检查；未声称重跑与该记录无关的核心 `make check`。


## 同日补充：记录动作回放检查

[第二版自包含HTML（已归档）](/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/sfwn-20261110/history/before-t11-diagnosis-20261111/sfwn_physics_usd_review_selfcontained.html) 已追加独立“回放检查”部分；完整方法和边界见 [诊断记录](2026-11-10-sfwn-action-replay.md)。最新文件11,502,550bytes，SHA-256为 `0f69d22a4ace095bf6a8abc86ce4d8dc0f4856ec64acdaeba7ce9bfe81781a5f`，内嵌20段视频、27张图片。原43项媒体与397条原始记录逐字节保留；首版HTML、工具和浏览器证据已归档至 `history/before-replay-20261110/`，上文首版哈希仍只绑定该历史版本。

完成T11 unseen_background_3及Z6 mixed_5的4种候选协议，共8次独立进程校准。3次触发状态异常、4次轨迹校准失败、1次初始化不一致。T11的两次绝对底座回放均在第3227步出现同类发散（原记录第3980步），状态序列逐值一致；Z6一次在970步突跳（原记录1644步），尾段形态不同。未取得两例均通过的候选，按门禁未启动原定24次正式回放，不能记为0/3。此次证据不支持“都无法复现”，也未确认USD根因；没有改动原2类／9条历史异常计数。

32路新原生视频完整解码、逐命令相等核对、22页四视角抽帧复核通过。最新HTML完成隔离离线播放／跳转、图片解码、搜索和展开检查；三种尺寸无横向页面溢出、外部请求或脚本异常。新增及受影响的9张浏览器截图已实际查看。当前 `DELIVERY.json`、`PAYLOAD_VALIDATION.json` 和 `audit/browser.json` 均绑定最新文件哈希。所有自有仿真进程退出，GPU恢复空闲。


## 2026-11-11：烘箱定向诊断交付

[T11诊断与私有修正验证](2026-11-11-t11-contact-instability.md) 已补充完整证据链。最新[自包含HTML](/mnt/data/zhuzihou/GenManip-Sim/saved/reviews/scientific_experiments/sfwn-20261110/download/sfwn_physics_usd_review_selfcontained.html) 为13,648,345bytes，SHA-256 `b01d69b1e0da21321b20a16ae0f014f008f8e947764bed7c775665f870287f62`，含22段视频、33张图片及可下载私有配置。当前重建T11中的接触数值失稳已通过子步修正、重复、恢复及相关回归验证；未发布到源库，不推广为其他7例同因或通用USD错误。原始审核内容及历史版本均保留。
