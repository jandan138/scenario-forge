"""Embedded SDK bridge appended to task10_pbd_policy, never imported by core."""


class Task10PbdRuntime:
    def __init__(self, stage, root):
        import json
        import numpy as np
        from pxr import UsdGeom
        from omni.isaac.dynamic_control import _dynamic_control
        self.stage, self.root = stage, root
        self.prim = stage.GetPrimAtPath(root)
        self.config = json.loads(self.prim.GetAttribute('titration:pbd_config').Get())
        prefix = root.rsplit('/obj_titration_station',1)[0]
        for item in self.config['systems'].values():
            for key in ('system_path','particle_path','material_path'):
                item[key] = prefix+item[key][len('/World'):]
        self.np = np
        self.dc = _dynamic_control.acquire_dynamic_control_interface()
        self.ledger = TitrationLedger(self.config['particle_volume_ml'],  # noqa: F821
                                     self.config['systems']['Source']['initial_volume_ml'])
        self.sets = {name: UsdGeom.Points(stage.GetPrimAtPath(item['particle_path']))
                     for name, item in self.config['systems'].items()}
        self.initial = {name: np.array(p.GetPrim().GetAttribute('titration:initial_points').Get(), dtype=np.float32).reshape(-1,3)
                        for name,p in self.sets.items()}
        self.initial_velocities = {}
        for name,geom in self.sets.items():
            attr = geom.GetPrim().GetAttribute('titration:initial_velocities')
            velocity = np.array(attr.Get(),dtype=np.float32).reshape(-1,3) if attr and attr.HasAuthoredValueOpinion() else np.zeros_like(self.initial[name])
            if velocity.shape != self.initial[name].shape:
                raise RuntimeError('Initial particle position/velocity arrays differ: '+name)
            self.initial_velocities[name] = velocity
        self.falling_ids = []
        self.receiver_dose_ids = []
        self.initial_receiver_n = len(self.initial['Receiver'])
        self.mass = self.config['per_particle_mass_kg']
        self.spacing = self.config['particle_spacing_m']
        self.mouth_z = self.config['receiver_mouth_local_z_m']
        self.mouth_radius = self.config['receiver_mouth_radius_m']
        self.cavity_profile = np.array(self.config['systems']['Receiver']['cavity_profile_local_m'])
        self.contact_distance = 2*self.config['particle_system_parameters']['Receiver']['particleContactOffset']
        self.receiver_path = prefix+'/obj_receiver_flask'
        self.body_path = root+'/Instance/Burette/body_link'
        self.emit_local = self.config['emit_body_local_m']
        self.shader = stage.GetPrimAtPath(self.config['systems']['Receiver']['material_path']+'/Shader')
        self.previous_falling_points = {}
        self.previous_receiver_pose = None
        self.mouth_entered = set()
        self.last_color = None
        self.last_error = ''

    def put(self, name, value):
        self.prim.GetAttribute('titration:'+name).Set(value)

    def read(self, name):
        points = self.np.array(self.sets[name].GetPointsAttr().Get(), dtype=self.np.float32).reshape(-1,3)
        velocities = self.np.array(self.sets[name].GetVelocitiesAttr().Get(), dtype=self.np.float32).reshape(-1,3)
        if points.shape != velocities.shape or not self.np.isfinite(points).all() or not self.np.isfinite(velocities).all():
            raise RuntimeError('Invalid live particle arrays: '+name)
        return points, velocities

    def write(self, name, points, velocities, ids=None):
        from pxr import Vt, UsdPhysics, Sdf
        geom = self.sets[name]
        points = self.np.asarray(points, dtype=self.np.float32).reshape(-1,3)
        velocities = self.np.asarray(velocities, dtype=self.np.float32).reshape(-1,3)
        if points.shape != velocities.shape:
            raise RuntimeError('Particle positions and velocities differ')
        # One USD change block prevents transient inconsistent array lengths.
        with Sdf.ChangeBlock():
            geom.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(points))
            geom.GetVelocitiesAttr().Set(Vt.Vec3fArray.FromNumpy(velocities))
            item = self.config['systems'][name]
            spacing = item.get('particle_spacing_m',self.spacing)
            mass = item.get('per_particle_mass_kg',self.mass)
            geom.GetWidthsAttr().Set(Vt.FloatArray([spacing]*len(points)))
            geom.GetIdsAttr().Set(Vt.Int64Array(list(range(len(points))) if ids is None else ids))
            UsdPhysics.MassAPI(geom.GetPrim()).GetMassAttr().Set(mass*len(points))
            if name == 'Falling':
                system = self.stage.GetPrimAtPath(item['system_path'])
                system.GetAttribute('physxParticleIsosurface:isosurfaceEnabled').Set(bool(len(points)))

    def pose(self, path):
        from pxr import Gf
        handle = self.dc.get_rigid_body(path)
        if not handle:
            raise RuntimeError('Rigid pose unavailable: '+path)
        pose = self.dc.get_rigid_body_pose(handle)
        return (self.np.array([pose.p.x,pose.p.y,pose.p.z]),
                self.np.array(Gf.Matrix3d(Gf.Quatd(pose.r.w,Gf.Vec3d(pose.r.x,pose.r.y,pose.r.z)))))

    def reset(self):
        for name, points in self.initial.items():
            self.write(name, points, self.initial_velocities[name])
        self.ledger.reset()
        self.falling_ids = []
        self.receiver_dose_ids = []
        self.previous_falling_points.clear()
        self.previous_receiver_pose = None
        self.mouth_entered = set()
        self.last_color = None
        self.put('reset_requested',False)

    def update(self, dt):
        import math
        if not math.isfinite(dt):
            raise ValueError('Nonfinite physical step')
        if dt <= 0:
            return
        expected = self.config['runtime_contract']['physics_dt']
        if abs(dt-expected)>1e-8:
            raise ValueError(f'Unexpected physical step: {dt}; task requires {expected}')
        from pxr import Gf
        if self.prim.GetAttribute('titration:reset_requested').Get():
            self.reset()
        articulation = self.dc.get_articulation(self.root)
        dof = self.dc.find_articulation_dof(articulation,'stopcock_joint') if articulation else 0
        if not dof:
            raise RuntimeError('Live stopcock joint unavailable')
        angle = min(90., abs(math.degrees(self.dc.get_dof_position(dof))))
        np = self.np
        falling, fall_vel = self.read('Falling')
        if len(falling) != len(self.falling_ids):
            raise RuntimeError('Falling particle IDs do not match live data')
        receiver_pos, receiver_rot = self.pose(self.receiver_path)
        local = (falling-receiver_pos) @ receiver_rot.T
        # Require a real downward crossing of the mouth plane. Being below
        # the rim after traversing a wall is not a valid reagent admission.
        previous = np.array([self.previous_falling_points.get(pid,point)
                             for pid,point in zip(self.falling_ids,falling)],dtype=float).reshape(-1,3)
        previous_pos,previous_rot = self.previous_receiver_pose or (receiver_pos,receiver_rot)
        previous_local = (previous-previous_pos) @ previous_rot.T
        denominator = previous_local[:,2]-local[:,2]
        fraction = np.divide(previous_local[:,2]-self.mouth_z,denominator,
                             out=np.zeros(len(falling)),where=denominator!=0)
        crossing = previous_local+(local-previous_local)*fraction[:,None]
        crossed = ((previous_local[:,2] >= self.mouth_z) & (local[:,2] < self.mouth_z)
                   & (np.linalg.norm(crossing[:,:2],axis=1) < self.mouth_radius))
        self.mouth_entered.update(pid for pid,yes in zip(self.falling_ids,crossed) if yes)
        radius = np.interp(local[:,2],self.cavity_profile[:,0],self.cavity_profile[:,1])
        within_cavity = ((local[:,2]>self.config['receiver_floor_local_z_m'])
                         & (local[:,2]<self.mouth_z) & (np.linalg.norm(local[:,:2],axis=1)<radius))
        eligible = np.array([pid in self.mouth_entered for pid in self.falling_ids],dtype=bool) & within_cavity
        inside = np.zeros(len(falling),dtype=bool)
        receiver_data = None
        if eligible.any():
            receiver_data = self.read('Receiver')
            inside[eligible] = touching_receiver_bulk(  # noqa: F821
                falling[eligible],receiver_data[0],self.initial_receiver_n,receiver_pos,receiver_rot[2,:],
                self.contact_distance,self.spacing*.8)
        received = [pid for pid,yes in zip(self.falling_ids,inside) if yes]
        # A dose that passes below the mouth outside its aperture missed the
        # receiver, including liquid landing on the stirrer above flask-floor Z.
        spilled_mask = (~inside) & (~within_cavity) & (local[:,2] < self.mouth_z-2*self.spacing)
        spilled = [pid for pid,yes in zip(self.falling_ids,spilled_mask) if yes]
        new_ids = self.ledger.tick(angle,dt,received=received,spilled=spilled)
        if received:
            current, velocity = receiver_data
            self.mouth_entered.difference_update(received)
            self.receiver_dose_ids.extend(received)
            self.write('Receiver', np.concatenate([current,falling[inside]]),
                       np.concatenate([velocity,fall_vel[inside]]))
        # Spill particles remain physical; only their bookkeeping state changes.
        # Their IDs stay here, allowing later motion without invented mass.
        keep = ~inside
        keep_points, keep_vel = falling[keep], fall_vel[keep]
        self.falling_ids = [pid for pid,yes in zip(self.falling_ids,keep) if yes]
        if new_ids:
            source, source_vel = self.read('Source')
            n = len(new_ids)
            if n > len(source):
                raise RuntimeError('Source particle budget exhausted unexpectedly')
            # Authorized source-to-tip transfer; no full capillary-flow claim.
            selected = np.argsort(source[:,2])[:n]
            take = np.ones(len(source),dtype=bool)
            take[selected] = False
            self.write('Source',source[take],source_vel[take])
            body_pos,body_rot = self.pose(self.body_path)
            center = np.array(self.emit_local) @ body_rot + body_pos
            offsets = np.array([[(pid%2-.5)*self.spacing,((pid//2)%2-.5)*self.spacing,
                                 -((n-1-i)//4)*self.spacing]
                                for i,pid in enumerate(new_ids)],dtype=np.float32)
            emitted = offsets @ body_rot+center
            speed = emission_speed(flow_rate(angle),self.spacing)  # noqa: F821
            v = np.tile(np.array([0.,0.,-speed],dtype=np.float32) @ body_rot,(n,1))
            keep_points = np.concatenate([keep_points,emitted])
            keep_vel = np.concatenate([keep_vel,v])
            self.falling_ids.extend(new_ids)
        if received or new_ids:
            self.write('Falling',keep_points,keep_vel,self.falling_ids)
        self.previous_falling_points = dict(zip(self.falling_ids,keep_points.copy()))
        self.previous_receiver_pose = (receiver_pos.copy(),receiver_rot.copy())
        ledger = self.ledger
        phase,color = indicator(ledger.received_ml)  # noqa: F821
        if color != self.last_color:
            self.shader.GetAttribute('inputs:glass_color').Set(Gf.Vec3f(*color))
            self.last_color = color
        released = len(ledger.states)*ledger.quantum_ml
        values = {'stopcock_angle_deg':angle,'valve_open_fraction':flow_rate(angle)/MAX_RATE,  # noqa: F821
                  'valve_state':'CLOSED' if angle<=5 else 'DRIP' if angle<15 else 'FINE' if angle<40 else 'OPEN',
                  'flow_rate_ml_s':flow_rate(angle) if released < 25-ledger.quantum_ml else 0.,  # noqa: F821
                  'burette_liquid_volume_ml':max(0.,25-released),
                  'burette_liquid_level':max(0.,25-released)/25,
                  'dispensed_volume_ml':ledger.received_ml,'released_volume_ml':released,
                  'inflight_volume_ml':ledger.inflight_ml,'spilled_volume_ml':ledger.spilled_ml,
                  'source_total_volume_ml':ledger.source_ml,'conservation_error_ml':ledger.conservation_error_ml,
                  'indicator_phase':phase,'overshoot':ledger.overshoot,'task_success':ledger.success,
                  'endpoint_hold_seconds':ledger.hold_s,'completion_hold_seconds':3. if ledger.success else 0.,
                  'completion_volume_ml':ledger.completed_volume_ml if ledger.success else -1.,
                  'controller_pose_valid':True,'pbd_valid':True,'pbd_error':'',
                  'source_particle_count':len(self.initial['Source'])-len(ledger.states),
                  'receiver_particle_count':self.initial_receiver_n+len(self.receiver_dose_ids),
                  'falling_particle_count':len(self.falling_ids)}
        for name,value in values.items():
            self.put(name,value)


def setup(db):
    import carb.settings
    import omni.physx.bindings._physx as pb
    settings = carb.settings.get_settings()
    for key in (pb.SETTING_UPDATE_TO_USD,pb.SETTING_UPDATE_PARTICLES_TO_USD,pb.SETTING_UPDATE_VELOCITIES_TO_USD):
        settings.set(key,True)
    settings.set(pb.SETTING_SUPPRESS_READBACK,False)
    db.per_instance_state.runtime = None


def cleanup(db):
    db.per_instance_state.runtime = None


def compute(db):
    import omni.usd
    import omni.physx
    root = str(db.node.get_prim_path()).split('/Instance/Runtime/')[0]
    stage = omni.usd.get_context().get_stage()
    try:
        # OnPhysicsStep precedes the usual USD readback. Pull the completed
        # physical state before resizing; stale USD positions freeze old doses.
        omni.physx.get_physx_interface().update_transformations(False,True,True)
        if db.per_instance_state.runtime is None:
            db.per_instance_state.runtime = Task10PbdRuntime(stage,root)
        db.per_instance_state.runtime.update(float(db.inputs.deltaSeconds))
    except Exception as exc:
        prim = stage.GetPrimAtPath(root)
        prim.GetAttribute('titration:pbd_valid').Set(False)
        prim.GetAttribute('titration:controller_pose_valid').Set(False)
        prim.GetAttribute('titration:pbd_error').Set(str(exc))
    return True
