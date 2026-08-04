# Generated background support quarantine

> Resolved later on 2026-08-04. The two backgrounds were re-admitted as v2
> after source correction and independent support audit; see
> [generated-room support remediation and v4 gallery](2026-08-04-generated-room-support-remediation-and-v4-gallery.md).

Date: 2026-08-04

## Decision

The `modern_wet_chemistry` and `bioclean` v1 generated backgrounds are
quarantined from the public background gallery. Their historical packages and
render evidence remain immutable, but they are not current selectable
backgrounds.

## Reason

Visual review found small decoration roots with almost no horizontal overlap
with their intended sink-bench support:

- `modern_wet_chemistry`: `MinorPlace_obj_025__wash_bottles_and_dispenser`
- `bioclean`: `MinorPlace_obj_016__wash_bottle_and_soap_dispenser`

This is a producer-source placement defect. Scenario Forge must not compensate
for it with asset-specific transforms or geometry patches.

## Restoration gate

Each background may return only as a new source-bound revision after all of the
following are present:

1. a reviewed support-relation sidecar bound to the source USD hash;
2. an independent ConvertAsset support audit with a passing result;
3. a Scenario Forge package referencing that passing certificate; and
4. seven-view Isaac Sim visual review with no blocking geometry defect.

The other three published backgrounds remain available while the two sources
are repaired.
