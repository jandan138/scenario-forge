# Workspace profile-4 closure for candidate 067 (2026-07-27)

ConvertAsset has formally marked `scientific_environment_067` as
`not_applicable` for the fixed eBench dual-arm workcell. This is a final
placement decision, not an asset-admission failure: the source background
remains a valid visual-static package, but it has no rule-compliant location
for the unchanged `2.345 × 2.645 m` eBench workbench.

The consumed producer sidecar is revision
`2026-07-26-workspace-integration-profile-4`, commit
`88f134242c6f81502ea972c3b9de88776f8b44ec`. Its source hash remains
`af81e8a6439d80a5521c97bb44972d2f014661c8df127e85ffdd5d55b371124a`.

ConvertAsset quantified and ruled out all reviewed locations:

- the prior west-wall and north-wall hood-pair locations either place the
  workcell against a wall or drive its rear through a wall face;
- the usable north and west aisles are respectively narrower than the fixed
  workbench depth or width, so a wall-flush placement enters the interior row;
- making that placement fit would require inactivating six or more background
  assemblies that the profile is meant to preserve;
- the interior islands contain about 175 ungrouped loose props, so clearing
  them would violate the complete-assembly rule.

No source USD/MDL/mesh, physical property, robot, eBench table, vessel pose,
task pose, or GenManip code changed. No consumer-side hide list, collider,
physics workaround, or camera workaround is permitted or needed.

## Scenario Forge disposition

The generator reads profile-4 and rejects an explicit request for candidate
067 before package generation. It therefore excludes 067 from the current
profile-enabled output. The previously generated profile-3 package and its
two renders remain diagnostic evidence only; they are not a handoff candidate.
Candidates 059, 066, 083, and 084 are unaffected by this closure.
