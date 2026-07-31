from __future__ import annotations

from pathlib import Path
import runpy

import pytest


def _script_module() -> dict[str, object]:
    return runpy.run_path(
        str(
            Path(__file__).parents[1]
            / "scripts/generate_scientific_workbench_layout_prototypes.py"
        )
    )


def test_authored_state_layer_is_explicitly_static_and_package_relative(
    tmp_path: Path,
) -> None:
    module = _script_module()
    render = module["authored_state_layer_text"]
    base_scene = tmp_path / "package/scene/main.usda"
    layer_path = (
        tmp_path
        / "package/adapters/ebench/genmanip/evidence/authored_key_states/aligned/scene.usda"
    )

    text = render(
        base_scene=base_scene,
        layer_path=layer_path,
        poses={
            "/World/Beaker": {
                "xyz": [0.1, 0.2, 0.3],
                "wxyz": [1.0, 0.0, 0.0, 0.0],
            }
        },
    )

    assert str(base_scene) not in text
    assert "../../../../../../scene/main.usda" in text
    assert 'over "Beaker"' in text
    assert '"!resetXformStack!"' in text
    assert "cameraSettings" in text
    assert "scenarioForgeAuthoredStaticPreview = true" in text
    assert "metersPerUnit = 1" in text
    assert 'upAxis = "Z"' in text
    assert 'DomeLight "ScenarioForgePreviewDomeLight"' in text
    assert "orbitPosition" in text
    assert "orbitTarget" in text


@pytest.mark.parametrize(
    ("task_key", "state_id", "prim_path", "opening_height", "target_xy"),
    [
        (
            "task2",
            "cylinder_aligned_over_beaker",
            "/World/graduated_cylinder_03",
            0.2722941904,
            (0.30, -0.17),
        ),
        (
            "task13",
            "cylinder_aligned_to_funnel",
            "/World/graduated_cylinder_03",
            0.2722941904,
            (0.30, -0.20),
        ),
        (
            "task16",
            "sample_a_aligned",
            "/World/graduated_cylinder_03",
            0.2722941904,
            (0.28, -0.20),
        ),
        (
            "task16",
            "sample_b_aligned",
            "/World/conical_bottle03",
            0.1965674179,
            (0.28, -0.20),
        ),
    ],
)
def test_authored_pour_opening_is_projected_over_target(
    task_key: str,
    state_id: str,
    prim_path: str,
    opening_height: float,
    target_xy: tuple[float, float],
) -> None:
    module = _script_module()
    states = module["KEY_STATES"][task_key]
    state = next(item for item in states if item["id"] == state_id)
    pose = state["poses"][prim_path]
    w, x, y, z = pose["wxyz"]
    local = (0.0, 0.0, opening_height)
    rotated = (
        (1 - 2 * (y * y + z * z)) * local[0]
        + 2 * (x * y - z * w) * local[1]
        + 2 * (x * z + y * w) * local[2],
        2 * (x * y + z * w) * local[0]
        + (1 - 2 * (x * x + z * z)) * local[1]
        + 2 * (y * z - x * w) * local[2],
        2 * (x * z - y * w) * local[0]
        + 2 * (y * z + x * w) * local[1]
        + (1 - 2 * (x * x + y * y)) * local[2],
    )
    opening_xy = (
        pose["xyz"][0] + rotated[0],
        pose["xyz"][1] + rotated[1],
    )

    assert opening_xy == pytest.approx(target_xy, abs=1e-4)
