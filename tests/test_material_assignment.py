from __future__ import annotations

from pathlib import Path

import pytest

from scenario_forge.assets.material_recipe import (
    MaterialRecipeError,
    load_recipe,
    match_material,
    matching_rule,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RECIPE_PATH = REPO_ROOT / "configs" / "material_recipes" / "drying_box_v1.yaml"

# Semantic part names observed across the ten drying_box family assets
# (external_artifacts/incoming/drying_box). The recipe must assign every one
# of these through an explicit rule, never through the default fallback.
FAMILY_PART_NAMES = (
    "base", "blower_rotor", "cabinet_caster_swivel", "cabinet_caster_wheel",
    "carriage", "caster_fl_brake", "caster_fl_swivel", "caster_fl_wheel",
    "caster_fr_brake", "caster_fr_swivel", "caster_fr_wheel", "caster_rl_swivel",
    "caster_rl_wheel", "caster_rr_swivel", "caster_rr_wheel", "chimney_damper",
    "circulation_fan_rotor", "clamp", "control_knob", "disconnect_handle",
    "door", "door_latch", "drop_door", "emergency_stop", "exhaust_damper",
    "foot_fl", "foot_fr", "foot_rl", "foot_rr", "fresh_air_damper",
    "front_door", "front_latch", "front_valve_knob", "gauge_needle",
    "green_button", "hepa_blower_rotor", "latch_actuator_rod", "latch_left",
    "latch_right", "left_door", "left_latch", "locking_handwheel",
    "lower_control_knob", "lower_dial", "lower_door", "lower_fan_rotor",
    "lower_latch_cam", "lower_pushbutton", "lower_shelf",
    "lower_toggle_handle", "main_door", "panel_gauge_needle", "power_button",
    "power_rocker", "pressure_door", "pump_rotor", "purge_gauge_needle",
    "rail_stage1", "rear_door", "rear_latch", "red_button", "refractory_door",
    "regulator_knob", "right_door", "right_latch", "service_drawer", "shelf",
    "shelf_lower", "shelf_upper", "side_fan_rotor", "start_button",
    "stop_button", "temperature_needle", "thermostat_knob",
    "top_gauge_needle", "tray", "trolley", "trolley_caster_swivel",
    "trolley_caster_wheel", "upper_control_knob", "upper_dial", "upper_door",
    "upper_fan_rotor", "upper_latch_cam", "upper_pushbutton", "upper_shelf",
    "upper_toggle_handle",
)


def _write_recipe(tmp_path: Path, body: str) -> Path:
    recipe_path = tmp_path / "recipe.yaml"
    recipe_path.write_text(body, encoding="utf-8")
    return recipe_path


def test_load_recipe_rejects_rule_referencing_unknown_material(tmp_path: Path) -> None:
    recipe_path = _write_recipe(
        tmp_path,
        """
name: bad
version: 1
default_material: steel
materials:
  steel: {kind: parametric, diffuse_color: [0.5, 0.5, 0.5], roughness: 0.4, metallic: 1.0}
rules:
  - {pattern: "door", material: ghost}
""",
    )
    with pytest.raises(MaterialRecipeError, match="ghost"):
        load_recipe(recipe_path)


def test_load_recipe_rejects_unknown_default_material(tmp_path: Path) -> None:
    recipe_path = _write_recipe(
        tmp_path,
        """
name: bad
version: 1
default_material: ghost
materials:
  steel: {kind: parametric, diffuse_color: [0.5, 0.5, 0.5], roughness: 0.4, metallic: 1.0}
rules: []
""",
    )
    with pytest.raises(MaterialRecipeError, match="ghost"):
        load_recipe(recipe_path)


def test_load_recipe_rejects_unknown_material_kind(tmp_path: Path) -> None:
    recipe_path = _write_recipe(
        tmp_path,
        """
name: bad
version: 1
default_material: steel
materials:
  steel: {kind: holographic}
rules: []
""",
    )
    with pytest.raises(MaterialRecipeError, match="holographic"):
        load_recipe(recipe_path)


def test_match_material_first_rule_wins() -> None:
    recipe = load_recipe(RECIPE_PATH)
    # "door_latch" contains "door"; the latch rule is earlier and must win.
    assert match_material(recipe, "door_latch") == "chrome"
    assert match_material(recipe, "main_door") == "powder_coat_light"


def test_match_material_is_case_insensitive() -> None:
    recipe = load_recipe(RECIPE_PATH)
    assert match_material(recipe, "Red_Button") == "button_red"


def test_match_material_falls_back_to_default() -> None:
    recipe = load_recipe(RECIPE_PATH)
    assert match_material(recipe, "mystery_widget") == recipe.default_material


def test_family_part_names_never_hit_default() -> None:
    recipe = load_recipe(RECIPE_PATH)
    unmatched = [
        name for name in FAMILY_PART_NAMES if matching_rule(recipe, name) is None
    ]
    assert unmatched == []


def test_family_recipe_expectations() -> None:
    recipe = load_recipe(RECIPE_PATH)
    expected = {
        "base": "powder_coat_light",
        "main_door": "powder_coat_light",
        "pressure_door": "stainless_brushed",
        "refractory_door": "stainless_brushed",
        "shelf": "stainless_brushed",
        "tray": "stainless_brushed",
        "circulation_fan_rotor": "stainless_brushed",
        "exhaust_damper": "stainless_brushed",
        "red_button": "button_red",
        "stop_button": "button_red",
        "emergency_stop": "button_red",
        "start_button": "button_green",
        "green_button": "button_green",
        "gauge_needle": "needle_red",
        "thermostat_knob": "plastic_black",
        "upper_dial": "dial_aluminum",
        "caster_fl_wheel": "rubber_black",
        "foot_fl": "rubber_black",
        "caster_fl_swivel": "zinc_steel",
        "caster_fl_brake": "zinc_steel",
        "clamp": "chrome",
        "locking_handwheel": "chrome",
        "trolley": "stainless_brushed",
        "carriage": "zinc_steel",
    }
    for part_name, material in expected.items():
        assert match_material(recipe, part_name) == material, part_name


FIXTURE_USDA = """#usda 1.0
(
    defaultPrim = "root"
    metersPerUnit = 0.01
    upAxis = "Y"
)

def Xform "root"
{
    def Xform "group_0"
    {
        def Xform "base"
        {
            def Mesh "mesh_0"
            {
                int[] faceVertexCounts = [3]
                int[] faceVertexIndices = [0, 1, 2]
                point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
                float2[] primvars:st = [(0, 0), (1, 0), (0, 1)]
            }
        }
    }

    def Xform "group_1"
    {
        def Xform "shelf"
        {
            def Mesh "mesh_0"
            {
                int[] faceVertexCounts = [3]
                int[] faceVertexIndices = [0, 1, 2]
                point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
                float2[] primvars:st = [(0, 0), (1, 0), (0, 1)]
            }
        }
    }

    def Xform "group_2"
    {
        def Xform "red_button"
        {
            def Mesh "mesh_0"
            {
                int[] faceVertexCounts = [3]
                int[] faceVertexIndices = [0, 1, 2]
                point3f[] points = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
                float2[] primvars:st = [(0, 0), (1, 0), (0, 1)]
            }
        }
    }
}
"""


def _write_fake_library(root: Path) -> None:
    for channel in ("Color", "NormalGL", "Roughness", "Metalness"):
        texture = root / "Metal009" / f"Metal009_1K-JPG_{channel}.jpg"
        texture.parent.mkdir(parents=True, exist_ok=True)
        texture.write_bytes(b"\xff\xd8\xff\xd9")
    for channel in ("Color", "NormalGL", "Roughness"):
        texture = root / "PowderCoatLight_SF" / f"PowderCoatLight_SF_1K_{channel}.jpg"
        texture.parent.mkdir(parents=True, exist_ok=True)
        texture.write_bytes(b"\xff\xd8\xff\xd9")


def test_assign_materials_to_fixture_stage(tmp_path: Path) -> None:
    Usd = pytest.importorskip("pxr.Usd", reason="material assignment requires OpenUSD")
    UsdShade = pytest.importorskip(
        "pxr.UsdShade", reason="material assignment requires OpenUSD"
    )
    from scenario_forge.adapters.usd_material_assignment import assign_materials

    usd_path = tmp_path / "oven.usda"
    usd_path.write_text(FIXTURE_USDA, encoding="utf-8")
    library_root = tmp_path / "library"
    _write_fake_library(library_root)
    out_path = tmp_path / "oven_textured.usda"

    recipe = load_recipe(RECIPE_PATH)
    report = assign_materials(usd_path, recipe, library_root, out_path)

    assert report["recipe"] == "drying_box_v1"
    assert report["unmatched"] == []
    assigned = {entry["part"]: entry["material"] for entry in report["assigned"]}
    assert assigned == {
        "base": "powder_coat_light",
        "shelf": "stainless_brushed",
        "red_button": "button_red",
    }

    stage = Usd.Stage.Open(str(out_path))
    bound: dict[str, str] = {}
    for prim in stage.Traverse():
        if prim.GetTypeName() != "Mesh":
            continue
        binding = UsdShade.MaterialBindingAPI(prim).GetDirectBinding()
        material_path = binding.GetMaterialPath()
        assert material_path, f"no material bound on {prim.GetPath()}"
        bound[prim.GetParent().GetName()] = str(material_path)
        material = UsdShade.Material(stage.GetPrimAtPath(material_path))
        assert material.GetSurfaceOutput().GetConnectedSources()

    assert bound["base"].endswith("powder_coat_light")
    assert bound["shelf"].endswith("stainless_brushed")
    assert bound["red_button"].endswith("button_red")

    def preview_surface(material_path: str) -> object:
        material_prim = stage.GetPrimAtPath(material_path)
        for child in material_prim.GetChildren():
            shader = UsdShade.Shader(child)
            if shader and shader.GetIdAttr().Get() == "UsdPreviewSurface":
                return shader
        raise AssertionError(f"no UsdPreviewSurface under {material_path}")

    red_surface = preview_surface(bound["red_button"])
    assert tuple(red_surface.GetInput("diffuseColor").Get()) == pytest.approx((0.5, 0.02, 0.02))
    assert red_surface.GetInput("metallic").Get() == 0.0

    steel_prim = stage.GetPrimAtPath(bound["shelf"])
    texture_shaders = [
        UsdShade.Shader(child) for child in steel_prim.GetChildren()
        if child.GetTypeName() == "Shader" and UsdShade.Shader(child).GetIdAttr().Get() == "UsdUVTexture"
    ]
    assert texture_shaders, "stainless_brushed must wire texture files"
    file_values = {
        shader.GetInput("file").Get().path for shader in texture_shaders
    }
    assert all(value.startswith("./textures/") for value in file_values)
    copied = sorted((tmp_path / "textures").iterdir())
    assert {path.name for path in copied} >= {
        "Metal009_1K-JPG_Color.jpg",
        "Metal009_1K-JPG_Roughness.jpg",
        "Metal009_1K-JPG_NormalGL.jpg",
        "Metal009_1K-JPG_Metalness.jpg",
        "PowderCoatLight_SF_1K_Color.jpg",
        "PowderCoatLight_SF_1K_NormalGL.jpg",
        "PowderCoatLight_SF_1K_Roughness.jpg",
    }
    assert len(report["textures_copied"]) == 7
