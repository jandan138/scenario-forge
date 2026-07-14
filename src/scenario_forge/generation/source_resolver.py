from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from scenario_forge.adapters.convert_asset import load_convert_asset_package_handoff
from scenario_forge.assets.source import LocalUSDAssetSource


SOURCE_BINDINGS_SCHEMA_VERSION = "scenario-source-bindings/v0.2"
SUPPORTED_SOURCE_BINDINGS_SCHEMA_VERSIONS = frozenset(
    {"scenario-source-bindings/v0.1", SOURCE_BINDINGS_SCHEMA_VERSION}
)
_TOP_LEVEL_FIELDS = frozenset({"schema_version", "bindings"})
_LOCAL_USD_FIELDS = frozenset(
    {
        "resolver",
        "source_usd",
        "role",
        "license",
        "source_uri",
        "attribution",
        "redistributable",
        "exclude_relative_paths",
        "root_prim_path",
        "expected_sha256",
    }
)
_CONVERT_ASSET_FIELDS = frozenset(
    {
        "resolver",
        "source_usd",
        "package_dir",
        "manifest_path",
        "producer_revision",
        "expected_scope_prims",
        "license",
        "attribution",
        "redistributable",
        "exclude_relative_paths",
        "expected_consumer_profile",
        "expected_runtime_profile",
    }
)
_CONVERT_ASSET_V02_FIELDS = _CONVERT_ASSET_FIELDS | {"usage"}


class ScenarioSourceBindingError(ValueError):
    """Raised when local build inputs cannot be mapped to asset sources."""


def resolve_scenario_source_bindings(
    bindings_path: str | Path,
) -> dict[str, LocalUSDAssetSource]:
    """Resolve an external source-binding file into compiler asset sources.

    Paths are local build inputs and resolve relative to the binding file. They
    are intentionally separate from the portable ScenarioSpec.
    """

    path = Path(bindings_path)
    try:
        raw_data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScenarioSourceBindingError(
            f"cannot read scenario source bindings: {path}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ScenarioSourceBindingError(
            f"scenario source bindings are not valid YAML: {path}"
        ) from exc

    data = _mapping(raw_data, "source bindings")
    _reject_unknown_fields(data, _TOP_LEVEL_FIELDS, "source bindings")
    schema_version = _required_string(data, "schema_version", "source bindings")
    if schema_version not in SUPPORTED_SOURCE_BINDINGS_SCHEMA_VERSIONS:
        raise ScenarioSourceBindingError(
            "unsupported source bindings schema_version "
            f"{schema_version!r}; expected one of "
            f"{sorted(SUPPORTED_SOURCE_BINDINGS_SCHEMA_VERSIONS)!r}"
        )

    raw_bindings = _mapping(data.get("bindings"), "source bindings.bindings")
    if not raw_bindings:
        raise ScenarioSourceBindingError("source bindings.bindings must not be empty")

    base_dir = path.parent.resolve()
    sources: dict[str, LocalUSDAssetSource] = {}
    for raw_asset_id, raw_binding in raw_bindings.items():
        if not isinstance(raw_asset_id, str) or not raw_asset_id:
            raise ScenarioSourceBindingError(
                "source bindings.bindings keys must be non-empty asset ids"
            )
        field = f"source bindings.bindings.{raw_asset_id}"
        binding = _mapping(raw_binding, field)
        resolver = _required_string(binding, "resolver", field)
        try:
            if resolver == "local_usd":
                _reject_unknown_fields(binding, _LOCAL_USD_FIELDS, field)
                source = _resolve_local_usd(raw_asset_id, binding, base_dir, field)
            elif resolver == "convert_asset_package":
                _reject_unknown_fields(
                    binding,
                    (
                        _CONVERT_ASSET_V02_FIELDS
                        if schema_version == SOURCE_BINDINGS_SCHEMA_VERSION
                        else _CONVERT_ASSET_FIELDS
                    ),
                    field,
                )
                source = _resolve_convert_asset_package(
                    raw_asset_id,
                    binding,
                    base_dir,
                    field,
                    usage=(
                        _required_usage(binding, field)
                        if schema_version == SOURCE_BINDINGS_SCHEMA_VERSION
                        else "scene_overlay"
                    ),
                )
            else:
                raise ScenarioSourceBindingError(
                    f"{field}.resolver has unsupported value {resolver!r}"
                )
        except ScenarioSourceBindingError:
            raise
        except ValueError as exc:
            raise ScenarioSourceBindingError(f"{field}: {exc}") from exc
        sources[raw_asset_id] = source
    return sources


