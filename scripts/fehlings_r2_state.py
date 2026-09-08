"""Pure r2 teaching policy and fitted visual geometry, not reaction kinetics."""
import math

POLICY_VERSION = 'visual_sedimentation_v2'
RADIAL = 64
AXIAL = 32
SEDIMENT_VOLUME_M3 = .3e-6


def initial_state():
    return {'heated_s':0.0,'observe_s':0.0,'anchor':None,'stage':'ready','success':False}


def appearance(seconds):
    t=min(60.0,max(0.0,seconds))
    progress=max(0.0,(t-30)/30)
    blue,cloud,clear=(.40,.72,.95),(.65,.30,.14),(.94,.97,1.0)
    if t<=30:
        rgb,opacity=blue,.55
    elif t<=45:
        a=(t-30)/15
        rgb=tuple(x+(y-x)*a for x,y in zip(blue,cloud))
        opacity=.55+.25*a
    else:
        a=(t-45)/15
        rgb=tuple(x+(y-x)*a for x,y in zip(cloud,clear))
        opacity=.80-.55*a
    return dict(progress=progress,color=rgb,opacity=opacity,sediment=progress,
                sediment_opacity=min(1.0,max(0.0,(t-30)/3)),
                reaction_stage='warming' if t<=30 else 'clouding' if t<45 else 'settling' if t<60 else 'developed')


def advance(state,dt,immersed,withdrawn,position):
    state=dict(state)
    if state['success'] or dt<=0:
        return state
    if immersed:
        state['heated_s']=min(60.0,state['heated_s']+dt)
    ready=state['heated_s']>=60-1e-6
    if ready and withdrawn:
        if state['anchor'] is None:
            state['anchor']=tuple(position)
        if math.dist(position,state['anchor'])>.02:
            state['anchor'],state['observe_s']=tuple(position),0.0
        else:
            state['observe_s']+=dt
        state['success']=state['observe_s']>=3-1e-6
    else:
        state['observe_s'],state['anchor']=0.0,None
    state['stage']=('complete' if state['success'] else 'observing' if ready and withdrawn
                    else 'ready_to_withdraw' if ready else 'heating' if state['heated_s'] else 'ready')
    return state


def radius_at(profile,z):
    for (za,ra),(zb,rb) in zip(profile,profile[1:]):
        if z<=zb:
            return ra+(rb-ra)*max(0.0,(z-za)/(zb-za))
    return profile[-1][1]


def volume_to_height(profile,volume):
    if volume<=0:
        return profile[0][0]
    for (za,ra),(zb,rb) in zip(profile,profile[1:]):
        whole=math.pi*(zb-za)*(ra*ra+ra*rb+rb*rb)/3
        if volume<=whole:
            lo,hi=za,zb
            for _ in range(36):
                mid=(lo+hi)/2
                r=ra+(rb-ra)*(mid-za)/(zb-za)
                v=math.pi*(mid-za)*(ra*ra+ra*r+r*r)/3
                if v<volume:
                    lo=mid
                else:
                    hi=mid
            return (lo+hi)/2
        volume-=whole
    raise ValueError('visual sediment exceeds cavity volume')


def mesh_topology(part):
    n=RADIAL
    if part=='surface':
        return [3]*n,[v for i in range(n) for v in (n,i,(i+1)%n)]
    counts=[4]*(AXIAL*n)+[3]*n
    indices=[v for j in range(AXIAL) for i in range(n)
             for v in (j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)]
    indices += [v for i in range(n) for v in ((AXIAL+1)*n,(i+1)%n,i)]
    return counts,indices


def fitted_region(profile,low,high,meniscus):
    ring=[(math.cos(2*math.pi*i/RADIAL),math.sin(2*math.pi*i/RADIAL)) for i in range(RADIAL)]
    points=[]
    for j in range(AXIAL+1):
        z=low+(high-low)*j/AXIAL
        # Small radial inset keeps chords at cavity-profile kinks inside the wall.
        r=max(1e-6,radius_at(profile,z)-.00002)
        points.extend((r*x,r*y,z) for x,y in ring)
    body=points+[(0.0,0.0,low)]
    surface=points[-RADIAL:]+[(0.0,0.0,high-min(meniscus,(high-low)/4))]
    return dict(body=body,surface=surface)


def geometry(profile,sample_top,progress):
    p=min(1.0,max(0.0,progress))
    floor=profile[0][0]
    bed_top=volume_to_height(profile,p*SEDIMENT_VOLUME_M3)
    # The hidden zero-progress mesh stays nondegenerate; its logical thickness is zero.
    sediment=fitted_region(profile,floor,max(floor+.000001,bed_top),0.0)
    sample_low=floor if p==0 else bed_top+.00001
    if sample_low>=sample_top:
        raise ValueError('sediment intersects sample surface')
    return dict(Sample=fitted_region(profile,sample_low,sample_top,.00015),Sediment=sediment,
                sediment_height_m=bed_top-floor)
