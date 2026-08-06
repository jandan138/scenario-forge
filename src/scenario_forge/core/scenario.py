from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Mapping, TypeAlias


JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)

_PACKAGE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_V02_EXACT_BIMANUAL_PREDICATE_TYPES = (
    "named_frames_relative_pose_reached",
    "named_frame_tilt_angle_reached",
    "object_returned_to_post_warmup_pose",
)
_V03_EXACT_BIMANUAL_PREDICATE_TYPES = (
    "named_frames_relative_pose_reached",
    "named_frames_relative_pose_reached",
    "object_returned_to_post_warmup_pose",
)
_EXACT_BIMANUAL_PREDICATE_TYPES = frozenset(
    (*_V02_EXACT_BIMANUAL_PREDICATE_TYPES, *_V03_EXACT_BIMANUAL_PREDICATE_TYPES)
)
_V05_SUCCESS_PREDICATE_TYPES = frozenset(
    {
        "relative_pose_reached",
        "object_at_initial_pose",
        "articulation_joint_state_reached",
    }
)
_PROGRESS_RUBRIC_CONDITION_TYPES = frozenset(
    {
        "object_lifted",
        "pose_while_grasped",
        "object_released_on_support",
        "liquid_transfer_ratio",
    }
)
_V06_PROGRESS_RUBRIC_CONDITION_TYPES = frozenset(
    {
        *_PROGRESS_RUBRIC_CONDITION_TYPES,
        "relative_pose_reached",
        "object_at_initial_pose",
        "motion_trajectory_completed",
    }
)


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _package_segment(value: object, field: str) -> str:
    text = _string(value, field)
    if _PACKAGE_SEGMENT.fullmatch(text) is None:
        raise ValueError(f"{field} must be a portable package path segment")
    return text


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return tuple(value)


def _number_tuple(value: object, field: str, length: int) -> tuple[float, ...]:
    if (
        not isinstance(value, list)
        or len(value) != length
        or not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    ):
        raise ValueError(f"{field} must contain {length} numbers")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{field} must contain finite numbers")
    return result


def _json_mapping(value: object, field: str) -> dict[str, JsonValue]:
    data = _mapping(value, field)
    return {str(key): _copy_json(item, f"{field}.{key}") for key, item in data.items()}


def _copy_json(value: object, field: str) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_copy_json(item, field) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _copy_json(item, f"{field}.{key}") for key, item in value.items()}
    raise ValueError(f"{field} must contain JSON-compatible values")


@dataclass(frozen=True)
class PoseSpec:
    xyz: tuple[float, float, float]
    wxyz: tuple[float, float, float, float]
    scale_xyz: tuple[float, float, float] | None = None

    @classmethod
    def from_mapping(cls, value: object, field: str = "pose") -> PoseSpec:
        data = _mapping(value, field)
        xyz = _number_tuple(data.get("xyz"), f"{field}.xyz", 3)
        wxyz = _number_tuple(data.get("wxyz"), f"{field}.wxyz", 4)
        if not math.isclose(
            sum(component * component for component in wxyz),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-5,
        ):
            raise ValueError(f"{field}.wxyz must be a unit quaternion")
        scale = data.get("scale_xyz")
        return cls(
            xyz=(xyz[0], xyz[1], xyz[2]),
            wxyz=(wxyz[0], wxyz[1], wxyz[2], wxyz[3]),
            scale_xyz=(
                None
                if scale is None
                else tuple(_number_tuple(scale, f"{field}.scale_xyz", 3))  # type: ignore[arg-type]
            ),
        )

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "xyz": list(self.xyz),
            "wxyz": list(self.wxyz),
        }
        if self.scale_xyz is not None:
            result["scale_xyz"] = list(self.scale_xyz)
        return result


@dataclass(frozen=True)
class SceneSourceSpec:
    asset_id: str
    root_prim_path: str
    overlay_asset_ids: tuple[str, ...] = ()
    inactive_prim_paths: tuple[str, ...] = ()
    world_anchored_prim_paths: tuple[str, ...] = ()
    pose: PoseSpec | None = None
    composition_mode: str = "referenced_assets"

    @classmethod
    def from_mapping(
        cls,
        value: object,
        *,
        schema_version: str = "scenario-spec/v0.1",
    ) -> SceneSourceSpec:
        data = _mapping(value, "scene")
        raw_overlays = data.get("overlay_asset_ids")
        if schema_version == "scenario-spec/v0.1" and raw_overlays is not None:
            raise ValueError(
                "scene.overlay_asset_ids requires scenario-spec/v0.2"
            )
        overlay_asset_ids: tuple[str, ...] = ()
        if raw_overlays is not None:
            overlay_asset_ids = _string_tuple(
                raw_overlays,
                "scene.overlay_asset_ids",
            )
            if not overlay_asset_ids:
                raise ValueError("scene.overlay_asset_ids must not be empty when present")
            if len(set(overlay_asset_ids)) != len(overlay_asset_ids):
                raise ValueError("scene.overlay_asset_ids must contain unique asset ids")
        asset_id = _string(data.get("asset_id"), "scene.asset_id")
        if asset_id in overlay_asset_ids:
            raise ValueError("scene.overlay_asset_ids must not contain scene.asset_id")
        composition_mode = data.get("composition_mode", "referenced_assets")
        if composition_mode not in {"referenced_assets", "producer_entrypoint"}:
            raise ValueError(
                "scene.composition_mode must be 'referenced_assets' or "
                "'producer_entrypoint'"
            )
        if composition_mode != "referenced_assets" and schema_version != "scenario-spec/v0.7":
            raise ValueError("scene.composition_mode requires scenario-spec/v0.7")
        return cls(
            asset_id=asset_id,
            root_prim_path=_string(data.get("root_prim_path"), "scene.root_prim_path"),
            overlay_asset_ids=overlay_asset_ids,
            inactive_prim_paths=_string_tuple(
                data.get("inactive_prim_paths", []), "scene.inactive_prim_paths"
            ),
            world_anchored_prim_paths=_string_tuple(
                data.get("world_anchored_prim_paths", []),
                "scene.world_anchored_prim_paths",
            ),
            pose=(
                None
                if data.get("pose") is None
                else PoseSpec.from_mapping(data.get("pose"), "scene.pose")
            ),
            composition_mode=str(composition_mode),
        )

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "asset_id": self.asset_id,
            "root_prim_path": self.root_prim_path,
        }
        if self.overlay_asset_ids:
            result["overlay_asset_ids"] = list(self.overlay_asset_ids)
        if self.inactive_prim_paths:
            result["inactive_prim_paths"] = list(self.inactive_prim_paths)
        if self.world_anchored_prim_paths:
            result["world_anchored_prim_paths"] = list(
                self.world_anchored_prim_paths
            )
        if self.pose is not None:
            result["pose"] = self.pose.to_mapping()
        if self.composition_mode != "referenced_assets":
            result["composition_mode"] = self.composition_mode
        return result


