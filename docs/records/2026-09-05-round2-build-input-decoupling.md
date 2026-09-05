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
inventory/batch records and will publish its own result index.
