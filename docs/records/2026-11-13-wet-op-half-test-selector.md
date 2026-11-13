# WET-OP half-test selector delivery — 2026-11-13

Added and committed (`7c331a9748c78aa529c450b0ad243d649e54f00a` on `migration/wet-op-private-20261107`) two additive evaluation selector JSON files in `/cpfs/shared/wet_op_bench/GenManip-Sim` on `genmanip-2gpu` (`10.150.170.198`) to provide a 340-episode half-size test suite (`50%` of the 680-episode `scientific_experiments/test` set) and its 280-episode seen-task companion selector. `/mnt/data/chenjiantong/GenManip-Sim` and existing selectors (including `configs/tasks/scientific_experiments/test/zero_shot/half/half.json`, which retains `mixed_1..10`) were left untouched.

## Added files

| Selector ID (`config_or_benchmark_id`) | Relative path under `/cpfs/shared/wet_op_bench/GenManip-Sim` | Episodes | SHA-256 |
| --- | --- | --- | --- |
| `scientific_experiments/test/half` | `configs/tasks/scientific_experiments/test/half/half.json` | 340 | `0d8c368d701dc87a3d703bea5512c2539f18fb7b3c65a22114e59e1fcf01a8ff` |
| `scientific_experiments/test/demonstrations_based/half` | `configs/tasks/scientific_experiments/test/demonstrations_based/half/half.json` | 280 | `a47130b0495d863c6d697a3a8487630c94f8700c4df6c47a9cb11a1d7ac6fa9a` |

## Selection design

- **14 seen tasks (`task_01`–`task_14`)**: all 4 splits (`mixed`, `unseen_background`, `unseen_instruction`, `unseen_prospect`), even indices `{2, 4, 6, 8, 10}` (`14 × 4 × 5 = 280` episodes). Preserves counterfactual index pairing across splits, all 3 seen rooms (`2 + 2 + 1` per split), and all 3 unseen rooms (`1 + 2 + 2` per unseen-room split).
- **6 zero-shot tasks (`task_z1`–`task_z6`)**: `mixed_11 .. mixed_20` (`6 × 10 = 60` episodes). Covers one complete 10-scene unseen-room cycle (`2 + 4 + 4` across the 3 unseen rooms) with zero source-episode overlap against `validation` (`mixed_1..4`).
- **Flat `.yml` listing in `test/half/half.json`**: `parse_configs_and_benchmark_id` expands nested JSONs with a FIFO `Queue`, so mixing a nested `.json` with direct `.yml` entries would place zero-shot episodes ahead of seen episodes. Listing all 340 `.yml` entries directly preserves canonical `task_01..task_14` followed by `task_z1..task_z6` order.

## Verification and standards synchronization

- Verified with `/root/miniconda3/envs/client/bin/python` via `genmanip.core.evaluator.utils.parse_configs_and_benchmark_id`:
  - `scientific_experiments/test/half` resolves to `340` unique episodes with `benchmark_id == "scientific_experiments"`.
  - `scientific_experiments/test/demonstrations_based/half` resolves to `280` unique episodes matching `half[:280]`.
  - All 340 referenced `.yml` configs, `saved/tasks/<task_name>/000/meta_info.pkl` files, and `saved/assets/<usd_name>` USD layers exist on `/cpfs/shared/wet_op_bench/GenManip-Sim`.
- Ran `python -m unittest discover -s tests/unit -v` in `/cpfs/shared/wet_op_bench/GenManip-Sim`: all 41 unit tests pass, including `ValidationBackgroundV2Test.test_existing_selectors_do_not_include_holdout`.
- VAL-002, VAL-003, and VAL-006 boundaries were respected: existing tasks, assets, metadata, simulator runtime code, and historical selectors were not modified. Because this change only adds selector index lists over already-delivered episodes without changing USD, physics, asset, or package contracts, `docs/standards/` requires no rule changes.
