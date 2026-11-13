# External Artifacts

This directory is an index for artifacts that are too large or too environment-specific for git.

Allowed in git:

- Small YAML/JSON manifests.
- Claim-bearing validation reports.
- Tiny fixtures needed by tests.

Do not commit:

- Raw USD asset trees.
- Rendered images or videos.
- Simulator dumps.
- Model checkpoints.
- Large generated scenario packages.

Current indexed external artifacts:

- `scientific_environment_background_screening_20260723`: 92 complete
  scientific-environment thumbnails, 10 Isaac Sim 4.1 retakes, the final
  seven-scene shortlist, and the non-executable ConvertAsset batch request at
  `/cpfs/user/zhuzihou/dev/scenario-forge/outputs/scientific_environment_background_screening_20260723`.
  Catalog digest:
  `d60b1a9e87b36fb4669b7d7959bf01230d28c29ee10edc030a19156871a9b787`;
  request SHA-256:
  `183e75a8fb210acc11c1c9b59660c05314b198974db51c5967d3b1dfe0d0bbc3`.

- `centrifuge_proxy_parent_local_r7`: promoted articulated package at
  `/cpfs/user/zhuzihou/dev/scenario-forge/outputs/tube_task_assets_20260729/centrifuge_proxy_parent_local_r7/package`.
  Facade source SHA-256:
  `04135987bf22cb1b63515726ff78bf4be341bc9f1400eccad59a5a6d371f9149`;
  `asset.usd` SHA-256:
  `3573bb0eb474b80f842ea4d70dd2be2c2b5019a181d604bc1e17d4c7b7754926`;
  profile r3 SHA-256:
  `8f53e05548b8681a8332d08c2442f7049d6c360c3e2352c342b4f4ca3961784d`;
  report SHA-256:
  `10b5c31f856b9258e832487abdbf08f38801cea6fb28d6ab5d7e249bcb1c54bf`;
  final manifest SHA-256:
  `7948fff535514227b7e6cce636dc9be63145837bc783802b1f4ce63658233598`;
  receipt: `evidence/articulation_runtime_qualification/promotion.json`.

- `magnetic_stirrer_archive`: two USD extracts from
  `valid_with_json_by_final_category_usd.zip` whose archive labels are
  magnetic stirrer / magnetic stirrer with hot plate. Layout matches
  `drying_box/<asset>/usd/` (canonical USD + four-view PNGs + contact sheet).
  Provenance: `incoming/magnetic_stirrer_archive/provenance.json`.

- `hunyuan_isaac_articulation_assets_skill`: the Hunyuan3D→Isaac articulated
  asset skill package, extracted into the committed tree
  `skills/hunyuan-isaac-articulation-assets/` (agent tooling, producer role;
  no asset qualification implied). Source archive
  `incoming/from_xinyu/hunyuan-isaac-articulation-assets.7z` SHA-256:
  `d112b48cb2d5a855d313af51f13a23376548f9521ae915ba624ce233a0ea59cb`;
  provenance: `incoming/from_xinyu/provenance.json`; indexed 2026-09-17.

- `asset_evidence_ika_oven_125`: evidence images extracted from
  `incoming/from_xinyu/IKA_OVEN_125_reference.docx` (source SHA-256:
  `c4338164e43123d09102865b295cd5ab04dd238aa186a373d92ae7362562ec21`),
  stored under `asset_evidence/ika-oven-125/` with per-image hashes in
  `asset_evidence/ika-oven-125/MANIFEST.sha256` (catalog digest:
  `90d6b591634617264285de3e813ca01238effaf1521061cfcebe961a6f0a2886`) and in
  the image inventory of `docs/design/asset-specs/ika-oven-125.md`.

- `asset_evidence_traditional_titration_burette_and_stand`: evidence images
  extracted from
  `incoming/from_xinyu/Traditional_Titration_Burette_and_Stand_Asset_Reference.docx`
  (source SHA-256:
  `49b697f42cc9b61c26649cab50b2eb8f720e7e6d0931090bb4f825f7547bf126`),
  stored under `asset_evidence/traditional-titration-burette-and-stand/`
  with per-image hashes in
  `asset_evidence/traditional-titration-burette-and-stand/MANIFEST.sha256`
  (catalog digest:
  `68af1981b7c07a446fc19d2e60faabf1ac5f2e42344b7385112a7c15438f7e65`) and in
  the image inventory of
  `docs/design/asset-specs/traditional-titration-burette-and-stand.md`.

