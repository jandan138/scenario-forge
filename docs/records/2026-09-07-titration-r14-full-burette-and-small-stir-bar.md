# Titration VR r1.4: full burette visuals and smaller stir bar

## Change and ownership

r1.3 is retained. r1.4 consumes ConvertAsset's source-bound
`traditional_titration_station_r3` (`afbda7f`) rather than adding local device
geometry patches. The producer owns lower-charge geometry, water material,
initial visibility, concave meniscus and the small column-height compensation.
Scenario Forge owns scene integration, receiver bindings and the visual stir bar.

The new bar has a 15 mm straight capsule section and 2.5 mm radius: total
length including caps is **20 mm**, diameter **5 mm**. Its center follows the
measured inner floor plus radius plus 0.15 mm clearance. It is still a visual
animation, not a new graspable rigid object.

## Liquid semantics

- Metered column remains 25 mL over 320 mm, bottom fixed at the final mark.
- Straight lower glass, valve connection, outlet and tip receive a fitted
  continuous visual core. Lower precharge does not add to the metered 25 mL.
- Full liquid is visible before Run. During the episode only the upper level
  descends; end-of-scale keeps lower precharge. Reset restores full visibility.
- No whole-device drainage, falling drops, PBD or chemistry solver is added.
- Receiver r1.3 fitted geometry/materials and pink endpoint behavior are retained.
- Existing object/link/config paths, articulation, contacts, masses and layout
  remain unchanged. A 52-physical-prim comparison is identical to r1.3.

## Verification

The producer has three standalone Isaac 4.5 passes on its exact asset SHA.
The task uses three fresh Isaac 4.5 scene runs with prescribed device joint
positions: initial-before-Run, running initial, mid-scale, end-scale, and reset
are checked numerically. Success is checked before the deliberate overshoot
and end-scale extension; material reset remains a separate gate.

The scene SHA tested is
`0c8ae14dba864a7d447fb1193fb60a28fa3e5cee1349fa9a88d4a17129668e80`.
Only reports with this SHA can finalize the task. Producer evidence is copied
without changing the scene or asset bytes. Candidate scratch reports do not
enter the delivery.

1920×1080 Isaac 4.5 renders cover full burette, lower connection, meniscus,
flask and overview at full/mid/end scale. These are clearly labeled visual
snapshots, not robot recordings. Local visual review accepts them with a
near-clear-liquid contrast caveat; the original dark room reflections remain.

`make check` covers tests, Ruff, package and phase10x smoke. Focused tests cover
capsule overall length and liquid state checks. ZIP dependency closure, CRC
and SHA are required for finalization. No robot-policy success is claimed.

## Delivery

Output root:
`outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_4_20260907/`

Handoff ZIP: `handoff/scientific_workbench_traditional_acid_base_titration_vr_r1_4.zip`.
Open `scene.usd` inside the extracted folder using Isaac Sim 4.5 and allow its
script nodes. Keep `deps/` and `task_config.py` together with the scene.

Evidence includes `scene_overview.png`, `stir_bar_before_after.png`, burette
views, three runtime reports and physical/closure audits. Current task heads
advance to r1.4 only after the ZIP is finalized. No old outputs are archived
or deleted by this revision.

Final result: three scene cold starts passed, dependency closure has no missing
or external resources, ZIP CRC passed, and `make check` passed with 922 tests
and 1 skip. ConvertAsset's two focused tests and new-file Ruff checks passed.
