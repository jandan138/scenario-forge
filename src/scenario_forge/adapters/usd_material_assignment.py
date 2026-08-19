"""Apply material recipes to USD assets (OpenUSD adapter).

Assigns recipe materials to every mesh in a USD file: part names are read
from each mesh's parent Xform, texture files are copied from the material
library into ``<out_dir>/textures/`` and referenced with anchored relative
paths. ``pxr`` is imported lazily, matching the adapter-layer convention.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from scenario_forge.assets.material_recipe import (
    MaterialRecipe,
    MaterialRecipeError,
    MaterialSpec,
    match_material,
    matching_rule,
)


def assign_materials(
    usd_path: str | Path,
    recipe: MaterialRecipe,
    library_root: str | Path,
    out_path: str | Path | None = None,
    *,
    textures_dirname: str = "textures",
) -> dict[str, object]:
    """Assign recipe materials to every mesh in a USD file.

    Returns an assignment report covering per-mesh bindings, unmatched
    (default-fallback) parts, created materials, and copied textures.
    """
    from pxr import Usd, UsdGeom, UsdShade

    source = Path(usd_path)
    stage = Usd.Stage.Open(str(source))
    if stage is None:
        raise MaterialRecipeError(f"cannot open USD stage: {source}")

    target = Path(out_path) if out_path is not None else source
    textures_dir = target.parent / textures_dirname

    scope_path = _materials_scope_path(stage)
    created: dict[str, object] = {}
    textures_copied: list[str] = []

    def material_for(name: str) -> object:
        if name not in created:
            created[name] = _create_material(
                stage,
                scope_path,
                recipe.materials[name],
                Path(library_root),
                textures_dir,
                textures_copied,
            )
        return created[name]

    assigned: list[dict[str, str]] = []
    unmatched: list[dict[str, str]] = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        part_name = _part_name_for(prim)
        material_name = match_material(recipe, part_name)
        material = material_for(material_name)
        UsdShade.MaterialBindingAPI(prim).Bind(material)
        assigned.append(
            {
                "mesh": str(prim.GetPath()),
                "part": part_name,
                "material": material_name,
            }
        )
        if matching_rule(recipe, part_name) is None:
            unmatched.append({"part": part_name, "material": material_name})

    if out_path is not None:
        # Sdf.Layer.Export preserves authored (relative) asset paths verbatim,
        # unlike Usd.Stage.Export which rebases them to absolute paths. This
        # keeps ./textures/... anchored next to the exported layer. The
        # single-layer assumption matches the procedural family inputs.
        stage.GetRootLayer().Export(str(target))
    else:
        stage.GetRootLayer().Save()

    return {
        "usd": str(source),
        "output": str(target),
        "recipe": recipe.name,
        "recipe_version": recipe.version,
        "assigned": assigned,
        "unmatched": unmatched,
        "materials_created": sorted(created),
        "textures_copied": sorted(textures_copied),
    }


def _materials_scope_path(stage: object) -> object:
    from pxr import Sdf, Usd

    assert isinstance(stage, Usd.Stage)
    default_prim = stage.GetDefaultPrim()
    if default_prim and default_prim.IsValid():
        return default_prim.GetPath().AppendChild("_materials")
    root = stage.GetPrimAtPath("/root")
    if root and root.IsValid():
        return Sdf.Path("/root/_materials")
    return Sdf.Path("/_materials")


def _part_name_for(mesh_prim: object) -> str:
    from pxr import Usd

    assert isinstance(mesh_prim, Usd.Prim)
    parent = mesh_prim.GetParent()
    if parent and parent.IsValid() and not parent.IsPseudoRoot():
        if parent.GetName() not in {"root", "Root"}:
            return parent.GetName()
    return mesh_prim.GetName()


def _create_material(
    stage: object,
    scope_path: object,
    spec: MaterialSpec,
    library_root: Path,
    textures_dir: Path,
    textures_copied: list[str],
) -> object:
    from pxr import Gf, Sdf, Usd, UsdShade

    assert isinstance(stage, Usd.Stage)
    assert isinstance(scope_path, Sdf.Path)
    material_path = scope_path.AppendChild(f"sf_{spec.name}")
    material = UsdShade.Material.Define(stage, material_path)
    surface = UsdShade.Shader.Define(stage, material_path.AppendChild("PreviewSurface"))
    surface.CreateIdAttr("UsdPreviewSurface")
    surface_output = surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(surface_output)

    if spec.kind == "parametric":
        if spec.diffuse_color is not None:
            surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
                Gf.Vec3f(*spec.diffuse_color)
            )
        if spec.roughness is not None:
            surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(spec.roughness)
        if spec.metallic is not None:
            surface.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(spec.metallic)
        if spec.clearcoat is not None:
            surface.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(spec.clearcoat)
            surface.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float).Set(0.1)
        return material

    st_reader = UsdShade.Shader.Define(stage, material_path.AppendChild("PrimvarST"))
    st_reader.CreateIdAttr("UsdPrimvarReader_float2")
    st_reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    st_result = st_reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    channel_inputs = {
        "color": ("diffuseColor", Sdf.ValueTypeNames.Color3f, "rgb", "sRGB"),
        "roughness": ("roughness", Sdf.ValueTypeNames.Float, "r", "raw"),
        "metallic": ("metallic", Sdf.ValueTypeNames.Float, "r", "raw"),
        "normal": ("normal", Sdf.ValueTypeNames.Normal3f, "rgb", "raw"),
    }
    for channel, relative in sorted(spec.textures.items()):
        input_name, value_type, output_name, color_space = channel_inputs[channel]
        copied = _copy_texture(library_root / relative, textures_dir)
        if copied not in textures_copied:
            textures_copied.append(copied)
        texture = UsdShade.Shader.Define(
            stage, material_path.AppendChild(f"Texture_{channel}")
        )
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(
            Sdf.AssetPath(f"./{textures_dir.name}/{Path(relative).name}")
        )
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set(color_space)
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(st_result)
        texture_output = texture.CreateOutput(output_name, value_type)
        surface.CreateInput(input_name, value_type).ConnectToSource(texture_output)
    return material


def _copy_texture(source: Path, textures_dir: Path) -> str:
    if not source.exists():
        raise MaterialRecipeError(f"texture file missing from library: {source}")
    textures_dir.mkdir(parents=True, exist_ok=True)
    target = textures_dir / source.name
    if not target.exists() or target.read_bytes() != source.read_bytes():
        shutil.copyfile(source, target)
    return f"{textures_dir.name}/{source.name}"
