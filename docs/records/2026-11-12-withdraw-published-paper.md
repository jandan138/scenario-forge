# 2026-11-12 — Withdraw the paper tree from the published repository

The public repository is `jandan138/scenario-forge`. `paper/` had been tracked
since the Lab2Sim figure commits and was visible on `origin/main`. On
2026-11-12 the author required that tree to be removed from the published
history.

The published branch no longer contains `paper/`. `.gitignore` ignores the
whole directory. Tests that read those sources skip unless the directory is
present and not ignored. VAL-005 and the artifact policy now say the paper
tree stays out of the published repository. This does not relax the rules for
USD, video, simulation frames, or other large artifacts.

Local working copies of `paper/` were left in place and were not deleted.
Historical records that describe the 2026-09-22 retention decision remain as
records of that earlier decision. GitHub can continue to serve the old commit
ids until it garbage-collects them; copies already cloned elsewhere also remain.
