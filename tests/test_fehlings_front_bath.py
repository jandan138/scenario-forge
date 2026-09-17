import math

import numpy as np
import pytest


def test_front_bath_looks_at_lower_sample_from_workbench_front():
    from scripts.render_fehlings_water_bath import front_bath_view

    tube = np.array([0.3715, -0.0279, 0.9101])
    name, position, target, focal = front_bath_view(tube)
    assert name == 'front_bath'
    position = np.asarray(position, dtype=float)
    target = np.asarray(target, dtype=float)
    offset = position - target
    assert offset[1] < 0
    distance = float(np.linalg.norm(offset))
    assert 0.25 <= distance <= 0.35
    assert target[2] == pytest.approx(tube[2] + 0.018)
    assert math.degrees(math.asin(offset[2] / distance)) < 15
    assert focal >= 50
