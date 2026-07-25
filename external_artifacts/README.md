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

Current indexed screening runs:

- `scientific_environment_background_screening_20260723`: 92 complete
  scientific-environment thumbnails, 10 Isaac Sim 4.1 retakes, the final
  seven-scene shortlist, and the non-executable ConvertAsset batch request at
  `/cpfs/user/zhuzihou/dev/scenario-forge/outputs/scientific_environment_background_screening_20260723`.
  Catalog digest:
  `d60b1a9e87b36fb4669b7d7959bf01230d28c29ee10edc030a19156871a9b787`;
  request SHA-256:
  `183e75a8fb210acc11c1c9b59660c05314b198974db51c5967d3b1dfe0d0bbc3`.
