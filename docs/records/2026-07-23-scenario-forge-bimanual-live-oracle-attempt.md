# 2026-07-23 Scenario Forge Bimanual Live Oracle Attempt

## Scope

This record covers the first EOS/GenManip launch against the current collected
package for `scientific_workbench_bimanual_pour`. It is an execution record,
not a task-success claim. The package was treated as immutable and no changes
were made to GenManip.

## Frozen inputs

- package:
  `/cpfs/user/zhuzihou/dev/scenario-forge/outputs/scientific_workbench_bimanual_pour/adapters/ebench/genmanip`
- package tree digest (`sha256-package-tree-v1`):
  `c2613039e72786c355a039cb6a41d8cfc7cb7897fbd7d9a7ad1154fcf1132cd6`
- Scenario Forge revision: `1b3fbf8fab91364d20b30e7f8e33f8ac0802eda4`
- ConvertAsset revision: `73a84d3c2cfc8378cd5c255cf2282a20da017b8f`
- GenManip checkout used for the launch: `1e6061fa89344b4149b32423e0e82b71df20c5f3`
- EOS adapter checkout: `d6f1dfc891b4a2248c675c2253d6b7eaa57e703e`

## Static admission

The task-scoped GenManip admission helper was run directly against the exact
package (without starting Isaac):

- Lift2 R5a maximum inner aperture: `0.088 m`;
- conical bottle cooked grasp envelope: `0.0447801391 m`, compatible candidate;
- graduated-cylinder interaction profile `r3` envelope: `0.04701 m`,
  compatible;
- admission status: `ready`, blockers: `[]`.

This confirms that the ConvertAsset r3 geometry is no longer the old 115 mm
aperture blocker. It does not prove a robot action, contact, hold, or task
predicate.

## Live launch result

The existing EOS live CLI was launched with the exact package, explicit Isaac
Python, private runtime directory, a fresh run nonce, and all four repository
revisions. Its retained output is:

`outputs/scientific_workbench_bimanual_pour/eos_live_oracle_20260723T/`

The EOS envelope reports:

- `overall_status=launch_or_evidence_failed`;
- `evidence_ingestion.status=unavailable`;
- `blockers=[raw_evidence_missing]`;
- process exit code `1`;
- package digest unchanged before/after.

The GenManip stderr is explicit:

```text
RuntimeCanaryError: runtime canary requires executable
'scenario-forge-genmanip-runtime-contract/v0.2'
```

The current package carries
`scenario-forge-genmanip-runtime-contract/v0.4`. The checked-out GenManip
runtime contract parser and the task runner still hard-require v0.2, so the
process stops before Isaac startup. Consequently:

- `rollout_started=false` was not asserted; the transport envelope leaves it
  `null` because no terminal raw runtime evidence exists;
- no stage action, control acknowledgement, contact, hold, pose predicate, or
  five-stage result was observed;
- no liquid-transfer or benchmark claim is available.

## Decision and next owner

This is an external GenManip runtime-compatibility blocker, not a Scenario
Forge asset or package-integrity failure. Scenario Forge must not downgrade the
authoritative v0.4 contract merely to satisfy an older runner, and it must not
add an episode runner or simulator-specific compatibility shim to the package
compiler.

The next required delivery from the GenManip/EOS integration lane is a
package-linked runner that accepts the v0.4 contract (or an explicitly
versioned, lossless v0.4-to-runtime projection owned by that lane), then runs
the five stages through native robot actions. Once that runner exists, rerun the
same EOS launch command with a new nonce and retain raw terminal evidence.

## Claim boundary

The current evidence proves package immutability, successful r3 static
embodiment admission, and an honest pre-physics launch failure. It does not
prove Isaac reset, robot control, grasp, stable hold, alignment, tilt, return,
liquid transfer, model evaluation, official EBench reproduction, or benchmark
success.
