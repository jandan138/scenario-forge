"""Materialize randomizable VR object subtrees into the handoff scene layer."""

from __future__ import annotations

from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


class VRObjectMaterializationError(ValueError):
    """Raised when a VR object cannot be published as an inline subtree."""


def materialize_vr_object_subtrees(
    *,
    scene_path: Path,
    scene_prim_paths: Sequence[str],
    runtime_prim_paths: Sequence[str],
    evidence_path: Path,
    prunable_dependency_roots: Sequence[Path] = (),
) -> dict[str, Any]:
    """Inline composed ``obj_*`` subtrees while preserving composed transforms."""

    if len(scene_prim_paths) != len(runtime_prim_paths):
        raise VRObjectMaterializationError(
            "scene and runtime object paths must have the same length"
        )
    try:
        from pxr import Sdf, Usd, UsdGeom  # type: ignore
    except ImportError as exc:
        raise VRObjectMaterializationError(
            "VR object materialization requires the USD Python runtime"
        ) from exc

    scene_path = Path(scene_path).resolve()
    evidence_path = Path(evidence_path)
    stage = Usd.Stage.Open(str(scene_path), Usd.Stage.LoadAll)
    if stage is None:
        raise VRObjectMaterializationError(
            f"cannot open VR scene for object materialization: {scene_path}"
        )

    before: dict[str, dict[str, Any]] = {}
    for scene_prim_path, runtime_prim_path in zip(
        scene_prim_paths, runtime_prim_paths, strict=True
    ):
        _validate_object_paths(scene_prim_path, runtime_prim_path)
        prim = stage.GetPrimAtPath(scene_prim_path)
        if not prim.IsValid() or not prim.IsActive() or not prim.IsA(UsdGeom.Xform):
            raise VRObjectMaterializationError(
                f"VR object root must be an Xform: {scene_prim_path}"
            )
        before[scene_prim_path] = _object_snapshot(stage, prim)

    flattened = stage.Flatten(addSourceFileComment=False)
    root_layer = stage.GetRootLayer()
    for scene_prim_path in scene_prim_paths:
        existing = root_layer.GetPrimAtPath(scene_prim_path)
        if existing is not None:
            edit = Sdf.BatchNamespaceEdit()
            edit.Add(Sdf.NamespaceEdit.Remove(scene_prim_path))
            if not root_layer.Apply(edit):
                raise VRObjectMaterializationError(
                    f"cannot replace authored VR object root: {scene_prim_path}"
                )
        parent_path = Sdf.Path(scene_prim_path).GetParentPath()
        if root_layer.GetPrimAtPath(parent_path) is None:
            Sdf.CreatePrimInLayer(root_layer, parent_path)
        if not Sdf.CopySpec(
            flattened,
            Sdf.Path(scene_prim_path),
            root_layer,
            Sdf.Path(scene_prim_path),
        ):
            raise VRObjectMaterializationError(
                f"cannot copy flattened VR object subtree: {scene_prim_path}"
            )
        spec = root_layer.GetPrimAtPath(scene_prim_path)
        if spec is None:
            raise VRObjectMaterializationError(
                f"flattened VR object subtree is missing: {scene_prim_path}"
            )
        _rebase_asset_paths(spec, scene_path.parent)

    temporary = scene_path.with_name(f".{scene_path.name}.materializing.usda")
    if not root_layer.Export(str(temporary), args={"format": "usda"}):
        raise VRObjectMaterializationError(
            f"cannot export materialized ASCII VR scene: {temporary}"
        )
    try:
        after_stage = Usd.Stage.Open(str(temporary), Usd.Stage.LoadAll)
        if after_stage is None:
            raise VRObjectMaterializationError(
                f"cannot reopen materialized VR scene: {temporary}"
            )
        records: list[dict[str, Any]] = []
        for scene_prim_path, runtime_prim_path in zip(
            scene_prim_paths, runtime_prim_paths, strict=True
        ):
            prim = after_stage.GetPrimAtPath(scene_prim_path)
            if not prim.IsValid() or not prim.IsA(UsdGeom.Xform):
                raise VRObjectMaterializationError(
                    f"materialized VR object root is not an Xform: {scene_prim_path}"
                )
            after = _object_snapshot(after_stage, prim)
            expected = before[scene_prim_path]
            if after["non_transform_content_fingerprint"] != expected[
                "non_transform_content_fingerprint"
            ]:
                raise VRObjectMaterializationError(
                    f"materialization changed non-transform content: {scene_prim_path}"
                )
            if not _transform_maps_close(
                expected["world_transforms"], after["world_transforms"]
            ):
                raise VRObjectMaterializationError(
                    f"materialization changed composed transforms: {scene_prim_path}"
                )
            arcs_after = _composition_arc_count(prim)
            if arcs_after:
                raise VRObjectMaterializationError(
                    f"materialized object retains {arcs_after} composition arcs: "
                    f"{scene_prim_path}"
                )
            records.append(
                {
                    "object_name": scene_prim_path.rsplit("/", 1)[-1],
                    "scene_prim_path": scene_prim_path,
                    "runtime_prim_path": runtime_prim_path,
                    "prim_count": after["prim_count"],
                    "composition_arcs_before": expected["composition_arc_count"],
                    "composition_arcs_after": arcs_after,
                    "structure_fingerprint": after["structure_fingerprint"],
                    "non_transform_content_fingerprint": after[
                        "non_transform_content_fingerprint"
                    ],
                    "transform_equivalent": True,
                }
            )

        _validate_dependency_closure(temporary)
        os.replace(temporary, scene_path)
        _prune_unreferenced_usd_layers(
            scene_path=scene_path,
            dependency_roots=prunable_dependency_roots,
        )
        _validate_dependency_closure(scene_path)
    finally:
        if temporary.exists():
            temporary.unlink()

    report = {
        "schema_version": "scenario-forge-vr-object-materialization/v0.1",
        "status": "pass",
        "scene": scene_path.name,
        "serialization": "usda_ascii",
        "object_scope": "task_config.obj_prim_list",
        "objects": records,
        "excluded": ["room", "table", "robot", "lights", "fluid_helpers"],
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def validate_vr_variant_object_parity(
    variant_reports: Mapping[str, Path], *, evidence_path: Path
) -> dict[str, Any]:
    """Require identical non-transform object content across VR variants."""

    if len(variant_reports) < 2:
        raise VRObjectMaterializationError(
            "VR variant parity requires at least two variants"
        )
    reports: dict[str, Mapping[str, Any]] = {}
    for variant, path in variant_reports.items():
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("status") != "pass":
            raise VRObjectMaterializationError(
                f"VR object materialization did not pass for {variant}"
            )
        reports[variant] = payload

    by_variant = {
        variant: {
            str(item["object_name"]): item
            for item in _mapping_list(report.get("objects"), f"{variant}.objects")
        }
        for variant, report in reports.items()
    }
    baseline_variant = next(iter(by_variant))
    baseline_names = set(by_variant[baseline_variant])
    for variant, objects in by_variant.items():
        if set(objects) != baseline_names:
            raise VRObjectMaterializationError(
                f"VR object set differs between {baseline_variant} and {variant}"
            )

    records: list[dict[str, Any]] = []
    for object_name in sorted(baseline_names):
        fingerprints = {
            variant: str(objects[object_name]["non_transform_content_fingerprint"])
            for variant, objects in by_variant.items()
        }
        if len(set(fingerprints.values())) != 1:
            raise VRObjectMaterializationError(
                f"{object_name} non-transform content differs across VR variants"
            )
        structures = {
            variant: str(objects[object_name]["structure_fingerprint"])
            for variant, objects in by_variant.items()
        }
        if len(set(structures.values())) != 1:
            raise VRObjectMaterializationError(
                f"{object_name} structure differs across VR variants"
            )
        records.append(
            {
                "object_name": object_name,
                "variants": list(by_variant),
                "structure_fingerprint": next(iter(structures.values())),
                "non_transform_content_fingerprint": next(
                    iter(fingerprints.values())
                ),
                "transform_opinions": "excluded",
            }
        )

    report = {
        "schema_version": "scenario-forge-vr-variant-object-parity/v0.1",
        "status": "pass",
        "variants": list(by_variant),
        "objects": records,
        "comparison": "all_non_transform_content",
        "excluded_properties": ["xformOp:*", "xformOpOrder"],
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _validate_object_paths(scene_path: str, runtime_path: str) -> None:
    scene_name = scene_path.rsplit("/", 1)[-1]
    runtime_name = runtime_path.rsplit("/", 1)[-1]
    if (
        not scene_path.startswith("/")
        or not runtime_path.startswith("/")
        or not scene_name.startswith("obj_")
        or scene_name != runtime_name
    ):
        raise VRObjectMaterializationError(
            "VR scene and runtime object roots must be matching absolute obj_* paths"
        )


def _object_snapshot(stage: Any, root_prim: Any) -> dict[str, Any]:
    from pxr import Usd, UsdGeom  # type: ignore

    root_path = str(root_prim.GetPath())
    structure: list[dict[str, Any]] = []
    content: list[dict[str, Any]] = []
    world_transforms: dict[str, list[float]] = {}
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    for prim in Usd.PrimRange(root_prim):
        relative = str(prim.GetPath())[len(root_path) :] or "."
        attributes = []
        values = []
        for attribute in sorted(prim.GetAttributes(), key=lambda item: item.GetName()):
            name = attribute.GetName()
            if name == "xformOpOrder" or name.startswith("xformOp:"):
                continue
            attributes.append(
                {
                    "name": name,
                    "type": str(attribute.GetTypeName()),
                    "variability": str(attribute.GetVariability()),
                }
            )
            property_stack = attribute.GetPropertyStack(Usd.TimeCode.Default())
            asset_base = (
                Path(property_stack[0].layer.realPath).parent
                if property_stack and property_stack[0].layer.realPath
                else None
            )
            values.append(
                {
                    "name": name,
                    "default": _json_value(attribute.Get(), asset_base=asset_base),
                    "time_samples": [
                        [
                            float(time),
                            _json_value(attribute.Get(time), asset_base=asset_base),
                        ]
                        for time in attribute.GetTimeSamples()
                    ],
                }
            )
        relationships = [
            {
                "name": relationship.GetName(),
                "targets": sorted(str(path) for path in relationship.GetTargets()),
            }
            for relationship in sorted(
                prim.GetRelationships(), key=lambda item: item.GetName()
            )
        ]
        structure.append(
            {
                "path": relative,
                "type": prim.GetTypeName(),
                "applied_schemas": sorted(prim.GetAppliedSchemas()),
                "attributes": attributes,
                "relationships": [item["name"] for item in relationships],
            }
        )
        content.append(
            {
                "path": relative,
                "attributes": values,
                "relationships": relationships,
            }
        )
        if prim.IsA(UsdGeom.Xformable):
            matrix = cache.GetLocalToWorldTransform(prim)
            world_transforms[relative] = [
                float(matrix[row][column])
                for row in range(4)
                for column in range(4)
            ]
    return {
        "prim_count": len(structure),
        "composition_arc_count": _composition_arc_count(root_prim),
        "structure_fingerprint": _fingerprint(structure),
        "non_transform_content_fingerprint": _fingerprint(
            {"structure": structure, "content": content}
        ),
        "world_transforms": world_transforms,
    }


def _composition_arc_count(root_prim: Any) -> int:
    from pxr import Usd  # type: ignore

    count = 0
    for prim in Usd.PrimRange(root_prim):
        count += int(prim.HasAuthoredReferences())
        count += int(prim.HasAuthoredPayloads())
        count += int(prim.HasAuthoredInherits())
        count += int(prim.HasAuthoredSpecializes())
        count += len(prim.GetVariantSets().GetNames())
    return count


def _rebase_asset_paths(root_spec: Any, package_root: Path) -> None:
    for spec in _walk_specs(root_spec):
        for key in spec.ListInfoKeys():
            value = spec.GetInfo(key)
            rewritten = _rewrite_asset_value(value, package_root)
            if rewritten != value:
                spec.SetInfo(key, rewritten)


def _walk_specs(prim_spec: Any) -> Any:
    yield prim_spec
    for prop in prim_spec.properties:
        yield prop
    for child in prim_spec.nameChildren:
        yield from _walk_specs(child)


def _rewrite_asset_value(value: Any, package_root: Path) -> Any:
    from pxr import Sdf  # type: ignore

    if isinstance(value, Sdf.AssetPath):
        path = value.path
        if not path:
            return value
        parsed = urlparse(path)
        if parsed.scheme and parsed.scheme != "file":
            raise VRObjectMaterializationError(
                f"VR object contains a remote asset dependency: {path}"
            )
        resolved = Path(parsed.path if parsed.scheme == "file" else path)
        if not resolved.is_absolute():
            resolved = (package_root / resolved).resolve()
        else:
            resolved = resolved.resolve()
        try:
            relative = resolved.relative_to(package_root)
        except ValueError as exc:
            raise VRObjectMaterializationError(
                f"VR object dependency escapes the package: {path}"
            ) from exc
        return Sdf.AssetPath(relative.as_posix())
    if isinstance(value, list):
        return [_rewrite_asset_value(item, package_root) for item in value]
    if isinstance(value, tuple):
        return tuple(_rewrite_asset_value(item, package_root) for item in value)
    if isinstance(value, dict):
        return {
            key: _rewrite_asset_value(item, package_root)
            for key, item in value.items()
        }
    return value


def _validate_dependency_closure(scene_path: Path) -> set[Path]:
    try:
        from pxr import UsdUtils  # type: ignore
    except ImportError as exc:
        raise VRObjectMaterializationError(
            "VR dependency validation requires the USD Python runtime"
        ) from exc
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(scene_path))
    if unresolved:
        raise VRObjectMaterializationError(
            "VR scene has unresolved dependencies: "
            + ", ".join(sorted(str(item) for item in unresolved))
        )
    result = {
        Path(layer.realPath).resolve()
        for layer in layers
        if getattr(layer, "realPath", "")
    }
    result.update(Path(str(asset)).resolve() for asset in assets)
    return result


def _prune_unreferenced_usd_layers(
    *, scene_path: Path, dependency_roots: Sequence[Path]
) -> None:
    referenced = _validate_dependency_closure(scene_path)
    for root in dependency_roots:
        root = Path(root).resolve()
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in {".usd", ".usda", ".usdc", ".usdz"}
                and path.resolve() not in referenced
            ):
                path.unlink()