@dataclass(frozen=True)
class ObjectBindingSpec:
    object_id: str
    asset_id: str
    source_prim_path: str
    role: str
    pose: PoseSpec
    named_frames: tuple[tuple[str, PoseSpec], ...] = ()
    metadata: dict[str, JsonValue] | None = None
    instance_mode: str = "referenced_asset"

    @classmethod
    def from_mapping(
        cls,
        value: object,
        index: int = 0,
        *,
        schema_version: str = "scenario-spec/v0.1",
    ) -> ObjectBindingSpec:
        field = f"objects[{index}]"
        data = _mapping(value, field)
        raw_frames = data.get("named_frames", {})
        frame_data = _mapping(raw_frames, f"{field}.named_frames")
        named_frames = tuple(
            (name, PoseSpec.from_mapping(frame, f"{field}.named_frames.{name}"))
            for name, frame in frame_data.items()
            if isinstance(name, str) and name
        )
        if len(named_frames) != len(frame_data):
            raise ValueError(f"{field}.named_frames keys must be non-empty strings")
        raw_metadata = data.get("metadata")
        instance_mode = data.get("instance_mode", "referenced_asset")
        if instance_mode not in {"referenced_asset", "embedded_scene_prim"}:
            raise ValueError(
                f"{field}.instance_mode must be 'referenced_asset' or "
                "'embedded_scene_prim'"
            )
        if instance_mode != "referenced_asset" and schema_version != "scenario-spec/v0.7":
            raise ValueError(f"{field}.instance_mode requires scenario-spec/v0.7")
        return cls(
            object_id=_string(data.get("id"), f"{field}.id"),
            asset_id=_string(data.get("asset_id"), f"{field}.asset_id"),
            source_prim_path=_string(data.get("source_prim_path"), f"{field}.source_prim_path"),
            role=_string(data.get("role"), f"{field}.role"),
            pose=PoseSpec.from_mapping(data.get("pose"), f"{field}.pose"),
            named_frames=named_frames,
            metadata=(
                None
                if raw_metadata is None
                else _json_mapping(raw_metadata, f"{field}.metadata")
            ),
            instance_mode=str(instance_mode),
        )

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "id": self.object_id,
            "asset_id": self.asset_id,
            "source_prim_path": self.source_prim_path,
            "role": self.role,
            "pose": self.pose.to_mapping(),
        }
        if self.named_frames:
            result["named_frames"] = {
                name: pose.to_mapping() for name, pose in self.named_frames
            }
        if self.metadata is not None:
            result["metadata"] = _copy_json(self.metadata, "metadata")
        if self.instance_mode != "referenced_asset":
            result["instance_mode"] = self.instance_mode
        return result


@dataclass(frozen=True)
class ActorSpec:
    actor_id: str
    end_effector: str
    capabilities: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: object, index: int = 0) -> ActorSpec:
        field = f"robot.actors[{index}]"
        data = _mapping(value, field)
        return cls(
            actor_id=_string(data.get("id"), f"{field}.id"),
            end_effector=_string(data.get("end_effector"), f"{field}.end_effector"),
            capabilities=_string_tuple(data.get("capabilities"), f"{field}.capabilities"),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": self.actor_id,
            "end_effector": self.end_effector,
            "capabilities": list(self.capabilities),
        }


@dataclass(frozen=True)
class RobotSpec:
    profile_ref: str
    spawn: PoseSpec
    actors: tuple[ActorSpec, ...]

    @classmethod
    def from_mapping(cls, value: object) -> RobotSpec:
        data = _mapping(value, "robot")
        raw_actors = data.get("actors")
        if not isinstance(raw_actors, list) or not raw_actors:
            raise ValueError("robot.actors must be a non-empty list")
        actors = tuple(ActorSpec.from_mapping(actor, index) for index, actor in enumerate(raw_actors))
        _require_unique((actor.actor_id for actor in actors), "actor")
        return cls(
            profile_ref=_string(data.get("profile_ref"), "robot.profile_ref"),
            spawn=PoseSpec.from_mapping(data.get("spawn"), "robot.spawn"),
            actors=actors,
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "profile_ref": self.profile_ref,
            "spawn": self.spawn.to_mapping(),
            "actors": [actor.to_mapping() for actor in self.actors],
        }


