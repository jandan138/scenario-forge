# 2026-08-01 Scientific Workbench v4 Candidate Evidence

## Decision

The three asset-ready Feishu Task Design rows are rebuilt as immutable v4
candidates. They replace v3 in the coverage directory but v3 artifacts remain
unchanged for provenance.

## Completed Evidence

For each of the following packages:

1. `scientific_workbench_pour_cylinder_to_beaker.v4_20260801_r1`;
2. `scientific_workbench_funnel_pour_cylinder_to_flask.v4_20260801_r1`;
3. `scientific_workbench_two_sample_mix.v4_20260801_r1`.

Scenario Forge records passing package closure, native GenManip post-reset
render, tabletop placement, and initial-scene visual-review gates. The closure
audit starts at `scene/main.usda` and follows reachable USD/MDL references, so
a retained full-source provenance copy cannot falsely fail a package that
actually consumes a scoped, package-local asset layer.

The v4 1920×1080 review images visibly show the Code-as-Room background,
eBench Lift2 robot, workbench, and task objects. The reviewed vessels are
identifiable but their transparent material remains visually darker than
physical glass under the selected lighting; this is recorded as a visual
limitation, not concealed as photorealism.

## Remaining Gate

Every v4 package has an exact fixed-base top-down IK request at
`adapters/ebench/genmanip/provisional_ik_preflight/request.yaml`. The inspected
GenManip checkout provides lower-level CuRobo planners but no standard command
that accepts this request schema and produces the required result schema.
Therefore the three packages remain `candidate`, with provisional IK marked
`not_run`.

When GenManip/CuRobo supplies a digest-bound
`ebench-provisional-ik-result/v0.1`, Scenario Forge validates it with
`scripts/ingest_provisional_ik_result.py`; rebuilding the directory then
promotes the corresponding immutable v4 package automatically if all five
gates pass.

## Claim Boundary

Passing the four completed gates establishes a self-contained rendered initial
package and a compliant authored tabletop layout. It does not establish actual
IK feasibility, collision-free approach, grasp closure, lift, dual-arm
coordination, liquid transfer, policy success, or benchmark success.
