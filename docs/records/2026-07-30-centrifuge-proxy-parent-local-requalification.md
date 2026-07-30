# 2026-07-30 Centrifuge Proxy Parent-Local Requalification

## Outcome

The corrected package is:

```text
/cpfs/user/zhuzihou/dev/scenario-forge/outputs/tube_task_assets_20260729/centrifuge_proxy_parent_local_r7/package
```

The raw source remains immutable. The r7 facade remaps collision Cube centers
into their moving parents' local frames while preserving every local scale; it
does not change tube or rack scale.

## Profile And Runtime Evidence

The producer profile is:

```text
/cpfs/user/zhuzihou/dev/scenario-forge/outputs/tube_task_assets_20260729/centrifuge_proxy_parent_local_r7/centrifuge.articulated_device_profile_r3.json
```

Its SHA-256 is
`8f53e05548b8681a8332d08c2442f7049d6c360c3e2352c342b4f4ca3961784d`.
Its corrected lid contact frame is the actual lid-shell Cube local +Z face:
`translation + scale / 2` on Z.

The passing candidate report,
`evidence/articulated_task_qualification_profile_r3_contact_arc_safety_candidate/report.json`
(SHA-256 `10b5c31f856b9258e832487abdbf08f38801cea6fb28d6ab5d7e249bcb1c54bf`),
is now packaged at
`evidence/articulation_runtime_qualification/report.json`.

Isaac Sim 4.1 passed all five profile-required gates: `lid_contact_cycle`,
`button_contact_cycle`, `button_reset_stability`, `rotor_reset_stability`, and
`socket_insertion_clearance`. The lid pair contact reached
`-0.07981422543525696` rad in the closed band, stayed within
`[-1.5556521049, 0.0]`, returned open at `-1.5554765462875366`, and recorded no
tube-lid contact. Drive integrity passed and `asset.usd` remained
`3573bb0eb474b80f842ea4d70dd2be2c2b5019a181d604bc1e17d4c7b7754926`.

## Promotion And Consumption

Final promotion passed with manifest SHA-256
`7948fff535514227b7e6cce636dc9be63145837bc783802b1f4ce63658233598`.
The receipt is at `evidence/articulation_runtime_qualification/promotion.json`.
It binds the profile and report without changing package USD, physics, drives,
or colliders.

`load_convert_asset_package_handoff(..., usage="articulated_object")` accepted
the final package and its required device profile, runtime report, and promotion
receipt.

## Verification And Scope

Scenario Forge:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q \
  tests/test_build_centrifuge_proxy_aligned_facade.py \
  tests/test_build_centrifuge_device_profile.py \
  tests/test_qualify_centrifuge_task_interactions.py
PYTHONDONTWRITEBYTECODE=1 python -B -m compileall -q \
  scripts/build_centrifuge_proxy_aligned_facade.py \
  scripts/build_centrifuge_device_profile.py \
  scripts/qualify_centrifuge_task_interactions.py
```

ConvertAsset:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q \
  tests/test_finalize_articulated_package.py
PYTHONDONTWRITEBYTECODE=1 python -B -m compileall -q \
  scripts/finalize_articulated_package.py
```

The Scenario Forge focused suite passed 14 tests, the ConvertAsset finalizer
suite passed 10 tests, and both `compileall` commands passed. The `ruff` command
was unavailable, so no Ruff result is claimed.

This evidence is limited to the specified package collider/contact and
articulated-state gates. It does not claim robot-policy success, benchmark
performance, real-world physical parity, or authorization to change the
`k=0.365` tube/rack scale.
