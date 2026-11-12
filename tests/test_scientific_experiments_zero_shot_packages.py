"""Zero-shot colleague crates stay stub packages; metadata prims are not identities."""

from scripts.build_scientific_experiments_colleague_final import (
    METADATA_PRIM_NAMES,
    NON_SPLIT_PRIM_NAMES,
    OUT_DEFAULT,
    OUT_ZERO_SHOT,
    TASKS,
    TASK_SPECS,
    ZERO_SHOT_TASKS,
    admits_identity,
)


def test_zero_shot_task_table_is_the_six_z_directories():
    assert ZERO_SHOT_TASKS == (
        "task_z1_remove_beaker_pour_shake",
        "task_z2_key_steps_in_mof",
        "task_z3_boat_pour_stir",
        "task_z4_silver_mirror_reaction",
        "task_z5_fixed_weight_weighing",
        "task_z6_evaporative_crystallization_prep",
    )
    assert set(ZERO_SHOT_TASKS).isdisjoint(TASKS)
    assert OUT_ZERO_SHOT.name == "scientific_experiments_colleague_zero_shot_20260924"
    assert OUT_DEFAULT.name == "scientific_experiments_colleague_final_20260920"


def test_zero_shot_semantics_stay_stub_and_unverified():
    for task in ZERO_SHOT_TASKS:
        spec = TASK_SPECS[task]
        assert spec["mode"] == "stub"
        assert spec["title_zh"]
        assert spec["primary_objects"]
        assert "source_head" not in spec


def test_metadata_and_non_split_prims_are_not_identity_candidates():
    for name in METADATA_PRIM_NAMES | NON_SPLIT_PRIM_NAMES:
        assert not admits_identity(name)
    assert admits_identity("obj_beaker")
    assert admits_identity("table")
    assert admits_identity("Room")
    assert not admits_identity("fluid_runtime")
    assert not admits_identity("obj_grain_0001")
