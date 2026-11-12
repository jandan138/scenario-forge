"""Append to the source task14 controller; simulator imports stay in methods.

The source BalanceState, BalanceRuntime, button debounce and LCD are retained.
This class replaces only supported-mass discovery and task eligibility.
"""


class Task09InventoryRuntime(BalanceRuntime):  # noqa: F821
    def __init__(self, stage, root):
        import numpy as np
        from pxr import UsdPhysics
        super().__init__(stage, root)
        # Mass inventory does not need stale force magnitudes from sleeping
        # loads; allow ordinary bodies to sleep instead of waking them forever.
        self.weights = []
        self.np = np
        self.paths = []
        self.masses = {}
        self.handles = {}
        self.pan_path = root + '/Instance/WeighingPan'
        self.boat_path = str(self.prim.GetRelationship('balance:container').GetTargets()[0])
        self.samples = {str(p) for p in self.prim.GetRelationship('balance:samples').GetTargets()}
        for p in stage.Traverse():
            path = str(p.GetPath())
            if path.startswith(root + '/') or not p.HasAPI(UsdPhysics.RigidBodyAPI):
                continue
            if p.GetAttribute('physics:rigidBodyEnabled').Get() is False:
                continue
            mass = p.GetAttribute('physics:mass').Get()
            handle = self.dc.get_rigid_body(path)
            if mass is not None and mass > 0 and handle:
                self.paths.append(path)
                self.masses[path] = float(mass) * 1000
                self.handles[path] = handle
        self.filters = [self.pan_path, *self.paths, root+'/Instance/Body', '/World/table/*']
        self.contacts = self.sim.create_rigid_contact_view(
            self.paths, filter_patterns=[self.filters for _ in self.paths])
        self.sensor_paths = list(self.contacts.sensor_paths)
        self.edge_gap = {}
        self.edge_positions = {}
        self.previous_supports = {}
        self.previous_positions = {}
        self.age = {}
        self.accepted = set()
        self.boat_samples = set()
        self.raw_gross_g = 0.

    def eligible(self, pan_pose):
        return self.samples <= self.boat_samples

    def update(self, dt):
        if self.get('reset_requested'):
            self.edge_gap.clear()
            self.edge_positions.clear()
            self.previous_supports.clear()
            self.previous_positions.clear()
            self.age.clear()
            self.accepted.clear()
            self.boat_samples.clear()
        super().update(dt)

    def measure_gross(self, poses, dt):
        import json
        np = self.np
        matrix = self.contacts.get_contact_force_matrix(dt)
        net_forces = self.contacts.get_net_contact_forces(dt)
        supports = {}
        excluded = set()
        for i, path in enumerate(self.sensor_paths):
            v = self.dc.get_rigid_body_linear_velocity(self.handles[path])
            speed = (v.x*v.x + v.y*v.y + v.z*v.z)**.5
            prim = self.stage.GetPrimAtPath(path)
            if prim.GetAttribute('physics:kinematicEnabled').Get() is True:
                excluded.add(path)
            edges = set()
            position = self.dc.get_rigid_body_pose(self.handles[path]).p
            position = np.array([position.x, position.y, position.z])
            for j, target in enumerate(self.filters):
                if path == target:
                    continue
                key = (path, target)
                # Net force on the sensor must have an upward component.
                touching = float(matrix[i, j, 2]) > 1e-8
                gap = 0. if touching else self.edge_gap.get(key, 1.) + dt
                self.edge_gap[key] = gap
                if touching:
                    self.edge_positions[key] = position.copy()
                unchanged = (key in self.edge_positions and speed < 1e-7
                             and np.linalg.norm(position-self.edge_positions[key]) < 1e-5)
                if touching or (gap <= .10 and speed < .001) or unchanged:
                    edges.add(target)
            supports[path] = edges
            if float(net_forces[i, 2]-np.sum(matrix[i, :, 2])) > 1e-6:
                edges.add('external_support')
            if (speed < 1e-7 and np.linalg.norm(net_forces[i]) < 1e-9
                    and path in self.previous_positions
                    and np.linalg.norm(position-self.previous_positions[path]) < 1e-5):
                # Preserve external-support exclusions as well as pan edges
                # when an entirely quiet body stops publishing contacts.
                edges |= self.previous_supports.get(path, set())
            self.previous_supports[path] = edges.copy()
            self.previous_positions[path] = position.copy()
            self.age[path] = self.age.get(path, 0.) + dt if speed < .03 else 0.
        accepted, gross = supported_inventory(self.masses, supports, self.pan_path, excluded)  # noqa: F821
        # Count only settled loads. Removing a support invalidates descendants
        # immediately; prior contacts are retained only during quiet report gaps.
        unsettled = {p for p in accepted if self.age[p] < .15}
        accepted, gross = supported_inventory(  # noqa: F821
            self.masses, supports, self.pan_path, excluded | unsettled)
        self.accepted = accepted
        descendants = {self.boat_path} if self.boat_path in accepted else set()
        for _ in self.paths:
            descendants |= {p for p in accepted if supports.get(p) and supports[p] <= descendants}
        self.boat_samples = self.samples & descendants
        self.raw_gross_g = gross
        self.put('rigid_mass_g', gross)
        self.put('powder_mass_g', 0.)
        self.put('counted_particles', len(self.boat_samples))
        self.put('supported_sample_count', len(self.boat_samples))
        self.put('supported_paths', sorted(accepted))
        self.put('support_diagnostics', json.dumps({'supports': {p: sorted(v) for p, v in supports.items()},
                                                  'age': self.age, 'forces': matrix.tolist()}))
        self.put('contact_raw_gross_g', float(-np.sum(matrix[:, 0, 2])) / 9.81 * 1000)
        return gross


def compute(db):
    import omni.usd
    stage = omni.usd.get_context().get_stage()
    root = str(db.node.get_prim_path()).split('/BalanceRuntime/')[0]
    try:
        if db.per_instance_state.runtime is None:
            db.per_instance_state.runtime = Task09InventoryRuntime(stage, root)
        db.per_instance_state.runtime.update(float(db.inputs.deltaSeconds))
    except Exception as exc:
        from pxr import UsdGeom
        p = stage.GetPrimAtPath(root)
        for name, value in [('valid', False), ('stable', False), ('status', 'invalid'),
                            ('error', str(exc)), ('lcd_readout', '------')]:
            p.GetAttribute('balance:'+name).Set(value)
        base = root+'/Instance/Body/ControlPanel/LiveDigits'
        for i in range(8):
            for segment in 'abcdefg':
                item = stage.GetPrimAtPath(f'{base}/D{i}_{segment}')
                if item:
                    UsdGeom.Imageable(item).GetVisibilityAttr().Set(
                        'inherited' if segment == 'g' else 'invisible')
        db.per_instance_state.runtime = None
    return True
