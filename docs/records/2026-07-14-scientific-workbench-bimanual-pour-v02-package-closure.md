# 2026-07-14 Scientific-workbench Bimanual-pour v0.2 Package Closure

## Outcome

The current `scientific_workbench_bimanual_pour` build is a usable EBench/
GenManip task package. It combines the curated LabUtopia `lab_001` table and one
DryingBox context object, the EBench Lift2 dual-arm robot, and two independently
qualified ConvertAsset vessel packages. The package compiles, passes strict
portable validation and USD/material closure audit, resets in Isaac Sim through
GenManip, activates the exact v0.2 frame contract, and carries two current initial-
scene renders.

This is not a completed robot demonstration. The EOS five-stage result is a
digest-locked dry-run plan with no actions or contact measurements. No grasp,
stable hold, liquid transfer, task success, model score, or leaderboard result is
claimed.

The compact machine-readable summary is
[`evidence.yaml`](evidence/2026-07-14-scientific-workbench-bimanual-pour-v02-integration/evidence.yaml).

## Frozen producers and sources

| Component | Revision / identity | Role |
|---|---|---|
| Scenario Forge | `0afccde633cadceef11b813717561984f690cf30` | package producer; conditional GPU-dynamics export for qualified SDF objects |
| ConvertAsset | `ba4ac8ccbf3c32f257abdbb68a554a74a90003f1` | reference-closed vessel material, physics, collider, frame, and runtime qualification owner |
| GenManip | `00fd8dc96be5cf9cd919be9af4da723dc619ba73` | final v0.2 consumer and live runtime-canary producer |
| EmbodiedEval OS | `e6a3d17d2c9fc3c608d6c1c19ed86820ef90203e` | five-stage oracle-plan dry-run producer |
| DryingBox ConvertAsset delivery | `324ce6e6d4395ccfda1e59e5ae89de9389cdf225` | retained laboratory context package |
| LabUtopia source | SHA-256 `b3861b5a17945abe401062a04125969c3a63b0f8a0a5ce0026a461dbdfc935f2` | immutable `lab_001.usd` source |

The render manifest records GenManip revision
`17c82e023764f7754097e46cffd8418236d595cc`; the later `00fd8dc...` commit changes
only the standalone canary's pre-Isaac Pydantic preload, not scene construction or
rendering.

## Asset and package closure

The conical bottle retains one active rigid root, its qualified SDF mesh collider,
and the authoritative `opening`, `grasp`, and `support` frames. Its runtime-tree,
contract-payload, and interaction-report SHA-256 values are respectively:

```text
8865c06c5915227d4807d38641d46acd3450bbcedf414699ad2ee1d3603aa584
7a8efec731676cfe3a1b1ff55fd0c911a616ff045455b9bbbfa5dadd82b33923
b5ec7d721294c544d7be23cbac4044063dfa78bc087cf65175cc3b12d72100fc
```

The cylinder retains one active rigid root and the same three frame roles. Its
source mesh collision is disabled and exactly 13 package-owned Cube colliders are
enabled: one bottom and twelve wall segments. Its corresponding hashes are:

```text
2540ecd80cfdbd26cb31ba1d772ddf451206d3b3f49161f108ec67d5d52cab0d
4e88bb016013c9a84196a40380908c168394d3ddf755c25bcdac7772ec582967
2109713e3cb5788da5bf9b9dcc8b4f316505e3fccff5dc8e6a741822ec4271aa
```

Both task objects export `add_colliders=false`, `add_rigid_body=false`, and
`not_set_mass=true`; Scenario Forge does not repair ConvertAsset-owned vessel
physics. `EnableGPUDynamics=true` is exported because the admitted conical collider
uses SDF. The portable package passed `package check --require-asset-lock`.
Independent USD 0.26.5 inspection opened both package assets, the portable scene,
and the collected scene with zero unresolved external assets. Nested reference
probes preserved each vessel material under its instance-local `__aan_materials`
scope.

The generated local artifacts are intentionally ignored by Git:

| Artifact | Files / bytes | `sha256-package-tree-v1` |
|---|---:|---|
| `outputs/scientific_workbench_bimanual_pour` | 401 / 214,360,291 | `78851ace500cf71271ba6558e96ef6c732ca6599a628890241d5b060f2e01d33` |
| `outputs/scientific_workbench_bimanual_pour/adapters/ebench/genmanip` | 200 / 107,667,227 | `6d06c202196ef140075d85654c3a941e787d3f89a4deb9a6bb5da6529bdbe164` |