def _transform_maps_close(
    left: Mapping[str, Sequence[float]],
    right: Mapping[str, Sequence[float]],
    *,
    tolerance: float = 1e-8,
) -> bool:
    if set(left) != set(right):
        return False
    return all(
        len(left[path]) == len(right[path])
        and all(
            math.isclose(first, second, abs_tol=tolerance, rel_tol=tolerance)
            for first, second in zip(left[path], right[path], strict=True)
        )
        for path in left
    )


def _json_value(value: Any, *, asset_base: Path | None = None) -> Any:
    from pxr import Sdf  # type: ignore

    if isinstance(value, Sdf.AssetPath):
        path = value.path
        parsed = urlparse(path)
        if parsed.scheme:
            return {"asset": path}
        resolved = Path(path)
        if not resolved.is_absolute() and asset_base is not None:
            resolved = asset_base / resolved
        resolved = resolved.resolve()
        if resolved.is_file():
            return {"asset_sha256": sha256(resolved.read_bytes()).hexdigest()}
        return {"asset": resolved.as_posix()}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item, asset_base=asset_base)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_json_value(item, asset_base=asset_base) for item in value]
    try:
        return [_json_value(item, asset_base=asset_base) for item in value]
    except TypeError:
        return str(value)


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _mapping_list(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise VRObjectMaterializationError(f"{label} must be a list of mappings")
    return value
