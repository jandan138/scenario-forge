from __future__ import annotations


def validate_license(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "Missing license"
    return None
