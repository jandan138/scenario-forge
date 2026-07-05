from __future__ import annotations

from pathlib import Path
import re

MDL_TEXTURE_2D_RE = re.compile(r"texture_2d\(\s*\"([^\"]+)\"")
USD_MDL_ASSET_REF_RE = re.compile(rb"@([^@\r\n\x00]+?\.mdl)@", re.IGNORECASE)
USD_QUOTED_MDL_REF_RE = re.compile(rb"['\"]([^'\"\r\n\x00]+?\.mdl)['\"]", re.IGNORECASE)
USD_BARE_MDL_REF_RE = re.compile(
    rb"(?<![A-Za-z0-9_./:+-])([A-Za-z0-9_./:+-]+\.mdl)(?![A-Za-z0-9_./:+-])",
    re.IGNORECASE,
)
USD_ASSET_SUFFIXES = {".usd", ".usda", ".usdc"}


def audit_mdl_texture_closure(root: str | Path) -> dict[str, object]:
    bundle_root = Path(root)
    missing_textures: list[dict[str, str]] = []
    missing_material_refs: list[dict[str, str]] = []
    for material_path in sorted(bundle_root.rglob("*.mdl")):
        material_text = material_path.read_text(encoding="utf-8", errors="ignore")
        for texture_ref in MDL_TEXTURE_2D_RE.findall(material_text):
            if _is_external_texture_reference(texture_ref):
                continue
            texture_path = (material_path.parent / texture_ref).resolve()
            if texture_path.exists():
                continue
            missing_textures.append(
                {
                    "material": _display_path(material_path, bundle_root),
                    "texture": texture_ref,
                    "resolved_path": _display_path(texture_path, bundle_root),
                }
            )
    for usd_path in sorted(
        path for path in bundle_root.rglob("*") if path.is_file() and path.suffix.lower() in USD_ASSET_SUFFIXES
    ):
        missing_material_refs.extend(_missing_usd_material_refs(usd_path, bundle_root))
    return {
        "status": "passed" if not missing_textures and not missing_material_refs else "failed",
        "root": str(bundle_root),
        "missing_texture_count": len(missing_textures),
        "missing_textures": missing_textures,
        "missing_material_ref_count": len(missing_material_refs),
        "missing_material_refs": missing_material_refs,
    }


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _is_external_texture_reference(texture_ref: str) -> bool:
    return "://" in texture_ref or texture_ref.startswith(("/", "omniverse:", "mdl:"))


def _missing_usd_material_refs(usd_path: Path, root: Path) -> list[dict[str, str]]:
    raw = usd_path.read_bytes()
    refs: list[str] = []
    for pattern in (USD_MDL_ASSET_REF_RE, USD_QUOTED_MDL_REF_RE, USD_BARE_MDL_REF_RE):
        for raw_ref in pattern.findall(raw):
            ref = raw_ref.decode("utf-8", errors="ignore")
            if ref and ref not in refs:
                refs.append(ref)

    missing: list[dict[str, str]] = []
    for material_ref in refs:
        if _is_external_material_reference(material_ref):
            continue
        material_path = (usd_path.parent / material_ref).resolve()
        if material_path.exists():
            continue
        missing.append(
            {
                "usd": _display_path(usd_path, root),
                "material": material_ref,
                "resolved_path": _display_path(material_path, root),
            }
        )
    return missing


def _is_external_material_reference(material_ref: str) -> bool:
    return "://" in material_ref or material_ref.startswith(("/", "omniverse:", "mdl:"))
