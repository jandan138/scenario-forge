"""Compile source-bound native EBench intervention cells.

This adapter writes GenManip metadata from JSON; it never loads an external
pickle or executes a model. Producer overlays own all geometry and physics.
The prototype retains external source dependencies explicitly.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import pickle
import re
import shutil
from pathlib import Path
from typing import Any, Sequence
from itertools import product

import yaml


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unchanged_pose(left: Sequence[float], right: Sequence[float]) -> bool:
    return len(left) == len(right) and all(abs(a - b) <= 1e-6 for a, b in zip(left, right))


def _layout_variants(config, source_task, geometry_only):
    variants = config.get('layout_variants')
    if variants is None:
        return [{'id': None, 'overrides': {}}]
    if not geometry_only or not isinstance(variants, list) or not variants:
        raise ValueError('Layout variants require the scene-variants schema and a nonempty list')
    names = set()
    for variant in variants:
        name = variant['id']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name) or name in names:
            raise ValueError('Invalid or duplicate layout variant')
        names.add(name)
        if not variant['overrides']:
            raise ValueError('Layout variant must declare pose overrides')
        for object_id, fields in variant['overrides'].items():
            source = source_task['initial_layout'].get(object_id)
            if source is None or source.get('type', 'object') != 'object':
                raise ValueError('Pose override requires an existing object')
            if not fields or not set(fields) <= {'position', 'orientation'}:
                raise ValueError('Only position/orientation pose fields may be overridden')
            for field, values in fields.items():
                size = 3 if field == 'position' else 4
                if (not isinstance(values, list) or len(values) != size
                        or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)
                               for v in values)):
                    raise ValueError('Invalid pose vector')
                if field == 'orientation' and abs(sum(v*v for v in values)-1) > 1e-6:
                    raise ValueError('Pose quaternion must be normalized')
    return variants


def _initial_scene_pose_objects(config, source_task, geometry_only):
    objects = config.get('initial_scene_pose_objects', [])
    if not isinstance(objects, list) or (objects and not geometry_only):
        raise ValueError('Initial scene pose objects require a scene-variants list')
    if any(not isinstance(uid, str) or not re.fullmatch(r'[A-Za-z0-9_]+', uid) for uid in objects):
        raise ValueError('Invalid initial scene pose object id')
    if len(set(objects)) != len(objects):
        raise ValueError('Duplicate initial scene pose object')
    for uid in objects:
        pose = source_task['initial_layout'].get(uid)
        if (pose is None or pose.get('type', 'object') != 'object'
                or pose.get('path') or pose.get('is_articulation_part')):
            raise ValueError('Initial scene pose sync requires an existing scene object, not a spawned asset or articulation part')
        for field, size in [('position', 3), ('orientation', 4), ('scale', 3)]:
            values = pose.get(field)
            if (not isinstance(values, list) or len(values) != size
                    or any(isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) for v in values)):
                raise ValueError('Invalid source pose for initial scene sync')
        if abs(sum(v*v for v in pose['orientation'])-1) > 1e-6 or min(pose['scale']) <= 0:
            raise ValueError('Initial scene pose requires normalized quaternion and positive scale')
    return objects


def _scene_pose_text(default_prim, objects, layout):
    if not objects:
        return ''
    lines = [f'\nover "{default_prim}" {{']
    for uid in objects:
        pose = layout[uid]
        def vector(field):
            return '(' + ', '.join(repr(float(v)) for v in pose[field]) + ')'
        lines.extend([f' over "obj_{uid}" {{',
            '  double3 xformOp:translate:initialLayout = ' + vector('position'),
            '  quatd xformOp:orient:initialLayout = ' + vector('orientation'),
            '  double3 xformOp:scale:initialLayout = ' + vector('scale'),
            '  uniform token[] xformOpOrder = ["!resetXformStack!", "xformOp:translate:initialLayout", "xformOp:orient:initialLayout", "xformOp:scale:initialLayout"]',
            ' }'])
    return '\n'.join(lines + ['}', ''])


def preplaced_layout(source: dict[str, Any]) -> dict[str, Any]:
    """Use measured demonstration endpoints, requiring a stationary basket."""
    layout: dict[str, Any] = copy.deepcopy(source["task_data"]["initial_layout"])
    anchor = "basket_big"
    for field in ("position", "orientation", "scale"):
        recorded = source["objects"][anchor][field]
        if not _unchanged_pose(recorded["first"], recorded["last"]):
            raise ValueError("Source basket moved; endpoint placement needs an explicit frame transform")
        if not _unchanged_pose(recorded["first"], layout[anchor][field]):
            raise ValueError("Source basket frame differs from initial layout")
    for obj in ("dish1", "dish2", "dish3", "glass"):
        for field in ("position", "orientation", "scale"):
            recorded = source["objects"][obj][field]
            if not _unchanged_pose(recorded["first"], layout[obj][field]):
                raise ValueError(f"Source first pose differs for {obj}/{field}")
            layout[obj][field] = list(recorded["last"])
    return layout


def compile_suite(config: dict[str, Any], output: Path) -> dict[str, Any]:
    geometry_only = config.get("schema") == "ebench-native-scene-variants-build/v1"
    if not geometry_only and config.get("schema") != "ebench-native-intervention-build/v1":
        raise ValueError("Unknown intervention build schema")
    if geometry_only and config.get("preplaced_instruction") is not None:
        raise ValueError("Scene variant compilation preserves the original instruction")
    default_prim = config["base_default_prim"] if geometry_only else "root"
    if not isinstance(default_prim, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", default_prim):
        raise ValueError("Invalid native default prim")
    source_path = Path(config["source_layout"])
    source = json.loads(source_path.read_text())
    source_kind = source.get("source_kind")
    initial_only = source_kind == "source_initial_metadata_only"
    if source_kind != "source_demonstration_not_model_rollout" and not (geometry_only and initial_only):
        raise ValueError("Preplacement requires source demonstration endpoints")
    for key in (("metadata",) if initial_only else ("metadata", "database")):
        ref = source[key]
        if digest(Path(ref["path"])) != ref["sha256"]:
            raise ValueError(f"Source {key} changed")
    source_config_path = Path(config["source_task_config"])
    task_config = yaml.safe_load(source_config_path.read_text())
    if len(task_config["evaluation_configs"]) != 1:
        raise ValueError("One native task config is required")
    evaluation = task_config["evaluation_configs"][0]
    source_task = source["task_data"]
    variants = _layout_variants(config, source_task, geometry_only)
    scene_pose_objects = _initial_scene_pose_objects(config, source_task, geometry_only)
    remaining_instruction = config.get("preplaced_instruction")
    if remaining_instruction is not None and (
        not isinstance(remaining_instruction, str) or not remaining_instruction.strip()
    ):
        raise ValueError("Preplaced instruction must be nonempty text")
    placed = None if geometry_only else preplaced_layout(source)
    base = Path(config["base_scene"]).resolve()
    if digest(base) != config["base_scene_sha256"]:
        raise ValueError("Base scene changed")
    preserve_metadata = config.get("preserve_source_stage_metadata", False)
    if not isinstance(preserve_metadata, bool):
        raise ValueError("preserve_source_stage_metadata must be boolean")
    stage_metadata = None
    if preserve_metadata:
        # Optional adapter capability; pure JSON packaging retains no USD dependency.
        from pxr import Usd
        source_stage = Usd.Stage.Open(str(base))
        if not source_stage or source_stage.GetDefaultPrim().GetName() != default_prim:
            raise ValueError("Source stage default prim differs from configured root")
        stage_metadata = source_stage.GetPseudoRoot().GetAllMetadata()
    entrypoint = base.with_suffix(".usda")
    wrapper = entrypoint.read_text()
    source_reference = f"@./{base.name}@"
    if wrapper.count(source_reference) != 1:
        raise ValueError("Expected one native content-layer payload in the source entrypoint")
    wrapper = wrapper.replace(source_reference, "@./main.usd@")
    prefix = config["task_prefix"] if geometry_only else config.get("task_prefix", "dish")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", prefix):
        raise ValueError("Invalid task prefix")
    overlays = config["overlays"]
    if geometry_only:
        if ("control" not in overlays or len(overlays) < 2 or
                any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key) for key in overlays)):
            raise ValueError("Scene variants require control and named producer interventions")
    elif set(overlays) != {"control", "wide"}:
        raise ValueError("Expected control and wide producer overlays")
    for ref in overlays.values():
        if digest(Path(ref["path"])) != ref["sha256"]:
            raise ValueError("Producer overlay changed")
        paths = [str(Path(ref["path"]).resolve()), str(base)]
        if any("@" in p or "\n" in p for p in paths):
            raise ValueError("Unsupported USD asset path characters")
    # Validate source bindings and asset paths before starting a new output.
    output.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {"schema": "ebench-native-intervention-suite/v1", "cells": [],
                "status": "compiled_not_runtime_verified",
                "asset_closure": "external_source_bound_prototype",
                "source_layout_sha256": digest(source_path),
                "source_kind": source_kind,
                "source_stage_metadata_preserved": preserve_metadata,
                "source_task_config_sha256": digest(source_config_path),
                "base_scene": str(base), "base_scene_sha256": digest(base),
                "base_entrypoint": str(entrypoint), "base_entrypoint_sha256": digest(entrypoint),
                "new_model_episodes": 0}
    for geometry, ref in overlays.items():
        for progress, variant in product((("full",) if geometry_only else ("full", "preplaced")), variants):
            cell = f"{prefix}_{geometry}_{progress}"
            if variant['id'] is not None:
                cell += '_' + variant['id']
            task_name = f"eeos_evolution/{cell}"
            root = output / cell
            scene = root / "scene/main.usd"
            scene.parent.mkdir(parents=True)
            paths = [str(Path(ref["path"]).resolve()), str(base)]
            # Preservation includes absent opinions: injecting unit/axis defaults
            # can change source semantics when the source leaves them unauthored.
            defaults = '' if preserve_metadata else ' metersPerUnit = 1\n upAxis = "Z"\n'
            scene.write_text(f'#usda 1.0\n(\n defaultPrim = "{default_prim}"\n' + defaults
                             + ' subLayers = [\n'
                             + ",\n".join(f"  @{p}@" for p in paths) + "\n ]\n)\n")
            if stage_metadata is not None:
                compiled_stage = Usd.Stage.Open(str(scene))
                for key, value in stage_metadata.items():
                    compiled_stage.SetMetadata(key, value)
                compiled_stage.GetRootLayer().Save()
                del compiled_stage
            scene.with_suffix(".usda").write_text(wrapper)
            data = copy.deepcopy(source_task)
            if progress == "preplaced":
                data["initial_layout"] = copy.deepcopy(placed)
                if remaining_instruction is not None:
                    data["instruction"] = remaining_instruction
            for object_id, values in variant['overrides'].items():
                data['initial_layout'][object_id].update(copy.deepcopy(values))
            if scene_pose_objects:
                with scene.open('a') as stream:
                    stream.write(_scene_pose_text(default_prim, scene_pose_objects, data['initial_layout']))
            metadata = {"task_name": task_name, "episode_name": "000", "task_data": data,
                        "language_instruction": data["instruction"]}
            directory = root / "tasks" / task_name / "000"
            directory.mkdir(parents=True)
            (directory / "episode_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
            # JSON is authoritative; this is a deterministic compatibility encoding.
            (directory / "meta_info.pkl").write_bytes(pickle.dumps(metadata, protocol=4))
            native = {"evaluation_configs": [copy.deepcopy(evaluation)]}
            native["evaluation_configs"][0].update(task_name=task_name, num_test=1,
                                                    usd_name=str(scene.resolve().with_suffix("")))
            (root / "task_config.yml").write_text(yaml.safe_dump(native, sort_keys=False))
            cell_record = {"cell_id": cell, "geometry": geometry, "initial_progress": progress,
                "task_name": task_name, "task_config": str((root / "task_config.yml").resolve()),
                "task_directory": str(directory.parent.resolve()),
                "scene": str(scene.resolve()), "scene_sha256": digest(scene),
                "entrypoint": str(scene.with_suffix(".usda").resolve()),
                "entrypoint_sha256": digest(scene.with_suffix(".usda")),
                "producer_overlay_sha256": ref["sha256"],
                "metadata_sha256": digest(directory / "episode_metadata.json"),
                "pickle_sha256": digest(directory / "meta_info.pkl"),
                "changed_initial_objects": sorted(key for key in source_task['initial_layout']
                    if data['initial_layout'][key] != source_task['initial_layout'][key]),
                "layout_variant": variant['id'],
                "layout_overrides": copy.deepcopy(variant['overrides']),
                "initial_scene_pose_objects": list(scene_pose_objects),
                "instruction_intervention": {
                    "source_instruction": source_task["instruction"],
                    "compiled_instruction": data["instruction"],
                    "changed": data["instruction"] != source_task["instruction"],
                },
                "runtime_validated": False}
            manifest["cells"].append(cell_record)
    (output / "build_config.json").write_text(json.dumps(config, indent=2) + "\n")
    manifest['build_config_sha256'] = digest(output / 'build_config.json')
    (output / "suite.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def install_suite(output: Path, genmanip_root: Path) -> dict[str, Any]:
    """Register new task directories/configs; never replace existing tasks."""
    manifest = json.loads((output / "suite.json").read_text())
    if manifest.get("schema") != "ebench-native-intervention-suite/v1":
        raise ValueError("Unknown suite schema")
    config = json.loads((output / "build_config.json").read_text())
    if manifest.get('build_config_sha256') and digest(output/'build_config.json') != manifest['build_config_sha256']:
        raise ValueError('Build configuration changed')
    if digest(Path(config['source_layout'])) != manifest['source_layout_sha256']:
        raise ValueError('Source layout changed')
    source_config = Path(config["source_task_config"])
    if digest(source_config) != manifest["source_task_config_sha256"]:
        raise ValueError("Source task config changed")
    if digest(Path(manifest["base_scene"])) != manifest["base_scene_sha256"]:
        raise ValueError("Base scene changed")
    if digest(Path(manifest["base_entrypoint"])) != manifest["base_entrypoint_sha256"]:
        raise ValueError("Base entrypoint changed")
    for ref in config["overlays"].values():
        if digest(Path(ref["path"])) != ref["sha256"]:
            raise ValueError("Producer overlay changed")
    original_evaluation = yaml.safe_load(source_config.read_text())["evaluation_configs"][0]
    entries = []
    for cell in manifest["cells"]:
        name = Path(cell["task_name"])
        if name.is_absolute() or ".." in name.parts or name.parts[0] != "eeos_evolution":
            raise ValueError("Intervention must stay in the eeos_evolution task namespace")
        source = Path(cell["task_directory"])
        expected = {"evaluation_configs": [copy.deepcopy(original_evaluation)]}
        expected["evaluation_configs"][0].update(task_name=cell["task_name"], num_test=1,
            usd_name=str(Path(cell["scene"]).with_suffix("")))
        if yaml.safe_load(Path(cell["task_config"]).read_text()) != expected:
            raise ValueError("Compiled task config changed")
        for path, expected_hash in [(Path(cell["scene"]), cell["scene_sha256"]),
                               (Path(cell["entrypoint"]), cell["entrypoint_sha256"]),
                               (source / "000/episode_metadata.json", cell["metadata_sha256"]),
                               (source / "000/meta_info.pkl", cell["pickle_sha256"])]:
            if digest(path) != expected_hash:
                raise ValueError("Compiled cell changed")
        target = genmanip_root / "saved/tasks" / name
        config_target = genmanip_root / "configs/tasks" / name.with_suffix(".yml")
        if target.exists() or config_target.exists():
            raise FileExistsError(f"Task already registered: {name}")
        entries.append((source, target, Path(cell["task_config"]), config_target))
    installed = []
    for source, target, config_source, config_target in entries:
        target.parent.mkdir(parents=True, exist_ok=True)
        config_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        shutil.copy2(config_source, config_target)
        installed.append({"task_directory": str(target), "task_config": str(config_target),
                          "config_sha256": digest(config_target)})
    receipt = {"schema": "ebench-native-intervention-install/v1", "installed": installed,
               "runtime_validated": False}
    (output / "installation.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
