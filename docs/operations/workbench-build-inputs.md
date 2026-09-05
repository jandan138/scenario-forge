# Workbench build inputs

Current workbench generation reads the explicitly selected, hash-locked inputs
in `configs/build_inputs/scientific_workbench.v1.json`. These operational bindings
are local build inputs, not portable package identities.

The retained inputs total 489,614,946 bytes. They contain the required base USD
closure and authoring configuration, the rod/rack fixture, robot adapter metadata,
the shared environment closure, oven layout, and stirrer layout. The migration
uses a positive file list, excludes handoff directories and preview collections,
and records source paths, included subtrees, byte counts and SHA-256 tree hashes.
Source asset dependencies inside the selected closures remain intact.

Task02 now composes the producer's four dynamic-loaded initial states, the
web-standard glass assets and the rod/rack fixture through transformations in
one fresh output directory. It does not read stored r9/r10/r10.2 task packages.
Older transformation functions remain shared implementation code. Explicit
`--source-root` arguments are supported for historical reproduction.

```bash
PYTHONPATH=.:src \
  /cpfs/user/zhuzihou/conda-managed/envs/embodied-eval-os-py310/bin/python \
  -m scripts.build_task02_current --fill all --out /tmp/task02-rebuild
```

The output must be new. The existing delivered USD and ZIP files are not
rewritten. A rebuilt package has pending/unvalidated runtime claims until
independent evidence is attached; historical robot or benchmark success is
not inherited merely because reconstruction matches.

The oven and stirrer builders use dedicated layout inputs. Task11 and robot
bundle builders use the environment or small adapter-metadata input instead of
copying a historical Task02 package. Input hashes are checked when these
registered inputs are used; caller-supplied test fixtures remain supported.

`freeze_workbench_build_inputs.py` is a one-time migration command that requires
the historical inputs to be restored. Normal builds do not run that migration.
Older release-only render/finalization commands may require an OSS restore;
their output-directory names in code are not active build dependencies.

Verification compares composed prim sets, types, applied schema membership,
attribute values, material/texture content hashes, connections and relationship
targets. Identical assets can have different relative path spellings after
materialization. The current colleague-collision recipe also explicitly retains
the delivered collision APIs and disabled legacy unified proxies after flattening.
