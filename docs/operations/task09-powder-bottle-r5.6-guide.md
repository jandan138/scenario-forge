# Task09 粉末瓶 r5.6：120 Hz 勺碗摩擦（Isaac Sim 4.5）

在 r5.5 上只给勺碗新建 `BowlContact`。物理步频仍锁 120 Hz。当前合格包仍是 [r4 指南](task09-powder-bottle-r4-guide.md)。

## 和 r5.5 的预定差异

| 项 | r5.5 | r5.6 |
|---|---|---|
| 物理步频 | 120 Hz | 120 Hz |
| 勺碗接触材质 | 与粉粒共用 Contact 0.65/0.5 | **BowlContact 0.9/0.7，只绑碗** |

## 已观察到的结果

- 冷启动 8 s：**通过**。10240 粒；床深约 **11.68 mm**，距口约 **4.32 mm**。
- 规定舀取 50 s：**通过**。舟内 **221** 粒，LCD **0.48 g**；高峰 1102；内托下 0。与 r5.5 相同，仍低于 r4（253 / 0.55 g）。

## 复跑

```bash
python scripts/clone_task09_powder_r5_6.py \
  --source outputs/task09_powder_bottle_r5_5_20260915/prep_s1 \
  --out outputs/task09_powder_bottle_r5_6_YYYYMMDD/candidate
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_6_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_6_YYYYMMDD/settle --mode settle --seconds 8
/isaac-sim/python.sh scripts/validate_task09_powder.py \
  --root outputs/task09_powder_bottle_r5_6_YYYYMMDD/candidate \
  --out outputs/task09_powder_bottle_r5_6_YYYYMMDD/scoop --mode scoop --seconds 50
```
