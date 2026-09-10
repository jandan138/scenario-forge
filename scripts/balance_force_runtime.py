"""Embedded device bridge; loaded only by the target simulator, never core layers."""
import math

from scripts.balance_force_state import BalanceState, vertical_mass_g

SEGMENTS = {'0':'abcdef','1':'bc','2':'abdeg','3':'abcdg','4':'bcfg',
            '5':'acdfg','6':'acdefg','7':'abc','8':'abcdefg','9':'abcdfg',
            '-':'g','O':'abcdef','L':'def',' ':'','E':'adefg'}


class BalanceRuntime:
    def __init__(self, stage, root):
        import omni.physics.tensors as tensors
        from omni.isaac.dynamic_control import _dynamic_control
        self.stage = stage
        self.root = root
        self.prim = stage.GetPrimAtPath(root)
        self.sim = tensors.create_simulation_view('numpy')
        self.sim.set_subspace_roots('/')
        self.view = self.sim.create_articulation_view(root)
        meta = self.view.shared_metatype
        self.pan = meta.link_names.index('WeighingPan')
        self.body = meta.link_names.index('Body')
        self.tare = meta.dof_names.index('RightTarePress')
        self.dc = _dynamic_control.acquire_dynamic_control_interface()
        self.weights = []
        from pxr import UsdPhysics
        for p in stage.Traverse():
            if p.HasAPI(UsdPhysics.RigidBodyAPI) and not str(p.GetPath()).startswith(root+'/'):
                h = self.dc.get_rigid_body(str(p.GetPath()))
                if h:
                    self.weights.append(h)
        self.state = BalanceState(self.get('resolution_g'), self.get('target_g'),
                                  self.get('tolerance_g'), self.get('capacity_g'))
        self.pressed = False
        self.last_display = None

    def get(self, name):
        return self.prim.GetAttribute('balance:'+name).Get()

    def put(self, name, value):
        self.prim.GetAttribute('balance:'+name).Set(value)

    def pose(self, path):
        h = self.dc.get_rigid_body(path)
        if not h:
            return None
        return self.dc.get_rigid_body_pose(h)

    def eligible(self, pan_pose):
        """Task eligibility is independent of mass, which always comes from force."""
        from pxr import Gf
        targets = self.prim.GetRelationship('balance:container').GetTargets()
        if not targets:
            return False  # standalone instrument has no task success rule
        container = self.pose(str(targets[0]))
        spoon_targets = self.prim.GetRelationship('balance:spoon').GetTargets()
        if container is None or not spoon_targets:
            return False
        pan_inverse = Gf.Rotation(Gf.Quatd(float(pan_pose[6]),Gf.Vec3d(*map(float,pan_pose[3:6])))).GetInverse()
        p = pan_inverse.TransformDir(Gf.Vec3d(container.p.x,container.p.y,container.p.z)-Gf.Vec3d(*map(float,pan_pose[:3])))
        if abs(p[0]) > .025 or abs(p[1]-.020) > .025 or not .155 < p[2] < .22:
            return False
        spoon = self.pose(str(spoon_targets[0]))
        home = self.get('spoon_home_xyz')
        if spoon is None or sum((v-home[i])**2 for i,v in enumerate((spoon.p.x,spoon.p.y,spoon.p.z))) > .04**2:
            return False
        # A transferred sample must occupy the receiver volume. This does not
        # count samples or read their masses to manufacture the measured result.
        inv = Gf.Rotation(Gf.Quatd(container.r.w,Gf.Vec3d(container.r.x,container.r.y,container.r.z))).GetInverse()
        for target in self.prim.GetRelationship('balance:samples').GetTargets():
            sample = self.pose(str(target))
            if sample:
                q = inv.TransformDir(Gf.Vec3d(sample.p.x-container.p.x,sample.p.y-container.p.y,sample.p.z-container.p.z))
                if abs(q[0]) < .025 and abs(q[1]) < .025 and -.005 < q[2] < .04:
                    return True
        return False

    def measure_gross(self, poses, dt):
        """Default instrument channel: projected incoming load-cell joint force."""
        force = self.view.get_link_incoming_joint_force()[0,self.pan]
        return vertical_mass_g(tuple(map(float,force[:3])),tuple(map(float,poses[self.pan,3:7])),
                               self.get('gravity_m_s2'),self.get('pan_mass_g'))

    def update(self, dt):
        from pxr import UsdGeom
        if self.get('reset_requested'):
            self.state.reset()
            self.state.was_pressed = self.pressed
            self.pressed = False
            self.last_display = None
            self.put('reset_requested',False)
        # Sleeping loads produced stale/attenuated reaction readings in the
        # qualified runtimes. Wake dynamic task bodies without altering mass.
        for h in self.weights:
            self.dc.wake_up_rigid_body(h)
        poses = self.view.get_link_transforms()[0]
        velocities = self.view.get_link_velocities()[0]
        body = poses[self.body]
        vel = velocities[self.body]
        x,y,z,w = map(float,body[3:7])
        upright = 1-2*(x*x+y*y)
        supported = abs(float(body[2])+self.get('feet_min_z')-self.get('tabletop_z')) < .01
        valid = (upright >= math.cos(math.radians(5)) and supported
                 and sum(float(v)**2 for v in vel[:3]) < .005**2
                 and sum(float(v)**2 for v in vel[3:]) < .03**2)
        gross = self.measure_gross(poses, dt)
        valid = valid and math.isfinite(gross)
        q = float(self.view.get_dof_positions()[0,self.tare])
        self.pressed = q >= (.00045 if self.pressed else .0009)
        self.state.update(gross,dt,pressed=self.pressed,valid=valid,eligible=self.eligible(poses[self.pan]))
        s = self.state
        valid = valid and s.status not in ('overload','invalid','initializing')
        for name,value in [('gross_g',gross),('net_g',s.net_g),('tare_g',s.tare_g),
                           ('stable',s.stable),('valid',valid),('status',s.status),
                           ('tare_pending',s.pending_tare),('error',s.error),('tared',s.tared),
                           ('success',s.success),('target_hold_s',s.target_hold_s),
                           ('completed_net_g',s.completed_net_g or 0.),('tare_position_m',q)]:
            self.put(name,value)
        text = s.display()
        self.put('lcd_readout',text+' g' if s.status not in ('invalid','initializing','overload') else text)
        if text != self.last_display:
            chars = text.replace('.','').rjust(8)
            if len(chars)>8:
                chars='      OL'
            places = len(text.split('.')[1]) if '.' in text else -1
            base=self.root+'/Instance/Body/ControlPanel/LiveDigits'
            for i,char in enumerate(chars):
                for seg in 'abcdefg':
                    UsdGeom.Imageable(self.stage.GetPrimAtPath(f'{base}/D{i}_{seg}')).GetVisibilityAttr().Set(
                        'inherited' if seg in SEGMENTS.get(char,'') else 'invisible')
                UsdGeom.Imageable(self.stage.GetPrimAtPath(f'{base}/P{i}')).GetVisibilityAttr().Set(
                    'inherited' if i == 7-places and places>=0 else 'invisible')
            self.last_display=text
        for i,visible in enumerate((s.stable,s.pending_tare,not valid or bool(s.error))):
            p=self.stage.GetPrimAtPath(self.root+f'/Instance/Body/ControlPanel/Status/LED_{i}')
            if p:
                UsdGeom.Imageable(p).CreateVisibilityAttr('inherited' if visible else 'invisible')


