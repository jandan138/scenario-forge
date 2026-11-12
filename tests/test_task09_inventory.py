"""Support topology and completion regressions for the five-solid task."""
import pytest
from pathlib import Path
from types import SimpleNamespace

from scripts.task09_inventory import supported_inventory


def test_indirect_and_stacked_loads_are_counted_once():
    masses = {'boat': 10., 'a': .4, 'b': .6}
    edges = {'boat': {'pan'}, 'a': {'boat'}, 'b': {'boat', 'a'}}
    paths, gross = supported_inventory(masses, edges, 'pan')
    assert paths == {'boat', 'a', 'b'}
    assert gross == pytest.approx(11.)


def test_hovering_external_support_and_cycles_do_not_count():
    masses = dict(boat=10., a=1., b=1., spoon=20., c=1., d=1.)
    edges = {'boat': {'pan'}, 'a': {'boat', 'table'}, 'b': {'spoon'},
             'spoon': {'hand'}, 'c': {'d'}, 'd': {'c'}}
    assert supported_inventory(masses, edges, 'pan') == ({'boat'}, 10.)


def test_unloading_and_kinematic_hold_remove_descendants():
    masses = dict(boat=10., a=1.)
    edges = {'boat': {'pan'}, 'a': {'boat'}}
    assert supported_inventory(masses, edges, 'pan', excluded={'boat'}) == (set(), 0.)
    assert supported_inventory(masses, {'boat': set(), 'a': {'boat'}}, 'pan') == (set(), 0.)


def test_invalid_mass_is_rejected():
    with pytest.raises(ValueError):
        supported_inventory({'a': float('nan')}, {'a': {'pan'}}, 'pan')


def test_external_support_of_container_excludes_all_its_contents():
    assert supported_inventory({'boat': 10., 'a': 1.},
                               {'boat': {'pan', 'external_support'}, 'a': {'boat'}},
                               'pan') == (set(), 0.)


def test_sleeping_external_support_is_retained_and_moving_load_is_removed():
    import numpy as np
    namespace = {'BalanceRuntime': object, 'supported_inventory': supported_inventory}
    source = Path(__file__).resolve().parents[1]/'scripts/task09_inventory_runtime.py'
    exec(source.read_text(), namespace)
    runtime = namespace['Task09InventoryRuntime'].__new__(namespace['Task09InventoryRuntime'])
    runtime.np = np
    runtime.sensor_paths = runtime.paths = ['boat', 'sample']
    runtime.filters = ['pan', 'boat', 'sample']
    runtime.pan_path, runtime.boat_path = 'pan', 'boat'
    runtime.samples = {'sample'}
    runtime.masses = {'boat': 10., 'sample': 1.}
    runtime.handles = {'boat': 'boat', 'sample': 'sample'}
    for name in ('edge_gap', 'edge_positions', 'previous_supports', 'previous_positions', 'age'):
        setattr(runtime, name, {})
    positions = {'boat': [0, 0, 0], 'sample': [0, 0, .01]}
    runtime.dc = SimpleNamespace(
        get_rigid_body_linear_velocity=lambda _: SimpleNamespace(x=0., y=0., z=0.),
        get_rigid_body_pose=lambda p: SimpleNamespace(p=SimpleNamespace(
            **dict(zip(('x', 'y', 'z'), positions[p])))))
    runtime.stage = SimpleNamespace(GetPrimAtPath=lambda _: SimpleNamespace(
        GetAttribute=lambda _: SimpleNamespace(Get=lambda: False)))
    matrix = np.zeros((2, 3, 3))
    net = np.zeros((2, 3))
    runtime.contacts = SimpleNamespace(get_contact_force_matrix=lambda _: matrix,
                                       get_net_contact_forces=lambda _: net)
    runtime.put = lambda *_: None
    matrix[0, 0, 2] = .1
    matrix[1, 1, 2] = .01
    net[:, 2] = [.2, .01]  # Boat also rests on an untracked external support.
    assert runtime.measure_gross(None, .2) == 0.
    matrix[:] = 0.
    net[:] = 0.
    assert runtime.measure_gross(None, .2) == 0.  # Quiet contacts must not erase that exclusion.
    matrix[0, 0, 2] = .1
    matrix[1, 1, 2] = .01
    net[:, 2] = [.1, .01]
    assert runtime.measure_gross(None, .2) == 11.
    positions['sample'][2] = .1
    matrix[1] = 0.
    net[1] = 0.
    assert runtime.measure_gross(None, .2) == 10.
