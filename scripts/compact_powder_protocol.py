"""Profile-aware manipulation and measurable bed depth for the compact bottle."""
import math

# Cubic smoothstep u^2(3-2u) has max du/dt = 1.5 / duration.
SMOOTHSTEP_SPEED_PEAK = 1.5


def retime_keys_max_speed(keys, max_speed_m_s):
    """Stretch only those key segments whose smoothstep peak would exceed max_speed."""
    limit = float(max_speed_m_s)
    if not keys or limit <= 0:
        return list(keys)
    out = [keys[0]]
    t = float(keys[0][0])
    for (ta, pa, aa, _pha), (_tb, pb, ab, phb) in zip(keys, keys[1:]):
        orig = float(_tb) - float(ta)
        dist = math.dist(pa, pb)
        need = SMOOTHSTEP_SPEED_PEAK * dist / limit if limit else orig
        t += max(orig, need)
        out.append((t, pb, ab, phb))
    return out


def prescribed_spoon_keys(initial, bottle, receiver, cfg):
    """Official 50 s head keys, optionally stretched by spoon_max_speed_m_s."""
    import numpy as np
    mouth = cfg['bottle_height_m']
    floor = cfg['false_floor_m']
    surface = cfg['powder_surface_target_m']
    initial_pitch = math.degrees(2*math.atan2(initial[5],initial[3]))
    def head_from_root(root,pitch):
        a = math.radians(pitch)
        return (root[0]+.087*math.cos(a),root[1],root[2]-.087*math.sin(a))
    def working_height(pitch,x):
        a = math.radians(pitch)
        envelope = cfg['spoon_floor_envelope']
        dz = float(np.interp(pitch,[p[0] for p in envelope],[p[1] for p in envelope]))
        floor_clearance = floor+.00075-dz
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
    carry_pitch = float(cfg.get('carry_pitch_deg', 0.0) or 0.0)
    transfer_pitch = carry_pitch if cfg.get('carry_pitch_through_transfer') else 0.0
    keys += [(32,carry,carry_pitch,'lift_powder'),(36,over,transfer_pitch,'transfer'),
            (40,over,100,'slow_pour'),(44,away,0,'withdraw')]
    limit = cfg.get('spoon_max_speed_m_s')
    if limit:
        keys = retime_keys_max_speed(keys, limit)
    return keys


OFFICIAL_CLOSE_WINDOWS = {
    'settle_and_tare': (0.0, 8.0),
    'extract_from_beaker': (8.0, 11.0),
    'approach_bottle': (14.0, 20.0),
    'insert': (20.0, 21.0),
    'contact_pause': (21.0, 21.0),
    'slow_scoop': (21.0, 28.0),
    'lift_powder': (28.0, 32.0),
    'transfer': (32.0, 36.0),
    'slow_pour': (36.0, 40.0),
    'withdraw': (40.0, 42.0),
    'settled_readout': (42.0, 50.0),
}


def phase_progress(times, phases, frame):
    """Progress 0–1 through the contiguous recorded phase at frame."""
    phase = str(phases[frame])
    i0 = int(frame)
    while i0 > 0 and str(phases[i0 - 1]) == phase:
        i0 -= 1
    i1 = int(frame)
    n = len(phases)
    while i1 + 1 < n and str(phases[i1 + 1]) == phase:
        i1 += 1
    span = float(times[i1]) - float(times[i0])
    u = 0.0 if span <= 0 else (float(times[frame]) - float(times[i0])) / span
    return phase, max(0.0, min(1.0, u))


def canonical_close_time(phase, u):
    """Official 50 s close-camera clock for a recorded phase beat."""
    window = OFFICIAL_CLOSE_WINDOWS.get(str(phase))
    if not window:
        return 50.0 * float(u)
    start, end = window
    return start + max(0.0, min(1.0, float(u))) * (end - start)


