"""USD snapshots for the five fixed visual regions; no simulator imports."""
from hashlib import sha256
import json


def capture_visual(stage, tube):
    from pxr import Usd
    paths = tube.GetRelationship('fehlings:layerShaders').GetTargets()
    layers = []
    for path in paths:
        shader = stage.GetPrimAtPath(path)
        layers.append(dict(color=list(shader.GetAttribute('inputs:diffuseColor').Get()),
                           opacity=shader.GetAttribute('inputs:opacity').Get(),
                           roughness=shader.GetAttribute('inputs:roughness').Get()))
    visual = stage.GetPrimAtPath(str(tube.GetPath())+'/VisualLiquid')
    geometry = {str(p.GetPath()): dict(attributes={a.GetName():str(a.Get()) for a in p.GetAttributes()},
                                      relationships={r.GetName():[str(v) for v in r.GetTargets()] for r in p.GetRelationships()})
                for p in Usd.PrimRange(visual) if '/Looks' not in str(p.GetPath())}
    return dict(layers=layers,layer_progress=list(tube.GetAttribute('fehlings:layer_progress').Get()),
                layer_bounds_m=[list(v) for v in tube.GetAttribute('fehlings:layer_bounds_m').Get()],
                geometry_sha256=sha256(json.dumps(geometry,sort_keys=True).encode()).hexdigest())
