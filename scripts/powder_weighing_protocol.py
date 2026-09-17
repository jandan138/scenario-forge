"""Prescribed fixture motion and independent force-measurement acceptance."""
import math


def spoon_target(t, receiver_x, offset_z):
    waypoints = [(0,(-.007,0,.040),0,'settle_and_tare'),(5,(-.007,0,.040),0,'settle_and_tare'),
        (7,(-.007,0,.008),0,'insert'),(9,(.007,0,.008),0,'scoop'),
        (11,(.007,0,.040),0,'lift'),(15,(receiver_x,0,.040),0,'transfer'),
        (18,(receiver_x,0,.024),100,'pour'),(20,(receiver_x,0,.040),100,'withdraw'),
        (23,(receiver_x+.065,0,.065),0,'withdraw')]
    for (ta,pa,aa,_),(tb,pb,ab,phase) in zip(waypoints,waypoints[1:]):
        if ta <= t <= tb:
            s = (t-ta)/(tb-ta)
            s = s*s*(3-2*s)
            pos = tuple((1-s)*a+s*b+(offset_z if i==2 else 0) for i,(a,b) in enumerate(zip(pa,pb)))
            return pos,(1-s)*aa+s*ab,phase
    return (receiver_x+.065,0,.065+offset_z),0.,'settled_readout'


def measurement_check(rows, expected_g, tolerance_g):
    values = [row['net_g'] for row in rows if row.get('net_g') is not None]
    valid = bool(rows) and all(
        row.get('valid') and row.get('stable')
        and row.get('net_g') is not None and math.isfinite(row['net_g'])
        for row in rows)
    error = max((abs(v-expected_g) for v in values), default=float('inf'))
    spread = max(values)-min(values) if values else float('inf')
    return dict(passed=valid and error <= tolerance_g, expected_g=expected_g,
                max_error_g=error if math.isfinite(error) else None,
                range_g=spread if math.isfinite(spread) else None, samples=len(rows))
