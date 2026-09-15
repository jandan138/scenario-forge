import pytest
from pxr import Usd, UsdGeom

from scripts.clone_task09_powder_r5_3 import (
    DEFAULT_WALL_CONTACT_M,
    DEFAULT_WALL_REST_M,
    WALL_COUNT,
    patch_scene_config,
    patch_wall_collision_offsets,
)


MINI_USDA = '''#usda 1.0
def Xform "World"
{
    def Xform "obj_powder_bottle"
    {
        def Xform "Colliders"
        {
            def Mesh "Wall_00_00"
            {
                custom float physxCollision:contactOffset = 0.00005
                custom float physxCollision:restOffset = 0
            }
            def Mesh "Wall_07_31"
            {
                custom float physxCollision:contactOffset = 0.00005
                custom float physxCollision:restOffset = 0
            }
            def Mesh "Insert_05_00"
            {
                custom float physxCollision:contactOffset = 0.002
                custom float physxCollision:restOffset = 0.0004
            }
            def Mesh "Base"
            {
                custom float physxCollision:contactOffset = 0.00005
                custom float physxCollision:restOffset = 0
            }
        }
    }
}
'''


def test_r5_3_config_keeps_120hz_and_records_wall_offsets():
    cfg = patch_scene_config({
        'physics_hz': 120,
        'revision': 'r5.2',
        'status': 'candidate',
        'grain_contact_offset_m': 0.00025,
        'grain_rest_offset_m': 0.00015,
        'insert_contact_offset_m': 0.002,
        'insert_rest_offset_m': 0.0004,
        'qualified_runtime': 'Isaac Sim 4.5.0',
    })
    assert cfg['physics_hz'] == 120
    assert cfg['revision'] == 'r5.3'
    assert cfg['status'] == 'candidate'
    assert cfg['wall_contact_offset_m'] == DEFAULT_WALL_CONTACT_M
    assert cfg['wall_rest_offset_m'] == DEFAULT_WALL_REST_M
    assert cfg['grain_contact_offset_m'] == 0.00025
    assert cfg['insert_contact_offset_m'] == 0.002
    assert 'qualified_runtime' not in cfg


def test_wall_offsets_thicken_only_wall_meshes(tmp_path):
    path = tmp_path / 'scene.usda'
    path.write_text(MINI_USDA)
    count = patch_wall_collision_offsets(path, 2, 0.001, 0.0002)
    assert count == 2
    stage = Usd.Stage.Open(str(path))
    wall = stage.GetPrimAtPath('/World/obj_powder_bottle/Colliders/Wall_00_00')
    insert = stage.GetPrimAtPath('/World/obj_powder_bottle/Colliders/Insert_05_00')
    base = stage.GetPrimAtPath('/World/obj_powder_bottle/Colliders/Base')
    assert wall.GetAttribute('physxCollision:contactOffset').Get() == pytest.approx(0.001)
    assert wall.GetAttribute('physxCollision:restOffset').Get() == pytest.approx(0.0002)
    assert insert.GetAttribute('physxCollision:contactOffset').Get() == pytest.approx(0.002)
    assert insert.GetAttribute('physxCollision:restOffset').Get() == pytest.approx(0.0004)
    assert base.GetAttribute('physxCollision:contactOffset').Get() == pytest.approx(5e-5)
    assert UsdGeom.Mesh(stage.GetPrimAtPath('/World/obj_powder_bottle/Colliders/Wall_07_31'))


def test_wall_offsets_reject_wrong_count(tmp_path):
    path = tmp_path / 'scene.usda'
    path.write_text(MINI_USDA)
    with pytest.raises(ValueError):
        patch_wall_collision_offsets(path, WALL_COUNT, 0.001, 0.0002)
