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
release_status.yaml
directory/
  task_directory.yaml
  index.md
  index.html
```

`release_status.yaml` is refreshed from evidence inside each package every time
the command runs. The page displays both the newest immutable **current
candidate** and the separately-qualified `latest` package. A candidate stays
visible while any required promotion gate is still `not_run` or failed; only an
all-pass release becomes `latest`.

## Publish the reviewed directory

The repository's GitHub Pages source is `main:/docs`. After building the
directory, publish its HTML and candidate overview images into that source:

```bash
PYTHONPATH=src python scripts/publish_scientific_workbench_task_directory.py \
  --source outputs/scientific_workbench_coverage_factory_YYYYMMDD/directory \
  --out docs/task-directory
```

Commit the resulting `docs/task-directory/` files. GitHub Pages then serves the
directory at `/scenario-forge/task-directory/`. The publisher only copies the
reviewed overview images displayed by the page; portable packages and USD
assets remain outside the public site.

Give ConvertAsset the generated admission request. It must return source-bound
packages and manifests; Scenario Forge must not add a task-specific collider,
mass, inertia, scale, or PhysX workaround.

Every compiled scientific-workbench package writes an external IK request at:

```text
adapters/ebench/genmanip/provisional_ik_preflight/request.yaml
```

The GenManip/CuRobo owner should solve the listed candidates without base motion
and provide `ebench-provisional-ik-result/v0.1`. Ingest one returned result with:

```bash
PYTHONPATH=src python scripts/ingest_provisional_ik_result.py \
  --package outputs/<package-id> \
  --result /path/from-genmanip/result.yaml
```

The command verifies the result binds the exact request digest, requires all
declared task objects to have a passing candidate, and writes:

```text
evidence/provisional_ik_preflight.yaml
```

Re-run the directory builder afterwards; it promotes the immutable package to
`latest` automatically only when this and the other four gates all pass. That
evidence is only a fixed-base IK result. It does not authorize claims about
approach collisions, grasp/lift, task execution, liquid transfer, or benchmark
success.
