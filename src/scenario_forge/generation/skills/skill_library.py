from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class SkillLibraryError(ValueError):
    """Raised when a domain skill library is missing or malformed."""


@dataclass(frozen=True)
class AtomicSkill:
    skill_id: str
    required_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class SkillLibrary:
    domain: str
    skills: dict[str, AtomicSkill]
    robot_capabilities: dict[str, tuple[str, ...]]

    def required_capabilities_for_skills(self, skill_ids: tuple[str, ...]) -> tuple[str, ...]:
        required: set[str] = set()
        missing: list[str] = []
        for skill_id in skill_ids:
            skill = self.skills.get(skill_id)
            if skill is None:
                missing.append(skill_id)
                continue
            required.update(skill.required_capabilities)
        if missing:
            raise SkillLibraryError(f"Unknown atomic skills: {', '.join(sorted(missing))}")
        return tuple(sorted(required))

    def missing_robot_capabilities(
        self, robot_profile: str, required_capabilities: tuple[str, ...]
    ) -> tuple[str, ...]:
        robot_capabilities = self.robot_capabilities.get(robot_profile)
        if robot_capabilities is None:
            raise SkillLibraryError(f"Unknown robot profile: {robot_profile}")
        available = set(robot_capabilities)
        return tuple(capability for capability in required_capabilities if capability not in available)


def default_domain_pack_dir(domain: str = "scientific_workbench") -> Path:
    return Path(__file__).resolve().parents[4] / "configs" / "domain_packs" / domain


def load_skill_library(domain_pack_dir: str | Path | None = None) -> SkillLibrary:
    pack_dir = Path(domain_pack_dir) if domain_pack_dir is not None else default_domain_pack_dir()
    path = pack_dir / "atomic_skills.yaml"
    if not path.exists():
        raise SkillLibraryError(f"Missing atomic skills file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SkillLibraryError(f"Atomic skills file must be a mapping: {path}")
    if data.get("schema_version") != "atomic-skills/v0.1":
        raise SkillLibraryError("Unsupported atomic skills schema_version")

    raw_skills = data.get("skills")
    if not isinstance(raw_skills, dict):
        raise SkillLibraryError("Atomic skills field 'skills' must be a mapping")
    skills: dict[str, AtomicSkill] = {}
    for skill_id, raw_skill in raw_skills.items():
        if not isinstance(skill_id, str) or not isinstance(raw_skill, dict):
            raise SkillLibraryError("Each atomic skill entry must be a mapping")
        skills[skill_id] = AtomicSkill(
            skill_id=skill_id,
            required_capabilities=_string_tuple(raw_skill, "required_capabilities"),
        )

    raw_profiles = data.get("robot_profiles")
    if not isinstance(raw_profiles, dict):
        raise SkillLibraryError("Atomic skills field 'robot_profiles' must be a mapping")
    robot_capabilities: dict[str, tuple[str, ...]] = {}
    for profile_id, raw_profile in raw_profiles.items():
        if not isinstance(profile_id, str) or not isinstance(raw_profile, dict):
            raise SkillLibraryError("Each robot profile entry must be a mapping")
        robot_capabilities[profile_id] = _string_tuple(raw_profile, "capabilities")

    domain = data.get("domain", "unknown")
    if not isinstance(domain, str):
        raise SkillLibraryError("Atomic skills field 'domain' must be a string")
    return SkillLibrary(domain=domain, skills=skills, robot_capabilities=robot_capabilities)


def _string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SkillLibraryError(f"Atomic skills field {key!r} must be a list of strings")
    return tuple(value)