def map_retimed_clock(t, stretched_keys, official_keys):
    """Map a stretched-spoon clock back onto the official 50 s camera clock."""
    t = float(t)
    src = [float(k[0]) for k in stretched_keys]
    dst = [float(k[0]) for k in official_keys]
    if not src or len(src) != len(dst):
        return t
    if t <= src[0]:
        return t
    for sa, sb, oa, ob in zip(src, src[1:], dst, dst[1:]):
        if sa <= t <= sb:
            span = sb - sa
            u = 0.0 if span <= 0 else (t - sa) / span
            return oa + u * (ob - oa)
    return dst[-1] + (t - src[-1])


def prescribed_spoon(t, initial, bottle, receiver, cfg):
    import numpy as np
    def root_from_head(head,pitch):
        a = math.radians(pitch)
        return (head[0]-.087*math.cos(a),head[1],head[2]+.087*math.sin(a))
    def working_height(pitch,x):
        a = math.radians(pitch)
        envelope = cfg['spoon_floor_envelope']
        dz = float(np.interp(pitch,[p[0] for p in envelope],[p[1] for p in envelope]))
        floor_clearance = cfg['false_floor_m']+.00075-dz
        aperture = .024-.001
        crossing = math.sqrt(aperture**2-.0095**2)+x
        rim_clearance = cfg['bottle_height_m']+.001-crossing*math.tan(a)-.00094/math.cos(a)
        leading_edge_dz = -.012*math.sin(a)+.006995*math.cos(a)
        immersion = cfg['powder_surface_target_m']-.005-leading_edge_dz
        return max(floor_clearance,rim_clearance,immersion)
    away = (receiver[0]+.10,receiver[1],receiver[2]+.08)
    keys = prescribed_spoon_keys(initial, bottle, receiver, cfg)
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


def particle_bound_m(cfg):
    if cfg.get('powder_kind') == 'pbd_solid':
        if cfg.get('grain_radius_m') is not None:
            return float(cfg['grain_radius_m'])
        if cfg.get('grain_bound_m') is not None:
            return float(cfg['grain_bound_m'])
    return cfg['grain_bound_m']


def bed_depth(local, cfg):
    """Median/p10/p90 of occupied 4 mm column tops, after physical settlement."""
    import numpy as np
    bound = particle_bound_m(cfg)
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
    depths = maximum[counts>=5]+bound-cfg['false_floor_m']
    q = np.percentile(depths,[10,50,90]) if len(depths) else [0.,0.,0.]
    return dict(surface_depth_median_m=float(q[1]),surface_depth_p10_m=float(q[0]),
                surface_depth_p90_m=float(q[2]),columns=len(depths))


def fill_level(local,cfg):
    """Measure the actual bed and headspace, including grains above the rim."""
    import numpy as np
    bound = particle_bound_m(cfg)
    level = bed_depth(local,cfg)
    points = local[cavity_mask(local,cfg)&(local[:,2]>=cfg['false_floor_m'])]
    highest = float(points[:,2].max()+bound) if len(points) else cfg['false_floor_m']
    level.update(median_headspace_m=cfg['bottle_height_m']-cfg['false_floor_m']-level['surface_depth_median_m'],
                 minimum_headspace_m=cfg['bottle_height_m']-highest)
    assert np.isfinite(list(level.values())).all()
    return level


def exclusive_loose_count(in_bottle, in_spoon, in_boat):
    """Grains that are not in the bottle cavity, spoon bowl, or boat."""
    import numpy as np
    return int((~(np.asarray(in_bottle, dtype=bool)
                 | np.asarray(in_spoon, dtype=bool)
                 | np.asarray(in_boat, dtype=bool))).sum())


def near_full_check(level):
    return (level.get('columns',0)>0 and .010<=level.get('surface_depth_median_m',0)<=.012
            and .003<=level.get('median_headspace_m',0)<=.007
            and level.get('minimum_headspace_m',0)>=.001)