- `lab2sim_iclr2027_fig1_sources`: five ignored raster inputs were staged for the
  Lab2Sim paper hero. Their hash indexes left the published repository on
  2026-11-12 with the rest of `paper/`. The external sources remain the IKA
  OVEN evidence catalog, the Fehling r10 camera-only retake under
  `outputs/lab2sim_fig1_retake_20260917/`, and the current-delivery powder r4,
  titration r1.7, and OVEN r2 evidence trees.

- `lab2sim_iclr2027_result_sources`: fourteen ignored raster inputs were staged
  for Lab2Sim Figures 2–3 and the appendix. Their hash indexes left the
  published repository on 2026-11-12 with `paper/`. Sources remain the
  current-delivery task05 r11, task07 r10.1, stir-bar r5, water-bath r1,
  OVEN r2, and titration r1.7 evidence trees, the IKA OVEN and burette
  evidence catalogs, the phase-11 Lift2 runtime frame, and the camera-only
  OVEN r2 retake under `outputs/lab2sim_fig3_retake_20260917/oven_r2/`.

- `out_of_domain_factory_20261112`: three Code-as-Room (`room-source-v2`)
  out-of-domain room deliveries + `ConvertAsset` `visual_static_environment`
  packages (`kitchen_coffee_bar_v1`, `smt_qa_workshop_v1`,
  `office_print_studio_v1`), three manufacturer-grounded fixed-base v2
  articulated hero packages (`NespressoCreatistaPlus` final manifest SHA-256:
  `03ab59bf61f00fab25650d0d6645adb551e4ca85a56cf78422bd92d1b56674f3`,
  `IngunMA2111Fixture` final manifest SHA-256:
  `c1771f0e5a570d4e16f148bdb68159bf5052067ce37f911d30ab6d8129490b49`,
  `BrotherMFCL2820DW` final manifest SHA-256:
  `c8125e7bbeef95f5c87e24df0c30cd20e45c5fc0744076f26914840c22926ca4`), nine
  qualified rigid/context companion packages, Critic repair trace, and three
  compiled + GenManip-collected closed-loop evaluation packages under
  `external_artifacts/out_of_domain_factory_20261112/`. Also includes 16
  lossless 1920×1080 RayTraced Canary stage keyframes + 3 720p H.264
  progression videos under `out_of_domain_factory_20261112/showcase_media/`,
  and the single-file offline executive showcase
  `out_of_domain_factory_20261112/out_of_domain_hero_showcase_20261112.html`
  (58.08 MB, 46 deduplicated lossless PNGs + 3 inline MP4s, `external_urls=0`,
  SHA-256: `34a8f3e93b37b2d4745b6bd7043b078417b8587b3b393ee79420edb8b8b8178a`).
  Per-hero Blender Cycles `AgX` studio renders, datasheet evidence JSONs, and
  `MANIFEST.sha256` files are stored under
  `asset_evidence/{nespresso-creatista-plus-bne800,ingun-ma-2111-pcba-fixture,brother-mfc-l2820dw-printer}/`
  and indexed in `docs/records/2026-11-12-out-of-domain-closed-loop-canary.md`.

