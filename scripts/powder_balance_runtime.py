"""Powder fixture variant: measured world-space contact load on the actual pan.

Unlike incoming joint force, this channel remained valid when a micro-grain
contacted the free base in the recorded Isaac 4.5 regression fixture.
"""
from scripts.balance_force_runtime import BalanceRuntime
from collections import deque


class PowderBalanceRuntime(BalanceRuntime):
    def __init__(self, stage, root):
        super().__init__(stage, root)
        self.contacts = self.sim.create_rigid_contact_view(root+'/Instance/WeighingPan')
        if self.contacts.sensor_count != 1:
            raise RuntimeError('Exactly one weighing-pan contact sensor required')
        self.reset_force_window()

    def reset_force_window(self):
        self.force_window = deque()
        self.force_time = 0.
        self.window_impulse_g_s = 0.
        self.window_duration_s = 0.

    def update(self, dt):
        if dt <= 0:
            return
        if self.get('reset_requested'):
            self.reset_force_window()
        super().update(dt)

    def measure_gross(self, poses, dt):
        joint_gross = super().measure_gross(poses, dt)
        # Tensor contact vectors are world-space. This is the force ON the pan,
        # hence downward load has negative z. Impulse conversion uses actual dt.
        force = self.contacts.get_net_contact_forces(dt)[0]
        gross = -float(force[2])/self.get('gravity_m_s2')*1000
        self.put('joint_gross_g',joint_gross)
        self.put('channel_disagreement_g',joint_gross-gross)
        self.put('contact_raw_gross_g',gross)
        # Integrate actual force over one simulated second. High-frequency
        # contact impulses must not alias into a low-rate balance display.
        self.force_time += dt
        self.force_window.append((self.force_time,gross*dt,dt))
        self.window_impulse_g_s += gross*dt
        self.window_duration_s += dt
        while len(self.force_window)>1 and self.force_window[0][0] <= self.force_time-1.:
            _,impulse,duration = self.force_window.popleft()
            self.window_impulse_g_s -= impulse
            self.window_duration_s -= duration
        return self.window_impulse_g_s/self.window_duration_s


def compute(db):
    import omni.usd
    stage = omni.usd.get_context().get_stage()
    root = str(db.node.get_prim_path()).split('/BalanceRuntime/')[0]
    try:
        if db.per_instance_state.runtime is None:
            db.per_instance_state.runtime = PowderBalanceRuntime(stage,root)
        db.per_instance_state.runtime.update(float(db.inputs.deltaSeconds))
    except Exception as exc:
        from pxr import UsdGeom
        p = stage.GetPrimAtPath(root)
        for name,value in [('valid',False),('stable',False),('status','invalid'),('error',str(exc)),('lcd_readout','------')]:
            p.GetAttribute('balance:'+name).Set(value)
        base = root+'/Instance/Body/ControlPanel/LiveDigits'
        for i in range(8):
            for segment in 'abcdefg':
                item = stage.GetPrimAtPath(f'{base}/D{i}_{segment}')
                if item:
                    UsdGeom.Imageable(item).GetVisibilityAttr().Set('inherited' if segment=='g' else 'invisible')
            point = stage.GetPrimAtPath(f'{base}/P{i}')
            if point:
                UsdGeom.Imageable(point).GetVisibilityAttr().Set('invisible')
        db.per_instance_state.runtime = None
    return True
