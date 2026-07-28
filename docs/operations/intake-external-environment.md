# Intake an External Environment Source Tree

Use this small, simulator-neutral step when an externally delivered archive
contains a complete room or other environment that may later become a
Scenario Forge background. It records the exact extracted source snapshot for
the ConvertAsset owner; it does not extract archives, open USD, convert assets,
or admit a background package.

## Preconditions

1. Use an approved extractor that supports the archive format and extract the
   *entire* top-level source directory. Do not hand off the canonical USD by
   itself: keep its relative USD, material, texture, and lighting sidecars.
2. Stage that directory as an immutable source snapshot. The helper rejects
   symlinks and records a deterministic tree hash, but it does not change Unix
   permissions or prove dependency closure.
3. Compute the archive SHA-256. Keep download URLs, signed query strings,
   access keys, and credentials in the approved restricted system only.

The command accepts an opaque restricted reference, not a URL. It must begin
with `restricted/`; for example `restricted/vendor-room-20260727`. Do not put
a signed object-store URL or any credential material into this field.

## Create the intake record

Run from the repository root using a normal development Python environment.
Keep the output outside the extracted source tree so writing the record cannot
change the snapshot being hashed.

```bash
PYTHONPATH=src python scripts/intake_external_environment.py \
  --asset-id scientific_environment_room_a \
  --source-root /restricted/staged/environment-source \
  --source-usd world.usda \
  --archive-sha256 <64-lowercase-hex> \
  --restricted-provenance-id restricted/vendor-room-20260727 \
  --out outputs/scientific_environment_room_a/intake.yaml
```

Add `--expected-source-sha256 <64-lowercase-hex>` when the sender supplied a
canonical USD digest and it must be verified before writing the record.

The YAML contains only:

- a safe public asset ID;
- `LicenseRef-Internal-Restricted`, `redistributable: false`, and a fixed
  restricted-source attribution;
- canonical USD path relative to the source root and its SHA-256;
- deterministic full-tree SHA-256, file count, and byte count;
- archive SHA-256; and
- an opaque `restricted/...` provenance reference with `visibility: restricted`.

It intentionally contains neither an absolute source path nor a source URL.
If a URL contains credentials, do not redact and paste it—keep it out of the
record entirely.

The intake helper itself can record a generic package-safe ID. The scientific
workbench background generator consumes only `scientific_environment_` IDs
made of lower-case letters, digits, and underscores, so use that form when the
record is intended for this workflow.

## Handoff boundary

Give ConvertAsset the immutable source tree through the restricted channel plus
the intake YAML. ConvertAsset must perform source-bound visual-static admission,
dependency/material closure checks, Isaac runtime validation, and any later
workspace-zone profiling. Scenario Forge consumes only the returned package and
manifest; it does not repair this source tree or duplicate ConvertAsset work.