- `out_of_domain_factory_r2_20261113`: Round-2 (`r2`) CAD-grade procedural
  OpenUSD upgrade of all three out-of-domain articulated hero machines (`21`
  controllable DOFs total: `8 + 6 + 7`, `1.47–2.80 MB` per hero) and nine
  companion rigid/context assets, verified `27/27 PASS` against the `IKA OVEN 125`
  9-Gate Acceptance Suite (`out_of_domain_factory_r2_20261113/assets/ika_grade_acceptance/ika_acceptance_summary.json`)
  and promoted via `ConvertAsset` (`isaac41`):
  `NespressoCreatistaPlus` (raw source SHA-256:
  `12923e4903796b870045fe03402969f0291d90fda8c9e0b1852d9ff40e09173d`, final
  manifest SHA-256:
  `598322825cc4a631083146eb6e01cd988e18e1a5eee6208424b35f9ee1d90b25`),
  `IngunMA2111Fixture` (raw source SHA-256:
  `6fc110b5256fa9e35ce511225f2006c7523d465e234d772d272a9ab881fbe1dd`, final
  manifest SHA-256:
  `07250093c56b5619f617efd452e677306b7624452281db66f9e38c16276b2a71`), and
  `BrotherMFCL2820DW` (raw source SHA-256:
  `9a0f377ec553a6865202e3e1fc9ebbf475b608965c3a7f5e10cddffce655eed1`, final
  manifest SHA-256:
  `b6f91a7e6d4bdc291bf161911344aa063518ea9e3327f4914f08fadead6f0977`).
  Includes compiled + GenManip-collected `6 / 5 / 5` stage scenarios, 21
  lossless 1080p initial 7-view PNGs, 19 lossless 1080p Canary keyframes + 3
  720p H.264 `progression.mp4` videos, 4-view Blender Cycles studio renders +
  Isaac Sim 4.1 RTX inspection renders under `asset_evidence/*-r2/`, and the
  single-file offline showcase
  `out_of_domain_factory_r2_20261113/out_of_domain_hero_showcase_r2_20261113.html`
  (83.16 MB, 62 lossless PNGs + 3 inline MP4s, `external_urls=0`, SHA-256:
  `40a43415182bedfcff1823602b9776dabba1f359063bec8b7351c1ecfef6e1e6`).
  Indexed in `docs/records/2026-11-13-out-of-domain-cad-heroes-r2-acceptance.md`.

- `out_of_domain_factory_r3_20261113`: Round-3 (`r3`) Swarm Upgrade combining
  Track 1 (`GEN-008` `G1..G8 + G9a + G9b`, `30/30 PASS` across the three `r2`
  CAD articulated hero assets at
  `out_of_domain_factory_r3_20261113/hero_g9b_acceptance/ika_acceptance_summary_v2.json`,
  SHA-256:
  `327c7cbd67b1b285b4c2bc9ad3e11e7700f0162c024edc361c0f26a422da4a20`) and
  Track 2 (`Code-as-Room` architectural room upgrades with file-backed procedural
  PBR textures & visual-critic Cycles + Isaac Sim 4.1 RTX audits, admitted via
  `ConvertAsset` `isaac41` with `deps/textures/` preserved):
  `kitchen_coffee_bar_v2` (15 textures, manifest SHA-256:
  `7ea58583a17ea1a667853618db75d827814cce1f072ef81ff45bb8af2c95f113`),
  `smt_qa_workshop_v2` (11 textures, manifest SHA-256:
  `cca468903a228933219e790b7f1888be398b1154f5f37cb1b3de9877b5e066a4`), and
  `office_print_studio_v2` (10 textures, manifest SHA-256:
  `b82d209e324c07c188b0210fa2676ea32c411ece88cab2f327c68e7280d463c2`).
  Includes `rooms_admission_summary.json` (SHA-256:
  `dec24d6400c4e77c75c35de7da003171e3e98de1d3c6768da65e915c107cebf9`),
  `scene_gate_summary.json` (SHA-256:
  `3660a2c5247bf749541af3bdc69606cff237de38002b6fb26c6d7d51322d0ba6`),
  `predicate_canary_summary.json` (`0.00 -> 1.00` across `6 / 5 / 5` stages,
  `critic1_max_translation_drift_m <= 1e-06`, SHA-256:
  `65ecf85c911384fddbde08741ca18f22c960f6d197fd7310abf63e80cdb116d2`),
  `showcase_media/canary_media_summary.json` (SHA-256:
  `56cf10f4bb91067cf73d1ac770cb0d0f171744f9311fddf4d45f98ad9b97cb7c`),
  composed Isaac Sim 4.1 RTX critique
  `showcase_media/rtx_composed_critique_report.json` (`3/3 PASS`, `min >= 8.8`,
  SHA-256:
  `3f577638e154ac1648358bff205b80028d3680f8ee6583dfbdb85a6a58e62446`), and
  the single-file offline showcase
  `out_of_domain_factory_r3_20261113/out_of_domain_hero_showcase_r3_20261113.html`
  (124.68 MB, `130735689` bytes, 62 lossless PNGs + 3 inline MP4s,
  `external_urls=0`, SHA-256:
  `6f98d43af1c4f7abf882ac9c8d9eca52ce22f37188fce1dfba2a9864e1896a31`).
  Indexed in `docs/records/2026-11-13-out-of-domain-rooms-r3-and-gen008-gate.md`.

