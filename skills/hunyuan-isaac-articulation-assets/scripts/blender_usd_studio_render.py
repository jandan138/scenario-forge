#!/usr/bin/env python3
"""Render denoised Blender Cycles `AgX` 4-view studio sheets directly from USD.

Promoted from `external_artifacts/out_of_domain_factory_r2_20261113/assets/_helpers/`
(local amendment 2026-11-13) with portable Blender binary discovery.

Imports the actual authored USD (`import_guide=False`, so guide colliders stay hidden
and only `Visual` CAD meshes, vector OLED/TFT emissive segments, silk-screen labels, and
glass panes are rendered) and produces 4 lossless studio views:
  1. `preview_iso.png`    — Hero 3/4 front-left open/interactive isometric studio view
  2. `preview_front.png`  — Front-right 3/4 view showing control panel & overall proportions
  3. `preview_detail.png` — Tight macro on functional cavity / pogo-pin nest / cassette / chute
  4. `preview_ui.png`     — Tight macro on glowing TFT/OLED/LCD display, encoder & tactile keys
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


def resolve_blender_bin(explicit: str | None = None) -> str:
    """Resolve the Blender executable from explicit arg, env, PATH, or known host paths."""
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    env_bin = os.environ.get("BLENDER_BIN")
    if env_bin:
        candidates.append(env_bin)
    which_bin = shutil.which("blender")
    if which_bin:
        candidates.append(which_bin)
    candidates.extend([
        "/cpfs/shared/simulation/zhuzihou/tools/blender-4.4.3-linux-x64/blender",
        "/usr/local/bin/blender",
    ])
    for cand in candidates:
        if cand and Path(cand).is_file():
            return cand
    raise FileNotFoundError(
        "Blender executable not found. Set BLENDER_BIN or ensure `blender` is on PATH."
    )


_BLENDER_INNER = r"""
import bpy
import json
import math
import mathutils
from pathlib import Path
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
cfg = json.loads(Path(argv[0]).read_text(encoding="utf-8"))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = int(cfg.get("samples", 160))
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPENIMAGEDENOISE"
scene.cycles.max_bounces = 8
scene.cycles.glossy_bounces = 4
scene.cycles.transmission_bounces = 8
scene.cycles.transparent_max_bounces = 8
scene.render.resolution_x = int(cfg.get("width", 1280))
scene.render.resolution_y = int(cfg.get("height", 960))
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.compression = 15

for vt in ("AgX", "Filmic", "Standard"):
    try:
        scene.view_settings.view_transform = vt
        break
    except Exception:
        continue
try:
    scene.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    pass

# Studio world environment
world = bpy.data.worlds.new("CADStudioWorld")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.14, 0.17, 0.21, 1.0)
    bg.inputs[1].default_value = 0.65

# Import the actual authored USD (`import_guide=False` skips Collision scope!)
bpy.ops.wm.usd_import(
    filepath=str(cfg["usd_path"]),
    import_guide=False,
    import_proxy=True,
    import_render=True,
    import_visible_only=True,
    set_material_blend=True,
)

# Upgrade imported UsdPreviewSurface materials so emissive & glass look crisp in Cycles
for mat in bpy.data.materials:
    if not mat.use_nodes or not mat.node_tree:
        continue
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            if "Emission Color" in node.inputs and "Emission Strength" in node.inputs:
                ec = node.inputs["Emission Color"].default_value
                lum = max(ec[0], ec[1], ec[2])
                if lum > 0.02 and node.inputs["Emission Strength"].default_value <= 1.05:
                    node.inputs["Emission Strength"].default_value = 2.8
            if "Alpha" in node.inputs and node.inputs["Alpha"].default_value < 0.95:
                alpha_v = node.inputs["Alpha"].default_value
                if "Transmission Weight" in node.inputs:
                    node.inputs["Transmission Weight"].default_value = max(0.55, 1.0 - alpha_v)
                    node.inputs["Alpha"].default_value = min(0.92, alpha_v + 0.35)

# Seamless curved studio cyclorama floor
bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0.0, 0.0, -0.0005))
floor = bpy.context.active_object
floor_mat = bpy.data.materials.new("StudioPedestal")
floor_mat.use_nodes = True
fbsdf = floor_mat.node_tree.nodes.get("Principled BSDF")
fbsdf.inputs["Base Color"].default_value = (0.18, 0.20, 0.24, 1.0)
fbsdf.inputs["Metallic"].default_value = 0.08
fbsdf.inputs["Roughness"].default_value = 0.42
floor.data.materials.append(floor_mat)

# 4-light industrial product photography rig
lights_spec = [
    ("KeySoftbox", (0.75, -0.95, 1.05), 32.0, 0.85, (1.0, 0.98, 0.95)),
    ("FillSoftbox", (-0.88, -0.65, 0.82), 18.0, 0.90, (0.90, 0.95, 1.0)),
    ("TopRim", (0.05, 0.55, 1.20), 24.0, 0.75, (0.96, 0.98, 1.0)),
    ("FrontAccent", (0.0, -1.15, 0.42), 8.5, 0.55, (1.0, 0.99, 0.97)),
]
for lname, loc, energy, sz, rgb in lights_spec:
    ldata = bpy.data.lights.new(name=lname, type="AREA")
    ldata.energy = energy
    ldata.size = sz
    ldata.color = rgb
    lobj = bpy.data.objects.new(name=lname, object_data=ldata)
    scene.collection.objects.link(lobj)
    lobj.location = loc
    direction = mathutils.Vector((0.0, 0.0, 0.14)) - mathutils.Vector(loc)
    lobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

cam_data = bpy.data.cameras.new("StudioCam")
cam_obj = bpy.data.objects.new("StudioCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

for view in cfg["views"]:
    cam_data.lens = float(view.get("lens_mm", 52.0))
    eye = mathutils.Vector(view["eye"])
    target = mathutils.Vector(view["target"])
    cam_obj.location = eye
    cam_obj.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(view["out_png"])
    bpy.ops.render.render(write_still=True)
    print("Rendered:", view["out_png"], flush=True)
"""


def render_usd_studio_views(
    *,
    usd_path: Path,
    out_dir: Path,
    views: list[dict[str, Any]],
    samples: int = 160,
    width: int = 1280,
    height: int = 960,
    blender_bin: str | None = None,
) -> list[Path]:
    resolved_bin = resolve_blender_bin(blender_bin)
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = out_dir / "_blender_studio_cfg.json"
    script_path = out_dir / "_blender_studio_runner.py"
    cfg = {
        "usd_path": str(usd_path.resolve()),
        "samples": samples,
        "width": width,
        "height": height,
        "views": views,
    }
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    script_path.write_text(_BLENDER_INNER, encoding="utf-8")
    proc = subprocess.run(
        [resolved_bin, "-b", "--factory-startup", "-P", str(script_path), "--", str(cfg_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout[-3000:] + "\n" + proc.stderr[-3000:] + "\n")
        raise RuntimeError(f"Blender studio render failed for {usd_path}")
    cfg_path.unlink(missing_ok=True)
    script_path.unlink(missing_ok=True)
    return [Path(v["out_png"]) for v in views]
