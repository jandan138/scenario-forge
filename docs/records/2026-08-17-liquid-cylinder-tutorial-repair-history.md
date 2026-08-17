# Liquid-cylinder tutorial repair history

Date: 2026-08-17

## Outcome

The public Task 02 r8.7 liquid-cylinder tutorial now explains the graduated-cylinder
collision repair as a five-stage engineering history instead of presenting only the
final collider. The new section is available at
`docs/liquid-cylinder-tutorial/#repair-history`.

The page keeps the original visual language and media bundle. No new binary media or
private filesystem references were added.

## Evidence represented on the page

The history distinguishes:

1. the original open visual shell;
2. the r8.1 visible-partition no-go;
3. the r8.2 dual-rim closed-manifold no-go;
4. revocation of the old `simulationPoints` readback conclusion; and
5. the final 0812-topology warp with a single hidden, closed collision mesh.

The tutorial explicitly separates topology closure, GPU cooking, live static liquid
retention, loaded-start alignment, and scripted robot execution. It does not claim a
learned-policy result, an active liquid metric, or a benchmark pass.

## Teaching and UI changes

- Added the stable `repair-history` anchor and navigation entry.
- Added a responsive five-stage timeline with exact geometry and runtime facts.
- Added an 0812 beaker versus source graduated-cylinder topology comparison.
- Corrected the label `内腔杯口` to `杯口高度`.
- Added three evidence gates: collision container, loaded initial state, and robot
  execution.
- Added a four-branch failure-routing table so geometry, initial-state, and control
  failures are not repaired in the wrong layer.

## Verification

- Focused tutorial tests: 3 passed.
- Repository `make check`: 679 tests passed; Ruff, package smoke, Phase 10.x strict
  smoke, and `git diff --check` passed.
- Chromium visual audit:
  - 1440 x 1000 desktop;
  - 900 x 1100 tablet;
  - 390 x 844 mobile.
- Browser audit found no horizontal overflow, broken images, video errors, failed
  network requests, or console/runtime errors.
- The collider layer toggle changed its `aria-pressed` state and SVG opacity and then
  restored correctly. Keyboard focus was visible, and reduced-motion mode changed
  smooth scrolling to `auto`.
