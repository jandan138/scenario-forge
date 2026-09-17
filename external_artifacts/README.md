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

- `lab2sim_iclr2027_fig1_sources`: five ignored raster inputs staged for the
  Lab2Sim paper hero. Their immutable source and selected-asset hashes are in
  `paper/venues/iclr2027/figures/lab2sim/source/fig1-assets.json` and
  `paper/venues/iclr2027/figures/lab2sim/provenance.json`. Rebuild the ignored
  `source/*.png` files with
  `python scripts/prepare_lab2sim_fig1_assets.py`; `--check` verifies an
  existing staging tree. The sources are the IKA OVEN evidence catalog, the
  Fehling r10 camera-only retake under
  `outputs/lab2sim_fig1_retake_20260917/`, and the current-delivery powder r4,
  titration r1.7, and OVEN r2 evidence trees. Missing external sources are a
  hard error; the script never substitutes candidate or prototype renders.

- `lab2sim_iclr2027_result_sources`: fourteen ignored raster inputs staged for
  the Lab2Sim paper Figures 2–3 and appendix by
  `python scripts/prepare_lab2sim_result_assets.py` (`--check` verifies).
  Hashes, crops, and global brightness are in
  `paper/venues/iclr2027/figures/lab2sim/source/fig23-assets.json` and
  `paper/venues/iclr2027/figures/lab2sim/provenance.json`. Sources are the
  current-delivery task05 r11, task07 r10.1, stir-bar r5, water-bath r1,
  OVEN r2, and titration r1.7 evidence trees, the IKA OVEN and burette
  evidence catalogs, the phase-11 Lift2 runtime frame, and the camera-only
  OVEN r2 retake under `outputs/lab2sim_fig3_retake_20260917/oven_r2/`
  (`scripts/render_lab2sim_oven_retake.py`; same scene, same door command,
  new camera and exposure only).

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
