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
