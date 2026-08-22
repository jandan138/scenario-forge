# 2026-08-23 VR object materialization and transform correction

The earlier VR object-root rule conflated two independent concerns. The actual
downstream incompatibility was not the location of `obj_plate`: all four Task 02
variants already used the same root path. The incompatibility was composition.
One scene authored the complete plate subtree inline while other scenes authored
only its transform and supplied geometry, materials and collision through a
payload. A consumer that omitted `deps/` therefore received an empty root.

Future VR exports materialize every tabletop `obj_*` subtree into the ASCII
`scene.usd`. The exporter preserves the composed transform and rejects retained
composition arcs or non-transform drift. It no longer requires complete root
translate/orient/scale operations or equality with `scenario.yaml`; internal
visual and articulation transforms remain producer-owned.

`object_materialization.json` replaces `transform_ownership.json`. Multi-variant
Task 02 generation additionally requires identical structure and non-transform
content fingerprints for every object. Transform opinions, including an extra
internal visual correction in one variant, are deliberately excluded from the
cross-variant comparison. Existing r10.3 unvalidated outputs are historical and
are not rewritten. eBench continues to consume source-bound packages and USD
composition arcs.