@dataclass(frozen=True)
class TaskStepSpec:
    step_id: str
    skill: str
    actors: tuple[str, ...]
    parameters: dict[str, JsonValue]
    depends_on: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: object, index: int = 0) -> TaskStepSpec:
        field = f"steps[{index}]"
        data = _mapping(value, field)
        return cls(
            step_id=_string(data.get("id"), f"{field}.id"),
            skill=_string(data.get("skill"), f"{field}.skill"),
            actors=_string_tuple(data.get("actors"), f"{field}.actors"),
            parameters=_json_mapping(data.get("parameters"), f"{field}.parameters"),
            depends_on=_string_tuple(data.get("depends_on", []), f"{field}.depends_on"),
        )

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "id": self.step_id,
            "skill": self.skill,
            "actors": list(self.actors),
            "parameters": _copy_json(self.parameters, "parameters"),
        }
        if self.depends_on:
            result["depends_on"] = list(self.depends_on)
        return result


@dataclass(frozen=True)
class TaskInvariantSpec:
    invariant_id: str
    invariant_type: str
    actor: str
    object_id: str
    from_step: str
    through_step: str

    @classmethod
    def from_mapping(cls, value: object, index: int = 0) -> TaskInvariantSpec:
        field = f"invariants[{index}]"
        data = _mapping(value, field)
        return cls(
            invariant_id=_string(data.get("id"), f"{field}.id"),
            invariant_type=_string(data.get("type"), f"{field}.type"),
            actor=_string(data.get("actor"), f"{field}.actor"),
            object_id=_string(data.get("object"), f"{field}.object"),
            from_step=_string(data.get("from_step"), f"{field}.from_step"),
            through_step=_string(data.get("through_step"), f"{field}.through_step"),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": self.invariant_id,
            "type": self.invariant_type,
            "actor": self.actor,
            "object": self.object_id,
            "from_step": self.from_step,
            "through_step": self.through_step,
        }


@dataclass(frozen=True)
class SuccessPredicateSpec:
    predicate_id: str
    predicate_type: str
    sequence_index: int
    parameters: dict[str, JsonValue]

    @classmethod
    def from_mapping(cls, value: object, index: int = 0) -> SuccessPredicateSpec:
        field = f"success.predicates[{index}]"
        data = _mapping(value, field)
        sequence_index = data.get("sequence_index")
        if not isinstance(sequence_index, int) or isinstance(sequence_index, bool) or sequence_index < 0:
            raise ValueError(f"{field}.sequence_index must be a non-negative integer")
        return cls(
            predicate_id=_string(data.get("id"), f"{field}.id"),
            predicate_type=_string(data.get("type"), f"{field}.type"),
            sequence_index=sequence_index,
            parameters=_json_mapping(data.get("parameters"), f"{field}.parameters"),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": self.predicate_id,
            "type": self.predicate_type,
            "sequence_index": self.sequence_index,
            "parameters": _copy_json(self.parameters, "parameters"),
        }


@dataclass(frozen=True)
class ProgressRubricItemSpec:
    item_id: str
    weight: float
    active: bool
    requires: tuple[str, ...]
    temporal: dict[str, JsonValue]
    condition: dict[str, JsonValue]
    source_ref: dict[str, JsonValue]

    @classmethod
    def from_mapping(
        cls,
        value: object,
        *,
        schema_version: str,
    ) -> ProgressRubricItemSpec:
        data = _mapping(value, "progress rubric item")
        item_id = _string(data.get("id"), "progress rubric item.id")
        weight = data.get("weight")
        if (
            not isinstance(weight, (int, float))
            or isinstance(weight, bool)
            or not math.isfinite(weight)
            or weight <= 0.0
            or weight > 1.0
        ):
            raise ValueError("progress rubric item.weight must be a finite number in (0, 1]")
        active = data.get("active", True)
        if not isinstance(active, bool):
            raise ValueError("progress rubric item.active must be a boolean")
        requires = data.get("requires", [])
        temporal = dict(
            _json_mapping(data.get("temporal"), f"progress rubric item {item_id}.temporal")
        )
        kind = temporal.get("kind")
        if kind not in {"instant", "sustained", "terminal"}:
            raise ValueError(
                f"progress rubric item {item_id}.temporal.kind must be instant, "
                "sustained, or terminal"
            )
        if kind == "sustained":
            window = _mapping(
                temporal.get("window"), f"progress rubric item {item_id}.temporal.window"
            )
            _string(window.get("from_step"), f"progress rubric item {item_id}.window.from_step")
            _string(
                window.get("through_step"),
                f"progress rubric item {item_id}.window.through_step",
            )
        elif "window" in temporal:
            raise ValueError(
                f"progress rubric item {item_id}.temporal.window is only valid when "
                "kind is sustained"
            )
        condition = dict(
            _json_mapping(data.get("condition"), f"progress rubric item {item_id}.condition")
        )
        condition_type = condition.get("type")
        supported_condition_types = (
            _V06_PROGRESS_RUBRIC_CONDITION_TYPES
            if schema_version in {"scenario-spec/v0.6", "scenario-spec/v0.7"}
            else _PROGRESS_RUBRIC_CONDITION_TYPES
        )
        if condition_type not in supported_condition_types:
            raise ValueError(
                f"progress rubric item {item_id}.condition.type must be one of "
                + ", ".join(sorted(supported_condition_types))
            )
        _mapping(
            condition.get("parameters"),
            f"progress rubric item {item_id}.condition.parameters",
        )
        source_ref = dict(
            _json_mapping(data.get("source_ref", {}), f"progress rubric item {item_id}.source_ref")
        )
        return cls(
            item_id=item_id,
            weight=float(weight),
            active=active,
            requires=tuple(_string_tuple(requires, f"progress rubric item {item_id}.requires")),
            temporal=temporal,
            condition=condition,
            source_ref=source_ref,
        )

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "id": self.item_id,
            "weight": self.weight,
            "active": self.active,
            "temporal": _copy_json(self.temporal, "temporal"),
            "condition": _copy_json(self.condition, "condition"),
            "source_ref": _copy_json(self.source_ref, "source_ref"),
        }
        if self.requires:
            result["requires"] = list(self.requires)
        return result