## Initial-scene render evidence

Isaac Sim performed a real GenManip reset before producing:

- `workspace_closeup.png`, SHA-256
  `556b54d98c66bf71ab3027eb99312031e4cdd6c14ab92699793e0056637d3e3f`;
- `scene_overview.png`, SHA-256
  `5b681f2511e995a09cfce677114e8f69869f01f5ca10c72ffaca0e3ae43ee90a`.

The hash-bound render manifest, runtime log, and visual-ready gate have SHA-256
`27b77e77bdfcaf89fb866ad31a793771d04d94f5a20a96ff2fee01ecc042ea27`,
`43db4020a11d31afa9f654bd324f80768ef8099bbef696bae37662fe0413eecc`,
and `fd8bf0cd19c846d437b5d08f87cc7e92fb112dd1ea64216f51c82b97d2f565a1`.
The log contains no material-scope, missing-asset, unresolved-reference, MDL,
texture, shader, traceback, or fatal signal.

An independent image-only reviewer rated the pair **usable with WARN**. The
close-up passed and clearly shows the dual arms, both glass vessels, work surface,
and exactly one drying box. The overview shows the same set without duplicates or
visible broken geometry, but the empty tabletop dominates and partially hides the
robot base and drying box. The pair is accepted as initial-scene evidence, not as
polished product imagery or proof that every robot component is fully exposed.

## Live GenManip canary

The final live run used a private workspace and real `IsaacEvalEnvRay.reset`. It
passed in 58.15 seconds and wrote authoritative evidence before Isaac fast
shutdown:

```text
/tmp/scenario-forge-final-runtime-canary.8yXC32/evidence.json
sha256 78966b4d8661fc71170bc81d280b9dd55e06a7475518786983f7424890d1b309
```

The v0.2 frame-aware contract activated; both runtime UIDs resolved to exactly one
declared rigid root. A single Lift2 joint received a bounded `0.005 rad` target,
showed `0.0040479433 rad` motion, and recovered to `0.0007715146 rad` maximum
error. Object-pose mutation was not used.

The first attempt failed before reset because Isaac's bundled lazy Pydantic path
mixed with the EOS environment's newer `pydantic-core`. GenManip commit
`00fd8dc...` preloads the four public Pydantic symbols that its runtime imports
before Isaac changes import paths. The regression is test-first, uses no Conda
installation or modification, and the relevant GenManip suite passes 66 tests.

## EOS five-stage dry run

EOS read the immutable collected package and produced a plan in this order:

1. `target_grasp_hold`;
2. `source_pick`;
3. `mouth_alignment`;
4. `pour_pose`;
5. `source_return`.

The retained transient outputs are under `/tmp/eos-bimanual-final.K2Yiiq`:

| File | SHA-256 |
|---|---|
| `evidence_envelope.json` | `5f5fc3aeeadf9b655c790d3f4edfac11526b9f3f97480e7dbaab74a404259809` |
| `oracle_plan.json` | `d7ef10f1818300af3734d1af59b9eb4576aeaced2fffbb2824c9312af0ab89b5` |
| `render_canary_metadata.json` | `c66a90bab82c8f31f4b9ef0f41faab693e8ebbd2282fb1860e6098255615d58c` |

The package digest before and after remained
`6d06c202196ef140075d85654c3a941e787d3f89a4deb9a6bb5da6529bdbe164`.
`rollout_started=false`; every stage trace is `not_started`; contact and the hold
invariant are `not_evaluated`. Those are required blockers for the next execution
step, not passed results.

## Exact completion boundary

Completed here:

- reproducible package compilation from exact source-bound deliveries;
- exact v0.2 actor, object, named-frame, stage, invariant, and predicate transport;
- physics/material/reference closure and strict asset-lock validation;
- post-reset close-up and overview images with independent visual review;
- live GenManip reset, contract activation, rigid-root parity, and robot micro-
  motion/recovery smoke;
- EOS five-stage plan and evidence-envelope generation without mutating the package.

Not evaluated here:

- robot-finger contact, grasp closure, or stable retention;
- execution of any of the five oracle stages;
- collision-free dual-arm reachability and long-horizon control;
- real or simulated liquid transfer;
- final task predicates, task success, policy/model quality, EBench score, or
  leaderboard comparability.

The next implementation belongs in EOS/GenManip: execute the five stages and
populate actions, control acknowledgements, runtime frame measurements, contact/
hold evidence, and predicate evaluations. Scenario Forge remains the portable
compiler and evidence-contract owner.
