"""Invoke ConvertAsset's triangle/ray probes to measure the visual receiver cavity."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


def measure(scene: Path, producer: Path) -> dict:
    sys.path.insert(0, str(producer))
    from convert_asset.simple_sdf_liquid_runtime import _ray_x_intersection, _triangles
    from pxr import Gf, Usd, UsdGeom

    stage = Usd.Stage.Open(str(scene))
    container = stage.GetPrimAtPath('/World/obj_receiver_flask')
    mesh_path = '/World/obj_receiver_flask/Visual/Source/mesh'
    inverse = UsdGeom.XformCache().GetLocalToWorldTransform(container).GetInverse()
    triangles = [tuple(tuple(inverse.Transform(Gf.Vec3d(*p))) for p in tri)
                 for tri in _triangles(stage, mesh_path)]
    vertical = [tuple((p[2], p[0], p[1]) for p in tri) for tri in triangles]
    floors = [v for tri in vertical if (v := _ray_x_intersection(1e-7, 2e-7, tri)) is not None and v < 0.025]
    if len(floors) < 2:
        raise ValueError('could not measure both inner and outer bottom surfaces')
    floor = max(floors)
    top, gap = 0.089, 0.00015
    levels = sorted({floor+gap, top,
                     *[floor+gap+(top-floor-gap)*i/64 for i in range(1,64)],
                     *[round(p[2], 7) for tri in triangles for p in tri if floor+gap < p[2] < top]})
    angular_rays = []
    for i in range(64):
        angle = 2*math.pi*i/64 + 1e-6
        c, s = math.cos(angle), math.sin(angle)
        angular_rays.append([tuple((c*p[0]+s*p[1], -s*p[0]+c*p[1], p[2]) for p in tri) for tri in triangles])
    profile = []
    maximum_gap = 0.0
    for z in levels:
        radii = []
        for rays in angular_rays:
            values = [x for tri in rays if (x := _ray_x_intersection(0.0, z, tri)) is not None and x > 1e-6]
            if not values:
                raise ValueError(f'no inner-wall hit at height {z}')
            radii.append(min(values))
        radius = min(radii)-gap
        if radius <= 0:
            raise ValueError('non-positive liquid radius')
        maximum_gap = max(maximum_gap, max(radii)-radius)
        profile.append([z, radius])
    return {'schema_version': 'scenario-forge-visual-cavity-profile/v1',
            'source_scene_sha256': sha256(scene.read_bytes()).hexdigest(),
            'source_mesh': mesh_path, 'measurement_frame': '/World/obj_receiver_flask',
            'method': 'ConvertAsset triangle/ray probes; 64 azimuths; conservative inner-wall rings',
            'producer': str(producer),
            'producer_probe_sha256': sha256((producer/'convert_asset/simple_sdf_liquid_runtime.py').read_bytes()).hexdigest(),
            'inner_floor_m': floor, 'wall_clearance_m': gap, 'maximum_sampled_wall_gap_m': maximum_gap,
            'surface_height_m': top, 'axial_profile_m': profile}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--producer', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = measure(args.scene, args.producer)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='axial_profile_m'}))
