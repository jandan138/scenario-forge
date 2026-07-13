from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, TypeAlias


JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)

_PACKAGE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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
    return tuple(float(item) for item in value)


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
    inactive_prim_paths: tuple[str, ...] = ()
    world_anchored_prim_paths: tuple[str, ...] = ()
    pose: PoseSpec | None = None

    @classmethod
    def from_mapping(cls, value: object) -> SceneSourceSpec:
        data = _mapping(value, "scene")
        return cls(
            asset_id=_string(data.get("asset_id"), "scene.asset_id"),
            root_prim_path=_string(data.get("root_prim_path"), "scene.root_prim_path"),
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
        )

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "asset_id": self.asset_id,
            "root_prim_path": self.root_prim_path,
        }
        if self.inactive_prim_paths:
            result["inactive_prim_paths"] = list(self.inactive_prim_paths)
        if self.world_anchored_prim_paths:
            result["world_anchored_prim_paths"] = list(
                self.world_anchored_prim_paths
            )
        if self.pose is not None:
            result["pose"] = self.pose.to_mapping()
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

    @classmethod
    def from_mapping(cls, value: object, index: int = 0) -> ObjectBindingSpec:
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
class SuccessSpec:
    operator: str
    claim_scope: str
    predicates: tuple[SuccessPredicateSpec, ...]

    @classmethod
    def from_mapping(cls, value: object) -> SuccessSpec:
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
        return cls(
            operator=operator,
            claim_scope=_string(data.get("claim_scope"), "success.claim_scope"),
            predicates=predicates,
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "operator": self.operator,
            "claim_scope": self.claim_scope,
            "predicates": [predicate.to_mapping() for predicate in self.predicates],
        }


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
        if data.get("schema_version") != "scenario-spec/v0.1":
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
            ObjectBindingSpec.from_mapping(item, index) for index, item in enumerate(raw_objects)
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
        success = SuccessSpec.from_mapping(data.get("success"))
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
            schema_version="scenario-spec/v0.1",
            scenario_id=_package_segment(data.get("scenario_id"), "scenario_id"),
            domain=_string(data.get("domain"), "domain"),
            task_family=_string(data.get("task_family"), "task_family"),
            instruction=_string(data.get("instruction"), "instruction"),
            scene=SceneSourceSpec.from_mapping(data.get("scene")),
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
            _validate_parameter_references(
                predicate.parameters, object_ids, self.objects, predicate.predicate_id
            )

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
    for key in ("source_frame", "target_frame"):
        value = parameters.get(key)
        if not isinstance(value, str):
            continue
        object_id, separator, frame_id = value.rpartition(".")
        if not separator or object_id not in object_ids:
            raise ValueError(f"{owner} references unknown frame {value}")
        frame_ids = {name for name, _ in object_by_id[object_id].named_frames}
        if frame_id not in frame_ids:
            raise ValueError(f"{owner} references unknown frame {value}")
