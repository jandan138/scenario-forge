# EBench source metadata: preserve absent unit opinions

The EEOS glasses contactOffset pair failed its complete flattened USD audit:
the source content layer had no authored metersPerUnit, while the compiled
control added metersPerUnit=1. No episode was dispatched with that pair.

The preservation option now omits legacy unit/axis defaults before copying
source-authored metadata. The default packaging path is unchanged. The existing
metadata regression test is parameterized with and without authored units;
the missing-unit case failed before the fix. Historical compiled packages are
retained; callers must regenerate a separately identified output.

Applicable rules: USD-007 and VAL-002/003/006. The design contract and USD-007
note are synchronized: absence of unit/axis opinions is preserved under the
opt-in contract. This is CPU composition evidence, not native runtime evidence.
Validation log: /tmp/eeos-forge-metadata-check-20260913.log.

Targeted adapter tests: 15 passed. Full make check was started and remained live
at this handoff (make PID 1176457, pytest PID 1176459, unified session 63988);
its completion is not yet claimed. The regenerated EEOS metadata-v2 pair passed
full source Flatten equality after restoring only the registered treatment
property, plus source task_data and evaluation-config equality checks.

Completion update: the same make-check session exited 0. Tests: 1023 passed,
1 skipped in 327.92 seconds; ruff, package smoke, Phase 10.x and diff check
passed. No runtime qualification is inferred from those checks.
