# Workbench table gray-top package consumption

Date: 2026-08-19

Scenario Forge now binds
`scientific_workbench_ebench_table_static_support` to ConvertAsset
`outputs/scientific_workbench_standard_table_20260819`. The 20260811 package
remains readable and was not rewritten.

The new package owns the table visual:

- `__aan_static_support_proxy` is authored invisible
- furniture `Body` is inactive
- tabletop is an opaque mid-gray `UsdPreviewSurface`

Glass evidence scenes no longer overlay Body, proxy visibility, or an
`EvidenceTableTop` material. Camera, lights, room, and object pose are
unchanged.

Published glass-guide stills were rendered against the previous table
appearance. Re-render those pages before republishing if the tabletop color
must match the new package.
