from collections import Counter
import math

from scripts.generate_traditional_titration_vr_r13 import closed_liquid_mesh, liquid_normals, water_controller
from scripts.validate_traditional_titration_vr_r1 import evaluate_report


def test_liquid_is_closed_and_follows_tapered_profile():
    points, counts, indices = closed_liquid_mesh([[0.004, 0.039], [0.04, 0.034], [0.089, 0.024]])
    edges = Counter()
    cursor = 0
    for count in counts:
        face = indices[cursor:cursor+count]
        cursor += count
        for a, b in zip(face, face[1:]+face[:1]):
            edges[tuple(sorted((a, b)))] += 1
    assert set(edges.values()) == {2}
    assert abs(min(p[2] for p in points) - 0.004) < 1e-9
    assert abs(max(p[2] for p in points) - 0.089) < 1e-9
    assert points[0][0] > points[-66][0]


def test_controller_updates_transmission_color_without_changing_flow_logic():
    source = '''colorless = (0.92, 0.97, 1.0)
pale = (1.0, 0.48, 0.65)
deep = (0.75, 0.02, 0.2)
for name in ("inputs:diffuseColor", "inputs:baseColor"):
    pass
success = hold >= 3.0 and visited_open and visited_fine and visited_drip and not overshoot
'''
    updated = water_controller(source)
    assert 'inputs:glass_color' in updated
    assert '(0.97, 0.99, 1.0)' in updated
    assert source.splitlines()[-1] == updated.splitlines()[-1]


def test_material_reset_is_required_when_transmissive_liquid_is_present():
    report = {'liquid_material': {'initial': [[0.97, 0.99, 1.0]],
                                'endpoint': [[1.0, 0.80, 0.88]],
                                'reset': [[1.0, 0.80, 0.88]]}}
    assert evaluate_report(report)['checks']['liquid_material_reset'] is False
    report['liquid_material']['reset'] = [[0.97, 0.99, 1.0]]
    assert evaluate_report(report)['checks']['liquid_material_reset'] is True


def test_liquid_normals_are_smooth_on_sides_and_keep_surface_separate():
    profile = [[0.004, 0.039], [0.04, 0.034], [0.089, 0.024]]
    points, counts, indices = closed_liquid_mesh(profile)
    normals = liquid_normals(profile, counts, indices)
    assert len(normals) == len(indices)
    assert all(abs(math.sqrt(sum(x*x for x in n))-1) < 1e-8 for n in normals)
    assert normals[-1] == (0.0, 0.0, 1.0)
    assert normals[0][0] > 0.9
