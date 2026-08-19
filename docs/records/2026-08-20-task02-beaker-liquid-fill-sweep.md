# 2026-08-20 Task02 beaker liquid fill sweep

The existing liquid-autofill workflow was exercised against the Task02 r10.3 no-fluid source at
`/World/obj_beaker`. Four independent variants targeted 20%, 40%, 60%, and 80% settled q95 fill.
Each variant passed three producer cold starts and one final self-contained scene integration in
EOS-managed Isaac Sim 4.1.

| Variant | Particles | Measured q95 fill | Minimum retention | Below floor | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| fill20 | 408 | 22.48% | 100% | 0 | pass |
| fill40 | 816 | 44.13% | 100% | 0 | pass |
| fill60 | 1122 | 60.09% | 100% | 0 | pass |
| fill80 | 1530 | 81.94% | 100% | 0 | pass |

All sixteen observations reported zero selected hard runtime errors. Package audit opened every
USD with `/World` as default prim, found 59 used layers per variant with none outside the delivery
directory, and passed ZIP integrity for all four packages. Source and recipe bindings remained
unchanged from the quantity-cylinder golden regression.

Claim boundary: qualified GPU-PBD loaded starts only. No robot, pouring, liquid-transfer metric,
or benchmark success is inferred.
