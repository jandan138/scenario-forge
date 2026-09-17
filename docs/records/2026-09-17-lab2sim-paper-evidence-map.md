# Lab2Sim paper evidence map

Date: 2026-09-17.

## Scope

For the ICLR 2027 Lab2Sim draft, the author confirms that the IKA OVEN 125
(Task 12) and the traditional burette (titration) cases were produced end to
end by the Lab2Sim agent workflow—request, manufacturer evidence, agent-written
asset specification, generated articulated USD, ConvertAsset admission, and
the delivered scene—and that colleagues validated the outputs. The paper
writes these two cases as completed agent traces (Figure 3).

The remaining paper scenes (Fehling, powder, titration station, OVEN in
Figure 1; stopper removal, glass-rod rack, stir-bar insertion, tube water bath
in Figure 2) are reported as the compiler's delivered laboratories. The paper
reports qualitative system results and does not infer a success rate, robot
policy success, or physics accuracy from any figure.

## Repository bindings

### OVEN 125 (Figure 3a)

- Manufacturer evidence: `external_artifacts/asset_evidence/ika-oven-125/`
- Asset specification: `docs/design/asset-specs/ika-oven-125.md`
- Current scene delivery:
  `outputs/scientific_workbench_task12_oven_unload_dual_glassware_vr_r2_20260904/`
- Admission: `.../deps/oven/promotion_receipt.json` (`status: promoted`,
  formal runtime isaac41, isaac45 compatibility checked)
- Paper retake (camera only): `outputs/lab2sim_fig3_retake_20260917/oven_r2/`
  produced by `scripts/render_lab2sim_oven_retake.py`; same door-hinge command
  as the evidence renderer, exposure multiplier 1.08, no scene edits.

### Traditional burette (Figure 3b)

- Manufacturer evidence:
  `external_artifacts/asset_evidence/traditional-titration-burette-and-stand/`
- Asset specification:
  `docs/design/asset-specs/traditional-titration-burette-and-stand.md`
- Current scene delivery:
  `outputs/scientific_workbench_traditional_acid_base_titration_vr_r1_7_20260908/`
- Admission: `.../deps/titration_assets/promotion_receipt.json`
  (`status: promoted`, runtime Isaac Sim 4.5)

### Figure 2 laboratories

All four are `current_delivery` heads in
`configs/artifact_retention/current_task_heads.v1.json`:

- `task05_remove_ground_glass_stopper` r11 —
  `outputs/scientific_workbench_task05_task09_r11_20260817/packages/task05/`
- `task07_glass_rod_to_rack` r10.1 —
  `outputs/scientific_workbench_tasks_02_07_08_r10_1_20260817/packages/task07/analytical_instrumentation/`
- `insert_stir_bar_into_beaker` r5 —
  `outputs/scientific_workbench_insert_stir_bar_into_beaker_vr_r5_20260825/vr/`
- `water_bath_heat_tube` r1 —
  `outputs/scientific_workbench_water_bath_tube_heat_vr_r1_20260902/vr/`

### Figure sources and hashes

Staging: `scripts/prepare_lab2sim_fig1_assets.py` (Figure 1) and
`scripts/prepare_lab2sim_result_assets.py` (Figures 2–3 and appendix). Source
and derived hashes, crops, global brightness, render manifests, scene hashes,
and promotion receipts are recorded in
`paper/venues/iclr2027/figures/lab2sim/provenance.json`. Raw simulator frames
remain outside git under the artifact policy.

## Claim boundary

- "End to end" is claimed only for the OVEN 125 and burette traces and rests
  on the author's confirmation plus the linked specification, delivery, and
  promotion artifacts. The middle column of Figure 3 is labelled
  `Agent-written contract`; no separately signed freeze artifact is claimed.
- The Figure 2 gallery establishes delivered, admitted laboratory scenes and
  visible task object state only.
- Historical dated records are not rewritten by this map.

No general scene-authoring rule changes. This record maps paper claims to
existing evidence and does not change package, USD, adapter, or runtime
behavior.
