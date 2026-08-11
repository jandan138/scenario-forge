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

Release records can declare:

- `release_status: canonical_candidate | prototype`;
- `score_ceiling` between 0 and 1;
- `missing_capabilities` as an explicit list.

The page presents evidence-first task cards, tier/status filters, and a compact
18-row coverage matrix in Feishu order. Multiple immutable background packages
remain available from each card's variant disclosure. The publisher copies
every referenced release overview, not only the current candidate image, so all
reviewed variants remain inspectable after deployment.

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

## Asset-expansion batch

The 2026-08-10 asset-expansion batch is generated with:

```bash
PYTHONPATH=src python scripts/generate_scientific_workbench_asset_expansion.py \
  --out outputs/scientific_workbench_asset_expansion_YYYYMMDD
```

The default runtime lane is the EOS-managed Isaac Sim 4.1 + GenManip Python.
The generator adds the existing CuRobo source tree to `PYTHONPATH` through the
preview adapter's `runtime_python_paths`; it does not install a new environment
or modify GenManip. Use `--static-only` for package-contract tests that must not
launch Isaac Sim.

Each generated package contains the canonical Scenario Forge package plus
eBench/GenManip and VR adapter exports. Static and static-support objects are
preloaded package-first with GenManip's generic collider and rigid-body switches
disabled. This preserves ConvertAsset-owned support collision and keeps visual
fixtures nonphysical without adding object-specific adapter patches.

The same task objects, table, robot, world poses, and PhysX profile are exported
to eBench and VR. A non-pour task is represented in VR by one dependency role
per task object under `deps/objects/<object-id>/`; the legacy two-vessel pour
layout retains `source_container` and `target_container` paths for compatibility.

## USD + config review handoff

After the reviewed adapter exports exist, build the two colleague-facing ZIPs:

```bash
PYTHONPATH=src python scripts/export_scientific_workbench_usd_handoff.py \
  --out outputs/scientific_workbench_usd_handoff_20260811
```

Task 1 is emitted in a separate bimanual-pour archive. Tasks 2, 4, 5, 7, 8,
13, 14, 15, and 16 are emitted in the regular archive. Every task directory
contains `scene.usd`, `task_config.py`, `parity_manifest.json`, and the exact
package-relative `deps/` closure. Open `scene.usd` directly in Isaac Sim 4.1;
keep `deps/` beside it. These review archives deliberately omit the robot model
and do not claim task or benchmark success.
