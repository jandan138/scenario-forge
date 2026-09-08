"""Finalize the single-material r1.6 scene using fresh runtime and render evidence."""
import argparse
import json
from pathlib import Path

from scripts.finalize_traditional_titration_vr_r15 import prepare as prepare_linear
from scripts.finalize_traditional_titration_vr_r1 import main as finalize


def prepare(root, reports):
    for path in reports:
        report = json.loads(path.read_text())
        if (report.get('receiver_visual_mode') != 'single_material'
                or report.get('linear_policy_checks', {}).get('single_material_persistent') is not True):
            raise ValueError('r1.6 requires single-material runtime evidence')
    prepare_linear(root, reports)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    args = parser.parse_args()
    prepare(args.root, args.report)
    argv = ['--root', str(args.root)]
    for path in args.report:
        argv.extend(['--report', str(path)])
    raise SystemExit(finalize(argv))
