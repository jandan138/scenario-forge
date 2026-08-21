# 2026-08-21 Task 02 simple collision A/B

The current formal Task 02 fill40 package does not use the graduated-cylinder
visual shell directly. Its hidden liquid collider is a source-measured,
0812-topology-derived closed manifold with 50 points, 96 triangles, zero
boundary edges, and a 16.5 mm cavity radius. The visual Hollow Body remains
unchanged: 384 points, 288 faces, 192 boundary edges, and an approximately
19.185 mm inner radius.

ConvertAsset screened three routes with the exact same formal 580-particle
fill40 fixture and particle parameters:

| Route | Static result |
|---|---|
| Visual components: body/rim SDF plus solid convexHull parts | Blocked on run 1: 580 outside, 580 below floor |
| Visual Hollow Body direct convexDecomposition plus solid parts | Blocked on run 1: 580 outside, 578 below floor |
| Qualified closed unified proxy control | Three runs pass: 0 outside, 0 below floor, q95 38.99%–39.06% |

Only the control was eligible for the prescribed motion gate. Three independent
Isaac Sim 4.1 runs performed a 2 s settle, 0.10 m vertical lift in 1 s, 2 s
hold, 1 s return, and 2 s final hold. Every run retained all 580 particles with
zero below-floor particles and maximum root tracking error
`1.1126200363809069e-08 m`.

Evidence root:
`outputs/task02_graduated_cylinder_simple_collision_ab_20260821/`.

This establishes that the two simple visual-mesh routes do not reproduce the
qualified collider under the fixed protocol. It does not claim robot grasp,
pouring, benchmark success, or universal failure for every possible remeshing
algorithm. The formal closed proxy remains the only admitted Task 02 route.
