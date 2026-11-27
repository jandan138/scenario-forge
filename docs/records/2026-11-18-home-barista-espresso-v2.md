# Home Barista Pro 19B source assets, 2026-11-18

The [builder](../../external_artifacts/ce_op_home_v2_20261118/builders/build_home_barista_espresso_v2.py) produces the fixed-base machine, demitasse and capsule under `external_artifacts/ce_op_home_v2_20261118/hero_espresso/source`. The design basis is the [frozen specification](../../external_artifacts/ce_op_home_v2_20261118/specs/home-barista-espresso-center-v2.md) and its [acceptance configuration](../../external_artifacts/ce_op_home_v2_20261118/specs/ika_specs/home-barista-espresso-center-v2.yaml).

The authored machine is closed for measurement and studio inspection. Its passive hinge has a −70° physics reset. The encoder uses local Z in both joint frames, aligned with the physical shaft into the fascia. The base weighs 4.65 kg and the other links total 0.55 kg. The power, temperature and froth keys have 2.8 mm travel and return mechanically. The device graph latches power, enforces the brew-lever interlock and drives the displays, jets and cup fill. At 60 physics steps per second the nominal pour takes 38 steps.

## Reopen and visual evidence

The unchanged acceptance verifier returned **PASS_STATIC_ONLY, 5/5** on its first invocation against the final assets. The factory-layout staging copy had the same source bytes as the published packages. The archived report uses repository-relative paths to those packages and the critic report. [Acceptance report](../../external_artifacts/ce_op_home_v2_20261118/evidence/home-barista-espresso-center-v2/home-barista-espresso-center-v2_ika_acceptance_report.json)

| Check | Observation |
|---|---|
| G1 fixed base and topology | One articulation root at `Joints/BaseToWorld`, nine rigid links, eight movable joints, 23 colliders. The serial rotor joint follows all seven depth-one joints in both the composed stage and the serialized layer. |
| G2 reopen and bounds | OpenUSD 26.05 reopened all three component roots at one metre per unit, Z up. Closed machine W × D × H measured 171.0 × 393.2 × 308.0 mm with its feet at Z = 0. The machine resolves 20 local PNGs. Both workpieces resolve without external files. |
| G3 control clearance | Minimum pairwise gap 9.70 mm at rest and across 48 combinations of pressed, released and rotated control poses. |
| G9a offline appearance | Nine primary meshes met the geometry threshold. Five PBR material classes were present. Both standby textures exceeded the luma-variation threshold. All four 1280 × 960 Blender 4.4.3 Cycles AgX views passed the size, exposure and contrast checks. |
| G9b independent critique | All five dimensions passed. The minimum score was 8.1/10. The reviewer saw slight faceting in the chrome rear-cover trim and broad reflections on the open hinges. |

The three closed views show the authored standby state. The detail view uses the open lever, extended tray and seated capsule in a prescribed pose. The [review](../../external_artifacts/ce_op_home_v2_20261118/evidence/home-barista-espresso-center-v2/home-barista-espresso-center-v2_visual_critique_report.json) binds the source USDs, final PNGs, frozen specification and review references by SHA-256. [Standby close-up](../../external_artifacts/ce_op_home_v2_20261118/evidence/home-barista-espresso-center-v2/blender_studio/preview_ui.png) · [Open chamber](../../external_artifacts/ce_op_home_v2_20261118/evidence/home-barista-espresso-center-v2/blender_studio/preview_detail.png)

Pure USD measurements placed the cup sole 4.0 mm above the tray at its specified spawn, and the capsule 4.0 mm above the chute floor with 4.5 mm minimum side clearance. The cup fill stayed on the porcelain floor and met the crema at five fill fractions. The capsule shell, foil and hull each passed a closed-edge check. A mounted graph test with supplied joint and receiver readings exercised wake, release, interlock, three menu choices, completed fill, both ablations and reset while the key was held. Live PhysX gates G4–G8, RTX exposure and robot integration remain untested.

## Build identity

| File | SHA-256 |
|---|---|
| Builder | `df629c0d371aa14773501fc7f0904d65862f9a07397e61ce8ef4bc46b90027cc` |
| Machine `asset.usda` | `d7bd021250ed98ac20265e7d4183d381d40f822067c1867bd3657c80f871dd20` |
| Cup `asset.usda` | `9a72922966aa3817cb9f6b59a83e0c8a97c9d95ad31455138977ebc743b7c212` |
| Capsule `asset.usda` | `b0fd6b0a7874a7a10436492f5e5b2891cee2976428e83a700eb6c241896dfe24` |
| Fixed-base static audit | `8602a2753044aa51c348832a4c94198f23563e727e4a5c90a126a2cb32178c79` |

The builder checks every typeset label, package filename, generated layer and PNG text field. An independent case-insensitive scan found zero forbidden matches across the builder and three source packages. All 12 acceptance-verifier tests passed. Repository-wide `make check` stopped in pytest with 44 failures and 25 errors, including missing historical workbench and robot-bundle artifacts.

The applicable standards at repository revision `5bde2b4` are GEN-007/008, ART-005, USD-002/008, MAT-002/003/004, STATE-002/003 and VAL-001/003. These asset-specific dimensions, drives, materials and observations apply the existing rules. They introduce no change to a general standard or package contract.
