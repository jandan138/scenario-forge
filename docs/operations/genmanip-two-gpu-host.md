# GenManip independent two-GPU host

Host: `root@10.150.170.198:22`, hostname `dsw-536365-6d7df697d5-kvttx`.
Control-host SSH alias: `ssh genmanip-2gpu`. This is a new resource; the existing `dsw-4090` entry is unchanged.

## Environment and data

- Two NVIDIA GeForce RTX 4090 devices, 46,068 MiB each; driver 570.153.02.
- 28 CPUs and approximately 200 GiB RAM.
- Isaac Sim 4.1 at `/isaac-sim/python.sh`; Python 3.10.14, torch 2.2.2+cu118, Ray 2.48.0, FastAPI 0.110.0.
- `/cpfs/user/zhuzihou`, `/cpfs/shared/simulation` and `/mnt/data` are shared EFC mounts. No project data or conda environment copy is needed.
- GenManip receiver: `/mnt/data/chenjiantong/GenManip-Sim`. This is a shared worktree: changing its files/branch affects other hosts. Use isolated worktrees for development.
- Client interpreter: `/root/miniconda3/envs/client/bin/python`. Explicitly prepend `/mnt/data/zhuzihou/GenManip-Sim/standalone_tools/packages/genmanip_client/src` to PYTHONPATH; the image's default import resolves to `/root/GenManip-Sim` instead.
- `ffmpeg`, `ffprobe` and `rsync` exist under `/usr/bin`; tmux is absent and is not required by the task launcher. Do not install packages into Isaac's default interpreter or copy conda prefixes.

## Two-lane execution

| Physical GPU | UUID |
| --- | --- |
| 0 | `GPU-a053a144-3915-a050-4456-25045cb069a5` |
| 1 | `GPU-bc44fb01-b6fa-60ed-64be-2857b933ffad` |

Use one Isaac worker per physical card, at most two at once. Initial allocation is 12 Ray CPUs per lane, OMP/MKL threads 8, object-store proportion 0.04 per independent Ray cluster. Check current availability before launching; do not stop unrelated processes.

Pin CUDA visibility to the selected numeric physical index. The existing GenManip worker derives renderer `active_gpu` from that index and uses `physics_gpu=0` within the visible CUDA space, with multi-GPU rendering disabled. Verify actual worker GPU UUIDs rather than relying only on environment strings.

Each lane requires its own run ID, bind-checked port, output directory, Ray temp directory and Kit/Omni/texture caches. The qualified task-local launcher uses `/tmp/dnsmoke/<run-id-hash>/`; its `omni_config/omniverse.toml` declares the global Omni cache, and the worker receives the corresponding `texture_cache` path. Failed attempts must use fresh run IDs. Long jobs need durable process supervision and explicit completion/error handoff; a configured SSH alias alone does not provide that.

## Qualification evidence

Evidence and task-local launchers: `/cpfs/user/zhuzihou/dev/scenario-forge/external_artifacts/genmanip_2gpu_host_20261107`.

The clock probes measure actual `World.current_time` before/after stepping and bind each process to its expected physical UUID. Native checks cover ordinary pouring on GPU 0 and liquid titration on GPU 1, first separately and then concurrently. `acceptance_status.json`, `audit.json`, GPU samples and image review record the actual outcome. The admission is limited to these GenManip/Isaac paths; it does not certify model serving or training workloads, arbitrary trajectories or policy success.

Acceptance on 2026-11-07: both clock probes and all four native runs passed; 32 camera images reviewed; intended physical UUIDs confirmed; overlapping parallel GPU occupancy observed. See [dated acceptance record](../records/2026-11-07-genmanip-two-gpu-host-acceptance.md). Ready for up to two isolated GenManip/Isaac workers within this verified scope.
