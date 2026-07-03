from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def write_yaml_artifact(path: str | Path, data: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return output_path
