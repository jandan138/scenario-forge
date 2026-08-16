# Task 02 r8.5: 40% liquid package

Date: 2026-08-16

## Outcome

Scenario Forge consumes ConvertAsset's promoted r4 cylinder-to-beaker transfer
pair and emits the portable Task 02 r8.5 scenario package at:

```text
outputs/scientific_workbench_task02_r85_20260816/
```

The package retains the r7 modern wet-chemistry room, the 2.000 x 0.800 x
0.755 m workbench, the eBench dual-arm configuration and the existing task
semantics. It adds the promoted 580-particle state and the qualified source and
target container components through the ConvertAsset handoff adapter.

## Package behavior

- Source liquid settles at approximately 40% of the cylinder's effective
  height. Particle physics remains the 0812 parameter set; visible volume comes
  from particle count rather than larger particles.
- Container and particle initial states are baked into final world coordinates
  so the PBD points do not lose a parent transform in Isaac Sim 4.1.
- The adapter validates package ID, entry prim, hashes, dependency closure,
  particle count, qualification contract and three cold-run promotion evidence.
- Preview orchestration supports a product smoke finalization gate while
  keeping simulator imports out of the pure package layer.
- No GenManip source file and no consumer-side cylinder collider, scale,
  mass/inertia, rest-offset or friction patch is used.

## Verification

The initial-scene evidence is under:

```text
outputs/scientific_workbench_task02_r85_20260816/
  ebench/evidence/initial_scene/
```

The overview, workspace and task-object close-up passed local visual review.
The close-up shows the transparent beaker and cylinder with the blue liquid at
the intended source fill. The finalized product smoke ran for 960 physics steps
(8 seconds) and passed. Targeted package, adapter and preview tests pass; the
repository-wide `make check` is the final integration gate.

## Claim boundary

r8.5 is the portable scenario/package result. It does not contain an episode
runner and does not claim policy or benchmark success. The five-stage scripted
robot proof is produced and validated in Embodied Eval OS as r8.6 evidence.
