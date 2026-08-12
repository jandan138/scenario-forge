# Dynamic tabletop dressing

Scientific-workbench packages may add deterministic, physically present
`context_prop` objects to make the table read as a working environment without
changing the task contract.

- One fixed preset is assigned to each background and is reused unchanged by
  every task in that room.
- A preset contains four to six visible groups and at most ten dynamic rigid
  bodies.
- The standard table is 2.0 × 0.8 × 0.755 m. Context centers stay inside the
  0.10 m edge margin, prefer the far half (`y >= 0.10 m`), and stay outside the
  central task keep-out (`x [-0.38, 0.38]`, `y [-0.30, 0.20]`).
- Stacking is forbidden except for declared rack/support relations.
- Context assets are producer-qualified dynamics. Scenario Forge does not add
  colliders, rigid bodies, mass, or simulator-warning suppression.
- Context props are absent from task steps, success predicates, metrics and VR
  `obj_prim_list`. Their metadata records `dressing_preset_id`, `group_id`, and
  `metric_participation: none`.

The checked-in presets live at
`configs/dressing_presets/scientific_workbench_v1.yaml`. They are deterministic
generation inputs, not runtime randomization.
