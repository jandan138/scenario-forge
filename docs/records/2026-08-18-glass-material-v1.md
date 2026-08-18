# Glass material v1 asset handoff and visual guide

Four source-bound ConvertAsset `_glass_v1` packages were consumed without reimplementing USD/MDL conversion. Scenario Forge produced a unified asset handoff ZIP and a fixed-camera visual guide.

- Assets: 250 mL graduated cylinder, 325 mL beaker, 250 mL 29/42 flat-bottom flask, dynamic beaker.
- Excluded: glass rod and stopper. The flask ground joint remains frosted.
- Runtime evidence: Isaac Sim 4.1, modern wet chemistry room, standard 2000×800×755 mm table.
- Preservation: package physics and interaction profiles are byte-identical to pre-change inputs; visual overlays contain no geometry or physics authoring.
- Task boundary: no existing eBench or VR task package was upgraded.

The page media is hash-locked in `docs/glass-material-guide/assets/provenance.json`. The authoritative package evidence remains in ConvertAsset; the Scenario Forge ZIP is a consumer handoff, not a second conversion authority.

## Visual QA

The eight source renders were inspected locally as four fixed-pose pairs; this was a local review, not an independent reviewer. The published page was then opened in real Chromium at 1440×1000, 1024×768, and 390×844. Full-page captures showed no broken media, horizontal overflow, clipped sections, or mobile layout failure. The draggable split was exercised after synchronizing the overlay image to the rendered stage width.
