#!/usr/bin/env python3
"""Compile native source-bound EBench intervention cells without running episodes."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scenario_forge.adapters.ebench.intervention_suite import compile_suite, install_suite  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--install-genmanip-root", type=Path)
    args = parser.parse_args()
    if args.install_genmanip_root:
        result = install_suite(args.output.resolve(), args.install_genmanip_root.resolve())
        print(json.dumps({"installed": len(result["installed"]), "runtime_validated": False}))
    else:
        if args.config is None:
            parser.error("--config is required for compilation")
        result = compile_suite(json.loads(args.config.read_text()), args.output.resolve())
        print(json.dumps({"cells": len(result["cells"]), "status": result["status"]}))


if __name__ == "__main__":
    main()