- `out_of_domain_factory_r4_20261113`: Round-4 (`r4`) internalized
  `scenario-forge` room deliveries (`producer.repo == "scenario-forge"`, zero
  external `Code-as-Room` dependency; `rooms/rooms_admission_summary.json`
  SHA-256:
  `0d1fcbcb6a7571a102a1394b35f451d5eff7aa0cc1846459503eddfce819d748`) and three
  domain-matched freestanding 4-legged worktables (`GEN-009`, `Z = 0.000..0.755 m`,
  replacing the floating `0.71..0.75 m` gray slab;
  `tables/tables_qualification_summary.json` SHA-256:
  `f37f0ff7a370ee277dfe8fa1ffa40e6824cb548d4ca0e9726353bb233d2143f8`,
  `tables/renders/tables_visual_critique_report.json` SHA-256:
  `7b4d5433b9c38cbd3a6f7238178a993d7453c087737da7742c766a98a5f1bdae`):
  `CoffeeBarOakSteelTable` (manifest SHA-256:
  `214296817b2debff524ef12d2e1d9bbf10a6e1ffe1276300b4cadee5e6f55bef`),
  `SmtEsdAluminumBenchTable` (manifest SHA-256:
  `c3e109aee7fb69ce5f0062938bfdc83924a29b9877d8cfbc7300fc3f8d702e58`),
  and `OfficeBirchSteelTable` (manifest SHA-256:
  `c97f6066486d011b776444f4c043dae903b795bed5820f78255fe9e796821206`).
  Includes `scene_gate/scene_gate_summary.json` (`3/3 PASS`, SHA-256:
  `89ceede0ddde7fc0eb4443065c02713ce41f8947203d1b6f9cbea5bdc067f0cf`),
  `canary/predicate_canary_summary.json` (`0.00 -> 1.00`, `0.000 m` cold-reset
  drift, SHA-256:
  `cc5be6d7395a88af1e9be42e9b638b2fc422a60f3393fad681d6ed1453997675`),
  `media/canary_media_summary.json` (SHA-256:
  `ee89c9ab9ad01092a378f4da31ba7bffeb1c1d91ab8aeca66131dd7953e88a4d`),
  composed Isaac Sim 4.1 RTX blind critique
  `media/rtx_composed_critique_report.json` (`3/3 PASS`, `min 8.9/10`, SHA-256:
  `cd5837a8755001885ccf57732ee5bd56bb33f314a7dfd08b86642cfbb70543fe`), and the
  unified 4-scenario (`3 r4 + 1 Real-to-Sim`) offline HTML showcase
  `out_of_domain_factory_r4_20261113/out_of_domain_and_real2sim_showcase_r4_20261113.html`
  (250.62 MB, `262798095` bytes, 118 lossless PNGs + 4 inline H.264 MP4s,
  `external_urls=0`, SHA-256:
  `71f3e2a71a3c4bb26b58abe3f120d473a45962227f8ee414588e001eb37457c8`;
  manifest `out_of_domain_and_real2sim_showcase_r4_manifest.json` SHA-256:
  `2b2d8cc54233f892ab24343e9003aca23dc0e1738f5a2596de0eb8178c769737`).
  Indexed in `docs/records/2026-11-13-internalized-room-r4-tables-and-real2sim.md`.

