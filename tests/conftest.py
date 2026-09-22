"""Managed-environment fixtures; portable tests do not activate these sources."""
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import re

import pytest


@pytest.fixture(scope="module")
def verified_colleague_inputs():
    """Use retained identical inputs if the original shared mount is unavailable.

    This changes only test-local generator constants. Neither source files nor
    production generator defaults are rewritten, and a hash mismatch is a failure.
    """
    @contextmanager
    def bind(generator, original_handoff_manifest):
        root = Path(__file__).resolve().parents[1]
        with pytest.MonkeyPatch.context() as patch:
            for name in vars(generator):
                match = re.fullmatch(r"TASK(\d+)_SCENE", name)
                if not match:
                    continue
                original = getattr(generator, name)
                if original.is_file():
                    continue
                hashes = json.loads(original_handoff_manifest.read_text())["source_hashes"]
                expected = hashes[f"task{match[1]}_scene"].removeprefix("sha256:")
                task = original.parent.parent.name
                retained = (
                    root / "outputs/scientific_experiments_colleague_final_20260920/packages"
                    / task / "assets/composed/seen_scene_01/scene.usd"
                )
                assert retained.is_file(), f"Missing retained source: {retained}"
                actual = sha256(retained.read_bytes()).hexdigest()
                assert actual == expected, f"Retained source hash mismatch: {retained}"
                patch.setattr(generator, name, retained)
            yield
    return bind
