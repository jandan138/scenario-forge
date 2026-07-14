# 2026-07-14 DryingBox_03 Source-Bound Package Integration

## Outcome

The golden `scientific_workbench_bimanual_pour` scenario now consumes the
ConvertAsset-owned dynamic `DryingBox_03` package and its manifest. The raw
LabUtopia `lab_001.usd` remains unchanged. Scenario Forge composes the copied
package as a strong scene overlay and does not author mass, diagonal inertia,
center of mass, principal axes, `PhysicsMassAPI`, or a warning suppressor.

This is a source-bound `provisional_geometry` integration. It is not evidence of
measured, BOM-derived, CAD-derived, or calibrated real-world physics.

## Input identity

| Item | Identity |
| --- | --- |
| Scenario Forge base revision | `8fd0a70e87f21f34098b3767496abf55e7d01ca9` plus this working-tree change |
| ConvertAsset delivery revision | `324ce6e6d4395ccfda1e59e5ae89de9389cdf225` |
| Producer manifest SHA-256 | `be988683935c2e107335fff3cbe4b562aee186a0c076d7445a2b907f07412dc9` |
| Raw LabUtopia source SHA-256 | `b3861b5a17945abe401062a04125969c3a63b0f8a0a5ce0026a461dbdfc935f2` |
| ConvertAsset root USD SHA-256 | `e217cc8857430429648eebd051061a7f2c20bfd94cf43148867327845b73c1cc` |
| Physics profile SHA-256 | `37b1024418fbcfcf3c3148cce9daf96437d0b3cf157f0c4a0a6b4723b24b8940` |
| Producer quality tier | `provisional_geometry` |
| Producer package scope | `/World/DryingBox_03` |

The external manifest and `package/evidence/manifest.json` were byte-identical.
The inbound adapter also checked the source/root/profile hashes, source integrity,
consumer/runtime profiles, scope mapping, profile admission, and producer runtime
warning gate before replacing the output directory. The generated runtime closure
keeps `deps/`, `physics/`, and `overlays/`; producer logs, renders, and the raw
`evidence/` directory are not copied into the portable package.

## Composition evidence

The static package was generated under a fresh `/tmp` scratch root. Its relevant
hashes were:

| Artifact | SHA-256 |
| --- | --- |
| Portable `scene/main.usda` | `74aa32c9324c7bed744b86880f8207cdc7cf0f713df88debef553930847a30f9` |
| GenManip `scene.usda` | `19a24e880460e80a2d7264d64503cb60f20c9c78ef453b469a6dff5bf4da0b30` |
| Scenario Forge provenance summary | `3891946e8c44fb52baa93e30754db3998b27c6ea63707c3244ebaa6c8208333f` |
| GenManip package manifest | `f7f807b0ad58b89bbb7e197fae28958dcd08bf8af90b1fd679f0b2056bfbfc05` |

OpenUSD property-stack inspection found one active DB03 in each final stage. For
the door rigid body, `physics:mass`, `physics:diagonalInertia`,
`physics:centerOfMass`, and `physics:principalAxes` all resolve first to the copied
ConvertAsset `overlays/physics_profile.usda`. Neither Scenario Forge-generated
scene layer contains those fields.

## Final GenManip runtime evidence

The final collected package was initialized and reset with the existing EOS
Isaac Sim 4.1 environment and GenManip revision
`6ff55ed7c7bd441825d56f1016a30e03b524ebea`. The render manifest records Isaac
Sim `4.1.0.0`, Lift2 injection, zero actions, and 50 warmup steps.

ConvertAsset's own `aan06.physx_scope.v3` parser was then applied to the final
GenManip runtime log with the explicit mapping:

```text
/World/DryingBox_03
  -> /World/scientific_workbench_bimanual_pour/room/DryingBox_03
```

The gate passed with:

- `scoped_event_count: 0`;
- `unattributed_event_count: 0`;
- `out_of_scope_event_count: 3`.

The three out-of-scope events belong to Lift2 `dummy_base_rotate`,
`dummy_base_x`, and `dummy_base_y`. Each carries the parsed invalid-inertia,
negative-mass, and small-sphere-fallback categories. Therefore the supported
claim is **DB03-scoped mass/inertia warnings are zero**; the whole task scene is
not warning-free.

| Runtime artifact | SHA-256 |
| --- | --- |
| Runtime log | `6409c78130128cf8b6b6ab2db43f89b93757456f501fac96dbfb698e197fd836` |
| Workspace close-up | `9a9155768fa35863c8e7cd0c98b8f2d80e63b0eab41d9669e433fb5b44ae6de3` |
| Scene overview | `aec87c6e9c64efd8fbe7aa7a6e6ce93bbaa3995a4a4e6235781fb6c4f1a1ac9d` |
| Render manifest | `4155448be4c1d7a2aa19254ac5e8a0bd81402c53730a44a17bc11557e6c22bd9` |
| Visual-ready gate | `192ac6578320bedc0b4f236006586fc6255a197a191d7c53c76725906cb86dbb` |

The structural render gate passed both views. A separate clean-room visual review
rated the workspace close-up `PASS` and the scene overview `WARN`: the flask,
cylinder, robot, task surface, and exactly one drying box are visible without an
obvious pink/black material fallback or broken geometry, but the overview devotes
too much of the frame to the tabletop and partly obscures the drying box. A future
camera-only improvement should use a higher, slightly farther-back overview aimed
toward the rear work area. This framing warning does not change the USD composition
or DB03 scoped-physics result.

## Verification and replacement contract

`make check` passed with 250 tests, Ruff, package smoke, strict Phase 10.x smoke,
and `git diff --check`. Generated USD trees, images, and logs remain under scratch
storage and are not committed.

A future measured or approved ConvertAsset profile is consumed by replacing the
external package/manifest/revision inputs. Scenario Forge should not gain a local
DryingBox physics patch when that replacement happens.
