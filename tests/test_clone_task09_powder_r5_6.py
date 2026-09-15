import pytest
from pxr import Usd

from scripts.clone_task09_powder_r5_6 import (
    CONTACT_DYNAMIC_FRICTION,
    CONTACT_STATIC_FRICTION,
    DEFAULT_SPOON_DYNAMIC_FRICTION,
    DEFAULT_SPOON_STATIC_FRICTION,
    POWDER_CONTACT_PATH,
    SPOON_BOWL_MATERIAL_PATH,
    SPOON_BOWL_MESH_PATH,
    SPOON_GRIP_MATERIAL_PATH,
    patch_scene_config,
    patch_spoon_bowl_friction,
)


MINI_USDA = '''#usda 1.0
def Xform "World"
{
    def Xform "obj_sampling_spoon"
    {
        def Xform "GeometryOffset"
        {
            def Xform "Normalize"
            {
                def Xform "Axis"
                {
                    def Xform "CategoryOrient"
                    {
                        def Xform "Model"
                        {
                            def Xform "textured_mesh"
                            {
                                def Mesh "textured_mesh"
                                {
                                    bool physics:collisionEnabled = 1
                                    rel material:binding:physics = </World/PowderLooks/Contact>
                                }
                            }
                        }
                    }
                }
            }
        }
        def Material "PhysicsMaterial" (
            apiSchemas = ["PhysicsMaterialAPI"]
        )
        {
            float physics:dynamicFriction = 0.3
            float physics:restitution = 0.04
            float physics:staticFriction = 0.4
        }
        def Scope "PhysicsCollision"
        {
            def Cube "SideGripProxyPositiveY"
            {
                rel material:binding:physics = </World/obj_sampling_spoon/PhysicsMaterial>
            }
        }
    }
    def Xform "obj_powder_bottle"
    {
        def Xform "Colliders"
        {
            def Mesh "Wall_00_00"
            {
                rel material:binding:physics = </World/PowderLooks/Contact>
            }
        }
    }
    def "PowderLooks"
    {
        def Material "Contact" (
            prepend apiSchemas = ["PhysicsMaterialAPI"]
        )
        {
            float physics:dynamicFriction = 0.5
            float physics:restitution = 0
            float physics:staticFriction = 0.65
        }
    }
}
'''


def test_r5_6_config_keeps_120hz_and_raises_bowl_friction_above_shared_contact():
    cfg = patch_scene_config({
        'physics_hz': 120,
        'revision': 'r5.5',
        'status': 'candidate',
        'powder_surface_target_m': 0.091,
        'insert_contact_offset_m': 0.003,
        'qualified_runtime': 'Isaac Sim 4.5.0',
    })
    assert cfg['physics_hz'] == 120
    assert cfg['revision'] == 'r5.6'
    assert cfg['powder_surface_target_m'] == 0.091
    assert cfg['insert_contact_offset_m'] == 0.003
    assert cfg['spoon_static_friction'] == DEFAULT_SPOON_STATIC_FRICTION
    assert cfg['spoon_dynamic_friction'] == DEFAULT_SPOON_DYNAMIC_FRICTION
    assert DEFAULT_SPOON_STATIC_FRICTION > CONTACT_STATIC_FRICTION
    assert DEFAULT_SPOON_DYNAMIC_FRICTION > CONTACT_DYNAMIC_FRICTION
    assert 'qualified_runtime' not in cfg


def test_r5_6_rejects_keeping_shared_contact_friction():
    with pytest.raises(ValueError):
        patch_scene_config(
            {'physics_hz': 120, 'revision': 'r5.5', 'powder_surface_target_m': 0.091},
            static_friction=CONTACT_STATIC_FRICTION,
            dynamic_friction=CONTACT_DYNAMIC_FRICTION,
        )


def test_bowl_rebind_does_not_change_shared_contact_or_grip(tmp_path):
    path = tmp_path / 'scene.usda'
    path.write_text(MINI_USDA)
    patched = patch_spoon_bowl_friction(path, 0.9, 0.7)
    assert patched == SPOON_BOWL_MATERIAL_PATH
    stage = Usd.Stage.Open(str(path))
    bowl = stage.GetPrimAtPath(SPOON_BOWL_MESH_PATH)
    wall = stage.GetPrimAtPath('/World/obj_powder_bottle/Colliders/Wall_00_00')
    grip = stage.GetPrimAtPath('/World/obj_sampling_spoon/PhysicsCollision/SideGripProxyPositiveY')
    contact = stage.GetPrimAtPath(POWDER_CONTACT_PATH)
    bowl_mat = stage.GetPrimAtPath(SPOON_BOWL_MATERIAL_PATH)
    grip_mat = stage.GetPrimAtPath(SPOON_GRIP_MATERIAL_PATH)
    assert [str(t) for t in bowl.GetRelationship('material:binding:physics').GetTargets()] == [SPOON_BOWL_MATERIAL_PATH]
    assert [str(t) for t in wall.GetRelationship('material:binding:physics').GetTargets()] == [POWDER_CONTACT_PATH]
    assert [str(t) for t in grip.GetRelationship('material:binding:physics').GetTargets()] == [SPOON_GRIP_MATERIAL_PATH]
    assert bowl_mat.GetAttribute('physics:staticFriction').Get() == pytest.approx(0.9)
    assert bowl_mat.GetAttribute('physics:dynamicFriction').Get() == pytest.approx(0.7)
    assert contact.GetAttribute('physics:staticFriction').Get() == pytest.approx(0.65)
    assert contact.GetAttribute('physics:dynamicFriction').Get() == pytest.approx(0.5)
    assert grip_mat.GetAttribute('physics:staticFriction').Get() == pytest.approx(0.4)


def test_bowl_rebind_rejects_missing_mesh(tmp_path):
    path = tmp_path / 'scene.usda'
    path.write_text('#usda 1.0\ndef Xform "World" {}\n')
    with pytest.raises(ValueError):
        patch_spoon_bowl_friction(path, 0.9, 0.7)
