import numpy as np

from scripts.render_task09_powder import load_recording


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
