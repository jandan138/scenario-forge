# Liquid autofill contract

Scenario Forge exposes a portable packaging workflow around a ConvertAsset-owned GPU-PBD liquid
producer. The boundary is intentional:

- ConvertAsset inspects mesh geometry, selects collision approximations, authors particle physics,
  and supplies three Isaac Sim 4.1 cold-run observations.
- Scenario Forge validates the versioned handoff, copies the full source dependency closure,
  authors a relative alias USD, performs one final eight-second full-scene integration, and emits a
  deterministic ZIP.

Neither the core package nor schemas import simulator SDKs. Scenario Forge never reimplements USD
mesh conversion, SDF cooking, or PBD tuning.

## Commands

`scenario-forge liquid inspect` returns candidate and rejection diagnostics. `liquid add` accepts
one exact prim and one fill ratio from 0.10 through 0.80. Fill means the settled live-particle q95
height in the target's local up axis, normalized from recovered cavity floor to rim.

## Promotion invariant

No formal alias USD, dependency directory, or ZIP survives a failed producer or final integration
gate. The working state is renamed to a `_diagnostics` directory. A formal package contains only
relative USD dependencies and preserves the source defaultPrim.

The package claim is `qualified_gpu_pbd_loaded_start`. Robot success, transfer success, metrics,
and benchmark success are explicitly false.
