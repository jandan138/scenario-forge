# 2026-08-11 cold-output OSS archive

Old, unreferenced output variants under `outputs/` were archived to unique
permanent prefixes in `pjlab-bjpai-zhuzihou-assets` and removed locally only
after count/size checks, common-MD5 `rclone check`, deterministic SHA-256
restore samples, atomic quarantine, `make check`, and a final tree SHA-256.

The pilot and five production batches removed 160,800,452,967 local bytes.
Directories referenced by active source, paper, configuration, result, or
operations material and directories younger than seven days were retained.
The canonical bimanual-pour output and current August evidence were not
removed.

Authoritative manifests, logs, remote prefixes, and restore instructions are
in `/cpfs/user/zhuzihou/ops/storage-cleanup/REPORT-2026-08-11.md` and its
`runs/` directory. Every batch passed the full 609-test `make check` path,
ruff, package/USD/suite smoke checks, and stable Git-status comparison.
