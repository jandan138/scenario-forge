"""Task-scoped clock contracts and evidence; SDK imports remain lazy."""
import math


def scene_capacity_settings(configuration):
    """Consume task producer capacities without inventing global defaults."""
    contract=configuration['runtime_contract']
    result={}
    for key,name in (
            ('scene_gpu_found_lost_aggregate_pairs_capacity','gpuFoundLostAggregatePairsCapacity'),
            ('scene_gpu_total_aggregate_pairs_capacity','gpuTotalAggregatePairsCapacity')):
        if key in contract:
            value=contract[key]
            if not isinstance(value,int) or isinstance(value,bool) or not 0<value<2**32:
                raise ValueError('Scene capacity must be a positive UInt: '+key)
            result[name]=value
    return result


def runtime_settings(configuration):
    contract=configuration['runtime_contract']
    dt=float(contract['physics_dt'])
    if not math.isfinite(dt) or dt<=0:
        raise ValueError('Positive finite physical dt required')
    hz=round(1/dt)
    if hz<=0 or abs(dt-1/hz)>1e-12:
        raise ValueError('Physical dt must map exactly to integer scene frequency')
    return {'physics_dt':dt,'physics_hz':hz,
            'min_iterations':int(contract['scene_min_position_iterations']),
            'max_iterations':int(contract['scene_max_position_iterations'])}


def clock_summary(samples,target_s,world_physics_dt_s,scene_time_steps_per_second):
    values=list(map(float,samples))
    if (not values or not math.isfinite(world_physics_dt_s)
            or abs(world_physics_dt_s-target_s)>1e-8
            or scene_time_steps_per_second<=0 or abs(1/scene_time_steps_per_second-target_s)>1e-8
            or any(not math.isfinite(v) or abs(v-target_s)>1e-8 for v in values)):
        raise ValueError('Native callback, World and active PhysicsScene must agree with target dt')
    return {'source':'native_physics_step_callback','count':len(values),'min_s':min(values),
            'max_s':max(values),'sum_s':sum(values),'target_s':target_s,
            'world_physics_dt_s':world_physics_dt_s,
            'scene_time_steps_per_second':scene_time_steps_per_second}


def synchronize_loaded_scene(stage, physics_path, app=None):
    """Repair Isaac4.5's missing loaded-scene registration while fully stopped.

The SDK clears its Python scene registry on OPENED and can miss the already
loaded prim. A public USD type resync registers the real scene handle; no SDK
cache values or getters are overwritten. Source attributes/relationships stay
unchanged and actual step callbacks must still prove the clock separately.
"""
    try:
        import omni.timeline
        import omni.usd
    except ImportError:
        return {'sdk_scene_resync':False,'offline_stage':True}
    if omni.usd.get_context().get_stage()!=stage:
        return {'sdk_scene_resync':False,'offline_stage':True}
    from pxr import PhysxSchema
    if not omni.timeline.get_timeline_interface().is_stopped():
        raise RuntimeError('Loaded-scene synchronization requires stopped physics')
    prim=stage.GetPrimAtPath(physics_path)
    api=PhysxSchema.PhysxSceneAPI(prim)
    hz=api.GetTimeStepsPerSecondAttr().Get()
    if not prim.IsActive() or prim.GetTypeName()!='PhysicsScene' or not hz:
        raise ValueError('Valid active PhysicsScene required')
    try:
        from isaacsim.core.simulation_manager import SimulationManager
    except ImportError:
        return {'sdk_scene_resync':False,'scene_time_steps_per_second':hz}
    try:
        registered=SimulationManager.get_physics_dt(physics_path)
    except Exception:
        registered=None
    refreshed=False
    if registered is None:
        try:
            prim.SetTypeName('Scope')
            if app is not None:
                app.update()
        finally:
            prim.SetTypeName('PhysicsScene')
        for _ in range(2):
            if app is not None:
                app.update()
        refreshed=True
    if abs(SimulationManager.get_physics_dt(physics_path)-1/hz)>1e-8 or abs(SimulationManager.get_physics_dt()-1/hz)>1e-8:
        raise ValueError('SDK default scene and requested scene clocks disagree')
    return {'sdk_scene_resync':refreshed,'scene_time_steps_per_second':hz,
            'sdk_scene_physics_dt_s':SimulationManager.get_physics_dt(physics_path)}
