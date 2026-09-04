# VR articulated link registration

The VR collection contract requires every physical articulation link to be
registered, not only the public `obj_*` root. The standard VR exporter now
expands each future `articulated_object` entry after object materialization:
the root is followed by every composed `RigidBodyAPI` link below its identity
`Instance`, using USD traversal order and the runtime `/World/_scene` prefix.

Registration and transform ownership are deliberately separate. Only the
public device root participates in `layout_randomization`; registered links
follow that root through the articulation and are never randomized separately.
Joints, meshes, materials, and collider children are not links and are not
added to `obj_prim_list`.

Before link enumeration, the exporter applies the fixed-base v2 validator. A
Scope `Instance`, kinematic link, missing articulation root, invalid BaseFixed,
or escaped joint target blocks the new export rather than receiving a local
physics patch.

The already delivered Task09 r16 and Task12 r2 ZIPs remain byte-stable and are
not rebuilt. This policy applies to subsequent generated packages and new
revisions. Tests cover deterministic complete registration, rejection of the
legacy Scope shape, and root-only local randomization.
