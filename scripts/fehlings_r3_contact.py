"""Collision-free contact between the sample region and a profile-defined visual bath."""
import math

CONTACT_POLICY_VERSION='visual_water_contact_v3'


def _add(a,b):
    return tuple(x+y for x,y in zip(a,b))


def _sub(a,b):
    return tuple(x-y for x,y in zip(a,b))


def _mul(a,k):
    return tuple(x*k for x in a)


def _dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def _cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def _unit(a):
    length=math.sqrt(_dot(a,a))
    return _mul(a,1/length) if length>1e-20 else (1.0,0.0,0.0)


def _support(shape,d):
    a,b,ra,rb=shape
    axis=_unit(_sub(b,a))
    radial=_sub(d,_mul(axis,_dot(d,axis)))
    if _dot(radial,radial)<1e-24:
        return a if _dot(a,d)>_dot(b,d) else b
    radial=_unit(radial)
    pa,pb=_add(a,_mul(radial,ra)),_add(b,_mul(radial,rb))
    return pa if _dot(pa,d)>_dot(pb,d) else pb


def _line(simplex):
    a,b=simplex[:2]
    ab,ao=_sub(b,a),_mul(a,-1)
    if _dot(ab,ao)>0:
        direction=_cross(_cross(ab,ao),ab)
        if _dot(direction,direction)<1e-32:
            if _dot(ab,ao)<=_dot(ab,ab)+1e-16:
                return [a,b],direction,True
            return [b],_mul(b,-1),False
        return [a,b],direction,False
    return [a],ao,_dot(ao,ao)<1e-24


def _triangle(simplex):
    a,b,c=simplex[:3]
    ab,ac,ao=_sub(b,a),_sub(c,a),_mul(a,-1)
    normal=_cross(ab,ac)
    if _dot(_cross(normal,ac),ao)>0:
        return _line([a,c] if _dot(ac,ao)>0 else [a,b])
    if _dot(_cross(ab,normal),ao)>0:
        return _line([a,b])
    if _dot(normal,normal)<1e-32:
        return _line([a,b])
    return ([a,b,c],normal,False) if _dot(normal,ao)>0 else ([a,c,b],_mul(normal,-1),False)


def frustum_overlap(first,second):
    """GJK narrowphase on two finite, capped circular frusta; no physics SDK."""
    def support(d):
        return _sub(_support(first,d),_support(second,_mul(d,-1)))
    direction=(1.0,.317,.173)
    simplex=[support(direction)]
    direction=_mul(simplex[0],-1)
    for _ in range(80):
        if _dot(direction,direction)<1e-24:
            return True
        direction=_unit(direction)
        point=support(direction)
        if _dot(point,direction)<-1e-10:
            return False
        simplex.insert(0,point)
        if len(simplex)==2:
            simplex,direction,hit=_line(simplex)
        elif len(simplex)==3:
            simplex,direction,hit=_triangle(simplex)
        else:
            a,b,c,d=simplex[:4]
            ao=_mul(a,-1)
            hit=True
            for x,y,opposite in ((b,c,d),(c,d,b),(d,b,c)):
                normal=_cross(_sub(x,a),_sub(y,a))
                if _dot(normal,_sub(opposite,a))>0:
                    x,y=y,x
                    normal=_mul(normal,-1)
                if _dot(normal,ao)>1e-20:
                    simplex,direction,hit=_triangle([a,x,y])
                    break
        if hit:
            return True
    # Nonconvergence is not permission to accumulate heating time.
    return False


def _bounds(shape):
    a,b,ra,rb=shape
    axis=_unit(_sub(b,a))
    widths=[math.sqrt(max(0.0,1-v*v)) for v in axis]
    return ([min(a[i]-ra*widths[i],b[i]-rb*widths[i]) for i in range(3)],
            [max(a[i]+ra*widths[i],b[i]+rb*widths[i]) for i in range(3)])


def bath_contact(sample_profile,sample_top,origin,axis,water_profile):
    """All geometry is expressed in the current beaker's local coordinates."""
    axis=_unit(axis)
    water_shapes=[((0,0,z0),(0,0,z1),r0,r1) for (z0,r0),(z1,r1) in zip(water_profile,water_profile[1:])]
    for (z0,r0),(z1,r1) in zip(sample_profile,sample_profile[1:]):
        if z0>=sample_top:
            break
        high=min(z1,sample_top)
        radius=r0+(r1-r0)*(high-z0)/(z1-z0)
        shape=(_add(origin,_mul(axis,z0)),_add(origin,_mul(axis,high)),r0,radius)
        lo,hi=_bounds(shape)
        for water in water_shapes:
            wlo,whi=_bounds(water)
            if any(hi[i]<wlo[i]-1e-10 or lo[i]>whi[i]+1e-10 for i in range(3)):
                continue
            if frustum_overlap(shape,water):
                return True
    return False


def water_mesh(profile,segments=96):
    """Closed visual water volume with a separate flat top; same profile as contact."""
    points=[(r*math.cos(2*math.pi*i/segments),r*math.sin(2*math.pi*i/segments),z)
            for z,r in profile for i in range(segments)]
    counts=[4]*((len(profile)-1)*segments)+[3]*segments
    indices=[v for j in range(len(profile)-1) for i in range(segments)
             for v in (j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i)]
    center=len(points)
    body=points+[(0,0,profile[0][0])]
    indices += [v for i in range(segments) for v in (center,(i+1)%segments,i)]
    surface=points[-segments:]+[(0,0,profile[-1][0])]
    surface_indices=[v for i in range(segments) for v in (segments,i,(i+1)%segments)]
    return {'body':(body,counts,indices),'surface':(surface,[3]*segments,surface_indices)}
