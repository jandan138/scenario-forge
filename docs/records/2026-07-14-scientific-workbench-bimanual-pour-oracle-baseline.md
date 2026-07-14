# 2026-07-14 Bimanual Pour Oracle Baseline

## Decision

The current `scientific_workbench_bimanual_pour` static package is frozen by its
complete regular-file tree digest before the downstream five-stage oracle run. The
machine-readable record is
[`package_baseline.yaml`](evidence/2026-07-14-scientific-workbench-bimanual-pour-oracle-baseline/package_baseline.yaml).

The package has 198 files and 120,066,353 bytes of regular-file content. Its sorted
`sha256sum` stream, including `./` relative paths, hashes to:

```text
59d6024db27db865be103fd2ddeb7b9a66672238b0f628149d5a065d77cdebe4
```

A second clean static build with the same inputs and an output directory ending in
`package` matched the baseline byte-for-byte. The package is non-redistributable,
so the 120 MB build tree is not committed. The compact record binds the full tree,
the important entry points, the LabUtopia source USD, the ConvertAsset delivery,
and the Scenario Forge, ConvertAsset, GenManip, EOS, and LabUtopia revisions. The
frozen Scenario Forge revision includes the corrected local-`+Y` vessel opening
frames and same-side Lift2 actor assignment; superseded pre-correction and
cross-midline builds are not oracle inputs.

## Reproduction caveat

The current asset-lock generator derives `lock_id` from the output directory name.
A trial build written directly to a differently named output directory therefore
changed only `locks/asset_lock.yaml`; placing the output at `<any-parent>/package`
restored exact reproducibility. This output-path coupling is real technical debt.
It is recorded here and should be removed by the generic compile-orchestration
lane, after the oracle has finished against this already-frozen package.

## Oracle preflight result

The frozen package is suitable for a reproducible preflight, but not yet for a
meaningful five-stage rollout. Two blocking mismatches were found by inspecting the
exact GenManip scene and runtime code:

1. GenManip binds each task UID to a wrapper Xform, while the actual rigid body,
   collision, and mass APIs are on its child `/mesh`. Object tracking and native
   metrics read the wrapper.
2. The native pour predicate reads object roots rather than named opening frames.
   With the rim centers actually aligned and the flask tilted 40 degrees, the
   required root offset falls outside the current success range.

The first requires task-ready vessel packages plus correct GenManip UID binding;
the second requires a frame-aware GenManip metric. An action schedule cannot repair
either contract, so the five-stage rollout is blocked at preflight rather than
reported as a failed policy experiment.

## Claim boundary

This record establishes exact static package identity and repeated static-build
reproducibility. It does not establish an Isaac Sim reset, grasp, alignment,
pouring, return placement, task success, or real fluid transfer. The next evidence
must first close the two preflight blockers. A later private, clean EOS/GenManip run
must bind every result to the complete regenerated package-tree digest.