@dataclass(frozen=True)
class ProgressRubricSpec:
    aggregation: dict[str, JsonValue]
    items: tuple[ProgressRubricItemSpec, ...]

    @classmethod
    def from_mapping(
        cls,
        value: object,
        *,
        schema_version: str,
    ) -> ProgressRubricSpec:
        data = _mapping(value, "success.progress_rubric")
        aggregation = dict(
            _json_mapping(data.get("aggregation"), "success.progress_rubric.aggregation")
        )
        if aggregation.get("type") != "weighted_progress_score":
            raise ValueError(
                "success.progress_rubric.aggregation.type must be weighted_progress_score"
            )
        if aggregation.get("normalization") not in {
            "declared_sum",
            "active_subset_renormalize",
        }:
            raise ValueError(
                "success.progress_rubric.aggregation.normalization must be "
                "declared_sum or active_subset_renormalize"
            )
        if aggregation.get("inactive_treatment") not in {"zero", "exclude"}:
            raise ValueError(
                "success.progress_rubric.aggregation.inactive_treatment must be "
                "zero or exclude"
            )
        raw_items = data.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            raise ValueError("success.progress_rubric.items must be a non-empty list")
        items = tuple(
            ProgressRubricItemSpec.from_mapping(
                item,
                schema_version=schema_version,
            )
            for item in raw_items
        )
        _require_unique((item.item_id for item in items), "progress rubric item")
        weight_sum = sum(item.weight for item in items)
        if not math.isclose(weight_sum, 1.0, rel_tol=0.0, abs_tol=1e-6):
            raise ValueError(
                "success.progress_rubric item weights must sum to 1.0, "
                f"got {weight_sum:.6f}"
            )
        return cls(aggregation=aggregation, items=items)

    def to_mapping(self) -> dict[str, object]:
        return {
            "aggregation": _copy_json(self.aggregation, "aggregation"),
            "items": [item.to_mapping() for item in self.items],
        }


@dataclass(frozen=True)
class SuccessSpec:
    operator: str
    claim_scope: str
    predicates: tuple[SuccessPredicateSpec, ...]
    progress_rubric: ProgressRubricSpec | None = None

    @classmethod
    def from_mapping(
        cls,
        value: object,
        *,
        schema_version: str,
    ) -> SuccessSpec:
        data = _mapping(value, "success")
        raw_predicates = data.get("predicates")
        if not isinstance(raw_predicates, list) or not raw_predicates:
            raise ValueError("success.predicates must be a non-empty list")
        predicates = tuple(
            SuccessPredicateSpec.from_mapping(predicate, index)
            for index, predicate in enumerate(raw_predicates)
        )
        _require_unique((predicate.predicate_id for predicate in predicates), "success predicate")
        operator = _string(data.get("operator"), "success.operator")
        if operator not in {"all", "any"}:
            raise ValueError("success.operator must be 'all' or 'any'")
        raw_rubric = data.get("progress_rubric")
        return cls(
            operator=operator,
            claim_scope=_string(data.get("claim_scope"), "success.claim_scope"),
            predicates=predicates,
            progress_rubric=(
                None
                if raw_rubric is None
                else ProgressRubricSpec.from_mapping(
                    raw_rubric,
                    schema_version=schema_version,
                )
            ),
        )

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "operator": self.operator,
            "claim_scope": self.claim_scope,
            "predicates": [predicate.to_mapping() for predicate in self.predicates],
        }
        if self.progress_rubric is not None:
            result["progress_rubric"] = self.progress_rubric.to_mapping()
        return result