def _resolve_local_usd(
    asset_id: str,
    binding: Mapping[str, Any],
    base_dir: Path,
    field: str,
) -> LocalUSDAssetSource:
    return LocalUSDAssetSource(
        asset_id=asset_id,
        source_usd=_local_path(binding, "source_usd", base_dir, field),
        role=_required_string(binding, "role", field),
        license=_required_string(binding, "license", field),
        source_uri=_required_string(binding, "source_uri", field),
        attribution=_string_tuple(binding.get("attribution", []), f"{field}.attribution"),
        redistributable=_boolean(
            binding.get("redistributable", True),
            f"{field}.redistributable",
        ),
        exclude_relative_paths=_string_tuple(
            binding.get("exclude_relative_paths", []),
            f"{field}.exclude_relative_paths",
        ),
        root_prim_path=_optional_string(
            binding.get("root_prim_path"),
            f"{field}.root_prim_path",
        ),
        expected_sha256=_optional_string(
            binding.get("expected_sha256"),
            f"{field}.expected_sha256",
        ),
    )


def _resolve_convert_asset_package(
    asset_id: str,
    binding: Mapping[str, Any],
    base_dir: Path,
    field: str,
    usage: str,
) -> LocalUSDAssetSource:
    handoff = load_convert_asset_package_handoff(
        _local_path(binding, "package_dir", base_dir, field),
        _local_path(binding, "manifest_path", base_dir, field),
        _local_path(binding, "source_usd", base_dir, field),
        expected_scope_prims=_nonempty_string_tuple(
            binding.get("expected_scope_prims"),
            f"{field}.expected_scope_prims",
        ),
        producer_revision=_required_string(binding, "producer_revision", field),
        expected_consumer_profile=_optional_string(
            binding.get("expected_consumer_profile"),
            f"{field}.expected_consumer_profile",
        )
        or "scenario-forge",
        expected_runtime_profile=_optional_string(
            binding.get("expected_runtime_profile"),
            f"{field}.expected_runtime_profile",
        )
        or "isaac41",
        usage=usage,
    )
    return handoff.to_local_usd_asset_source(
        asset_id=asset_id,
        license=_required_string(binding, "license", field),
        attribution=_string_tuple(binding.get("attribution", []), f"{field}.attribution"),
        redistributable=_boolean(
            binding.get("redistributable", False),
            f"{field}.redistributable",
        ),
        exclude_relative_paths=_string_tuple(
            binding.get("exclude_relative_paths", []),
            f"{field}.exclude_relative_paths",
        ),
    )


def _required_usage(data: Mapping[str, Any], field: str) -> str:
    usage = _required_string(data, "usage", field)
    if usage not in {"scene_overlay", "rigid_object"}:
        raise ScenarioSourceBindingError(
            f"{field}.usage must be 'scene_overlay' or 'rigid_object'"
        )
    return usage


def _local_path(
    data: Mapping[str, Any],
    key: str,
    base_dir: Path,
    field: str,
) -> Path:
    raw_path = _required_string(data, key, field)
    candidate = Path(raw_path)
    return candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ScenarioSourceBindingError(f"{field} must be a mapping")
    return value


def _reject_unknown_fields(
    data: Mapping[str, Any],
    allowed: frozenset[str],
    field: str,
) -> None:
    unexpected = sorted(
        key if isinstance(key, str) else repr(key)
        for key in data
        if key not in allowed
    )
    if unexpected:
        raise ScenarioSourceBindingError(
            f"{field} contains unexpected field(s): {', '.join(unexpected)}"
        )


def _required_string(data: Mapping[str, Any], key: str, field: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ScenarioSourceBindingError(f"{field}.{key} must be a non-empty string")
    return value


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ScenarioSourceBindingError(f"{field} must be a non-empty string")
    return value


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ScenarioSourceBindingError(f"{field} must be a list of non-empty strings")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise ScenarioSourceBindingError(f"{field} entries must be unique")
    return result


def _nonempty_string_tuple(value: object, field: str) -> tuple[str, ...]:
    result = _string_tuple(value, field)
    if not result:
        raise ScenarioSourceBindingError(f"{field} must not be empty")
    return result


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ScenarioSourceBindingError(f"{field} must be a boolean")
    return value
