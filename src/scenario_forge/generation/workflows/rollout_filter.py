from __future__ import annotations


def workflow_static_findings(
    required_asset_roles: tuple[str, ...],
    predicate_count: int,
) -> tuple[dict[str, str], ...]:
    findings: list[dict[str, str]] = []
    findings.append(
        {
            "name": "required_assets_declared",
            "status": "passed" if required_asset_roles else "failed",
        }
    )
    findings.append(
        {
            "name": "success_predicates_declared",
            "status": "passed" if predicate_count > 0 else "failed",
        }
    )
    return tuple(findings)