@dataclass(frozen=True)
class ScenarioSpec:
    schema_version: str
    scenario_id: str
    domain: str
    task_family: str
    instruction: str
    scene: SceneSourceSpec
    objects: tuple[ObjectBindingSpec, ...]
    robot: RobotSpec
    steps: tuple[TaskStepSpec, ...]
    invariants: tuple[TaskInvariantSpec, ...]
    success: SuccessSpec
    max_steps: int
    seed: str | int

    @classmethod
    def from_mapping(cls, value: object) -> ScenarioSpec:
        data = _mapping(value, "scenario spec")
        schema_version = data.get("schema_version")
        if schema_version not in {
            "scenario-spec/v0.1",
            "scenario-spec/v0.2",
            "scenario-spec/v0.3",
            "scenario-spec/v0.4",
            "scenario-spec/v0.5",
            "scenario-spec/v0.6",
            "scenario-spec/v0.7",
        }:
            raise ValueError("unsupported scenario spec schema_version")
        raw_objects = data.get("objects")
        raw_steps = data.get("steps")
        raw_invariants = data.get("invariants")
        if not isinstance(raw_objects, list) or not raw_objects:
            raise ValueError("objects must be a non-empty list")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("steps must be a non-empty list")
        if not isinstance(raw_invariants, list):
            raise ValueError("invariants must be a list")

        objects = tuple(
            ObjectBindingSpec.from_mapping(
                item, index, schema_version=str(schema_version)
            )
            for index, item in enumerate(raw_objects)
        )
        steps = tuple(TaskStepSpec.from_mapping(item, index) for index, item in enumerate(raw_steps))
        invariants = tuple(
            TaskInvariantSpec.from_mapping(item, index)
            for index, item in enumerate(raw_invariants)
        )
        _require_unique((item.object_id for item in objects), "object")
        _require_unique((item.step_id for item in steps), "step")
        _require_unique((item.invariant_id for item in invariants), "invariant")

        robot = RobotSpec.from_mapping(data.get("robot"))
        success = SuccessSpec.from_mapping(
            data.get("success"),
            schema_version=str(schema_version),
        )
        max_steps = data.get("max_steps")
        if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        seed = data.get("seed")
        if not isinstance(seed, (str, int)) or isinstance(seed, bool):
            raise ValueError("seed must be a string or integer")
        if isinstance(seed, int):
            if seed < 0:
                raise ValueError("seed must be a non-negative integer")
        else:
            seed = _package_segment(seed, "seed")

        spec = cls(
            schema_version=schema_version,
            scenario_id=_package_segment(data.get("scenario_id"), "scenario_id"),
            domain=_string(data.get("domain"), "domain"),
            task_family=_string(data.get("task_family"), "task_family"),
            instruction=_string(data.get("instruction"), "instruction"),
            scene=SceneSourceSpec.from_mapping(
                data.get("scene"),
                schema_version=schema_version,
            ),
            objects=objects,
            robot=robot,
            steps=steps,
            invariants=invariants,
            success=success,
            max_steps=max_steps,
            seed=seed,
        )
        spec._validate_references()
        return spec

    def _validate_references(self) -> None:
        actor_ids = {actor.actor_id for actor in self.robot.actors}
        object_ids = {item.object_id for item in self.objects}
        step_ids = {step.step_id for step in self.steps}
        step_positions = {step.step_id: index for index, step in enumerate(self.steps)}

        embedded = [
            item for item in self.objects if item.instance_mode == "embedded_scene_prim"
        ]
        if self.scene.composition_mode == "producer_entrypoint":
            if not embedded:
                raise ValueError(
                    "producer_entrypoint scene requires embedded_scene_prim objects"
                )
            for item in embedded:
                if item.asset_id != self.scene.asset_id:
                    raise ValueError(
                        f"embedded_scene_prim object {item.object_id} asset_id must "
                        "equal scene.asset_id"
                    )
        elif embedded:
            raise ValueError(
                "embedded_scene_prim objects require scene.composition_mode "
                "producer_entrypoint"
            )

        for step in self.steps:
            for actor in step.actors:
                if actor not in actor_ids:
                    raise ValueError(f"step {step.step_id} references unknown actor {actor}")
            for dependency in step.depends_on:
                if dependency not in step_ids:
                    raise ValueError(
                        f"step {step.step_id} depends on unknown step {dependency}"
                    )
                if dependency == step.step_id:
                    raise ValueError(f"step {step.step_id} cannot depend on itself")
            _validate_parameter_references(step.parameters, object_ids, self.objects, step.step_id)

        for invariant in self.invariants:
            if invariant.actor not in actor_ids:
                raise ValueError(
                    f"invariant {invariant.invariant_id} references unknown actor {invariant.actor}"
                )
            if invariant.object_id not in object_ids:
                raise ValueError(
                    f"invariant {invariant.invariant_id} references unknown object {invariant.object_id}"
                )
            if invariant.from_step not in step_ids:
                raise ValueError(
                    f"invariant {invariant.invariant_id} references unknown step {invariant.from_step}"
                )
            if invariant.through_step not in step_ids:
                raise ValueError(
                    f"invariant {invariant.invariant_id} references unknown step {invariant.through_step}"
                )
            if step_positions[invariant.from_step] > step_positions[invariant.through_step]:
                raise ValueError(
                    f"invariant {invariant.invariant_id} ends before it starts"
                )

        for predicate in self.success.predicates:
            _validate_v05_success_predicate(
                predicate,
                schema_version=self.schema_version,
                object_ids=object_ids,
            )
            _validate_parameter_references(
                predicate.parameters, object_ids, self.objects, predicate.predicate_id
            )
            if predicate.predicate_type in _EXACT_BIMANUAL_PREDICATE_TYPES:
                projection = _mapping(
                    predicate.parameters.get("diagnostic_compatibility_projection"),
                    f"{predicate.predicate_id}.diagnostic_compatibility_projection",
                )
                projection_parameters = _mapping(
                    projection.get("parameters"),
                    f"{predicate.predicate_id}.diagnostic_compatibility_projection.parameters",
                )
                _validate_parameter_references(
                    projection_parameters,
                    object_ids,
                    self.objects,
                    f"{predicate.predicate_id}.diagnostic_compatibility_projection",
                )
        _validate_progress_rubric_references(self, actor_ids, object_ids, step_positions)
        _validate_explicit_bimanual_success(self)

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "domain": self.domain,
            "task_family": self.task_family,
            "instruction": self.instruction,
            "scene": self.scene.to_mapping(),
            "objects": [item.to_mapping() for item in self.objects],
            "robot": self.robot.to_mapping(),
            "steps": [step.to_mapping() for step in self.steps],
            "invariants": [invariant.to_mapping() for invariant in self.invariants],
            "success": self.success.to_mapping(),
            "max_steps": self.max_steps,
            "seed": self.seed,
        }


def _require_unique(values: Any, kind: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"duplicate {kind} id {value}")
        seen.add(value)


