# Build the Scientific Workbench Task Directory

Build the Feishu-derived queue, ConvertAsset request, and static directory:

```bash
PYTHONPATH=src python scripts/build_scientific_workbench_task_directory.py \
  --out outputs/scientific_workbench_coverage_factory_YYYYMMDD
```

Inputs are declared in
`configs/task_coverage/scientific_workbench_coverage_factory.yaml`. The script
resolves each source binding before queueing a task, so an inventory label alone
cannot claim an unavailable package is ready.

The output contains:

```text
coverage_plan.yaml
convertasset_admission_request.yaml
directory/
  task_directory.yaml
  index.md
  index.html
```

The page displays both the newest immutable **current candidate** and the
separately-qualified `latest` package. A candidate stays visible with its
render/reset evidence while any required promotion gate is still `not_run` or
blocked; only an all-pass release becomes `latest`.

Give ConvertAsset the generated admission request. It must return source-bound
packages and manifests; Scenario Forge must not add a task-specific collider,
mass, inertia, scale, or PhysX workaround.

Every compiled scientific-workbench package writes an external IK request at:

```text
adapters/ebench/genmanip/provisional_ik_preflight/request.yaml
```

The GenManip/CuRobo owner should solve the listed candidates without base motion
and provide `ebench-provisional-ik-result/v0.1`. Scenario Forge validates it with
`validate_provisional_ik_result()` and writes:

```text
evidence/provisional_ik_preflight.yaml
```

That evidence is only a fixed-base IK result. It does not authorize claims about
approach collisions, grasp/lift, task execution, liquid transfer, or benchmark
success.
