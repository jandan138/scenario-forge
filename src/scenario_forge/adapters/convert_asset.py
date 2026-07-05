from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConvertAssetCommandPlan:
    """A dry command plan for invoking ConvertAsset from an outer workflow."""

    convert_asset_root: str
    input_usd: str
    output_usd: str
    operations: tuple[str, ...]

    def commands(self) -> tuple[tuple[str, ...], ...]:
        root = Path(self.convert_asset_root)
        wrapper = str(root / "scripts" / "isaac_python.sh")
        main = str(root / "main.py")

        commands: list[tuple[str, ...]] = []
        current_input = self.input_usd
        for operation in self.operations:
            if operation == "no-mdl":
                commands.append((wrapper, main, "no-mdl", current_input))
                current_input = self.output_usd
            elif operation == "mesh-faces":
                commands.append((wrapper, main, "mesh-faces", current_input))
            else:
                raise ValueError(f"Unsupported ConvertAsset operation: {operation}")
        return tuple(commands)


@dataclass(frozen=True)
class NormalizeAssetCommandPlan:
    """A dry command plan for ConvertAsset's package-level normalization CLI."""

    convert_asset_root: str
    source_usd: str
    package_dir: str

    def command(self) -> tuple[str, ...]:
        root = Path(self.convert_asset_root)
        return (
            str(root / "scripts" / "isaac_python.sh"),
            str(root / "main.py"),
            "normalize-asset",
            self.source_usd,
            "--package-dir",
            self.package_dir,
        )