def _validate_parameter_references(
    parameters: Mapping[str, JsonValue],
    object_ids: set[str],
    objects: tuple[ObjectBindingSpec, ...],
    owner: str,
) -> None:
    object_by_id = {item.object_id: item for item in objects}
    for key in ("object", "source", "target", "container", "relative_to", "relative_axis_object"):
        value = parameters.get(key)
        if isinstance(value, str) and value not in object_ids:
            raise ValueError(f"{owner} references unknown object {value}")
    for key in ("source_frame", "target_frame", "object_frame", "relative_to_frame"):
        value = parameters.get(key)
        if not isinstance(value, str):
            continue
        object_id, separator, frame_id = value.rpartition(".")
        if not separator or object_id not in object_ids:
            raise ValueError(f"{owner} references unknown frame {value}")
        frame_ids = {name for name, _ in object_by_id[object_id].named_frames}
        if frame_id not in frame_ids:
            raise ValueError(f"{owner} references unknown frame {value}")


def _validate_progress_rubric_references(
    spec: ScenarioSpec,
    actor_ids: set[str],
    object_ids: set[str],
    step_positions: dict[str, int],
) -> None:
    rubric = spec.success.progress_rubric
    if rubric is None:
        return
    if spec.schema_version not in {
        "scenario-spec/v0.4",
        "scenario-spec/v0.6",
        "scenario-spec/v0.7",
    }:
        raise ValueError(
            "success.progress_rubric requires scenario-spec/v0.4 or v0.6, "
            f"got {spec.schema_version}"
        )
    grasp_windows: list[tuple[str, str, str, str, str]] = []
    for item in rubric.items:
        owner = f"progress rubric item {item.item_id}"
        temporal = item.temporal
        if temporal["kind"] == "sustained":
            window = temporal["window"]
            from_step = window["from_step"]
            through_step = window["through_step"]
            for step_id in (from_step, through_step):
                if step_id not in step_positions:
                    raise ValueError(f"{owner} references unknown step {step_id}")
            if step_positions[from_step] > step_positions[through_step]:
                raise ValueError(f"{owner} window ends before it starts")
        parameters = item.condition.get("parameters")
        if not isinstance(parameters, Mapping):
            raise ValueError(f"{owner}.condition.parameters must be a mapping")
        _validate_parameter_references(parameters, object_ids, spec.objects, owner)
        for key in ("object", "source", "target", "support_surface"):
            value = parameters.get(key)
            if isinstance(value, str) and value not in object_ids:
                raise ValueError(f"{owner} references unknown object {value}")
        if item.condition["type"] == "pose_while_grasped":
            grasp = _mapping(parameters.get("grasp"), f"{owner}.grasp")
            actor = _string(grasp.get("actor"), f"{owner}.grasp.actor")
            grasp_object = _string(grasp.get("object"), f"{owner}.grasp.object")
            if actor not in actor_ids:
                raise ValueError(f"{owner} references unknown actor {actor}")
            if grasp_object not in object_ids:
                raise ValueError(f"{owner} references unknown object {grasp_object}")
            nested = _mapping(parameters.get("predicate"), f"{owner}.predicate")
            _string(nested.get("type"), f"{owner}.predicate.type")
            _validate_parameter_references(
                _mapping(nested.get("parameters"), f"{owner}.predicate.parameters"),
                object_ids,
                spec.objects,
                f"{owner}.predicate",
            )
            if temporal["kind"] == "sustained":
                grasp_windows.append(
                    (
                        actor,
                        grasp_object,
                        str(temporal["window"]["from_step"]),
                        str(temporal["window"]["through_step"]),
                        item.item_id,
                    )
                )
    for invariant in spec.invariants:
        if invariant.invariant_type != "maintain_grasp":
            continue
        for actor, grasp_object, from_step, through_step, item_id in grasp_windows:
            if (
                invariant.actor == actor
                and invariant.object_id == grasp_object
                and step_positions[invariant.from_step] <= step_positions[through_step]
                and step_positions[from_step] <= step_positions[invariant.through_step]
            ):
                raise ValueError(
                    f"invariant {invariant.invariant_id} duplicates progress rubric "
                    f"item {item_id}: a grasp condition may be a hard gate or a "
                    "scored rubric item, not both"
                )


def _validate_v05_success_predicate(
    predicate: SuccessPredicateSpec,
    *,
    schema_version: str,
    object_ids: set[str],
) -> None:
    parameters = predicate.parameters
    relative_to_part: object = None
    if predicate.predicate_type == "relative_pose_reached":
        raw_alignment = parameters.get("axis_alignment")
        if isinstance(raw_alignment, Mapping):
            relative_to_part = raw_alignment.get("relative_to_part")
    relative_axis_part = (
        parameters.get("relative_axis_part")
        if predicate.predicate_type == "object_at_initial_pose"
        else None
    )
    if schema_version not in {
        "scenario-spec/v0.5",
        "scenario-spec/v0.6",
        "scenario-spec/v0.7",
    }:
        if relative_to_part is not None or relative_axis_part is not None:
            raise ValueError(
                "articulated axis part references require scenario-spec/v0.5 or v0.6"
            )
        if predicate.predicate_type == "articulation_joint_state_reached":
            raise ValueError(
                "articulation_joint_state_reached requires scenario-spec/v0.5 or v0.6"
            )
        return
    if predicate.predicate_type not in _V05_SUCCESS_PREDICATE_TYPES:
        raise ValueError(
            f"{schema_version} success predicate type must be one of "
            + ", ".join(sorted(_V05_SUCCESS_PREDICATE_TYPES))
        )
    field = f"success predicate {predicate.predicate_id}.parameters"
    if predicate.predicate_type == "relative_pose_reached":
        if relative_to_part is not None:
            _string(
                relative_to_part,
                f"{field}.axis_alignment.relative_to_part",
            )
        return
    if predicate.predicate_type == "object_at_initial_pose":
        if relative_axis_part is not None:
            _string(relative_axis_part, f"{field}.relative_axis_part")
            relative_axis_object = _string(
                parameters.get("relative_axis_object"),
                f"{field}.relative_axis_object",
            )
            if relative_axis_object not in object_ids:
                raise ValueError(
                    f"{predicate.predicate_id} references unknown object "
                    f"{relative_axis_object}"
                )
        return
    _require_exact_fields(parameters, {"object", "joint", "state"}, field)
    object_id = _string(parameters.get("object"), f"{field}.object")
    if object_id not in object_ids:
        raise ValueError(f"{predicate.predicate_id} references unknown object {object_id}")
    _string(parameters.get("joint"), f"{field}.joint")
    _string(parameters.get("state"), f"{field}.state")


