# Lab2Sim Figures 2–3 contract

Date: 2026-09-17 (revised after the Figure 2/3 visual audit)

## Paper story

Lab2Sim is the actor. It turns wet-lab evidence into asset specifications,
iterates USD candidates, and admits them through ConvertAsset. The laboratory
scenes are the visible results. The author confirms that the IKA OVEN 125 and
the traditional burette are two end-to-end agent traces; the remaining scenes
show the breadth of laboratories the compiler delivers.

## Figure 2

Core conclusion: the agent's downstream scene suite covers distinct laboratory
layouts and manipulation verbs beyond the four stations already in Figure 1.

Archetype: 2×2 hierarchical image plate at ICLR text width (5.5 in).

Panel template: 16:9 station view (about 70 % of the cell) + 4:3 task-object
inset + one verb phrase under the inset + `Isaac scene · <revision>` tag.
Top-row stations are eBench room cutaways (`room_corner_b`) so the two
laboratories read as different rooms with the Lift2 at the bench; bottom-row
stations are bench-level views.

Panels (all `current_delivery` in `configs/artifact_retention/current_task_heads.v1.json`):

- a. Stopper removal — eBench task05 r11, teaching-research room with Lift2.
- b. Glass-rod rack — eBench task07 r10.1, analytical-instrumentation room with Lift2.
- c. Stir-bar insertion — VR bench r5.
- d. Tube water bath — VR bench r1.

Rows are intentionally homogeneous: top row room-scale eBench packages, bottom
row liquid stations on the VR bench. Fehling, powder, titration, OVEN,
centrifuge candidates, and the duplicate burette workspace are excluded.

## Figure 3

Core conclusion: in the two end-to-end agent cases, the agent-written asset
specification carries task-critical physical features from manufacturer
evidence into admitted USD.

Archetype: two rows × three columns with identical grammar
`Manufacturer evidence → Agent-written contract → Admitted USD`.

- Row a, IKA OVEN 125: catalog open-door view (E02) → spec `ika-oven-125`
  (envelope, `door_hinge` revolute 0–180°, handle collider, shelves as
  placement surfaces) → Task 12 r2 admitted scene, camera-only retake matched
  to the catalog three-quarter viewpoint.
- Row b, burette stopcock: exploded PTFE stopcock (B-E03 panel of image3)
  → spec `titration-burette-and-stand` (tube 560 mm / Ø12 mm, `stopcock`
  revolute 0–90°, handle `grasp_region`, `mount_frame` to stand FixedJoint)
  → titration r1.7 close view of the graduated tube and stopcock. The row is
  titled `Burette stopcock` because both image panels centre on the joint.

Image panels share a 1.15:1 aspect. The contract card shows the spec slug plus
four verifiable fields only; spec and admission meta lines are 7.5 pt in
`#3F4855`. Arrows join evidence→contract and contract→USD
within a row and never across rows. Each USD row carries its ConvertAsset
promotion runtime in the row label; the render manifest, scene hash, and
promotion receipt hash are bound in `provenance.json`. The label is
`Agent-written contract`; no `FROZEN` badge is shown because no separate
immutable freeze artifact exists.

## Export and review

- Backend: Python/Matplotlib only (`compose_galleries.py`), laid out at
  physical size so paper type is 7–8.5 pt with no LaTeX height cap.
- Outputs: editable-text SVG, PDF, and 600 dpi PNG.
- Sources staged and hash-bound by `scripts/prepare_lab2sim_result_assets.py`
  (`source/fig23-assets.json`); crops and global brightness are recorded.
- Review standalone, grayscale, dense crops, and the final paper pages; an
  independent visible-only reviewer must leave no Critical or Major finding.
