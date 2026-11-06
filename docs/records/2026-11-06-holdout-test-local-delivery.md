# Local holdout_test delivery — 2026-11-06

The user clarified that the new 136-case batch is a final local held-out test set, named `holdout_test`, separate from existing test and validation. Code is versioned normally; access secrecy is not required. Do not use model results for training/tuning or add the set to online/default evaluation. PR !309 was closed; replacement PR !310 targets feature/pioneer and must remain unmerged pending the user's decision.

The candidate worktree remains `/mnt/data/zhuzihou/GenManip-Sim-deliveries/validation-bg-v2-20261105`, on `feature/holdout-test-20261106`. Its explicit selector is `scientific_experiments/holdout_test/holdout_test.json`.

## Verification

All 136 YAML definitions match the prior definitions after the intended name substitution. All 136 metadata files match reserialization of the prior metadata with recursive string identity substitution; numerical initial states are unchanged. Scene layers match the same path/name substitution. Historical 136-case evidence remains under its original identity, not rewritten as new execution evidence.

Five fresh native cold starts, resets and bounded holds cover the five rooms, ordinary pouring, oven articulation, titration, powder weighing and water bath tasks. Three use 20 steps, two use 320 steps. Receipts bind current configuration, metadata and scene hashes. All 40 JPEGs decode; implementing-assistant contact-sheet review found no blocking missing assets, black frames or obvious displacement. Glass/metal glare and tight wrist framing remain limitations. This was not independent review or policy evaluation. Retained server/client/worker logs contain no matches for the audited fatal-error patterns; this is not a claim of warning-free execution.

41 GenManip unit tests pass, including exact 136-case selection and exclusion from existing JSON selectors. Scenario Forge core code is unchanged; the prior full make check passed 1259 tests, skipped one, and passed lint, smoke and Phase 10.x checks. Documentation changes do not require rerunning unchanged simulation or package tests.

## Package and installation

Evidence root: `/cpfs/user/zhuzihou/dev/scenario-forge/external_artifacts/holdout_test_20261106`.

Canonical package: `release/holdout_test_delta.zip`; SHA-256: `6717bffe9f902c65344f8d01538555b2abfd231364a5d694fad54735d90f6c5a`. ZIP CRC passes. The manifest binds 347 payload files and existing asset/configuration dependencies; `identity_mapping.json` preserves the old-to-new association. The earlier archive remains retained.

All 347 new files were installed additively under `/mnt/data/chenjiantong/GenManip-Sim/saved/`. Baseline dependencies and final installed hashes were checked. Only the 347 unchanged files owned by the earlier installation receipt were removed from the receiver. No differing destination or unrelated file was overwritten. New installation and old removal receipts remain in the respective evidence roots. The receiver code branch was not switched; assets installed does not mean the selector is active there.

Rollback defaults to dry-run and only removes unchanged files from the new installation receipt. Changed files cause rollback to stop. Old data can be restored from the retained original archive if needed.

## Standards synchronization

ASSET-001–005 and VAL-001–006 apply. No general rule, core API, schema or simulator contract changes: this is identity/path migration with evidence binding and additive installation. Standards need no amendment. This record and the candidate dataset guide supersede the earlier delivery checkpoint's pending status; historical records retain their chronological facts.
