# Round 2: background archival and build input decoupling

Two historical background batches were not referenced by current head runtime
USD/MDL/config files. Their immutable OSS archive completed with
35,917,409,949 bytes removed locally. Historical runbook mentions are retained as
provenance and restore instructions rather than reasons to retain large outputs.

Current Task02 generation, oven/stirrer layout assembly, and environment/robot
adapter consumers now use the bindings described in
[Workbench build inputs](../operations/workbench-build-inputs.md).
Six positive-list input closures occupy 489,614,946 bytes; they retain only
required input subtrees rather than complete historical multi-task deliveries.

Rebuild comparisons passed for all four Task02 fills in both VR and eBench,
for the oven (9048 prims), and for the stirrer (3037 prims). The eight Task02
comparisons include particle values and collision/material attributes. Asset
references compare resolved content hashes. During reconstruction a previously
uncaptured delivery correction was recovered: flattened VR roots must retain
the nine mesh collision APIs and keep both old unified proxies disabled.
Regression tests cover those effective opinions, not merely overlay text.

Isaac Sim 4.1 opened all six rebuilt VR scenes, advanced their timelines and
restored initial root poses after stop/close/reopen. This short smoke is not a
liquid-retention, robotic-interaction or task-success qualification. Existing
proxy-normal and transform-precision warnings are not suppressed or claimed fixed.
No existing delivered package was changed.

Detailed comparisons and runtime reports are under
`/cpfs/user/zhuzihou/ops/storage-cleanup/reports/round2/`.
The original Step 1 archive index is immutable; this round has separate
inventory/batch records and its own
[result index](../../external_artifacts/archive-index-round2-20260905.json).

## Completed execution

| Item | Bytes |
| --- | ---: |
| Two historical background directories archived and removed | 35,917,409,949 |
| Eight historical task directories archived and removed | 11,461,976,124 |
| Independent build inputs retained and backed up | 489,614,946 |
| Round-two net reclaimed | 46,889,771,127 |

Including round one, net reclaimed space is 66,014,628,006 bytes (66.01 GB).
Current delivered USD and ZIP files remain at their existing paths.
The archived task groups are r9, Task02 r10/r10.2/the earlier r10.3 fixture
layout, Task09 r15, and stirrer r2/r3/r4. Their active consumers use the new
inputs; historical release-only entrypoints require restoration when needed.

With those eight old directories quarantined, `make check` completed:
916 passed / 1 skipped, Ruff passed, package smoke passed, Phase 10.x passed.
This included a real fill20 reconstruction using the new input contract. The
skip is the existing historical Labspin bundle test whose r9 package input is
now archived; current Task11 construction remains covered by its current tests.

Both archive batches passed count/byte/hash checks and restore sampling before
local removal. Input closures were independently uploaded and checked under
`archives/scenario-forge/build-inputs-v1/<input-name>/<tree-sha256>/files/`.
The result index includes their exact URIs. Verification scratch outputs and
the unused first stirrer-input draft were removed and are not counted as
original space reclaimed.

Human-readable result:
`/cpfs/user/zhuzihou/ops/storage-cleanup/reports/round2/result.md`.
Recovery metadata and reconstruction evidence are also backed up at:

```text
aliyun-beijing-internal:pjlab-bjpai-zhuzihou-assets/archives/scenario-forge/artifact-history-v1/_manifests/retention-round2-final-20260905
```
