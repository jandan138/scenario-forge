# 斐林水浴 r7：玻璃试管与8 mL五层显色

从 r6 派生，目标 Isaac Sim 4.5。玻璃试管由 ConvertAsset 的 Blender 生产者制作；
名义尺寸参照常见18×150 mm商品，1 mm壁厚、20 mm最大卷口外径和密度2230 kg/m³为明确工程参数，
不是某品牌精密复刻或实物热学／强度资格。

## 资产与摆放

- 素玻璃、清透无色、轻卷口、真实开口、直筒圆底。
- 管身外径18 mm，内径16 mm，总长150 mm；底部外/内半径9/8 mm，共用z=9 mm球心。
- 一个动态根刚体，质量/质心/惯量来自实际玻璃实体积分，质量约18.0089 g。
- 玻璃用包内 OmniGlass，IOR=1.47、roughness=0.02；不是半透明塑料替代。
- 场景沿用显色任务的玻璃不投影可读性策略：新玻璃壳的 `primvars:doNotCastShadows=true`，
  避免 RTX 阴影在贴壁假液体上形成黑色条纹。只影响场景视觉，生产者玻璃材质和物理参数原样保留。
- 精确玻璃壳 SDF 碰撞，需要 r6 同类的 GPU/SDF 运行环境；没有用填满管腔的圆柱碰撞。
- 原架子的实际网格导向孔初测直径约20.46 mm，管身有约1.23 mm单边余量。
  底托、插入和拔出仍需以最终运行证据验收，不能仅由孔径推断通过。

最终三次运行确认原架 `scale=(1,1,1)` 可用：近竖直稳定落座，实际动态刚体上提脱离导向孔，
下降后重新落座。规定速度试验不是机器人抓取资格；架子没有被放大。

玻璃资产位于 `deps/chemistry_test_tube_18x150_r1/`，内有 `source/tube.blend`、
`source/geometry.json`、Blender独立重开、静态与材质依赖证据。旧依赖作为历史来源保留，
活动试管由新资产物化，根路径仍为 `/World/obj_sample_tube`。

## 样液与任务

预置样液为8 mL视觉表示。用生产者实际内腔计算液面，计入五个网格的截面离散与凹液面；
下端留0.1 mm的几何余量，径向沿用0.02 mm内缩。各层按实际液柱高度等分，约8.5 mm一层。
精确液面、实现体积与层高见 `evidence/sample_recipe.json`。
当前样液底部局部 z=1.1 mm，顶部 z≈43.78056 mm，液柱高≈42.68056 mm，
每层高≈8.53611 mm；五层网格合计约7.99999986 mL。
这8 mL不会自动添加流体碰撞或8 g质量；物理质量是生产者玻璃实体质量。

显色时间策略沿用 r6：0–3秒同蓝，中下部较早经过绿、黄、橙，上部随后追上，30秒全部趋于橙红。
累计时间仅来自样液区域接触水浴；离水暂停、重入继续。完成后取出近竖直、稳定观察3秒成功。
控制器代码沿用 r6；新内腔、样液高度、管身半径和管口高度同步更新。
`fehlings:layerMeshes` / `fehlings:layerShaders` 仍是自下而上五个目标，更新颜色、opacity、roughness。
新属性：`fehlings:container_kind=glass_test_tube_18x150`、`fehlings:sample_volume_ml=8`。

## 验证与复现

```bash
PYTHONPATH=src python -m scripts.generate_fehlings_water_bath_r7 --out <全新输出目录>
/isaac-sim/python.sh -m scripts.validate_fehlings_water_bath_r7 --root <包目录> --out <报告.json>
/isaac-sim/python.sh -m scripts.render_fehlings_water_bath --root <包目录> --report <报告.json>
PYTHONPATH=src python -m scripts.finalize_fehlings_water_bath_r7 --root <包目录> --report <报告1.json> --report <报告2.json> --report <报告3.json>
```

最终包要求三次独立冷启动、架内稳定/拔出/再插入、水浴接触及显色、观察和重置验证，
以及实际玻璃、管口、圆底、五层颜色的渲染检查。图像回放保留的实际状态；
运动学规定动作不作为机器人真实抓取成功。无真实化学、热传递、洒出或破碎模拟。
规范依据：MAT-001～006、STATE-001～006、USD-002/004、ASSET-001/002、VAL-001～006。

最终化前须由生产者 `promote_chemistry_test_tube.py` 验证同一场景的三份报告并同步资产资格元数据。
它只给出 Isaac 4.5 当前 r7 架子／水浴规定动作的范围，不给出实物耐热、机器人或PBD资格。
架子上提试验使用动态刚体与规定垂直速度；独立触水用例之间将动态烧杯恢复并沉降，
避免“只碰杯壁”等负例推移烧杯后污染下一个用例。长试管的倒置负例已提高，避免管口触底。
这些是测试过程，不是包内新增的自动复位或抓取行为。

推荐看 `evidence/initial_scene/color_progression.png`、`observed_tube_full.png`、
`outside_no_heating_mouth_detail.png` 和 `rack_reinserted_tube_full.png`。
29张最终回放图已做本地目视检查；玻璃反射、架子遮挡及中间色层边界仍有可见限制。
