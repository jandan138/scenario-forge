from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_r9_2_uses_world_x_opposed_socket_pair() -> None:
    source = (ROOT / "scripts/generate_scientific_workbench_task11_vr_r9_2.py").read_text()
    assert "PRIMARY_SOCKET = 0" in source
    assert "BALANCE_SOCKET = 12" in source
    assert 'release_id="r9_2"' in source
    assert "world_x_left_right_pair" in source
