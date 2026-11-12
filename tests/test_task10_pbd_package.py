"""Portable package integration must preserve producer bytes and clean entries."""
import json

from scripts.build_task10_pbd_package import build


def test_package_preserves_candidate_and_exposes_both_runtimes(tmp_path):
    candidate = tmp_path/'candidate'
    candidate.mkdir()
    scene = '#usda 1.0\n(defaultPrim = "World"\n metersPerUnit = 1\n upAxis = "Z")\ndef Xform "World" {}\n'
    for name in ('scene41.usda','scene45.usda','demo41.usda','demo45.usda'):
        (candidate/name).write_text(scene)
    (candidate/'manifest.json').write_text(json.dumps({'source_sha256':'a'*64,'status':'candidate'}))
    out = build(candidate,tmp_path/'package')
    assert (out/'assets/composed/scene41.usda').read_text() == scene
    assert (out/'scene/isaac45.usda').exists()
    evidence = json.loads((out/'evidence/build.json').read_text())
    assert evidence['unresolved'] == []
    assert evidence['runtime_status'] == 'not_qualified'
    assert not (out/'robot/robot.usd').exists()
