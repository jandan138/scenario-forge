# Task11 VR r6 assembled preview and table support

r6 consumes the ConvertAsset LABSPIN X8 r5 rest-pose package and lowers the
device root from 0.82 m to the 0.755 m workbench surface. The primary tube,
balance tube, and their independent PBD sets are regenerated from the same
rotor sockets at the new device pose. r5 remains unchanged.

Three cold Isaac Sim 4.1 runs of eight seconds passed. The measured base/table
gap was 4.47e-10 m, the largest link reset/first-step jump was 1.60e-7 m, all
background objects stayed fixed, both dynamic tubes settled, and both
2640-particle sets retained 100% with zero below-floor particles.

Matched pre-Run and post-Run overview/closeup renders show the same assembled
closed device resting on the table with no floating, first-frame assembly, or
visible interpenetration. The base remains fixed; robot policy and Task11
benchmark success are not claimed. Isaac 4.5 graph migration is outside this
Isaac 4.1 package revision.
