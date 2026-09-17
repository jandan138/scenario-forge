import numpy as np
import pytest

from scripts.render_task09_powder import load_recording, recorded_powder_prototype


def test_replay_decompresses_each_state_array_only_once(tmp_path, monkeypatch):
    path = tmp_path/'states.npz'
    positions = np.arange(18,dtype=np.float32).reshape(3,2,3)
    np.savez_compressed(path,positions=positions,times=[0.,1.,2.])
    reads = []
    original = np.lib.npyio.NpzFile.__getitem__
    def tracked(archive,name):
        reads.append(name)
        return original(archive,name)
    monkeypatch.setattr(np.lib.npyio.NpzFile,'__getitem__',tracked)
    recording = load_recording(path)
    for _ in range(2):
        for frame in range(3):
            np.testing.assert_array_equal(recording['positions'][frame],positions[frame])
            assert recording['times'][frame]==frame
    assert sorted(reads)==['positions','times']


def test_pbd_replay_uses_visual_sphere_not_grain_mesh():
    spec = recorded_powder_prototype({
        'revision': 'r6.0',
        'powder_kind': 'pbd_solid',
        'grain_radius_m': 0.0007,
    })
    assert spec['kind'] == 'sphere'
    assert spec['radius_m'] == pytest.approx(0.0007)
    assert spec['display_color'] == (0.91, 0.82, 0.45)
    viscous = recorded_powder_prototype({
        'revision': 'r6.0',
        'powder_kind': 'pbd_viscous',
        'grain_radius_m': 0.0007,
    })
    assert viscous['kind'] == 'sphere'


def test_rigid_replay_still_copies_grain_mesh():
    assert recorded_powder_prototype({'revision': 'r5.7'})['kind'] == 'copy_mesh'