def _validate_explicit_bimanual_success(spec: ScenarioSpec) -> None:
    exact = [
        predicate
        for predicate in spec.success.predicates
        if predicate.predicate_type in _EXACT_BIMANUAL_PREDICATE_TYPES
    ]
    if not exact:
        if spec.schema_version in {"scenario-spec/v0.3", "scenario-spec/v0.4"}:
            raise ValueError(
                f"{spec.schema_version} requires the exact ordered bimanual success contract"
            )
        return
    if spec.schema_version == "scenario-spec/v0.2":
        expected_types = _V02_EXACT_BIMANUAL_PREDICATE_TYPES
    elif spec.schema_version in {"scenario-spec/v0.3", "scenario-spec/v0.4"}:
        expected_types = _V03_EXACT_BIMANUAL_PREDICATE_TYPES
    else:
        raise ValueError(
            "explicit bimanual predicates require scenario-spec/v0.2 or later"
        )
    if spec.success.operator != "all":
        raise ValueError("explicit bimanual predicates require success.operator 'all'")
    if len(exact) != len(spec.success.predicates) or [
        predicate.predicate_type for predicate in exact
    ] != list(expected_types):
        raise ValueError(
            "explicit bimanual success list order must be align, tilt, then return"
        )
    if [predicate.sequence_index for predicate in exact] != [0, 1, 2]:
        raise ValueError(
            "explicit bimanual success predicate sequence_index values must be 0, 1, 2"
        )
    for predicate in exact:
        _validate_explicit_predicate(predicate, schema_version=spec.schema_version)
    if spec.schema_version in {"scenario-spec/v0.3", "scenario-spec/v0.4"}:
        _validate_v03_bimanual_relationships(exact)


def _validate_explicit_predicate(
    predicate: SuccessPredicateSpec,
    *,
    schema_version: str,
) -> None:
    parameters = predicate.parameters
    field = f"success predicate {predicate.predicate_id}.parameters"
    if predicate.predicate_type == "named_frames_relative_pose_reached":
        if schema_version == "scenario-spec/v0.2":
            _require_exact_fields(
                parameters,
                {
                    "source_frame",
                    "target_frame",
                    "horizontal_error_max_m",
                    "signed_height_range_m",
                    "source_normal_axis",
                    "target_normal_axis",
                    "normal_angle_max_deg",
                    "bounds",
                    "diagnostic_compatibility_projection",
                },
                field,
            )
            _non_negative_finite_number(
                parameters.get("horizontal_error_max_m"),
                f"{field}.horizontal_error_max_m",
            )
            _ordered_finite_range(
                parameters.get("signed_height_range_m"),
                f"{field}.signed_height_range_m",
            )
            _bounded_angle(
                parameters.get("normal_angle_max_deg"),
                f"{field}.normal_angle_max_deg",
            )
        else:
            _validate_v03_relative_pose_parameters(parameters, field)
        _require_value(parameters.get("source_normal_axis"), "z", f"{field}.source_normal_axis")
        _require_value(parameters.get("target_normal_axis"), "z", f"{field}.target_normal_axis")
    elif predicate.predicate_type == "named_frame_tilt_angle_reached":
        if schema_version != "scenario-spec/v0.2":
            raise ValueError(
                "named_frame_tilt_angle_reached is only valid in scenario-spec/v0.2"
            )
        _require_exact_fields(
            parameters,
            {
                "object_frame",
                "world_axis",
                "angle_range_deg",
                "bounds",
                "diagnostic_compatibility_projection",
            },
            field,
        )
        _require_value(parameters.get("world_axis"), "z", f"{field}.world_axis")
        angle_range = _ordered_finite_range(
            parameters.get("angle_range_deg"),
            f"{field}.angle_range_deg",
        )
        if angle_range[0] < 0.0 or angle_range[1] > 180.0:
            raise ValueError(f"{field}.angle_range_deg must remain within [0, 180]")
    else:
        _require_exact_fields(
            parameters,
            {
                "object",
                "translation_error_max_m",
                "rotation_error_max_deg",
                "bounds",
                "diagnostic_compatibility_projection",
            },
            field,
        )
        _non_negative_finite_number(
            parameters.get("translation_error_max_m"),
            f"{field}.translation_error_max_m",
        )
        _bounded_angle(
            parameters.get("rotation_error_max_deg"),
            f"{field}.rotation_error_max_deg",
        )
    _require_value(parameters.get("bounds"), "inclusive", f"{field}.bounds")
    _validate_diagnostic_projection(
        parameters.get("diagnostic_compatibility_projection"),
        f"{field}.diagnostic_compatibility_projection",
    )


