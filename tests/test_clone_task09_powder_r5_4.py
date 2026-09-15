import pytest
from pxr import Usd

from scripts.clone_task09_powder_r5_4 import (
    DEFAULT_INSERT_CONTACT_M,
    DEFAULT_INSERT_REST_M,
    INSERT_COUNT,
    patch_insert_collision_offsets,
    patch_scene_config,
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
                custom float physxCollision:contactOffset = 0.001
                custom float physxCollision:restOffset = 0.0002
            }
            def Mesh "Insert_05_00"
            {
                custom float physxCollision:contactOffset = 0.002
                custom float physxCollision:restOffset = 0.0004
            }
            def Mesh "Insert_05_31"
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


def test_r5_4_config_keeps_120hz_and_thickens_insert():
    cfg = patch_scene_config({
        'physics_hz': 120,
        'revision': 'r5.3',
        'status': 'candidate',
        'wall_contact_offset_m': 0.001,
        'insert_contact_offset_m': 0.002,
        'insert_rest_offset_m': 0.0004,
        'qualified_runtime': 'Isaac Sim 4.5.0',
    })
    assert cfg['physics_hz'] == 120
    assert cfg['revision'] == 'r5.4'
    assert cfg['insert_contact_offset_m'] == DEFAULT_INSERT_CONTACT_M
    assert cfg['insert_rest_offset_m'] == DEFAULT_INSERT_REST_M
    assert cfg['wall_contact_offset_m'] == 0.001
    assert 'qualified_runtime' not in cfg


def test_insert_offsets_thicken_only_insert_meshes(tmp_path):
    path = tmp_path / 'scene.usda'
    path.write_text(MINI_USDA)
    count = patch_insert_collision_offsets(path, 2, 0.003, 0.0006)
    assert count == 2
    stage = Usd.Stage.Open(str(path))
    insert = stage.GetPrimAtPath('/World/obj_powder_bottle/Colliders/Insert_05_00')
    wall = stage.GetPrimAtPath('/World/obj_powder_bottle/Colliders/Wall_00_00')
    base = stage.GetPrimAtPath('/World/obj_powder_bottle/Colliders/Base')
    assert insert.GetAttribute('physxCollision:contactOffset').Get() == pytest.approx(0.003)
    assert insert.GetAttribute('physxCollision:restOffset').Get() == pytest.approx(0.0006)
    assert wall.GetAttribute('physxCollision:contactOffset').Get() == pytest.approx(0.001)
    assert base.GetAttribute('physxCollision:contactOffset').Get() == pytest.approx(5e-5)


def test_insert_offsets_reject_wrong_count(tmp_path):
    path = tmp_path / 'scene.usda'
    path.write_text(MINI_USDA)
    with pytest.raises(ValueError):
        patch_insert_collision_offsets(path, INSERT_COUNT, 0.003, 0.0006)
