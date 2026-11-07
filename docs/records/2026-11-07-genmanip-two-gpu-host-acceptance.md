# Independent two-GPU host acceptance — 2026-11-07

The user chose to add 10.150.170.198 as an independent two-card host, not replace either historical four-card machine. After the user appended the control host's public key in the platform terminal, SSH login succeeded. The control-host alias `genmanip-2gpu` was added; the existing SSH config was backed up and the `dsw-4090` entry was preserved.

Observed host: dsw-536365-6d7df697d5-kvttx, two RTX 4090 devices with 46,068 MiB each, driver 570.153.02, 28 CPUs and approximately 200 GiB RAM. Shared EFC project/data mounts and the existing Isaac 4.1 installation are available. No environments or dataset assets were copied, no package installation was performed, and no model service was configured. The client is explicitly routed to the verified shared source because the default import points to /root/GenManip-Sim.

## Verified behavior

Both physical GPUs independently passed a SimulationApp/World clock probe. Actual World.current_time advanced from approximately 0.025 to 1.025 seconds; this is measured simulation time, not an assertion that 60 API calls equal 60 physics ticks. NVML process observations bind each probe to its intended UUID.

Native GenManip checks used ordinary pouring on GPU 0 (20-step hold) and liquid titration on GPU 1 (320-step hold), first separately and then concurrently. All four runs completed, with finite state checks, matching configuration/metadata/scene hashes, and no matches for the audited fatal-error patterns in retained server/client/worker logs. Worker PIDs were mapped to the intended physical GPU UUIDs. 54 five-second samples observed both parallel workers occupying their intended cards; this establishes overlapping jobs, not a throughput benchmark or identical physics-step timestamps.

All 32 initial/after-hold four-camera images decode and were visually reviewed by the implementing assistant. No blocking black frames, yellow-grid materials or missing task assets were identified. Glass glare and fixed-camera framing remain limitations. This is not independent review, full task success, VLA serving or training qualification.

Observed parallel worker environments carry CUDA masks 0/1, different Omni config/cache/data/log paths and different local texture cache paths. Their respective omniverse.toml files declare distinct global Omni cache roots. Ports and run IDs are unique. The launcher allocates 12 Ray CPUs per lane, OMP/MKL threads 8 and object-store proportion 0.04 per independent cluster.

## Evidence and maintenance

Evidence root: `/cpfs/user/zhuzihou/dev/scenario-forge/external_artifacts/genmanip_2gpu_host_20261107`. It contains host_inventory.json, clock_gpu0/1.json, acceptance_status.json, audit.json, selected worker environment records, GPU occupancy samples, receipts, logs and four image sheets. The runbook is [GenManip two-GPU host](../operations/genmanip-two-gpu-host.md).

Existing datasets, metrics, receiver Git branch and other hosts' jobs were not changed. Applicable VAL-001–004 evidence boundaries were followed; no scene schema/API or general standard changed. Documentation and the task-local evidence are synchronized in this change.
