"""Profile-aware manipulation and measurable bed depth for the compact bottle."""
import math


def prescribed_spoon(t, initial, bottle, receiver, cfg):
    import numpy as np
    mouth = cfg['bottle_height_m']
    floor = cfg['false_floor_m']
    surface = cfg['powder_surface_target_m']
    initial_pitch = math.degrees(2*math.atan2(initial[5],initial[3]))
    def head_from_root(root,pitch):
        a = math.radians(pitch)
        return (root[0]+.087*math.cos(a),root[1],root[2]-.087*math.sin(a))
    def root_from_head(head,pitch):
        a = math.radians(pitch)
        return (head[0]-.087*math.cos(a),head[1],head[2]+.087*math.sin(a))
    def working_height(pitch,x):
        a = math.radians(pitch)
        envelope = cfg['spoon_floor_envelope']
        dz = float(np.interp(pitch,[p[0] for p in envelope],[p[1] for p in envelope]))
        floor_clearance = floor+.00075-dz
        # Conservative grip-rail clearance at the minimum neck aperture.
        aperture = .024-.001
        crossing = math.sqrt(aperture**2-.0095**2)+x
        rim_clearance = mouth+.001-crossing*math.tan(a)-.00094/math.cos(a)
        leading_edge_dz = -.012*math.sin(a)+.006995*math.cos(a)
        immersion = surface-.005-leading_edge_dz
        return max(floor_clearance,rim_clearance,immersion)
    entry_x,end_x = -.005,.008
    above = (bottle[0]+entry_x,bottle[1],bottle[2]+mouth+.03)
    entry = (bottle[0]+entry_x,bottle[1],bottle[2]+working_height(70,entry_x))
    filled = (bottle[0]+end_x,bottle[1],bottle[2]+working_height(30,end_x))
    carry = (bottle[0]+end_x,bottle[1],bottle[2]+mouth+.025)
    over = (receiver[0],receiver[1],receiver[2]+.05)
    away = (receiver[0]+.10,receiver[1],receiver[2]+.08)
    keys = [(8,head_from_root(initial[:3],initial_pitch),initial_pitch,'settle_and_tare'),
            (11,head_from_root((initial[0],initial[1],initial[2]+.13),initial_pitch),initial_pitch,'extract_from_beaker'),
            (14,above,70,'approach_bottle'),(20,entry,70,'insert'),(21,entry,70,'contact_pause'),
            (28,filled,30,'slow_scoop')]
    hold_m = cfg.get('lift_early_hold_m')
    if hold_m:
        keys.append((30,(filled[0],filled[1],filled[2]+float(hold_m)),20,'lift_powder'))
    keys += [(32,carry,0,'lift_powder'),(36,over,0,'transfer'),
            (40,over,100,'slow_pour'),(44,away,0,'withdraw')]
    if t<=8:
        return tuple(initial),'settle_and_tare'
    for (ta,pa,aa,_),(tb,pb,ab,phase) in zip(keys,keys[1:]):
        if ta<=t<=tb:
            u = (t-ta)/(tb-ta)
            u = u*u*(3-2*u)
            pitch = (1-u)*aa+u*ab
            head = tuple((1-u)*a+u*b for a,b in zip(pa,pb))
            if phase=='slow_scoop':
                head = (head[0],head[1],bottle[2]+working_height(pitch,head[0]-bottle[0]))
            angle = math.radians(pitch)/2
            return (*root_from_head(head,pitch),math.cos(angle),0.,math.sin(angle),0.),phase
    return (*root_from_head(away,0),1.,0.,0.,0.),'settled_readout'


def cavity_mask(local, cfg, margin=.001):
    import numpy as np
    profile = cfg['inner_profile']
    r = np.interp(local[:,2],[p['z'] for p in profile],[p['radius'] for p in profile])+margin
    exponent = np.interp(local[:,2],[p['z'] for p in profile],[p['exponent'] for p in profile])
    return (abs(local[:,0])/r)**exponent+(abs(local[:,1])/r)**exponent <= 1


def bed_depth(local, cfg):
    """Median/p10/p90 of occupied 4 mm column tops, after physical settlement."""
    import numpy as np
    inside = cavity_mask(local,cfg,margin=-.002)
    inside &= (local[:,2]>=cfg['false_floor_m']) & (local[:,2]<cfg['bottle_height_m'])
    points = local[inside]
    if not len(points):
        return dict(surface_depth_median_m=0.,surface_depth_p10_m=0.,surface_depth_p90_m=0.,columns=0)
    xy = np.floor(points[:,:2]/.004).astype(int)
    _,idx = np.unique(xy,axis=0,return_inverse=True)
    maximum = np.full(idx.max()+1,-np.inf)
    np.maximum.at(maximum,idx,points[:,2])
    counts = np.bincount(idx)
    depths = maximum[counts>=5]+cfg['grain_bound_m']-cfg['false_floor_m']
    q = np.percentile(depths,[10,50,90]) if len(depths) else [0.,0.,0.]
    return dict(surface_depth_median_m=float(q[1]),surface_depth_p10_m=float(q[0]),
                surface_depth_p90_m=float(q[2]),columns=len(depths))


def fill_level(local,cfg):
    """Measure the actual bed and headspace, including grains above the rim."""
    import numpy as np
    level = bed_depth(local,cfg)
    points = local[cavity_mask(local,cfg)&(local[:,2]>=cfg['false_floor_m'])]
    highest = float(points[:,2].max()+cfg['grain_bound_m']) if len(points) else cfg['false_floor_m']
    level.update(median_headspace_m=cfg['bottle_height_m']-cfg['false_floor_m']-level['surface_depth_median_m'],
                 minimum_headspace_m=cfg['bottle_height_m']-highest)
    assert np.isfinite(list(level.values())).all()
    return level


def near_full_check(level):
    return (level.get('columns',0)>0 and .010<=level.get('surface_depth_median_m',0)<=.012
            and .003<=level.get('median_headspace_m',0)<=.007
            and level.get('minimum_headspace_m',0)>=.001)
