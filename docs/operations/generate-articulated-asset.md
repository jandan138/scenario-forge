# Generate an Articulated Asset (Agent-Driven)

Runbook for the five-stage asset generation pipeline defined in
[agent-driven-asset-generation-pipeline](../design/agent-driven-asset-generation-pipeline.md).
Rules cited as GEN-xxx live in
[docs/standards/asset-generation.md](../standards/asset-generation.md).

This runbook covers **producer-role** work. It does not convert USD, does not
qualify physics, and does not admit assets into scenario packages — stage E
hands off to the existing ConvertAsset path (ASSET-001).

## Preconditions

- Repo dev environment (for hashing, intake snapshot, docs).
- `7z` available (one-time skill intake only).
- Isaac Sim 4.5 Kit Python — **stage D only**. Never required for `make check`
  or any repo validation.
- A human approver identified for the stage gates (GEN-006).

## One-time setup: skill intake

```bash
# Record source hashes first
sha256sum external_artifacts/incoming/from_xinyu/hunyuan-isaac-articulation-assets.7z

# Verify and extract
7z t external_artifacts/incoming/from_xinyu/hunyuan-isaac-articulation-assets.7z
7z x -o<staging> external_artifacts/incoming/from_xinyu/hunyuan-isaac-articulation-assets.7z
cp -r <staging>/hunyuan-isaac-articulation-assets skills/
```

Then record provenance in
`external_artifacts/incoming/from_xinyu/provenance.json` (schema
`scenario-forge.incoming-archive-extract/v0.1`) and index the archive digest
in `external_artifacts/README.md`. See [skills/README](../../skills/README.md)
for the update procedure (whole-directory replacement + re-apply local
amendments + hash update).

## Stage A — requirement capture

Agent: read the experiment requirement (natural language, video, images),
draft the asset request list — one row per asset: slug, why it is needed,
whether articulated, dimension-critical features, intended robot interaction.

Human: confirm scope and priorities before any searching starts.

## Stage B — evidence search

Agent: for each requested asset, find the real object — manufacturer catalog
page, datasheet, official photos, usage videos. Save evidence only under
`external_artifacts/asset_evidence/<slug>/` (GEN-004; never anywhere else —
some image formats are not extension-ignored, so location is the guarantee).
Grade every item E/F/D/U (GEN-002). Then hash:

```bash
cd external_artifacts/asset_evidence/<slug>
sha256sum $(ls | sort) > MANIFEST.sha256   # exclude MANIFEST itself
sha256sum MANIFEST.sha256                  # catalog digest → external_artifacts/README.md
```

Human: review the grading and coverage. Ungradeable fields stay U and flow to
the spec's punch list — they are never silently filled.

## Stage C — spec synthesis

Agent: instantiate
[docs/standards/templates/asset-spec-template.md](../standards/templates/asset-spec-template.md)
as `docs/design/asset-specs/<slug>.md`, all 14 sections (GEN-003). Frozen
tables carry per-field evidence grades; interaction dimensions are measured or
marked U — never derived from photo pixels (GEN-002).

Human: sign off the spec. Sign-off **freezes** it; generation-stage changes
require re-freeze. Commit the spec.

## Stage D — skill-driven generation

Agent: follow the skill's `SKILL.md` routing
(`skills/hunyuan-isaac-articulation-assets/`). Select the source route:
Hunyuan3D when available, otherwise the Blender-only procedural fallback
(local amendment 2026-09-17 — budget extra iteration rounds and record
`source_route: blender_procedural`). Write raw USD only to
`external_artifacts/incoming/<slug>_generated/` or a documented external path
(GEN-004).

Run the static contract gate with Isaac Kit Python, by full path:

```bash
<ISAAC_ROOT>/python.sh skills/hunyuan-isaac-articulation-assets/scripts/check_articulation_usd.py \
  --usd <file> --asset-root <prim> --mode fixed --json-out <report.json>
```

Warnings:

- Use Isaac's `python.sh`, not the repo dev Python.
- Invoke by full path — the skill's `scripts/` is not the repo `scripts/`.
- Never wire this gate into `make check` or any repo automation (GEN-001).
- Store the report under `external_artifacts/` and index its hash (GEN-005).

Human: review the report. Any FAIL blocks delivery. A static pass is
`static_audit_only` evidence, not runtime acceptance (GEN-007).

## Stage E — admission handoff

Agent:

1. Snapshot the generated tree immutably with the same pattern as
   `scripts/intake_external_environment.py` (full-tree SHA-256, canonical USD
   hash, license, opaque provenance ID; no absolute paths in the record).
2. Fill a ConvertAsset admission request YAML; precedents:
   `docs/operations/scientific-workbench-asset-library-role-admission-request.yaml`
   and siblings.

Handoff boundary: from here the existing pipeline owns the asset —
ConvertAsset conversion and qualification, admission via
`adapters/convert_asset.py`, source bindings, asset lock, scenario compile.
Rejections come back as capability-gap requests (ASSET-006) and route to
stage D (or C if the spec was wrong).

## Iteration and rejection handling

- D → C: spec gap found during generation → amend spec, re-freeze, regenerate.
- E → D: ConvertAsset rejection → fix at the producer with the rejection
  evidence attached; never patch producer articulation/colliders on the
  consumer side (ASSET-001).

## Troubleshooting

- **"No module named pxr" when running the gate**: you used the repo Python;
  use Isaac Kit `python.sh` per the skill's environment notes.
- **Hash mismatch on evidence or report**: re-hash and update both
  `MANIFEST.sha256` and the `external_artifacts/README.md` entry in the same
  change.
- **Isaac not available on this host**: stage D cannot run here; do not fake
  the gate — mark the asset's QA matrix `NOT_TESTED` and move the work to a
  host with Isaac 4.5.
