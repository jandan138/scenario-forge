import math


def test_paper_open_views_frame_the_oven_from_the_front_left():
    from scripts.render_lab2sim_oven_retake import OVEN_BOUND, paper_open_views

    low, high = OVEN_BOUND
    views = paper_open_views()

    assert [view[0] for view in views] == [
        "hero_open_threequarter",
        "hero_open_wide",
        "hero_open_tight",
    ]
    for _name, position, target, focal in views:
        # Target sits inside the oven's x/z envelope and just in front of it,
        # where the swung-open door lives.
        assert low[0] <= target[0] <= high[0]
        assert low[2] <= target[2] <= high[2]
        assert target[1] < low[1] + 0.2
        # Camera is in front (-y) and to the left (-x) of the oven, above it.
        assert position[1] < low[1]
        assert position[0] < low[0]
        assert position[2] > high[2]
        elevation = math.degrees(
            math.asin((position[2] - target[2]) / math.dist(position, target))
        )
        assert 12.0 <= elevation <= 25.0
        assert 24.0 <= focal <= 30.0


def test_oven_retake_is_camera_only():
    from scripts.render_lab2sim_oven_retake import DOOR_HINGE, EXPOSURE_MULTIPLIER

    assert DOOR_HINGE == "/World/obj_oven/Instance/Joints/DoorHinge"
    assert 1.0 <= EXPOSURE_MULTIPLIER <= 1.2
