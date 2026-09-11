"""Prescribed, collision-tested tool motion for the original task09 spoon."""
import math


def prescribed_spoon(t, initial, bottle, receiver):
    initial_pitch = math.degrees(2*math.atan2(initial[5],initial[3]))
    def root_from_head(head, pitch):
        a = math.radians(pitch)
        return (head[0]-.087*math.cos(a),head[1],head[2]+.087*math.sin(a))
    def head_from_root(root,pitch):
        a = math.radians(pitch)
        return (root[0]+.087*math.cos(a),root[1],root[2]-.087*math.sin(a))
    lifted = (initial[0],initial[1],initial[2]+.13)
    above = (bottle[0]-.008,bottle[1],bottle[2]+.170)
    insert = (bottle[0]-.008,bottle[1],bottle[2]+.14174)
    scooped = (bottle[0]-.002,bottle[1],bottle[2]+.13500)
    carry = (bottle[0]+.009,bottle[1],bottle[2]+.165)
    over_pan = (receiver[0],receiver[1],receiver[2]+.040)
    away = (receiver[0]+.10,receiver[1],receiver[2]+.080)
    keys = [(0,head_from_root(initial[:3],initial_pitch),initial_pitch,'settle'),
            (8,head_from_root(initial[:3],initial_pitch),initial_pitch,'settle_and_tare'),
            (11,head_from_root(lifted,initial_pitch),initial_pitch,'extract_from_beaker'),
            (14,above,70,'approach_bottle'),(20,insert,70,'insert'),
            (21,insert,70,'contact_pause'),(28,scooped,12,'slow_scoop'),(32,carry,0,'lift_powder'),
            (36,over_pan,0,'transfer'),(40,over_pan,100,'slow_pour'),(44,away,0,'withdraw')]
    if t<=8:
        return tuple(initial),'settle_and_tare'
    for (ta,pa,aa,_),(tb,pb,ab,phase) in zip(keys,keys[1:]):
        if ta<=t<=tb:
            u = (t-ta)/(tb-ta)
            u = u*u*(3-2*u)
            head = tuple((1-u)*a+u*b for a,b in zip(pa,pb))
            pitch = (1-u)*aa+u*ab
            if phase=='slow_scoop':
                # Measured original-spoon clearance envelope above the 131 mm
                # false floor; low pitches also clear the rim with the grip rails.
                envelope = [(12,.13500),(20,.13335),(25,.13351),(30,.13428),
                            (40,.13605),(50,.13799),(60,.13994),(70,.14174)]
                for (a0,h0),(a1,h1) in zip(envelope,envelope[1:]):
                    if a0<=pitch<=a1:
                        f = (pitch-a0)/(a1-a0)
                        head = (head[0],head[1],bottle[2]+(1-f)*h0+f*h1)
                        break
            angle = math.radians(pitch)/2
            return (*root_from_head(head,pitch),math.cos(angle),0.,math.sin(angle),0.),phase
    return (*root_from_head(keys[-1][1],0),1.,0.,0.,0.),'settled_readout'
