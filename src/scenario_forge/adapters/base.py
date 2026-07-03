from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class AdapterIssue:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class AdapterExportResult:
    adapter_name: str
    output_dir: Path
    artifacts: tuple[Path, ...]
    issues: tuple[AdapterIssue, ...] = ()


class SimulatorAdapter(Protocol):
    name: str

    def validate_capabilities(self, package_dir: Path) -> tuple[AdapterIssue, ...]:
        """Return adapter-specific blockers without mutating the portable package."""

    def export(self, package_dir: Path, out_dir: Path) -> AdapterExportResult:
        """Write simulator-specific artifacts under out_dir."""