def _validate_v03_relative_pose_parameters(
    parameters: Mapping[str, object],
    field: str,
) -> None:
    _require_exact_fields(
        parameters,
        {
            "source_frame",
            "target_frame",
            "target_frame_from_source_frame_nominal_pose",
            "source_origin_in_target_frame_range_m",
            "source_normal_axis",
            "target_normal_axis",
            "source_normal_polar_angle_range_deg",
            "source_normal_azimuth_range_deg",
            "bounds",
            "diagnostic_compatibility_projection",
        },
        field,
    )
    nominal_mapping = _mapping(
        parameters.get("target_frame_from_source_frame_nominal_pose"),
        f"{field}.target_frame_from_source_frame_nominal_pose",
    )
    _require_exact_fields(
        nominal_mapping,
        {"xyz", "wxyz"},
        f"{field}.target_frame_from_source_frame_nominal_pose",
    )
    nominal = PoseSpec.from_mapping(
        nominal_mapping,
        f"{field}.target_frame_from_source_frame_nominal_pose",
    )
    translation_ranges = _mapping(
        parameters.get("source_origin_in_target_frame_range_m"),
        f"{field}.source_origin_in_target_frame_range_m",
    )
    _require_exact_fields(
        translation_ranges,
        {"x", "y", "z"},
        f"{field}.source_origin_in_target_frame_range_m",
    )
    ordered_translation_ranges = tuple(
        _ordered_finite_range(
            translation_ranges.get(axis),
            f"{field}.source_origin_in_target_frame_range_m.{axis}",
        )
        for axis in ("x", "y", "z")
    )
    polar_range = _ordered_finite_range(
        parameters.get("source_normal_polar_angle_range_deg"),
        f"{field}.source_normal_polar_angle_range_deg",
    )
    if polar_range[0] < 0.0 or polar_range[1] > 180.0:
        raise ValueError(
            f"{field}.source_normal_polar_angle_range_deg must remain within [0, 180]"
        )
    azimuth_range = _ordered_finite_range(
        parameters.get("source_normal_azimuth_range_deg"),
        f"{field}.source_normal_azimuth_range_deg",
    )
    if azimuth_range[0] < -180.0 or azimuth_range[1] > 180.0:
        raise ValueError(
            f"{field}.source_normal_azimuth_range_deg must remain within [-180, 180]"
        )
    for axis, value, bounds in zip(
        ("x", "y", "z"),
        nominal.xyz,
        ordered_translation_ranges,
    ):
        _require_inside(
            value,
            bounds,
            f"{field} nominal {axis} translation",
        )
    normal = _rotate_local_z_by_quaternion(nominal.wxyz)
    horizontal_norm = math.hypot(normal[0], normal[1])
    if horizontal_norm <= 1e-9:
        raise ValueError(
            f"{field} nominal source normal must have a defined target-frame azimuth"
        )
    polar = math.degrees(math.atan2(horizontal_norm, normal[2]))
    azimuth = math.degrees(math.atan2(normal[1], normal[0]))
    _require_inside(
        polar,
        polar_range,
        f"{field} nominal source-normal polar angle",
    )
    _require_inside(
        azimuth,
        azimuth_range,
        f"{field} nominal source-normal azimuth",
    )


def _validate_v03_bimanual_relationships(
    predicates: list[SuccessPredicateSpec],
) -> None:
    pre_pour = predicates[0].parameters
    pour = predicates[1].parameters
    if (
        pre_pour.get("source_frame") != pour.get("source_frame")
        or pre_pour.get("target_frame") != pour.get("target_frame")
    ):
        raise ValueError("v0.3 pre-pour and pour predicates must use the same frames")
    source_frame = _string(pre_pour.get("source_frame"), "v0.3 source_frame")
    source_object_id = source_frame.rpartition(".")[0]
    return_object = predicates[2].parameters.get("object")
    if return_object != source_object_id:
        raise ValueError("v0.3 return object must match the source frame object")


def _rotate_local_z_by_quaternion(
    wxyz: tuple[float, float, float, float],
) -> tuple[float, float, float]:
    w, x, y, z = wxyz
    return (
        2.0 * (x * z + w * y),
        2.0 * (y * z - w * x),
        1.0 - 2.0 * (x * x + y * y),
    )


def _require_inside(
    value: float,
    bounds: tuple[float, float],
    field: str,
) -> None:
    if value < bounds[0] or value > bounds[1]:
        raise ValueError(f"{field} must remain inside its success range")


def _validate_diagnostic_projection(value: object, field: str) -> None:
    projection = _mapping(value, field)
    _require_exact_fields(projection, {"type", "parameters"}, field)
    projection_type = _string(projection.get("type"), f"{field}.type")
    if projection_type not in {"relative_pose_reached", "object_at_initial_pose"}:
        raise ValueError(
            f"{field}.type must be a supported diagnostic compatibility predicate"
        )
    _json_mapping(projection.get("parameters"), f"{field}.parameters")


def _require_exact_fields(
    value: Mapping[str, object], expected: set[str], field: str
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        raise ValueError(f"{field} is missing field(s): {', '.join(missing)}")
    if unexpected:
        raise ValueError(f"{field} contains unexpected field(s): {', '.join(unexpected)}")


def _finite_number(value: object, field: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
    ):
        raise ValueError(f"{field} must be a finite number")
    return float(value)


def _non_negative_finite_number(value: object, field: str) -> float:
    result = _finite_number(value, field)
    if result < 0.0:
        raise ValueError(f"{field} must be non-negative")
    return result


def _ordered_finite_range(value: object, field: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field} must contain two finite numbers")
    result = (_finite_number(value[0], field), _finite_number(value[1], field))
    if result[0] > result[1]:
        raise ValueError(f"{field} lower bound must not exceed upper bound")
    return result


def _bounded_angle(value: object, field: str) -> float:
    result = _finite_number(value, field)
    if result < 0.0 or result > 180.0:
        raise ValueError(f"{field} must be within [0, 180]")
    return result


def _require_value(value: object, expected: object, field: str) -> None:
    if value != expected:
        raise ValueError(f"{field} must be {expected!r}")
