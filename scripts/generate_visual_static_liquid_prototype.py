#!/usr/bin/env python3
"""Build a standalone visual-only colored-liquid vessel prototype.

This is an experimental generation-plan producer.  It composes already admitted
container/environment packages and authors only low-poly visual geometry.  It does
not alter producer assets or add task, metric, or simulator-runner behavior.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any, Mapping, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "scenario-forge-visual-static-liquid-prototype/v0.1"
DEFAULT_CONFIG = REPO_ROOT / "configs/prototypes/visual_static_liquid_v1.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "outputs/visual_static_liquid_prototype_20260816"
DEFAULT_ISAAC_PYTHON = Path(
    "/cpfs/shared/simulation/zhuzihou/dev/conda-managed/envs/"
    "embodied-eval-os-sim-isaacsim41-genmanip-py310/bin/python"
)
DEFAULT_RENDERER = REPO_ROOT / "scripts/ebench/render_visual_static_liquid_prototype.py"
USD_REFERENCE_RE = re.compile(r"@([^@]+)@")


def height_for_volume_fraction(
    axial_profile_m: Sequence[Sequence[float]], fill_fraction: float
) -> float:
    """Return the absolute liquid height for a piecewise-linear radius profile."""

    profile = _validated_profile(axial_profile_m)
    fraction = float(fill_fraction)
    if not 0.0 < fraction < 1.0:
        raise ValueError("fill_fraction must be between zero and one")
    segment_volumes = [
        _frustum_volume(profile[index], profile[index + 1])
        for index in range(len(profile) - 1)
    ]
    target = sum(segment_volumes) * fraction
    consumed = 0.0
    for index, segment_volume in enumerate(segment_volumes):
        if consumed + segment_volume < target:
            consumed += segment_volume
            continue
        start, end = profile[index], profile[index + 1]
        remaining = target - consumed
        low, high = start[0], end[0]
        for _ in range(80):
            middle = (low + high) / 2.0
            radius = _interpolate_radius(start, end, middle)
            partial = _frustum_volume(start, (middle, radius))
            if partial < remaining:
                low = middle
            else:
                high = middle
        return (low + high) / 2.0
    return profile[-1][0]


def build_liquid_mesh(
    axial_profile_m: Sequence[Sequence[float]],
    fill_fraction: float,
    *,
    radial_segments: int = 32,
    meniscus_depth_m: float = 0.0006,
) -> dict[str, Any]:
    """Build body and meniscus mesh arrays without importing USD or simulator SDKs."""

    if radial_segments < 12:
        raise ValueError("radial_segments must be at least 12")
    if meniscus_depth_m < 0.0 or not math.isfinite(meniscus_depth_m):
        raise ValueError("meniscus_depth_m must be finite and non-negative")
    profile = _validated_profile(axial_profile_m)
    fill_height = height_for_volume_fraction(profile, fill_fraction)
    truncated = [point for point in profile if point[0] < fill_height]
    for index in range(len(profile) - 1):
        if profile[index][0] <= fill_height <= profile[index + 1][0]:
            truncated.append(
                (fill_height, _interpolate_radius(profile[index], profile[index + 1], fill_height))
            )
            break
    if len(truncated) < 2:
        raise ValueError("fill_fraction produced an invalid liquid profile")

    body_points: list[tuple[float, float, float]] = []
    for z_value, radius in truncated:
        for index in range(radial_segments):
            angle = 2.0 * math.pi * index / radial_segments
            body_points.append((radius * math.cos(angle), radius * math.sin(angle), z_value))
    body_counts: list[int] = []
    body_indices: list[int] = []
    for ring in range(len(truncated) - 1):
        for index in range(radial_segments):
            following = (index + 1) % radial_segments
            body_counts.append(4)
            body_indices.extend(
                [
                    ring * radial_segments + index,
                    ring * radial_segments + following,
                    (ring + 1) * radial_segments + following,
                    (ring + 1) * radial_segments + index,
                ]
            )
    bottom_center = len(body_points)
    body_points.append((0.0, 0.0, truncated[0][0]))
    for index in range(radial_segments):
        following = (index + 1) % radial_segments
        body_counts.append(3)
        body_indices.extend([bottom_center, following, index])

    top_radius = truncated[-1][1]
    depth = min(meniscus_depth_m, top_radius * 0.05)
    surface_points = [(0.0, 0.0, fill_height - depth)]
    for index in range(radial_segments):
        angle = 2.0 * math.pi * index / radial_segments
        surface_points.append(
            (top_radius * math.cos(angle), top_radius * math.sin(angle), fill_height)
        )
    surface_counts = [3] * radial_segments
    surface_indices: list[int] = []
    for index in range(radial_segments):
        surface_indices.extend([0, index + 1, ((index + 1) % radial_segments) + 1])

    return {
        "fill_height_m": fill_height,
        "top_radius_m": top_radius,
        "body": {
            "points": body_points,
            "face_vertex_counts": body_counts,
            "face_vertex_indices": body_indices,
            "extent": _extent(body_points),
        },
        "surface": {
            "points": surface_points,
            "face_vertex_counts": surface_counts,
            "face_vertex_indices": surface_indices,
            "extent": _extent(surface_points),
        },
    }


def validate_config(raw: Mapping[str, Any]) -> dict[str, Any]:
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported visual-static-liquid prototype schema_version")
    profiles = _mapping(raw.get("vessel_profiles"), "vessel_profiles")
    if not profiles:
        raise ValueError("vessel_profiles must not be empty")
    normalized_profiles: dict[str, dict[str, Any]] = {}
    for profile_id, raw_profile in profiles.items():
        profile = dict(_mapping(raw_profile, f"vessel profile {profile_id}"))
        for field in ("source_id", "package_dir", "entry_prim"):
            if not isinstance(profile.get(field), str) or not profile[field]:
                raise ValueError(f"vessel profile {profile_id}.{field} is required")
        destination = profile.get("destination", f"deps/containers/{profile_id}")
        _validate_relative_path(destination, f"vessel profile {profile_id}.destination")
        profile["destination"] = destination
        profile["axial_profile_m"] = [
            list(point) for point in _validated_profile(profile.get("axial_profile_m"))
        ]
        normalized_profiles[str(profile_id)] = profile

    raw_instances = raw.get("instances")
    if not isinstance(raw_instances, list) or not raw_instances:
        raise ValueError("instances must be a non-empty list")
    ids: set[str] = set()
    instances: list[dict[str, Any]] = []
    for index, raw_instance in enumerate(raw_instances):
        instance = dict(_mapping(raw_instance, f"instance {index}"))
        instance_id = instance.get("id")
        if not isinstance(instance_id, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", instance_id):
            raise ValueError(f"instance {index}.id must be a valid USD identifier")
        if instance_id in ids:
            raise ValueError(f"duplicate instance id: {instance_id}")
        ids.add(instance_id)
        profile_id = instance.get("profile")
        if profile_id not in normalized_profiles:
            raise ValueError(f"instance {instance_id} references unknown profile")
        fill_fraction = float(instance.get("fill_fraction", math.nan))
        if not math.isfinite(fill_fraction) or not 0.0 < fill_fraction < 1.0:
            raise ValueError(f"instance {instance_id}.fill_fraction must be between zero and one")
        instance["fill_fraction"] = fill_fraction
        instance["color"] = _finite_vector(instance.get("color"), 3, f"instance {instance_id}.color")
        if any(value < 0.0 or value > 1.0 for value in instance["color"]):
            raise ValueError(f"instance {instance_id}.color values must be in [0, 1]")
        pose = _mapping(instance.get("pose"), f"instance {instance_id}.pose")
        instance["pose"] = {
            "xyz": _finite_vector(pose.get("xyz"), 3, f"instance {instance_id}.pose.xyz"),
            "wxyz": _finite_vector(pose.get("wxyz"), 4, f"instance {instance_id}.pose.wxyz"),
        }
        instances.append(instance)

    normalized = dict(raw)
    normalized["vessel_profiles"] = normalized_profiles
    normalized["instances"] = instances
    material = dict(_mapping(raw.get("material", {}), "material"))
    material.setdefault("ior", 1.333)
    material.setdefault("roughness", 0.04)
    material.setdefault("body_opacity", 0.55)
    material.setdefault("surface_opacity", 0.70)
    material.setdefault("metallic", 0.0)
    material.setdefault("meniscus_depth_m", 0.0006)
    material.setdefault("radial_segments", 32)
    for field in ("ior", "roughness", "body_opacity", "surface_opacity", "metallic"):
        material[field] = float(material[field])
        if not math.isfinite(material[field]):
            raise ValueError(f"material.{field} must be finite")
    material["meniscus_depth_m"] = float(material["meniscus_depth_m"])
    material["radial_segments"] = int(material["radial_segments"])
    normalized["material"] = material
    for section in ("environment", "table"):
        if section in raw:
            value = dict(_mapping(raw[section], section))
            for field in ("package_dir", "entry_prim", "destination"):
                if not isinstance(value.get(field), str) or not value[field]:
                    raise ValueError(f"{section}.{field} is required")
            _validate_relative_path(value["destination"], f"{section}.destination")
            normalized[section] = value
    return normalized


def prototype_scene_usda(
    *,
    instances: Sequence[Mapping[str, Any]],
    table_reference: str,
    room_reference: str | None,
    material: Mapping[str, float] | None = None,
    room_translate_xyz_m: Sequence[float] = (0.002882434, -0.0069055, 0.0),
) -> str:
    settings = {
        "ior": 1.333,
        "roughness": 0.04,
        "body_opacity": 0.55,
        "surface_opacity": 0.70,
        "metallic": 0.0,
        "emissive_gain": 0.0,
    }
    if material is not None:
        settings.update({key: float(value) for key, value in material.items() if key in settings})
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        "    kilogramsPerUnit = 1",
        '    upAxis = "Z"',
        "    framesPerSecond = 30",
        "    timeCodesPerSecond = 30",
        "    customLayerData = {",
        "        bool scenarioForgeAuthoredStaticPreview = true",
        "    }",
        ")",
        "",
        'def Xform "World"',
        "{",
    ]
    if room_reference is not None:
        translate = _tuple_text(room_translate_xyz_m)
        lines.extend(
            [
                '    def Xform "Room" (',
                f"        prepend references = @{room_reference}@</World>",
                "    )",
                "    {",
                f"        double3 xformOp:translate = {translate}",
                "        quatd xformOp:orient = (0, 0, 0, 1)",
                "        double3 xformOp:scale = (1, 1, 1)",
                '        uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient", "xformOp:scale"]',
                '        over "Beaker325ml" (active = false) {}',
                '        over "GraduatedCylinder250ml" (active = false) {}',
                '        over "PhysicsScene" (active = false) {}',
                '        over "table" (active = false) {}',
                "    }",
                "",
            ]
        )
    else:
        lines.extend(_neutral_backdrop_lines())
    lines.extend(
        [
            '    def Xform "Table" (',
            f"        prepend references = @{table_reference}@</World>",
            "    )",
            "    {",
            '        uniform token[] xformOpOrder = ["!resetXformStack!"]',
            "    }",
            "",
            '    def Scope "Looks"',
            "    {",
        ]
    )
    for instance in instances:
        lines.extend(_material_lines(instance, settings, indent="        "))
    lines.extend(["    }", "", '    def Xform "Showcase"', "    {"])
    for instance in instances:
        lines.extend(_instance_lines(instance, indent="        "))
    lines.extend(
        [
            "    }",
            "",
            '    def DomeLight "PrototypeDomeLight"',
            "    {",
            "        color3f inputs:color = (0.94, 0.97, 1)",
            "        float inputs:intensity = 850",
            "    }",
            '    def DistantLight "PrototypeKeyLight"',
            "    {",
            "        float inputs:angle = 2",
            "        color3f inputs:color = (1, 0.95, 0.90)",
            "        float inputs:intensity = 1100",
            "        double3 xformOp:rotateXYZ = (35, 0, -35)",
            '        uniform token[] xformOpOrder = ["xformOp:rotateXYZ"]',
            "    }",
            "}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_manifest(
    *,
    output_dir: Path,
    config_sha256: str,
    source_packages: Sequence[Mapping[str, Any]],
    generated_files: Sequence[Path],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "prototype_id": "visual_static_liquid_beaker_flask_v1",
        "status": "static_complete",
        "config_sha256": config_sha256,
        "source_packages": [dict(item) for item in source_packages],
        "generated_files": [
            {
                "path": path.relative_to(output_dir).as_posix(),
                "sha256": _sha256(path),
            }
            for path in generated_files
        ],
        "physics_contract": {
            "liquid_interactive": False,
            "particle_systems": 0,
            "liquid_rigid_bodies": 0,
            "liquid_colliders": 0,
            "tilt_behavior": "rigidly_follows_container",
        },
        "claim_boundary": (
            "Visual-only vessel filling prototype; not fluid physics, liquid transfer, "
            "task-package integration, policy success, metric evidence, or benchmark success."
        ),
    }


def build_prototype(config_path: Path, output_dir: Path) -> Path:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config = validate_config(_mapping(raw, "prototype config"))
    staging = output_dir.parent / f".{output_dir.name}.staging"
    _remove_path(staging)
    staging.mkdir(parents=True)
    try:
        source_packages: list[dict[str, Any]] = []
        for profile_id, profile in config["vessel_profiles"].items():
            source_packages.append(
                _copy_source_package(
                    source_id=profile["source_id"],
                    package_dir=Path(profile["package_dir"]),
                    destination=staging / profile["destination"],
                    output_root=staging,
                )
            )
        environment = config["environment"]
        source_packages.append(
            _copy_source_package(
                source_id="scientific_environment_code_room_wet_chemistry_v2",
                package_dir=Path(environment["package_dir"]),
                destination=staging / environment["destination"],
                output_root=staging,
            )
        )
        table = config["table"]
        source_packages.append(
            _copy_source_package(
                source_id="scientific_workbench_ebench_table_static_support",
                package_dir=Path(table["package_dir"]),
                destination=staging / table["destination"],
                output_root=staging,
            )
        )

        material = config["material"]
        authored_instances: list[dict[str, Any]] = []
        instance_records: list[dict[str, Any]] = []
        for instance in config["instances"]:
            profile = config["vessel_profiles"][instance["profile"]]
            mesh = build_liquid_mesh(
                profile["axial_profile_m"],
                instance["fill_fraction"],
                radial_segments=material["radial_segments"],
                meniscus_depth_m=material["meniscus_depth_m"],
            )
            authored = {
                **instance,
                "entry_prim": profile["entry_prim"],
                "asset_reference": f"{profile['destination']}/asset.usd",
                "mesh": mesh,
            }
            authored_instances.append(authored)
            instance_records.append(
                {
                    "id": instance["id"],
                    "profile": instance["profile"],
                    "fill_mode": "volume",
                    "fill_fraction": instance["fill_fraction"],
                    "fill_height_m": mesh["fill_height_m"],
                    "top_radius_m": mesh["top_radius_m"],
                    "color": instance["color"],
                    "pose": instance["pose"],
                }
            )

        neutral_scene = staging / "scene_neutral.usda"
        lab_scene = staging / "scene_lab.usda"
        neutral_scene.write_text(
            prototype_scene_usda(
                instances=authored_instances,
                table_reference=f"{table['destination']}/asset.usd",
                room_reference=None,
                material=material,
            ),
            encoding="utf-8",
        )
        lab_scene.write_text(
            prototype_scene_usda(
                instances=authored_instances,
                table_reference=f"{table['destination']}/asset.usd",
                room_reference=f"{environment['destination']}/asset.usd",
                material=material,
                room_translate_xyz_m=environment.get("translate_xyz_m", (0.0, 0.0, 0.0)),
            ),
            encoding="utf-8",
        )
        _validate_scene_references(neutral_scene, staging)
        _validate_scene_references(lab_scene, staging)
        normalized_config = {
            "schema_version": SCHEMA_VERSION,
            "prototype_id": config.get("prototype_id", "visual_static_liquid_beaker_flask_v1"),
            "material": material,
            "instances": instance_records,
            "render": config.get("render", {}),
        }
        normalized_path = staging / "prototype.yaml"
        normalized_path.write_text(
            yaml.safe_dump(normalized_config, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        manifest = build_manifest(
            output_dir=staging,
            config_sha256=_sha256(config_path),
            source_packages=source_packages,
            generated_files=[neutral_scene, lab_scene, normalized_path],
        )
        (staging / "prototype_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _remove_path(output_dir)
        staging.rename(output_dir)
    except BaseException:
        _remove_path(staging)
        raise
    return output_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--isaac-python", type=Path, default=DEFAULT_ISAAC_PYTHON)
    parser.add_argument("--renderer", type=Path, default=DEFAULT_RENDERER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = build_prototype(args.config.resolve(), args.output.resolve())
    print(f"Built visual-static-liquid prototype: {output}", flush=True)
    if args.render:
        import subprocess

        completed = subprocess.run(
            [
                str(args.isaac_python.resolve()),
                str(args.renderer.resolve()),
                "--prototype-dir",
                str(output),
            ],
            cwd=str(REPO_ROOT),
            check=False,
        )
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
    return 0


def _validated_profile(raw: Any) -> list[tuple[float, float]]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < 2:
        raise ValueError("axial_profile_m must contain at least two [height, radius] points")
    profile: list[tuple[float, float]] = []
    for index, point in enumerate(raw):
        values = _finite_vector(point, 2, f"axial_profile_m[{index}]")
        if values[1] <= 0.0:
            raise ValueError("axial profile radii must be positive")
        if profile and values[0] <= profile[-1][0]:
            raise ValueError("axial profile heights must increase")
        profile.append((values[0], values[1]))
    return profile


def _frustum_volume(start: Sequence[float], end: Sequence[float]) -> float:
    height = float(end[0]) - float(start[0])
    r0, r1 = float(start[1]), float(end[1])
    return math.pi * height * (r0 * r0 + r0 * r1 + r1 * r1) / 3.0


def _interpolate_radius(start: Sequence[float], end: Sequence[float], height: float) -> float:
    fraction = (height - float(start[0])) / (float(end[0]) - float(start[0]))
    return float(start[1]) + fraction * (float(end[1]) - float(start[1]))


def _extent(points: Sequence[Sequence[float]]) -> list[tuple[float, float, float]]:
    return [
        tuple(min(point[axis] for point in points) for axis in range(3)),
        tuple(max(point[axis] for point in points) for axis in range(3)),
    ]


def _material_lines(
    instance: Mapping[str, Any], settings: Mapping[str, float], *, indent: str
) -> list[str]:
    identifier = str(instance["id"])
    color = _tuple_text(instance["color"])
    emissive = _tuple_text(
        [float(component) * settings["emissive_gain"] for component in instance["color"]]
    )
    return [
        f'{indent}def Material "Liquid_{identifier}_Body"',
        f"{indent}{{",
        f'{indent}    token outputs:surface.connect = </World/Looks/Liquid_{identifier}_Body/PreviewSurface.outputs:surface>',
        f'{indent}    def Shader "PreviewSurface"',
        f"{indent}    {{",
        f'{indent}        uniform token info:id = "UsdPreviewSurface"',
        f"{indent}        color3f inputs:diffuseColor = {color}",
        f"{indent}        color3f inputs:emissiveColor = {emissive}",
        f"{indent}        float inputs:ior = {_number(settings['ior'])}",
        f"{indent}        float inputs:metallic = {_number(settings['metallic'])}",
        f"{indent}        float inputs:opacity = {_number(settings['body_opacity'])}",
        f"{indent}        float inputs:roughness = {_number(settings['roughness'])}",
        f"{indent}        token outputs:surface",
        f"{indent}    }}",
        f"{indent}}}",
        f'{indent}def Material "Liquid_{identifier}_Surface"',
        f"{indent}{{",
        f'{indent}    token outputs:surface.connect = </World/Looks/Liquid_{identifier}_Surface/PreviewSurface.outputs:surface>',
        f'{indent}    def Shader "PreviewSurface"',
        f"{indent}    {{",
        f'{indent}        uniform token info:id = "UsdPreviewSurface"',
        f"{indent}        color3f inputs:diffuseColor = {color}",
        f"{indent}        color3f inputs:emissiveColor = {emissive}",
        f"{indent}        float inputs:ior = {_number(settings['ior'])}",
        f"{indent}        float inputs:metallic = {_number(settings['metallic'])}",
        f"{indent}        float inputs:opacity = {_number(settings['surface_opacity'])}",
        f"{indent}        float inputs:roughness = {_number(settings['roughness'])}",
        f"{indent}        token outputs:surface",
        f"{indent}    }}",
        f"{indent}}}",
    ]


def _instance_lines(instance: Mapping[str, Any], *, indent: str) -> list[str]:
    identifier = str(instance["id"])
    pose = _mapping(instance["pose"], f"instance {identifier}.pose")
    xyz = _tuple_text(pose["xyz"])
    wxyz = pose["wxyz"]
    mesh = _mapping(instance["mesh"], f"instance {identifier}.mesh")
    lines = [
        f'{indent}def Xform "{identifier}"',
        f"{indent}{{",
        f"{indent}    double3 xformOp:translate = {xyz}",
        f"{indent}    quatd xformOp:orient = ({_number(wxyz[0])}, {_number(wxyz[1])}, {_number(wxyz[2])}, {_number(wxyz[3])})",
        f'{indent}    uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate", "xformOp:orient"]',
        f'{indent}    def Xform "Container" (',
        f"{indent}        prepend references = @{instance['asset_reference']}@<{instance['entry_prim']}>",
        f"{indent}    )",
        f"{indent}    {{",
        f"{indent}    }}",
        f'{indent}    def Xform "VisualLiquid"',
        f"{indent}    {{",
        f'{indent}        custom token scenarioForge:role = "visual_static_liquid"',
        f"{indent}        custom bool scenarioForge:interactive = 0",
        f'{indent}        custom token scenarioForge:fillMode = "volume"',
        f"{indent}        custom float scenarioForge:fillFraction = {_number(instance['fill_fraction'])}",
    ]
    lines.extend(
        _mesh_lines(
            "Body",
            _mapping(mesh["body"], "liquid body mesh"),
            f"/World/Looks/Liquid_{identifier}_Body",
            double_sided=False,
            indent=indent + "        ",
        )
    )
    lines.extend(
        _mesh_lines(
            "Surface",
            _mapping(mesh["surface"], "liquid surface mesh"),
            f"/World/Looks/Liquid_{identifier}_Surface",
            double_sided=True,
            indent=indent + "        ",
        )
    )
    lines.extend([f"{indent}    }}", f"{indent}}}", ""])
    return lines


def _mesh_lines(
    name: str,
    mesh: Mapping[str, Any],
    material_path: str,
    *,
    double_sided: bool,
    indent: str,
) -> list[str]:
    return [
        f'{indent}def Mesh "{name}" (',
        f'{indent}    prepend apiSchemas = ["MaterialBindingAPI"]',
        f"{indent})",
        f"{indent}{{",
        f"{indent}    bool doubleSided = {str(double_sided).lower()}",
        f"{indent}    float3[] extent = {_point_array_text(mesh['extent'])}",
        f"{indent}    int[] faceVertexCounts = {_int_array_text(mesh['face_vertex_counts'])}",
        f"{indent}    int[] faceVertexIndices = {_int_array_text(mesh['face_vertex_indices'])}",
        f"{indent}    point3f[] points = {_point_array_text(mesh['points'])}",
        f"{indent}    rel material:binding = <{material_path}>",
        f'{indent}    uniform token subdivisionScheme = "none"',
        f"{indent}}}",
    ]


def _neutral_backdrop_lines() -> list[str]:
    return [
        '    def Scope "NeutralBackdrop"',
        "    {",
        '        def Material "Mat"',
        "        {",
        '            token outputs:surface.connect = </World/NeutralBackdrop/Mat/PreviewSurface.outputs:surface>',
        '            def Shader "PreviewSurface"',
        "            {",
        '                uniform token info:id = "UsdPreviewSurface"',
        "                color3f inputs:diffuseColor = (0.18, 0.20, 0.23)",
        "                float inputs:roughness = 0.72",
        "                token outputs:surface",
        "            }",
        "        }",
        '        def Cube "Floor" (prepend apiSchemas = ["MaterialBindingAPI"])',
        "        {",
        "            double size = 1",
        "            rel material:binding = </World/NeutralBackdrop/Mat>",
        "            double3 xformOp:scale = (4, 4, 0.04)",
        "            double3 xformOp:translate = (0, 0, -0.02)",
        '            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
        "        }",
        "    }",
        "",
    ]


def _copy_source_package(
    *, source_id: str, package_dir: Path, destination: Path, output_root: Path
) -> dict[str, Any]:
    if not package_dir.is_dir():
        raise FileNotFoundError(package_dir)
    asset = package_dir / "asset.usd"
    manifest_path = package_dir / "evidence/manifest.json"
    if not asset.is_file() or not manifest_path.is_file():
        raise ValueError(f"source package is incomplete: {package_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("overall_status", manifest.get("status"))
    if status not in {"pass", "passed"}:
        raise ValueError(f"source package is not passing: {source_id}={status}")
    shutil.copytree(package_dir, destination)
    return {
        "source_id": source_id,
        "destination": destination.relative_to(output_root).as_posix(),
        "asset_sha256": _sha256(asset),
        "manifest_sha256": _sha256(manifest_path),
        "producer_package_id": manifest.get("package_id"),
        "producer_status": status,
    }


def _validate_scene_references(scene_path: Path, output_root: Path) -> None:
    for reference in USD_REFERENCE_RE.findall(scene_path.read_text(encoding="utf-8")):
        if "://" in reference or Path(reference).is_absolute():
            raise ValueError(f"scene has non-portable reference: {reference}")
        target = (scene_path.parent / reference).resolve()
        try:
            target.relative_to(output_root.resolve())
        except ValueError as error:
            raise ValueError(f"scene reference escapes output root: {reference}") from error
        if not target.exists():
            raise FileNotFoundError(target)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _finite_vector(value: Any, size: int, label: str) -> list[float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != size:
        raise ValueError(f"{label} must contain {size} values")
    vector = [float(item) for item in value]
    if not all(math.isfinite(item) for item in vector):
        raise ValueError(f"{label} must contain finite values")
    return vector


def _validate_relative_path(value: str, label: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a package-relative path")


def _number(value: Any) -> str:
    return f"{float(value):.9g}"


def _tuple_text(values: Sequence[Any]) -> str:
    return "(" + ", ".join(_number(value) for value in values) + ")"


def _point_array_text(values: Sequence[Sequence[Any]]) -> str:
    return "[" + ", ".join(_tuple_text(value) for value in values) + "]"


def _int_array_text(values: Sequence[Any]) -> str:
    return "[" + ", ".join(str(int(value)) for value in values) + "]"


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