- `real2sim_office_desk_20261113`: Single-Image Real-to-Sim Open-Office
  Workstation Twin (`GEN-010`) grounded from
  `evidence/source_photo.jpg` (SHA-256:
  `9a7d1149de9eb9aa852401ba53271f374f44b25e3e88f0743961f51811ecd195`), including
  `spatial_grounding/workstation_pose_grounding.json` (SHA-256:
  `7d580dbad44ef26ba612d335ff03038db0e218e708eeee56450a0eee7f8b4087`),
  19-surface 1:1 Texture Twin Ledger (`ledger/ledger_manifest.json` SHA-256:
  `64ea562f64c7b9f7531cb31c10a7c1657bf539031abfd63ef736d384d7d085b5`,
  `ledger/patch_critique_report.json` `19/19 PASS >= 8.4`, `max ΔE_ab = 0.3884`,
  SHA-256:
  `a0f5bb15ea699b0f06dcf28684a4513f80df5d98806d9c04ec23501f1eb90678`),
  internalized open-office room `real2sim_open_office_bay_v1`
  (`room/room_admission_summary.json` SHA-256:
  `74ea86a3086874649eb3519f9f9bf41fe49243cb88e1c3b60106180e2add04f3`,
  `room/renders/room_visual_critique_report.json` `min 8.9/10`, SHA-256:
  `2ac4323281b5fd0ac1c82b822c00792e4f231f920aa7a36e8b216c0271bf9ef9`),
  freestanding `Real2SimBunchStandingDesk` + 11 desktop props
  (`desk_and_props/qualification_summary.json` SHA-256:
  `f3d69a6544df26528a5b706f52c8965de5af8d366201d560ac5d0e86b7d060cb`),
  3-DOF `GEN-008` `10/10 PASS` hero `DesktopDualDrawerRiserRig`
  (`hero_rig/assets/ika_grade_acceptance/ika_acceptance_summary.json` SHA-256:
  `e506001ee450b7fbe939703f01ca70f01ad0f176cea3aa92857642a0aa79818f`, final
  manifest SHA-256:
  `569879c3393b7f885411261346fb5d20a68fc9460d85b95ee51a866a41d02718`,
  `hero_rig/critique/desktop-dual-drawer-riser-rig_visual_critique_report.json`
  `min 9.0/10`, SHA-256:
  `3419b37ecec94dbdee5afbd218c82c77a79d36580e5cc955e3675ae3f10b777a`),
  Cycles camera-matched reprojection board (`spatial_grounding/reprojection_comparison_board.png`
  SHA-256:
  `0d4d012401fd16503941babf7ae11d2e0ee671c32bef2f828cfec59bf236ad2c`,
  `spatial_grounding/reprojection_critique_report.json` `min 8.7/10`, SHA-256:
  `fa7fadaa3514c0d2b55426a47b2d77bc90464cadfab18eef098b2cf1a62d1e2a`),
  `scene_gate/scene_gate_summary.json` (`1/1 PASS`, SHA-256:
  `94dba9d136aeb2cd2252f52b6a1381313756ba5a01816f6c0e0a747fd1bba609`),
  5-stage `canary/predicate_canary_summary.json` (`0.00 -> 1.00`, `7e-06 m`
  cold-reset drift, SHA-256:
  `fd92a5a9596393a010d7daac83d37147d137dfc9edd02d35fb301f3f07921ef8`),
  `media/canary_media_summary.json` (SHA-256:
  `fad2d6509c9a6209e5aef41015713155fb4619de9c075c989fa6479aedad9b86`),
  RTX camera-matched reprojection board (`media/rtx_reprojection_comparison_board.png`
  `edge_iou=0.2483`, SHA-256:
  `4b5a04469519bd543e3885d18a9970142246d15f6e47d0436d8ed3a2bed1eadc`), and
  composed Isaac Sim 4.1 RTX blind critique
  `media/rtx_composed_critique_report.json` (`PASS`, `min 8.9/10`, SHA-256:
  `5fad71a7a453d7067775cc782c0db710d52cb2ebb2d907486183d982feab2509`).
  Indexed in `docs/records/2026-11-13-internalized-room-r4-tables-and-real2sim.md`.

## Historical output archive

The [round-two archive and build-input index](archive-index-round2-20260905.json)
records the large background cleanup and removal of old task build dependencies.
It adds 46.89 GB net reclaimed while preserving current delivered packages.
Reconstruction uses the [locked build inputs](../docs/operations/workbench-build-inputs.md).

The [2026-09-05 archive index](archive-index-20260905.json) maps original
directories to verified OSS copies, file manifests and retained exceptions.
See the [execution and restore record](../docs/records/2026-09-05-generated-artifact-retention-review.md)
for totals and restore commands. Current task heads remain in
`configs/artifact_retention/current_task_heads.v1.json`.
