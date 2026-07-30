# 2026-07-29 Articulated Handoff Promotion Hardening

## Scope

Scenario Forge now treats ConvertAsset's optional
`interaction_contract: {status: "not_requested"}` sentinel as absent for an
`articulated_object`. Rigid-object use still requires a passing rigid interaction
contract.

For articulated handoffs, the ConvertAsset adapter now requires and verifies the
producer promotion receipt at:

```text
evidence/articulation_runtime_qualification/promotion.json
```

The receipt must bind the final manifest, package asset, profile, runtime report,
and pre-promotion manifest. The adapter also requires passing report input and
drive integrity, a portable `qualified_package` block that binds `asset.usd`,
the entry prim, Isaac runtime profile, pre-promotion manifest, and unchanged
asset hashes, and rejects non-standard JSON numeric constants. Runtime DOF
identity remains `dof_index` plus `joint_prim`; duplicate raw DOF names remain
valid.

## Runtime Evidence

The HCI centrifuge qualifier was rerun with Isaac Sim 4.1 after strict JSON
serialization was added. The new report is passing and bound to the unchanged
package asset and pre-promotion manifest:

```text
outputs/tube_task_assets_20260729/uniform_scale_k0365/centrifuge/package/
evidence/articulated_task_qualification_hybrid_arc_strict_identity_candidate/report.json
```

Unbounded PhysX drive values are encoded as the explicit JSON string
`"unbounded"`, rather than invalid `Infinity` tokens.

## Verification

```bash
python -m pytest -q tests/test_convert_asset_adapter.py \
  tests/test_qualify_centrifuge_task_interactions.py
make check
```

The focused adapter and qualifier suite passed 54 tests. `make check` passed:
489 tests, Ruff, package smoke, Phase 10.x strict validation, and diff checks.

The Isaac Sim 4.1 qualifier command also returned `{"status": "pass"}` for
the strict-JSON candidate report above.

## Remaining Blocker

The centrifuge package is intentionally not promoted. A producer-owned
`aan.articulated_device_profile.v1` with measured authoritative frame values is
still required. The report alone proves the specified collider/contact gates; it
does not authorize guessed task frames or robot-policy claims.

## Resolution (2026-07-30)

The blocker is resolved for
`outputs/tube_task_assets_20260729/centrifuge_proxy_parent_local_r7/package`.
The measured r3 profile (SHA-256
`8f53e05548b8681a8332d08c2442f7049d6c360c3e2352c342b4f4ca3961784d`) and
passing report (SHA-256
`10b5c31f856b9258e832487abdbf08f38801cea6fb28d6ab5d7e249bcb1c54bf`) were
promoted with final manifest SHA-256
`7948fff535514227b7e6cce636dc9be63145837bc783802b1f4ce63658233598` and
receipt `evidence/articulation_runtime_qualification/promotion.json`.
`load_convert_asset_package_handoff(..., usage="articulated_object")` accepts
the final package and its bound profile, report, and receipt. The historical
blocker above remains applicable to the earlier unpromoted candidate only.
