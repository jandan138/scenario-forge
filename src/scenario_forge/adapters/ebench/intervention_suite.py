"""Compile source-bound native EBench intervention cells.

This adapter writes GenManip metadata from JSON; it never loads an external
pickle or executes a model. Producer overlays own all geometry and physics.
The prototype retains external source dependencies explicitly.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pickle
import re
import shutil
from pathlib import Path
from typing import Any, Sequence

import yaml


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unchanged_pose(left: Sequence[float], right: Sequence[float]) -> bool:
    return len(left) == len(right) and all(abs(a - b) <= 1e-6 for a, b in zip(left, right))


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
    if config.get("schema") != "ebench-native-intervention-build/v1":
        raise ValueError("Unknown intervention build schema")
    source_path = Path(config["source_layout"])
    source = json.loads(source_path.read_text())
    if source.get("source_kind") != "source_demonstration_not_model_rollout":
        raise ValueError("Preplacement requires source demonstration endpoints")
    for key in ("metadata", "database"):
        ref = source[key]
        if digest(Path(ref["path"])) != ref["sha256"]:
            raise ValueError(f"Source {key} changed")
    source_config_path = Path(config["source_task_config"])
    task_config = yaml.safe_load(source_config_path.read_text())
    if len(task_config["evaluation_configs"]) != 1:
        raise ValueError("One native task config is required")
    evaluation = task_config["evaluation_configs"][0]
    source_task = source["task_data"]
    remaining_instruction = config.get("preplaced_instruction")
    if remaining_instruction is not None and (
        not isinstance(remaining_instruction, str) or not remaining_instruction.strip()
    ):
        raise ValueError("Preplaced instruction must be nonempty text")
    placed = preplaced_layout(source)
    base = Path(config["base_scene"]).resolve()
    if digest(base) != config["base_scene_sha256"]:
        raise ValueError("Base scene changed")
    entrypoint = base.with_suffix(".usda")
    wrapper = entrypoint.read_text()
    source_reference = f"@./{base.name}@"
    if wrapper.count(source_reference) != 1:
        raise ValueError("Expected one native content-layer payload in the source entrypoint")
    wrapper = wrapper.replace(source_reference, "@./main.usd@")
    prefix = config.get("task_prefix", "dish")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", prefix):
        raise ValueError("Invalid task prefix")
    overlays = config["overlays"]
    if set(overlays) != {"control", "wide"}:
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
                "source_task_config_sha256": digest(source_config_path),
                "base_scene": str(base), "base_scene_sha256": digest(base),
                "base_entrypoint": str(entrypoint), "base_entrypoint_sha256": digest(entrypoint),
                "new_model_episodes": 0}
    for geometry, ref in overlays.items():
        for progress in ("full", "preplaced"):
            cell = f"{prefix}_{geometry}_{progress}"
            task_name = f"eeos_evolution/{cell}"
            root = output / cell
            scene = root / "scene/main.usd"
            scene.parent.mkdir(parents=True)
            paths = [str(Path(ref["path"]).resolve()), str(base)]
            scene.write_text('#usda 1.0\n(\n defaultPrim = "root"\n metersPerUnit = 1\n'
                             ' upAxis = "Z"\n subLayers = [\n'
                             + ",\n".join(f"  @{p}@" for p in paths) + "\n ]\n)\n")
            scene.with_suffix(".usda").write_text(wrapper)
            data = copy.deepcopy(source_task)
            if progress == "preplaced":
                data["initial_layout"] = copy.deepcopy(placed)
                if remaining_instruction is not None:
                    data["instruction"] = remaining_instruction
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
                "changed_initial_objects": [] if progress == "full" else ["dish1", "dish2", "dish3", "glass"],
                "instruction_intervention": {
                    "source_instruction": source_task["instruction"],
                    "compiled_instruction": data["instruction"],
                    "changed": data["instruction"] != source_task["instruction"],
                },
                "runtime_validated": False}
            manifest["cells"].append(cell_record)
    (output / "build_config.json").write_text(json.dumps(config, indent=2) + "\n")
    (output / "suite.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def install_suite(output: Path, genmanip_root: Path) -> dict[str, Any]:
    """Register new task directories/configs; never replace existing tasks."""
    manifest = json.loads((output / "suite.json").read_text())
    if manifest.get("schema") != "ebench-native-intervention-suite/v1":
        raise ValueError("Unknown suite schema")
    config = json.loads((output / "build_config.json").read_text())
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
