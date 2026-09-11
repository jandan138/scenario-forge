"""Finalize r5 exact-scene cold starts, material replay, visual review and closure."""
import argparse
from pathlib import Path

from scripts.fehlings_r5_state import POLICY_VERSION
from scripts.finalize_fehlings_water_bath import main as finalize
from scripts.finalize_fehlings_water_bath_r3 import prepare


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    args = parser.parse_args()
    prepare(args.root, args.report, policy_version=POLICY_VERSION)
    finalize()
