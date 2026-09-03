# Preheated water-bath centrifuge-tube VR candidate

This new task starts with one non-threaded, closed 15 mL tube in the front outer
slot of the admitted scaled SDF rack. The operating arm removes the tube,
immerses its lower body in a semantically preheated 60 C beaker bath for five
seconds, withdraws it, and returns it to the same slot. The rack, tube, magnetic
stirrer, SDF beaker, table, and room are all existing admitted or previously
consumed assets.

The beaker uses the current stir-bar r5 frozen PBD water: 969 particles,
transparent light-blue material, and unchanged particle, collision, and solver
parameters. Relocation to the stirrer working surface is world-baked into both
`points` and `physxParticle:simulationPoints`; the particle root remains
identity. A parent transform was rejected because Isaac Sim 4.1 did not render
or simulate that composition reliably. The water-bath group therefore remains
fixed rather than advertising unsupported runtime XY randomization.

The tube is a single dynamic closed assembly and contains a 70% amber
`VisualLiquid` child. That child has no collision, rigid body, mass, particle
API, or task metric role. The magnetic stirrer remains the existing single
rigid body with fixed visual controls. Scene metadata marks it `preheated` at
60 C with stirring disabled; no calibrated thermal transfer is simulated.

Three independent Isaac Sim 4.1 static runs and three independent robot-free
kinematic tube trajectories pass. Every run retains 969/969 particles with no
particles below the beaker and no hard PhysX/CUDA/Hydra errors. The tube returns
within about 1.37 mm of its initial slot pose. These are scene and robot-free
interaction claims, not Lift2 grasp, human VR collection, robot policy, or
benchmark success.

Isaac Sim 4.1 could not keep Camera annotators valid while resetting the PBD
World, and Timeline-only Camera capture returned stale rigid visuals. The final
video therefore uses a two-process evidence path: the physics process records
the actual tube pose and all 969 particle points at 30 fps; a paused-physics
Isaac 4.1 RTX process replays exactly those states. The render manifest labels
this method and explicitly denies a live-camera physics capture claim.
