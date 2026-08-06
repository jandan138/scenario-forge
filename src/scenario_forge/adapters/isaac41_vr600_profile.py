"""Shared Isaac Sim 4.1 runtime profile for eBench and VR collection.

The values mirror the Feishu VR task contract revision 600.  Keeping one
simulator-neutral mapping here prevents the two adapters from silently drifting.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PROFILE_ID = "manip/lift2/R5a_isaac41_vr600_v1"
RUNTIME_ROBOT_TYPE = "manip/lift2/R5a"
SOURCE_CONTRACT = "feishu:IWsNwtFX1iilwHkz5OGcnGyZnRd@600"

_PHYSX_SCENE_CONFIG: dict[str, Any] = {
    "BounceThreshold": 0.0,
    "BroadphaseType": "GPU",
    "CollisionSystem": "PCM",
    "EnableCCD": False,
    "EnableEnhancedDeterminism": False,
    "EnableExternalForcesEveryIteration": False,
    "EnableGPUDynamics": True,
    "EnableResidualReporting": False,
    "EnableSceneQuerySupport": True,
    "EnableStabilization": False,
    "FrictionCorrelationDistance": 0.02500000037252903,
    "FrictionOffsetThreshold": 0.03999999910593033,
    "FrictionType": "patch",
    "GpuCollisionStackSize": 67108864,
    "GpuFoundLostAggregatePairsCapacity": 10485760,
    "GpuFoundLostPairsCapacity": 262144,
    "GpuHeapCapacity": 67108864,
    "GpuMaxDeformableSurfaceContacts": 1048576,
    "GpuMaxHairContacts": 1048576,
    "GpuMaxNumPartitions": 8,
    "GpuMaxParticleContacts": 1048576,
    "GpuMaxRigidContactCount": 524288,
    "GpuMaxRigidPatchCount": 81920,
    "GpuMaxSoftBodyContacts": 1048576,
    "GpuTempBufferCapacity": 16777216,
    "GpuTotalAggregatePairsCapacity": 1024,
    "InvertCollisionGroupFilter": False,
    "MaxBiasCoefficient": float("inf"),
    "MaxPositionIterationCount": 255,
    "MaxVelocityIterationCount": 255,
    "MinPositionIterationCount": 1,
    "MinVelocityIterationCount": 0,
    "ReportKinematicKinematicPairs": False,
    "ReportKinematicStaticPairs": False,
    "SolverType": "TGS",
    "TimeStepsPerSecond": 60,
    "UpdateType": "Synchronous",
}

_ROBOT_MATERIAL = {
    "Restitution": 0.0,
    "DynamicFriction": 0.5,
    "StaticFriction": 0.5,
    "FrictionCombineMode": "max",
    "RestitutionCombineMode": "multiply",
    "ImprovePatchFriction": True,
}


def physx_scene_config() -> dict[str, Any]:
    return deepcopy(_PHYSX_SCENE_CONFIG)


def robot_material_config() -> dict[str, Any]:
    return deepcopy(_ROBOT_MATERIAL)


def genmanip_preprocess_config() -> list[dict[str, Any]]:
    return [
        {
            "type": "set_robot_physics_material",
            "robot_type": "lift2",
            "config": robot_material_config(),
        },
        {
            "type": "set_robot_contact_offset",
            "robot_type": "lift2",
            "config": 0.05,
        },
        {
            "type": "set_robot_rest_offset",
            "robot_type": "lift2",
            "config": 0.001,
        },
    ]


def vr_robot_contact_config() -> dict[str, Any]:
    return {
        "set_robot_physics_material": robot_material_config(),
        "set_robot_contact_offset": 0.05,
        "set_robot_rest_offset": 0.001,
    }