def setup(db):
    db.per_instance_state.runtime = None


def compute(db):
    import omni.usd
    stage = omni.usd.get_context().get_stage()
    root = str(db.node.get_prim_path()).split('/BalanceRuntime/')[0]
    try:
        if db.per_instance_state.runtime is None:
            db.per_instance_state.runtime = BalanceRuntime(stage,root)
        db.per_instance_state.runtime.update(float(db.inputs.deltaSeconds))
    except Exception as exc:
        p = stage.GetPrimAtPath(root)
        p.GetAttribute('balance:valid').Set(False)
        p.GetAttribute('balance:stable').Set(False)
        p.GetAttribute('balance:status').Set('invalid')
        p.GetAttribute('balance:error').Set(str(exc))
        p.GetAttribute('balance:lcd_readout').Set('------')
        from pxr import UsdGeom
        base=root+'/Instance/Body/ControlPanel/LiveDigits'
        for i in range(8):
            for segment in 'abcdefg':
                item=stage.GetPrimAtPath(f'{base}/D{i}_{segment}')
                if item:
                    UsdGeom.Imageable(item).GetVisibilityAttr().Set('inherited' if segment=='g' else 'invisible')
            point=stage.GetPrimAtPath(f'{base}/P{i}')
            if point:
                UsdGeom.Imageable(point).GetVisibilityAttr().Set('invisible')
        db.per_instance_state.runtime = None
    return True


def cleanup(db):
    db.per_instance_state.runtime = None
