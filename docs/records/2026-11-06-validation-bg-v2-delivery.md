# validation_bg_v2 delivery checkpoint — 2026-11-06

The new batch contains 136 cases across 20 tasks and five newly authored rooms. It preserves the original validation selectors and metric implementations. Source generation and category semantics are recorded in [the generation record](2026-11-05-validation-bg-v2-generation.md).

## Verified scope

- All 136 final native receipts match the delivered configuration, metadata and scene hashes.
- All 1,088 four-camera initial/after-hold JPEGs decode. The implementing assistant reviewed all 34 contact sheets; no blocking new visual defect was identified at that resolution. This is not an independent review.
- Runtime evidence covers reset and bounded holds on Isaac Sim 4.1: normally 20 steps, 320 for selected chemistry tasks. It establishes neither task completion nor successful robot policies. There are no demonstration LMDBs.
- Five ConvertAsset r5 room packages supply visual backgrounds. Fixed cameras mainly see floors and parts of cabinets; transparency, glare and wrist-camera framing limit visual interpretation.
- Some temporary startup logs from the unavailable four-GPU host could not be recovered. The retained receipts, images and shared worker logs do not justify a claim that every original startup log was reviewed.
- Candidate code integrates pioneer `97179149` through merge `9369e3fd`. Its 40 unit tests and 25 server tests pass. The prior 136-case evidence is separate from the representative smoke checks of the new request-retry server code.

## Artifacts and installation

Evidence root: `/cpfs/user/zhuzihou/dev/scenario-forge/external_artifacts/validation_bg_v2_20261105`.

The canonical delta directory is `release/validation_bg_v2_delta`; the adjacent ZIP has passed CRC validation and has a SHA-256 sidecar. Its manifest lists 347 new files (five background packages, 136 scene layers and 136 metadata files) and 695 runtime/configuration dependencies. It explicitly requires the existing baseline assets and the separately versioned Git configurations. Development symlinks and superseded room revisions are excluded.

All 347 files were installed additively into `/mnt/data/chenjiantong/GenManip-Sim` after checking the existing asset dependency hashes. No existing file was overwritten. `receiver_install_receipt.json` records created paths and hashes. Rollback is limited to those paths whose contents still match the receipt.

Code activation remains dependent on a PR merged into `feature/pioneer`. Git authentication succeeds; the enterprise PR API authentication/route is still being resolved. The old local branch has not been removed or rewritten. Asset installation does not mean that pioneer contains the new selector.

## Standards synchronization

Applicable rules: ASSET-001–005 and VAL-001–006. Normative rules need no change: this delivery applies existing producer qualification, evidence binding, additive installation and Git/large-artifact separation. No new simulator or core package contract is introduced. The GenManip dataset guide was updated with selection, scope, dependencies, installation and rollback instructions; this dated record preserves the remaining integration boundary.
