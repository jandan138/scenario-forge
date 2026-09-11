"""Task09 contact scale: explicitly never-sleeping grains need no per-step wake."""
from scripts.powder_balance_runtime import PowderBalanceRuntime, compute as base_compute


def requires_wake(name, sleep_threshold, stabilization_threshold):
    return not (name.startswith('obj_powder_grain_') and sleep_threshold == 0
                and stabilization_threshold == 0)


class Task09PowderRuntime(PowderBalanceRuntime):
    def __init__(self, stage, root):
        from pxr import UsdPhysics
        self._pending_outputs = None
        super().__init__(stage,root)
        self._output_attrs = {attr.GetName()[8:]:attr for attr in self.prim.GetAttributes()
                              if attr.GetName().startswith('balance:')}
        self.weights = []
        for prim in stage.Traverse():
            if prim.HasAPI(UsdPhysics.RigidBodyAPI) and not str(prim.GetPath()).startswith(root+'/'):
                if requires_wake(prim.GetName(),prim.GetAttribute('physxRigidBody:sleepThreshold').Get(),
                                 prim.GetAttribute('physxRigidBody:stabilizationThreshold').Get()):
                    handle = self.dc.get_rigid_body(str(prim.GetPath()))
                    if handle:
                        self.weights.append(handle)

    def put(self, name, value):
        if self._pending_outputs is None:
            super().put(name,value)
        else:
            self._pending_outputs[name] = value

    def update(self, dt):
        from pxr import Sdf
        self._pending_outputs = {}
        try:
            super().update(dt)
        finally:
            outputs = self._pending_outputs
            self._pending_outputs = None
            with Sdf.ChangeBlock():
                for name,value in outputs.items():
                    self._output_attrs[name].Set(value)


def compute(db):
    return base_compute(db,runtime_class=Task09PowderRuntime)
