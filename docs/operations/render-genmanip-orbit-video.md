# Render a GenManip orbit video

`scripts/ebench/render_genmanip_orbit_video.py` produces a standalone room
orbit from an already collected eBench/GenManip package. It restores the same
post-reset, pre-action state used by the package's initial-scene evidence,
freezes physics, and moves only a temporary camera.

Run the script inside the approved Isaac Sim 4.1 + GenManip environment:

```bash
python scripts/ebench/render_genmanip_orbit_video.py \
  --collected-root /absolute/path/to/package/adapters/ebench/genmanip \
  --genmanip-root /absolute/path/to/GenManip \
  --output-dir /absolute/path/to/video-output
```

The output contains a silent H.264 MP4, `video_manifest.json`, and the ffmpeg
log. The default camera path is 12 seconds at 1920x1080 and 30 fps: it starts
from the package's reviewed `scene_overview` camera, transitions to a safe
indoor orbit, turns 220 degrees, and finishes with a short hold. Intermediate
PNG frames are removed unless `--keep-frames` is requested.

This artifact is presentation evidence only. It does not claim task success,
policy success, physics fidelity, or successful liquid transfer, and it does
not modify the source task package.
